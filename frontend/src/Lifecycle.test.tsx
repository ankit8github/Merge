import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { api, ApiError } from './api';
import { useLifecycle } from './hooks/useLifecycle';
import { created, csrf, failure, H1, H2, hackathon, json, session, T1, team, U1 } from './test/fixtures';

const U2 = '00000000-0000-0000-0000-000000000022';
const base = `/api/hackathons/${H1}/teams/${T1}`;
const receipt = (subject = U1, deleted = true) => ({ schema_version: 1, data: { hackathon_id: H1, team_id: T1,
  user_id: subject, member_count: deleted ? 0 : 1, team_version: 3, leader_user_id: deleted ? null : U1, deleted } });
const scope = (user = U1, token = csrf) => ({ session: { ...session(), identity: { user_id: user, username: 'test_user' }, csrf_token: token }, epoch: 1, signal: new AbortController().signal });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('uses exact same-origin lifecycle paths, empty JSON, CSRF and original key', async () => {
  const fetch = vi.fn<(url: string, options: RequestInit) => Promise<Response>>(() => Promise.resolve(json(receipt()))); vi.stubGlobal('fetch', fetch);
  await api.lifecycle('leave', H1, T1, U1, 'exact-key', csrf);
  expect(fetch).toHaveBeenCalledWith(base + '/leave', expect.objectContaining({ method: 'POST', body: '{}', credentials: 'same-origin',
    headers: expect.objectContaining({ 'X-CSRF-Token': csrf, 'Idempotency-Key': 'exact-key' }) }));
  fetch.mockImplementation(() => Promise.resolve(json(receipt(U2, false))));
  await api.lifecycle('remove', H1, T1, U2, 'remove-key', csrf);
  expect(fetch.mock.calls.at(-1)?.[0]).toBe(base + `/members/${U2}/remove`);
});

it.each(['subject', 'scope', 'count', 'leader', 'deleted', 'version'])('rejects a mismatched %s receipt', async kind => {
  const value = receipt();
  if (kind === 'subject') value.data.user_id = U2;
  if (kind === 'scope') value.data.hackathon_id = H2;
  if (kind === 'count') value.data.member_count = 1;
  if (kind === 'leader') value.data.leader_user_id = U1;
  if (kind === 'deleted') value.data.deleted = false;
  if (kind === 'version') value.data.team_version = 1;
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(json(value))));
  await expect(api.lifecycle('leave', H1, T1, U1, 'key', csrf)).rejects.toMatchObject({ code: 'invalid_response' });
});

it('validates member pagination and projects only public roster fields', async () => {
  const fetch = vi.fn<(url: string, options: RequestInit) => Promise<Response>>(() => Promise.resolve(json({ items: [{ user_id: U2, display_name: 'Member', joined_at: '2026-11-13T00:00:00Z', ignored: 'private' }], next_cursor: U2 })));
  vi.stubGlobal('fetch', fetch);
  expect(await api.members(H1, T1, U1)).toEqual({ items: [{ user_id: U2, display_name: 'Member', joined_at: '2026-11-13T00:00:00Z' }], next_cursor: U2 });
  expect(fetch.mock.calls[0][0]).toBe(base + '/members?limit=20&cursor=' + U1);
  fetch.mockImplementation(() => Promise.resolve(json({ items: [], next_cursor: U2 })));
  await expect(api.members(H1, T1, null)).rejects.toBeInstanceOf(ApiError);
});

it('retains the exact key after lost delivery and a subsequent denial, without automatic replay', async () => {
  const fetch = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(failure(403, 'forbidden')).mockResolvedValueOnce(json(receipt()));
  vi.stubGlobal('fetch', fetch); const owner = scope(), workspace = new AbortController();
  const { result } = renderHook(() => useLifecycle(owner, vi.fn()));
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal));
  await waitFor(() => expect(result.current.operation('leave', H1, T1, U1)?.uncertain).toBe(true));
  expect(fetch).toHaveBeenCalledTimes(1);
  const key = result.current.operation('leave', H1, T1, U1)!.key;
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal));
  expect(fetch).toHaveBeenCalledTimes(1);
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal, true));
  await waitFor(() => expect(result.current.operation('leave', H1, T1, U1)?.error?.status).toBe(403));
  expect(result.current.operation('leave', H1, T1, U1)?.uncertain).toBe(true);
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal, true));
  await waitFor(() => expect(result.current.operation('leave', H1, T1, U1)?.status).toBe('success'));
  expect(fetch.mock.calls.every(([, options]) => options.headers['Idempotency-Key'] === key)).toBe(true);
});

it('isolates account journals and retries with the newly validated session CSRF', async () => {
  const fetch = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(json(receipt())); vi.stubGlobal('fetch', fetch);
  const initial = scope(), next = scope(U1, 'B'.repeat(43)), other = scope(U2), workspace = new AbortController();
  const { result, rerender } = renderHook(({ owner }) => useLifecycle(owner, vi.fn()), { initialProps: { owner: initial } });
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal));
  await waitFor(() => expect(result.current.commands(H1)[0].uncertain).toBe(true));
  rerender({ owner: other }); expect(result.current.commands(H1)).toEqual([]);
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal, true)); expect(fetch).toHaveBeenCalledTimes(1);
  rerender({ owner: next });
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal, true));
  await waitFor(() => expect(result.current.commands(H1)[0].status).toBe('success'));
  expect(fetch.mock.calls[1][1].headers['X-CSRF-Token']).toBe('B'.repeat(43));
  expect(window.sessionStorage.length).toBe(0);
});

it('ignores old-workspace 401 effects while retaining its original command', async () => {
  let finish!: (r: Response) => void; vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const owner = scope(), workspace = new AbortController(), expired = vi.fn();
  const { result } = renderHook(() => useLifecycle(owner, expired));
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal));
  workspace.abort(); await act(async () => finish(failure(401, 'invalid_session')));
  expect(expired).not.toHaveBeenCalled(); expect(result.current.commands(H1)[0].status).toBe('rejected');
});

it('cancels on session invalidation, fences late responses and keeps uncertainty', async () => {
  let finish!: (r: Response) => void; const fetch = vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })); vi.stubGlobal('fetch', fetch);
  const sessionAbort = new AbortController(), owner = { ...scope(), signal: sessionAbort.signal }, workspace = new AbortController();
  const { result, rerender } = renderHook(({ current }) => useLifecycle(current, vi.fn()), { initialProps: { current: owner } });
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal));
  act(() => sessionAbort.abort()); rerender({ current: scope(U2) });
  await act(async () => finish(json(receipt()))); expect(result.current.commands(H1)).toEqual([]);
  rerender({ current: scope() }); expect(result.current.commands(H1)[0].uncertain).toBe(true);
});

it('allows a new explicitly confirmed departure after a later rejoin using a new key', async () => {
  const fetch = vi.fn(() => Promise.resolve(json(receipt()))); vi.stubGlobal('fetch', fetch);
  const owner = scope(), workspace = new AbortController(); const { result } = renderHook(() => useLifecycle(owner, vi.fn()));
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal));
  await waitFor(() => expect(result.current.commands(H1)[0].status).toBe('success'));
  const old = result.current.commands(H1)[0].key;
  act(() => result.current.submit('leave', H1, T1, U1, workspace.signal));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(result.current.commands(H1)[0].key).not.toBe(old);
});

function appServer(creator = false, loseLeave = false) {
  let removed = false, left = creator, lost = false;
  const fetch = vi.fn((url: string, options: RequestInit) => {
    if (url === '/auth/session') return Promise.resolve(json(session()));
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon()], next_cursor: null }));
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: left ? null : team() }));
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: left ? [] : [team()], next_cursor: null }));
    if (url === base) return Promise.resolve(left ? failure(404, 'team_not_found') : json(team()));
    if (url.endsWith('/join-requests?limit=20')) return Promise.resolve(json({ items: [], next_cursor: null }));
    if (url === base + '/members?limit=20') return Promise.resolve(json({ items: [
      { user_id: U1, display_name: 'Leader', joined_at: '2026-11-13T00:00:00Z' },
      ...removed ? [] : [{ user_id: U2, display_name: 'Builder', joined_at: '2026-11-13T01:00:00Z' }]], next_cursor: null }));
    if (options.method === 'POST' && url === base + `/members/${U2}/remove`) { removed = true; return Promise.resolve(json(receipt(U2, false))); }
    if (options.method === 'POST' && url === base + '/leave') {
      left = true;
      if (loseLeave && !lost) { lost = true; return Promise.reject(new Error('synthetic-lost-delivery')); }
      return Promise.resolve(json(receipt()));
    }
    if (options.method === 'POST' && url === `/api/hackathons/${H1}/teams`) { left = false; return Promise.resolve(json(created(),201)); }
    return Promise.resolve(failure(404, 'team_not_found'));
  });
  vi.stubGlobal('fetch', fetch); return fetch;
}
async function manage() {
  render(<App />); fireEvent.click(await screen.findByRole('button', { name: /Test Challenge/ }));
  fireEvent.click(await screen.findByRole('button', { name: /View Test Team Alpha/ }));
  fireEvent.click(await screen.findByRole('button', { name: 'Manage membership' })); await screen.findByText('Builder');
}

it('requires explicit leave confirmation, supports cancel, then refetches membership and deleted detail', async () => {
  const fetch = appServer(); await manage();
  fireEvent.click(screen.getByRole('button', { name: 'Leave team' }));
  expect(fetch.mock.calls.some(([, o]) => o.method === 'POST')).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(screen.queryByRole('button', { name: 'Confirm leave' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Leave team' })); fireEvent.click(screen.getByRole('button', { name: 'Confirm leave' }));
  await screen.findByText(/Team change confirmed/);
  fireEvent.click(screen.getByRole('button', { name: 'My team' })); await screen.findByText(/You haven.t joined a team/);
  expect(fetch.mock.calls.filter(([, o]) => o.method === 'POST')).toHaveLength(1);
});

it('removes a named member only after confirmation and refreshes the authorized roster', async () => {
  const fetch = appServer(); await manage(); fireEvent.click(screen.getByRole('button', { name: 'Remove Builder' }));
  expect(fetch.mock.calls.some(([, o]) => o.method === 'POST')).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Confirm removal' })); await screen.findByText(/Team change confirmed/);
  fireEvent.click(await screen.findByRole('button', { name: 'Manage membership' }));
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Remove Builder' })).toBeNull());
  expect(fetch.mock.calls.filter(([url]) => url === base + `/members/${U2}/remove`)).toHaveLength(1);
});

it('keeps original leave recovery available after canonical membership disappears', async () => {
  const fetch=appServer(false,true); await manage();
  fireEvent.click(screen.getByRole('button',{name:'Leave team'})); fireEvent.click(screen.getByRole('button',{name:'Confirm leave'}));
  await screen.findByRole('button',{name:'Retry original leave'});
  fireEvent.click(screen.getByRole('button',{name:'My team'})); fireEvent.click(screen.getByRole('button',{name:'Refresh membership'}));
  await screen.findByText(/You haven.t joined a team/);
  fireEvent.click(screen.getByRole('button',{name:'Retry original leave'})); await screen.findByText(/Team change confirmed/);
  const posts=fetch.mock.calls.filter(([url])=>url===base+'/leave');
  expect(posts).toHaveLength(2);
  expect((posts[0][1].headers as Record<string,string>)['Idempotency-Key']).toBe((posts[1][1].headers as Record<string,string>)['Idempotency-Key']);
});

it('allows a former founder to explicitly start another creation only after a fresh teamless read', async () => {
  appServer(true); render(<App />);
  fireEvent.click(await screen.findByRole('button',{name:/Test Challenge/}));
  const name=await screen.findByLabelText('Team name'); fireEvent.change(name,{target:{value:'My first team'}});
  fireEvent.click(screen.getByRole('button',{name:'Create team'})); await screen.findByText(/Team creation confirmed/);
  fireEvent.click(await screen.findByRole('button',{name:/View Test Team Alpha/}));
  fireEvent.click(await screen.findByRole('button',{name:'Manage membership'}));
  fireEvent.click(screen.getByRole('button',{name:'Leave team'})); fireEvent.click(screen.getByRole('button',{name:'Confirm leave'}));
  fireEvent.click(await screen.findByRole('button',{name:'Start another team'}));
  await waitFor(() => expect((screen.getByRole('button',{name:'Create team'}) as HTMLButtonElement).disabled).toBe(false));
  expect((screen.getByLabelText('Team name') as HTMLInputElement).readOnly).toBe(false);
});
