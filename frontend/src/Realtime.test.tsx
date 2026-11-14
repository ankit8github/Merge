import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useLayoutEffect } from 'react';
import App from './App';
import { api, ApiError } from './api';
import { ReadInvalidation, useRealtime } from './hooks/useRealtime';
import { useRead } from './hooks/useRead';
import { H1, H2, U1, T1, json, failure, session, hackathon, team } from './test/fixtures';

class Source {
  static all: Source[] = [];
  listeners = new Map<string, EventListener>();
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) { Source.all.push(this); }
  addEventListener(kind: string, listener: EventListener) { this.listeners.set(kind, listener); }
  emit(kind: string, id = 'a'.repeat(64), h = H1, actor = U1) {
    this.listeners.get(kind)?.(new MessageEvent(kind, { lastEventId: id,
      data: JSON.stringify({ schema_version: 1, hackathon_id: h, user_id: actor }) }));
  }
}
beforeEach(() => { Source.all = []; vi.stubGlobal('EventSource', Source); });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it('opens a same-origin active-workspace stream and deduplicates invalidations but always refetches on reset', () => {
  const signal = new AbortController().signal, expired = vi.fn();
  const { result, unmount } = renderHook(() => useRealtime(H1, U1, signal, expired));
  const source = Source.all[0]; expect(source.url).toBe(`/api/hackathons/${H1}/events`);
  act(() => source.emit('reset')); expect(result.current.revision).toBe(1);
  act(() => source.emit('invalidate')); expect(result.current.revision).toBe(1);
  act(() => source.emit('invalidate', 'b'.repeat(64))); expect(result.current.revision).toBe(2);
  act(() => source.emit('reset', 'b'.repeat(64))); expect(result.current.revision).toBe(3);
  expect(result.current.status).toBe('connected'); expect(expired).not.toHaveBeenCalled();
  expect(sessionStorage.length).toBe(0); unmount(); expect(source.close).toHaveBeenCalled();
});

it('closes old hackathon and identity subscriptions and ignores their queued callbacks', () => {
  const signal = new AbortController().signal, expired = vi.fn();
  const { result, rerender } = renderHook(({ h, actor }) => useRealtime(h, actor, signal, expired), { initialProps: { h: H1, actor: U1 } });
  const old = Source.all[0]; rerender({ h: H2, actor: 'other-account' });
  expect(old.close).toHaveBeenCalled();
  act(() => { old.emit('reset'); old.emit('expired'); old.onerror?.(); });
  expect(result.current.revision).toBe(0); expect(expired).not.toHaveBeenCalled();
  expect(Source.all[1].url).toContain(H2);
});

it('fences callbacks during committed workspace layout before passive cleanup', () => {
  const signal = new AbortController().signal, expired = vi.fn();
  const { rerender } = renderHook(({ h }) => {
    const value = useRealtime(h, U1, signal, expired);
    useLayoutEffect(() => { if (h === H2) Source.all[0].emit('expired'); }, [h]);
    return value;
  }, { initialProps: { h: H1 } });
  rerender({ h: H2 });
  expect(expired).not.toHaveBeenCalled(); expect(Source.all[0].close).toHaveBeenCalled();
});

it('stops immediately on session abort and cancels reconnect timers/probes', async () => {
  vi.useFakeTimers(); const probe = vi.spyOn(api, 'session'); const controller = new AbortController(), expired = vi.fn();
  renderHook(() => useRealtime(H1, U1, controller.signal, expired));
  const old = Source.all[0]; act(() => old.onerror?.()); act(() => controller.abort());
  await act(async () => vi.advanceTimersByTimeAsync(60000));
  expect(old.close).toHaveBeenCalled(); expect(Source.all).toHaveLength(1); expect(probe).not.toHaveBeenCalled();
});

it('reconnects after a session probe and refetches on reset even with an identical cursor', async () => {
  vi.useFakeTimers(); vi.spyOn(api, 'session').mockResolvedValue(session());
  const signal = new AbortController().signal, expired = vi.fn();
  const { result } = renderHook(() => useRealtime(H1, U1, signal, expired));
  act(() => Source.all[0].emit('reset')); act(() => Source.all[0].onerror?.());
  expect(result.current.status).toBe('reconnecting');
  await act(async () => vi.advanceTimersByTimeAsync(1999)); expect(Source.all).toHaveLength(1);
  await act(async () => vi.advanceTimersByTimeAsync(1)); expect(Source.all).toHaveLength(2);
  act(() => Source.all[1].emit('reset')); expect(result.current.revision).toBe(2);
});

it.each(['expired', 'replaced'])('clears the workspace when a reconnect probe finds %s identity', async kind => {
  vi.useFakeTimers(); const expired = vi.fn(), signal = new AbortController().signal;
  const probe = vi.spyOn(api, 'session');
  if (kind === 'expired') probe.mockRejectedValue(new ApiError(401, 'invalid_session'));
  else probe.mockResolvedValue({ ...session(), identity: { user_id: 'other', username: 'other' } });
  renderHook(() => useRealtime(H1, U1, signal, expired));
  act(() => Source.all[0].onerror?.()); await act(async () => vi.advanceTimersByTimeAsync(2000));
  expect(expired).toHaveBeenCalledOnce(); expect(Source.all).toHaveLength(1);
});

it('backs off repeated storage failures without busy reconnecting', async () => {
  vi.useFakeTimers(); const probe = vi.spyOn(api, 'session').mockRejectedValue(new ApiError(503));
  const signal = new AbortController().signal, expired = vi.fn();
  renderHook(() => useRealtime(H1, U1, signal, expired)); act(() => Source.all[0].onerror?.());
  await act(async () => vi.advanceTimersByTimeAsync(60000));
  expect(probe).toHaveBeenCalledTimes(5); expect(Source.all).toHaveLength(1); expect(expired).not.toHaveBeenCalled();
});

it('rejects wrong-scope/malformed frames without invalidating canonical state', () => {
  const signal = new AbortController().signal, expired = vi.fn();
  const { result } = renderHook(() => useRealtime(H1, U1, signal, expired));
  act(() => Source.all[0].emit('invalidate', 'a'.repeat(64), H2));
  expect(result.current.revision).toBe(0); expect(expired).not.toHaveBeenCalled();
  expect(Source.all[0].close).toHaveBeenCalled();
});

it.each(['expired', 'replaced'])('closes a stream immediately on an %s session frame', kind => {
  const signal = new AbortController().signal, expired = vi.fn();
  const { result } = renderHook(() => useRealtime(H1, U1, signal, expired));
  act(() => Source.all[0].emit(kind === 'expired' ? 'expired' : 'reset', 'a'.repeat(64), H1, kind === 'expired' ? U1 : 'other'));
  expect(expired).toHaveBeenCalledOnce(); expect(Source.all[0].close).toHaveBeenCalled();
  expect(result.current.revision).toBe(0);
});

it('reports synchronous EventSource construction failure without crashing or busy retrying', async () => {
  vi.useFakeTimers(); const construct = vi.fn();
  vi.stubGlobal('EventSource', class { constructor() { construct(); throw new Error('unavailable'); } });
  const signal = new AbortController().signal, expired = vi.fn();
  const { result } = renderHook(() => useRealtime(H1, U1, signal, expired));
  expect(result.current.status).toBe('reconnecting');
  await act(async () => vi.advanceTimersByTimeAsync(1999)); expect(construct).toHaveBeenCalledOnce();
});

it('fences a stale session probe after navigation', async () => {
  vi.useFakeTimers(); let reject!: (e: ApiError) => void;
  vi.spyOn(api, 'session').mockImplementation(() => new Promise((_, r) => { reject = r; }));
  const signal = new AbortController().signal, expired = vi.fn();
  const { rerender } = renderHook(({ h }) => useRealtime(h, U1, signal, expired), { initialProps: { h: H1 } });
  act(() => Source.all[0].onerror?.()); await act(async () => vi.advanceTimersByTimeAsync(2000));
  rerender({ h: H2 }); await act(async () => reject(new ApiError(401)));
  expect(expired).not.toHaveBeenCalled(); expect(Source.all).toHaveLength(2);
});

it('preserves forms while refetching and ignores older canonical responses', async () => {
  let complete!: (value: string) => void;
  const load = vi.fn<(signal: AbortSignal) => Promise<string>>().mockResolvedValueOnce('initial')
    .mockImplementationOnce(() => new Promise(resolve => { complete = resolve; })).mockResolvedValueOnce('latest');
  const expired = vi.fn();
  function View({ revision }: { revision: number }) {
    return <ReadInvalidation.Provider value={revision}><Child /></ReadInvalidation.Provider>;
  }
  function Child() {
    const { state } = useRead(load, expired);
    return state.status === 'success' ? <><input aria-label="Keep input" defaultValue="" /><p>{state.data}</p></> : <p>Loading</p>;
  }
  const { rerender } = render(<View revision={0} />); const input = await screen.findByLabelText('Keep input');
  fireEvent.change(input, { target: { value: 'confirmation/input retained' } });
  rerender(<View revision={1} />); expect(screen.getByLabelText('Keep input')).toBe(input);
  rerender(<View revision={2} />); await screen.findByText('latest');
  await act(async () => complete('stale'));
  expect(screen.queryByText('stale')).toBeNull(); expect((input as HTMLInputElement).value).toBe('confirmation/input retained');
});

it('refetches team deletion/removal and keeps a command input mounted during invalidation', async () => {
  let member = true, deleted = false;
  const fetch = vi.fn((url: string, options: RequestInit) => {
    if (url === '/auth/session') return Promise.resolve(json(session()));
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon()], next_cursor: null }));
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: member ? team() : null }));
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: deleted ? [] : [team()], next_cursor: null }));
    if (url === `/api/hackathons/${H1}/teams/${T1}`) return Promise.resolve(deleted ? failure(404, 'team_not_found') : json(team()));
    if (url.endsWith('/join-requests?limit=20')) return Promise.resolve(json({ items: [], next_cursor: null }));
    return Promise.resolve(failure(404, 'team_not_found'));
  }); vi.stubGlobal('fetch', fetch);
  render(<App />); fireEvent.click(await screen.findByRole('button', { name: /Test Challenge/ }));
  fireEvent.click(await screen.findByRole('button', { name: /View Test Team Alpha/ }));
  const input = await screen.findByLabelText('Recipient account UUID'); fireEvent.change(input, { target: { value: 'retained' } });
  act(() => Source.all[0].emit('reset'));
  await waitFor(() => expect(fetch.mock.calls.filter(([url]) => url.endsWith('/me/team')).length).toBeGreaterThan(1));
  expect(screen.getByLabelText('Recipient account UUID')).toBe(input); expect((input as HTMLInputElement).value).toBe('retained');
  member = false; deleted = true; act(() => Source.all[0].emit('invalidate', 'b'.repeat(64)));
  await screen.findByText('This hackathon or team is no longer available. Refresh the list.');
  fireEvent.click(screen.getByRole('button', { name: 'My team' })); await screen.findByText(/You haven.t joined a team/);
  expect(fetch.mock.calls.every(([, options]) => options.method !== 'POST')).toBe(true);
});
