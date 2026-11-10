import { afterEach, expect, it, vi } from 'vitest';
import { api, ApiError, errorMessage } from './api';
import { csrf, failure, H1, H2, json, session, T1, team, U1 } from './test/fixtures';

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
it('sends only same-origin cookies and the exact auth/logout header contracts', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(json(session())).mockResolvedValueOnce(json({ user_id: U1, username: 'test_builder' }, 201)).mockResolvedValueOnce(new Response(null, { status: 204 }));
  vi.stubGlobal('fetch', fetch);
  const credentials = { username: 'test_builder', password: 'test-only-password' };
  await api.login(credentials); await api.register(credentials); await api.logout(csrf);
  for (const [url, options] of fetch.mock.calls) {
    expect(url).toMatch(/^\/auth\//);
    expect(options).toMatchObject({ method: 'POST', credentials: 'same-origin', cache: 'no-store', redirect: 'error' });
    expect(options.headers).not.toHaveProperty('Origin');
    expect(options.headers).not.toHaveProperty('Authorization');
    expect(options.headers).not.toHaveProperty('Cookie');
    expect(options.headers).not.toHaveProperty('X-User-ID');
  }
  expect(fetch.mock.calls[0][1].headers).toMatchObject({ 'X-Merge-Request': '1', 'Content-Type': 'application/json' });
  expect(fetch.mock.calls[0][1].headers).not.toHaveProperty('X-CSRF-Token');
  expect(fetch.mock.calls[2][1].headers).toMatchObject({ 'X-CSRF-Token': csrf });
  expect(fetch.mock.calls[2][1].headers).not.toHaveProperty('X-Merge-Request');
  expect(fetch.mock.calls[2][1].body).toBe('{}');
});
it('uses bounded keyset URLs without identity or CSRF on reads', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(json({ items: [team()], next_cursor: T1 })).mockResolvedValueOnce(json({ team: null }));
  vi.stubGlobal('fetch', fetch);
  await api.teams(H1, T1); expect(await api.myTeam(H1)).toBe(null);
  expect(fetch.mock.calls[0][0]).toBe(`/api/hackathons/${H1}/teams?limit=20&cursor=${T1}`);
  expect(fetch.mock.calls[1][0]).toBe(`/api/hackathons/${H1}/me/team`);
  expect(fetch.mock.calls[0][1].headers).toEqual({ Accept: 'application/json' });
  expect(fetch.mock.calls[0][1]).not.toHaveProperty('body');
});
it.each([
  { ...team(), hackathon_id: H2 }, { ...team(), member_count: 5 },
  { ...team(), readiness: 'forming' }, { ...team(), leader: {} }, { ...team(), created_at: 'invalid' },
])('rejects inconsistent/scoped team response %#', async value => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(value)));
  await expect(api.team(H1, T1)).rejects.toMatchObject({ code: 'invalid_response' });
});
it.each([{}, { items: [], next_cursor: 'bad' }, { items: Array(21).fill(team()), next_cursor: null }])('rejects malformed or oversized pages %#', async value => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(value)));
  await expect(api.teams(H1, null)).rejects.toMatchObject({ code: 'invalid_response' });
});
it('does not equate a missing team field with no membership', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({})));
  await expect(api.myTeam(H1)).rejects.toMatchObject({ code: 'invalid_response' });
});
it('excludes unexpected response fields from typed data', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ ...team(), private_extra: 'not rendered' })));
  expect(await api.team(H1, T1)).not.toHaveProperty('private_extra');
});
it('counts Unicode code points like the documented server string bounds', async () => {
  const value = { ...team(), name: '😀'.repeat(120), leader: { user_id: U1, display_name: '😀'.repeat(80) } };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(value)));
  expect(await api.team(H1, T1)).toMatchObject(value);
});
it('sanitizes HTML errors and never reflects server messages', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private upstream data', { status: 503 })));
  try { await api.session(); } catch (error) {
    expect(error).toBeInstanceOf(ApiError); expect(errorMessage(error as ApiError)).not.toMatch(/private|Untrusted/);
    expect((error as ApiError).message).toBe('Request could not be completed'); return;
  }
  throw new Error('Expected a failure');
});
it('bounds Retry-After and preserves retryable metadata without automatically retrying', async () => {
  const fetch = vi.fn().mockResolvedValue(failure(429, 'rate_limited', true, { 'Retry-After': '999999' }));
  vi.stubGlobal('fetch', fetch);
  const now = Date.now();
  await expect(api.session()).rejects.toMatchObject({ status: 429, retryable: true, retryAt: expect.any(Number) });
  expect(fetch).toHaveBeenCalledTimes(1);
  try { await api.session(); } catch (error) { expect((error as ApiError).retryAt - now).toBeLessThanOrEqual(3600100); }
});
it('requires the exact logout acknowledgement status', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({})));
  await expect(api.logout(csrf)).rejects.toMatchObject({ code: 'invalid_response' });
});
it('bounds slow requests and cancels a caller-aborted read', async () => {
  vi.useFakeTimers();
  const fetch = vi.fn((_url, options: RequestInit) => new Promise<Response>((_resolve, reject) => {
    options.signal?.addEventListener('abort', () => reject(new Error('Transport details must not escape')));
  }));
  vi.stubGlobal('fetch', fetch);
  const slow = expect(api.session()).rejects.toMatchObject({ status: 0, code: 'network_error' });
  await vi.advanceTimersByTimeAsync(20000); await slow;
  const controller = new AbortController();
  const cancelled = expect(api.session(controller.signal)).rejects.toBeInstanceOf(ApiError);
  controller.abort(); await cancelled;
  expect(fetch).toHaveBeenCalledTimes(2);
});
