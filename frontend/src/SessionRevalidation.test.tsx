import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { api, ApiError, type Session } from './api';
import { useSession } from './hooks/useSession';
import { NAVIGATION_KEY } from './hooks/useDiscoveryNavigation';
import { expectPublicNavigationOnly } from './test/navigationAssertions';
import { failure, H1, H2, hackathon, I1, invitation, json, session, T1, T2, team, U1 } from './test/fixtures';

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

type Handler = (url: string, options: RequestInit) => Response | Promise<Response> | undefined;
function server(handler: Handler = () => undefined) {
  const identity = session();
  const fetch = vi.fn((url: string, options: RequestInit) => {
    const custom = handler(url, options); if (custom) return Promise.resolve(custom);
    if (url === '/auth/session') return Promise.resolve(json(identity));
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon()], next_cursor: H1 }));
    if (url === '/api/hackathons?limit=20&cursor=' + H1) return Promise.resolve(json({ items: [hackathon(H2)], next_cursor: null }));
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: null }));
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: [team()], next_cursor: T1 }));
    if (url.endsWith('/teams?limit=20&cursor=' + T1)) return Promise.resolve(json({ items: [team(T2)], next_cursor: null }));
    if (url.endsWith('/invitations/mine?limit=20')) return Promise.resolve(json({ items: [invitation()], next_cursor: I1 }));
    if (url.endsWith('/invitations/mine?limit=20&cursor=' + I1)) return Promise.resolve(json({ items: [], next_cursor: null }));
    if (url === '/api/me/profile') return Promise.resolve(json({ ...identity.identity, display_name: 'Builder', skills: [], timezone: null, discoverable: false, version: 1 }));
    throw new Error('Unexpected offline URL');
  });
  vi.stubGlobal('fetch', fetch);
  return { fetch, identity };
}
async function choose() {
  fireEvent.click(await screen.findByRole('button', { name: /Test Challenge/ }));
  await screen.findByRole('heading', { name: 'Test Team Alpha' });
}
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

it('keeps the same authenticated DOM and unsaved draft during a valid focus check', async () => {
  const identity = session();
  let finish!: (reply: Response) => void, checks = 0;
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url === '/auth/session') return ++checks === 1 ? Promise.resolve(json(identity))
      : new Promise<Response>(resolve => { finish = resolve; });
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon()], next_cursor: null }));
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: null }));
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: [team()], next_cursor: null }));
    throw new Error('Unexpected offline URL');
  }));
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: /Test Challenge/ }));
  await screen.findByRole('heading', { name: 'Test Team Alpha' });
  const workspace = screen.getByRole('region', { name: 'Team workspace' });
  const draft = within(workspace).getByLabelText('Team name') as HTMLInputElement;
  fireEvent.change(draft, { target: { value: 'Unsaved team draft' } });
  fireEvent(window, new Event('focus'));
  expect(workspace.isConnected).toBe(true);
  expect(screen.queryByText('Restoring your session...')).toBeNull();
  await act(async () => finish(json(identity)));
  await waitFor(() => expect(checks).toBe(2));
  expect(screen.getByRole('region', { name: 'Team workspace' })).toBe(workspace);
  expect(screen.getByLabelText('Team name')).toBe(draft);
  expect(draft.value).toBe('Unsaved team draft');
});

it.each(['visible', 'pageshow', 'screenshot', 'minimize'])('preserves mounted UI and local draft on %s return', async kind => {
  const reply = deferred<Response>(); let hold = false;
  const { fetch, identity } = server(url => url === '/auth/session' && hold ? reply.promise : undefined);
  render(<App />); await choose();
  const workspace = screen.getByRole('region', { name: 'Team workspace' });
  const input = screen.getByLabelText('Team name') as HTMLInputElement;
  fireEvent.change(input, { target: { value: 'Retained draft' } });
  const reads = fetch.mock.calls.filter(([url]) => url !== '/auth/session').length;
  let visibility = 'visible'; vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => visibility as DocumentVisibilityState);
  hold = true;
  if (kind === 'minimize') {
    visibility = 'hidden'; fireEvent(document, new Event('visibilitychange')); fireEvent(window, new Event('blur'));
    expect(fetch.mock.calls.filter(([url]) => url === '/auth/session')).toHaveLength(1);
    visibility = 'visible'; fireEvent(document, new Event('visibilitychange')); fireEvent(window, new Event('focus'));
  } else if (kind === 'visible') fireEvent(document, new Event('visibilitychange'));
  else if (kind === 'screenshot') { fireEvent(window, new Event('blur')); fireEvent(window, new Event('focus')); }
  else fireEvent(window, new Event('pageshow'));
  expect(workspace.isConnected).toBe(true); expect(input.isConnected).toBe(true);
  expect(screen.queryByText('Restoring your session...')).toBeNull();
  hold = false; await act(async () => reply.resolve(json(identity)));
  expect(screen.getByRole('region', { name: 'Team workspace' })).toBe(workspace);
  expect(screen.getByLabelText('Team name')).toBe(input); expect(input.value).toBe('Retained draft');
  expect(fetch.mock.calls.filter(([url]) => url !== '/auth/session')).toHaveLength(reads);
  expect(fetch.mock.calls.every(([, o]) => !o.method || o.method === 'GET')).toBe(true);
});

it.each(['mine', 'invitations'])('retains selection, public pagination and %s local view state', async view => {
  server(); render(<App />); await choose();
  const workspace = within(screen.getByRole('region', { name: 'Team workspace' }));
  const catalog = within(screen.getByRole('complementary', { name: 'Hackathons' }));
  fireEvent.click(workspace.getByRole('button', { name: /Next page/ }));
  await screen.findByRole('heading', { name: 'Test Team Beta' });
  fireEvent.click(catalog.getByRole('button', { name: /Next page/ }));
  await catalog.findByRole('button', { name: /Second Challenge/ });
  fireEvent.click(screen.getByRole('button', { name: view === 'mine' ? 'My team' : 'Invitations' }));
  if (view === 'invitations') {
    fireEvent.click(await screen.findByRole('button', { name: 'Next invitations' }));
    await screen.findByText('No invitations on this page.');
  } else await screen.findByText('Your current membership in Test Challenge.');
  const active = screen.getByRole('button', { name: view === 'mine' ? 'My team' : 'Invitations' });
  const previous = view === 'invitations' ? screen.getByRole('button', { name: 'Previous invitations' }) : null;
  await act(async () => fireEvent(window, new Event('focus')));
  expect(active.getAttribute('aria-current')).toBe('page'); expect(active.isConnected).toBe(true);
  if (previous) {
    expect(screen.getByRole('button', { name: 'Previous invitations' })).toBe(previous);
    expect(previous.matches(':disabled')).toBe(false);
    expect(screen.getByText('No invitations on this page.')).toBeTruthy();
  }
  expect(JSON.parse(sessionStorage.getItem(NAVIGATION_KEY)!).value).toMatchObject({ hackathon: H1, view, teams: [null, T1], catalog: [null, H1] });
});

it('preserves an open profile editor and its unsaved fields after a 200 check', async () => {
  server(); render(<App />); await choose();
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  const skills = await screen.findByLabelText('Skills') as HTMLInputElement;
  fireEvent.change(skills, { target: { value: 'python, react' } });
  await act(async () => fireEvent(window, new Event('focus')));
  expect(screen.getByLabelText('Skills')).toBe(skills); expect(skills.value).toBe('python, react');
});

it.each([401, 403, 503])('hides protected content and closes the scope when background validation returns %s', async status => {
  let deny = false; const reply = deferred<Response>();
  server(url => deny && url === '/auth/session' ? reply.promise : undefined);
  render(<App />); await choose(); const workspace = screen.getByRole('region', { name: 'Team workspace' });
  deny = true; fireEvent(window, new Event('focus')); expect(workspace.isConnected).toBe(true);
  await act(async () => reply.resolve(failure(status)));
  expect(workspace.isConnected).toBe(false); expect(screen.queryByText('@test_builder')).toBeNull();
  if (status === 401) expect(screen.getByLabelText('Username')).toBeTruthy();
  else expect(screen.getByRole('heading', { name: 'Let us reconnect.' })).toBeTruthy();
});

it('coalesces rapid events into a single trailing check and ignores its superseded identity result', async () => {
  const identity = session(), first = deferred<Session>(), latest = deferred<Session>();
  const get = vi.spyOn(api, 'session').mockResolvedValueOnce(identity).mockReturnValueOnce(first.promise).mockReturnValueOnce(latest.promise);
  const { result } = renderHook(() => useSession());
  await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
  const before = result.current.state;
  act(() => { for (let i = 0; i < 20; i++) { fireEvent(window, new Event('focus')); fireEvent(window, new Event('pageshow')); } });
  expect(get).toHaveBeenCalledTimes(2); expect(result.current.state).toBe(before);
  await act(async () => first.resolve({ ...identity, identity: { user_id: T2, username: 'obsolete_identity' } }));
  expect(get).toHaveBeenCalledTimes(3); expect(result.current.state).toBe(before);
  await act(async () => latest.resolve(identity));
  expect(result.current.state.status).toBe('authenticated');
  if (before.status !== 'authenticated' || result.current.state.status !== 'authenticated') throw new Error();
  expect(result.current.state.epoch).toBe(before.epoch); expect(result.current.state.signal).toBe(before.signal);
  expect(before.signal.aborted).toBe(false);
});

it.each([200, 401, 403])('ignores a late background %s after explicit logout', async status => {
  const identity = session(), pending = deferred<Session>();
  vi.spyOn(api, 'session').mockResolvedValueOnce(identity).mockReturnValueOnce(pending.promise);
  const signout = vi.spyOn(api, 'logout').mockResolvedValue(undefined);
  const { result } = renderHook(() => useSession());
  await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
  const old = result.current.state; if (old.status !== 'authenticated') throw new Error();
  act(() => fireEvent(window, new Event('focus')));
  act(() => result.current.logout(identity));
  expect(old.signal.aborted).toBe(true); expect(result.current.state.status).toBe('ending');
  await act(async () => { if (status === 200) pending.resolve(identity); else pending.reject(new ApiError(status)); });
  expect(result.current.state.status).toBe('guest'); expect(signout).toHaveBeenCalledOnce();
});

it.each([200, 401, 403])('isolates late background %s from a subsequently authenticated account', async status => {
  const identity = session(), pending = deferred<Session>();
  vi.spyOn(api, 'session').mockResolvedValueOnce(identity).mockReturnValueOnce(pending.promise);
  const { result } = renderHook(() => useSession());
  await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
  const old = result.current.state; if (old.status !== 'authenticated') throw new Error();
  act(() => fireEvent(window, new Event('focus')));
  const replacement = { ...identity, identity: { user_id: T2, username: 'new_account' } };
  act(() => result.current.accept(replacement));
  await act(async () => { if (status === 200) pending.resolve(identity); else pending.reject(new ApiError(status)); });
  expect(old.signal.aborted).toBe(true);
  expect(result.current.state.status === 'authenticated' && result.current.state.session.identity).toEqual(replacement.identity);
});

it.each(['account', 'credentials', 'expiry'])('rotates the scope on validated %s replacement', async kind => {
  const identity = session();
  const replacement = { ...identity, ...(kind === 'account' ? { identity: { user_id: T2, username: 'new_account' } }
    : kind === 'credentials' ? { csrf_token: 'B'.repeat(43) } : { expires_at: new Date(Date.parse(identity.expires_at) + 1000).toISOString() }) };
  vi.spyOn(api, 'session').mockResolvedValueOnce(identity).mockResolvedValueOnce(replacement);
  const { result } = renderHook(() => useSession());
  await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
  const old = result.current.state; if (old.status !== 'authenticated') throw new Error();
  await act(async () => fireEvent(window, new Event('focus')));
  expect(old.signal.aborted).toBe(true);
  if (result.current.state.status !== 'authenticated') throw new Error();
  expect(result.current.state.epoch).not.toBe(old.epoch); expect(result.current.state.session).toBe(replacement);
});

it('keeps explicit session recovery blocking and ignores an old check which finishes afterwards', async () => {
  const identity = session(), pending = deferred<Session>(), latest = deferred<Session>();
  vi.spyOn(api, 'session').mockResolvedValueOnce(identity).mockReturnValueOnce(pending.promise).mockReturnValueOnce(latest.promise);
  const { result } = renderHook(() => useSession());
  await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
  const old = result.current.state; if (old.status !== 'authenticated') throw new Error();
  act(() => fireEvent(window, new Event('focus'))); act(() => result.current.restore());
  expect(result.current.state.status).toBe('checking'); expect(old.signal.aborted).toBe(true);
  await act(async () => latest.resolve(identity));
  const restored = result.current.state;
  await act(async () => pending.reject(new ApiError(401)));
  expect(result.current.state).toBe(restored);
});

it('expires at the advertised deadline even when background validation never completes', async () => {
  vi.useFakeTimers(); const identity = { ...session(), expires_at: new Date(Date.now() + 1000).toISOString() };
  const pending = deferred<Session>();
  vi.spyOn(api, 'session').mockResolvedValueOnce(identity).mockReturnValueOnce(pending.promise);
  const { result } = renderHook(() => useSession());
  await act(async () => vi.advanceTimersByTimeAsync(0));
  const old = result.current.state; if (old.status !== 'authenticated') throw new Error();
  act(() => fireEvent(window, new Event('focus')));
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(result.current.state.status).toBe('guest'); expect(old.signal.aborted).toBe(true);
  await act(async () => pending.resolve(identity)); expect(result.current.state.status).toBe('guest');
});

it('does not replay a pending or uncertain creation on foreground return or persist its journal', async () => {
  const pending = deferred<Response>(), storage = vi.spyOn(Storage.prototype, 'setItem');
  const { fetch, identity } = server((url, options) => options.method === 'POST' && url.endsWith('/teams') ? pending.promise : undefined);
  render(<App />); await choose();
  fireEvent.change(screen.getByLabelText('Team name'), { target: { value: 'Private command draft' } });
  fireEvent.click(screen.getByRole('button', { name: 'Create team' }));
  const signal = fetch.mock.calls.find(([, o]) => o.method === 'POST')![1].signal!;
  const key = (fetch.mock.calls.find(([, o]) => o.method === 'POST')![1].headers as Record<string, string>)['Idempotency-Key'];
  await act(async () => fireEvent(window, new Event('focus')));
  expect(signal.aborted).toBe(false); expect(screen.getByRole('button', { name: 'Creating team…' })).toBeTruthy();
  await act(async () => pending.reject(new Error('Synthetic ambiguous delivery')));
  const retry = screen.getByRole('button', { name: 'Retry original request' });
  await act(async () => fireEvent(window, new Event('focus')));
  expect(screen.getByRole('button', { name: 'Retry original request' })).toBe(retry);
  expect(fetch.mock.calls.filter(([, o]) => o.method === 'POST')).toHaveLength(1);
  expectPublicNavigationOnly(storage, key, identity.csrf_token, 'Private command draft');
  expect(JSON.stringify(window.history.state)).not.toContain(key);
});

it('keeps the active SSE stream on focus, then reconnects and refetches canonical data without replacing the view', async () => {
  class Source {
    static all: Source[] = [];
    listeners = new Map<string, EventListener>(); onerror: (() => void) | null = null;
    close = vi.fn();
    constructor(public url: string) { Source.all.push(this); }
    addEventListener(kind: string, listener: EventListener) { this.listeners.set(kind, listener); }
    reset() { this.listeners.get('reset')?.(new MessageEvent('reset', { lastEventId: 'a'.repeat(64),
      data: JSON.stringify({ schema_version: 1, hackathon_id: H1, user_id: U1 }) })); }
  }
  vi.stubGlobal('EventSource', Source);
  const { fetch } = server(); render(<App />); await choose();
  const workspace = screen.getByRole('region', { name: 'Team workspace' });
  const input = screen.getByLabelText('Team name') as HTMLInputElement;
  fireEvent.change(input, { target: { value: 'Keep through reconnect' } });
  const first = Source.all[0];
  await act(async () => fireEvent(window, new Event('focus')));
  expect(Source.all).toHaveLength(1); expect(first.close).not.toHaveBeenCalled();
  vi.useFakeTimers();
  act(() => first.onerror?.());
  await act(async () => vi.advanceTimersByTimeAsync(2000));
  expect(first.close).toHaveBeenCalled(); expect(Source.all).toHaveLength(2);
  const reads = fetch.mock.calls.filter(([url]) => url.endsWith('/teams?limit=20')).length;
  await act(async () => Source.all[1].reset());
  expect(fetch.mock.calls.filter(([url]) => url.endsWith('/teams?limit=20'))).toHaveLength(reads + 1);
  expect(screen.getByRole('region', { name: 'Team workspace' })).toBe(workspace);
  expect(screen.getByLabelText('Team name')).toBe(input); expect(input.value).toBe('Keep through reconnect');
  expect(fetch.mock.calls.every(([, o]) => !o.method || o.method === 'GET')).toBe(true);
});

it('hides the workspace when a background 200 advertises an already-expired session', async () => {
  const identity = session();
  vi.spyOn(api, 'session').mockResolvedValueOnce(identity).mockResolvedValueOnce({ ...identity, expires_at: '2000-01-01T00:00:00Z' });
  const { result } = renderHook(() => useSession());
  await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
  const old = result.current.state; if (old.status !== 'authenticated') throw new Error();
  await act(async () => fireEvent(window, new Event('focus')));
  expect(result.current.state.status).toBe('guest'); expect(old.signal.aborted).toBe(true);
});

it('keeps guest bootstrap private and does not auto-retry authentication on lifecycle events', async () => {
  const get = vi.spyOn(api, 'session').mockRejectedValue(new ApiError(401));
  const { result } = renderHook(() => useSession());
  expect(result.current.state.status).toBe('checking');
  await waitFor(() => expect(result.current.state.status).toBe('guest'));
  act(() => { fireEvent(window, new Event('focus')); fireEvent(window, new Event('pageshow')); fireEvent(document, new Event('visibilitychange')); });
  expect(get).toHaveBeenCalledOnce(); expect(result.current.state.status).toBe('guest');
});

it('checks absolute expiry synchronously on return from a suspended browser before its timer fires', async () => {
  vi.useFakeTimers(); const identity = { ...session(), expires_at: new Date(Date.now() + 1000).toISOString() };
  const get = vi.spyOn(api, 'session').mockResolvedValue(identity);
  const { result } = renderHook(() => useSession());
  await act(async () => vi.advanceTimersByTimeAsync(0));
  const before = result.current.state; if (before.status !== 'authenticated') throw new Error();
  vi.setSystemTime(Date.now() + 2000); // Browser suspension: no timer execution.
  act(() => fireEvent(window, new Event('focus')));
  expect(result.current.state.status).toBe('guest'); expect(before.signal.aborted).toBe(true);
  expect(get).toHaveBeenCalledOnce();
});

it.each([401, 403])('never conceals a current-scope %s denial behind queued focus events', async status => {
  const identity = session(), pending = deferred<Session>();
  const get = vi.spyOn(api, 'session').mockResolvedValueOnce(identity).mockReturnValueOnce(pending.promise);
  const { result } = renderHook(() => useSession());
  await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
  const old = result.current.state; if (old.status !== 'authenticated') throw new Error();
  act(() => { fireEvent(window, new Event('focus')); fireEvent(window, new Event('pageshow')); });
  expect(get).toHaveBeenCalledTimes(2);
  await act(async () => pending.reject(new ApiError(status)));
  expect(result.current.state.status).toBe(status === 401 ? 'guest' : 'error');
  expect(old.signal.aborted).toBe(true); expect(get).toHaveBeenCalledTimes(2);
});
