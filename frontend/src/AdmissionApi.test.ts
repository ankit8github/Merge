import { afterEach, expect, it, vi } from 'vitest';
import { api, type Decision } from './api';
import { H1, H2, T1, T2, U1, csrf, json } from './test/fixtures';

const R = '00000000-0000-0000-0000-000000000031';
const base = `/api/hackathons/${H1}/teams/${T1}/join-requests`;
function row(overrides = {}) {
  return { id: R, hackathon_id: H1, team_id: T1, requester_id: U1, status: 'pending',
    created_at: '2026-11-11T00:00:00Z', resolved_at: null, ...overrides };
}
afterEach(() => vi.unstubAllGlobals());

it.each([200, 201])('uses the exact scoped request POST and accepts documented status %s', async status => {
  const fetch = vi.fn().mockResolvedValue(json({ schema_version: 1, data: row({ resolved_by: U1, secret: 'private' }) }, status));
  vi.stubGlobal('fetch', fetch);
  const result = await api.createRequest(H1, T1, 'original key', csrf);
  expect(result).toEqual(row());
  expect(fetch).toHaveBeenCalledWith(base, expect.objectContaining({ method: 'POST', body: '{}', credentials: 'same-origin', cache: 'no-store',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'Idempotency-Key': 'original key' } }));
});

it.each(['approve', 'reject'] as Decision[])('validates exact %s decision and stored resolved reply', async decision => {
  const fetch = vi.fn().mockResolvedValue(json({ schema_version: 1, data: row({ status: decision === 'approve' ? 'approved' : 'rejected', resolved_at: '2026-11-11T01:00:00Z' }) }));
  vi.stubGlobal('fetch', fetch);
  await api.decideRequest(H1, T1, R, decision, 'key', csrf);
  expect(fetch).toHaveBeenCalledWith(base + '/' + R + '/decision', expect.objectContaining({ body: JSON.stringify({ decision }),
    headers: expect.objectContaining({ 'Idempotency-Key': 'key', 'X-CSRF-Token': csrf }) }));
});

it('reads only own status and bounded pending pages with no CSRF or identity headers', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(json({ request: null })).mockResolvedValueOnce(json({ items: [row()], next_cursor: R }));
  vi.stubGlobal('fetch', fetch);
  expect(await api.ownRequest(H1, T1)).toBe(null);
  expect((await api.pendingRequests(H1, T1, R)).items).toEqual([row()]);
  expect(fetch.mock.calls[0][0]).toBe(base + '/mine');
  expect(fetch.mock.calls[1][0]).toBe(base + '?limit=20&cursor=' + R);
  expect(fetch.mock.calls[1][1].headers).toEqual({ Accept: 'application/json' });
});

it.each([{ hackathon_id: H2 }, { team_id: T2 }, { id: 'invalid' }, { requester_id: 'invalid' },
  { status: 'other' }, { status: 'approved' }, { created_at: 'invalid' }, { resolved_at: '2026-11-11T01:00:00Z' },
  { status: 'rejected', resolved_at: '2026-11-10T00:00:00Z' }])('rejects malformed or cross-scope request metadata %j', async change => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ request: row(change) })));
  await expect(api.ownRequest(H1, T1)).rejects.toMatchObject({ code: 'invalid_response' });
});

it.each([{ items: [row({ status: 'approved', resolved_at: '2026-11-11T01:00:00Z' })], next_cursor: null },
  { items: [row(), row()], next_cursor: null }, { items: [row()], next_cursor: T2 },
  { items: Array.from({ length: 21 }, () => row()), next_cursor: null }])('rejects unsafe pending-page shape %j', async value => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(value)));
  await expect(api.pendingRequests(H1, T1, null)).rejects.toMatchObject({ code: 'invalid_response' });
});

it.each(['wrong-id', 'wrong-status', 'wrong-schema', 'wrong-http'])('refuses mismatched decision acknowledgement: %s', async kind => {
  const data = row({ id: kind === 'wrong-id' ? T2 : R, status: kind === 'wrong-status' ? 'rejected' : 'approved', resolved_at: '2026-11-11T01:00:00Z' });
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ schema_version: kind === 'wrong-schema' ? 2 : 1, data }, kind === 'wrong-http' ? 201 : 200)));
  await expect(api.decideRequest(H1, T1, R, 'approve', 'key', csrf)).rejects.toMatchObject({ code: 'invalid_response' });
});

it('rejects invalid keys, CSRF and decisions before network access', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  await expect(api.createRequest(H1, T1, 'bad\tkey', csrf)).rejects.toMatchObject({ status: 422 });
  await expect(api.createRequest(H1, T1, 'key', 'invalid')).rejects.toMatchObject({ status: 422 });
  await expect(api.decideRequest(H1, T1, R, 'join' as Decision, 'key', csrf)).rejects.toMatchObject({ status: 422 });
  expect(fetch).not.toHaveBeenCalled();
});
