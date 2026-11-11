import { afterEach, expect, it, vi } from 'vitest';
import { api } from './api';
import { H1, H2, T1, T2, U1, I1, I2, csrf, invitation, json } from './test/fixtures';

const base = `/api/hackathons/${H1}/teams/${T1}/invitations`;
const redeemed = () => invitation({ status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z', available: false });
afterEach(() => vi.unstubAllGlobals());

it('issues only recipient_id to the exact endpoint with current CSRF/key and drops extra response fields', async () => {
  const fetch = vi.fn().mockResolvedValue(json({ schema_version: 1, data: { ...invitation(), private: 'never display' } }, 201));
  vi.stubGlobal('fetch', fetch);
  const row = await api.issueInvitation(H1, T1, U1, 'original key', csrf);
  expect(row).not.toHaveProperty('private'); expect(row).not.toHaveProperty('available');
  expect(fetch).toHaveBeenCalledWith(base, expect.objectContaining({ method: 'POST', body: JSON.stringify({ recipient_id: U1 }),
    credentials: 'same-origin', cache: 'no-store', redirect: 'error', headers: {
      Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'Idempotency-Key': 'original key',
    } }));
});

it('redeems exactly {} and validates the original invitation acknowledgement', async () => {
  const fetch = vi.fn().mockResolvedValue(json({ schema_version: 1, data: redeemed() })); vi.stubGlobal('fetch', fetch);
  expect((await api.redeemInvitation(H1, T1, I1, 'redemption-key', csrf)).status).toBe('redeemed');
  expect(fetch).toHaveBeenCalledWith(base + '/' + I1 + '/redeem', expect.objectContaining({ method: 'POST', body: '{}',
    headers: expect.objectContaining({ 'X-CSRF-Token': csrf, 'Idempotency-Key': 'redemption-key' }) }));
});

it('fetches only the canonical mine inbox with bounded UUID pagination and no identity/CSRF headers', async () => {
  const fetch = vi.fn().mockResolvedValue(json({ items: [invitation()], next_cursor: I1 })); vi.stubGlobal('fetch', fetch);
  expect((await api.invitations(H1, I1)).items).toEqual([invitation()]);
  expect(fetch).toHaveBeenCalledWith(`/api/hackathons/${H1}/invitations/mine?limit=20&cursor=${I1}`,
    expect.objectContaining({ method: 'GET', headers: { Accept: 'application/json' } }));
});

it.each([{ hackathon_id: H2 }, { id: 'bad' }, { team_id: 'bad' }, { recipient_id: 'bad' }, { issued_by: 'bad' },
  { status: 'other' }, { status: 'redeemed' }, { created_at: 'bad' }, { expires_at: 'bad' },
  { expires_at: '2026-11-11T00:00:00Z' }, { expires_at: '2026-11-13T00:00:00Z' },
  { redeemed_at: '2026-11-11T01:00:00Z' },
  { status: 'redeemed', redeemed_at: '2026-11-10T00:00:00Z' },
  { status: 'redeemed', redeemed_at: '2026-11-12T00:00:00Z' }, { available: 'true' },
  { status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z', available: true }])('refuses unsafe inbox row %j', async change => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ items: [{ ...invitation(), ...change }], next_cursor: null })));
  await expect(api.invitations(H1, null)).rejects.toMatchObject({ code: 'invalid_response' });
});

it.each([{ items: [invitation(), invitation()], next_cursor: null },
  { items: [invitation()], next_cursor: I2 }, { items: [], next_cursor: I1 },
  { items: Array.from({ length: 21 }, () => invitation()), next_cursor: null }])('refuses unsafe inbox page', async value => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(value)));
  await expect(api.invitations(H1, null)).rejects.toMatchObject({ code: 'invalid_response' });
});

it.each(['team', 'recipient', 'schema', 'state', 'http'])('refuses mismatched issue acknowledgement: %s', async kind => {
  const row = { ...(kind === 'state' ? redeemed() : invitation()), team_id: kind === 'team' ? T2 : T1, recipient_id: kind === 'recipient' ? T2 : U1 };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ schema_version: kind === 'schema' ? 2 : 1, data: row }, kind === 'http' ? 200 : 201)));
  await expect(api.issueInvitation(H1, T1, U1, 'key', csrf)).rejects.toMatchObject({ code: 'invalid_response' });
});

it.each(['id', 'state', 'scope', 'http'])('refuses mismatched redemption acknowledgement: %s', async kind => {
  const row = { ...(kind === 'state' ? invitation() : redeemed()), id: kind === 'id' ? I2 : I1, hackathon_id: kind === 'scope' ? H2 : H1 };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ schema_version: 1, data: row }, kind === 'http' ? 201 : 200)));
  await expect(api.redeemInvitation(H1, T1, I1, 'key', csrf)).rejects.toMatchObject({ code: 'invalid_response' });
});

it('rejects invalid UUID/key/CSRF before network and never uses an actor selector', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  await expect(api.issueInvitation(H1, T1, 'username', 'key', csrf)).rejects.toMatchObject({ code: 'invalid_response' });
  await expect(api.issueInvitation(H1, T1, U1, 'bad\tkey', csrf)).rejects.toMatchObject({ status: 422 });
  await expect(api.redeemInvitation(H1, T1, I1, 'key', 'bad')).rejects.toMatchObject({ status: 422 });
  expect(fetch).not.toHaveBeenCalled();
});

it('preserves microsecond ordering for a valid redemption just before expiry', async () => {
  const row = { ...redeemed(), expires_at: '2026-11-12T00:00:00.000002+00:00',
    created_at: '2026-11-11T00:00:00.000002+00:00', redeemed_at: '2026-11-12T00:00:00.000001Z' };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ schema_version: 1, data: row })));
  expect((await api.redeemInvitation(H1, T1, I1, 'key', csrf)).redeemed_at).toBe(row.redeemed_at);
});

it('rejects redemption at the same microsecond as expiry even with different timezone encodings', async () => {
  const row = { ...redeemed(), expires_at: '2026-11-12T00:00:00.000002+00:00',
    created_at: '2026-11-11T00:00:00.000002+00:00', redeemed_at: '2026-11-12T01:00:00.000002+01:00' };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ schema_version: 1, data: row })));
  await expect(api.redeemInvitation(H1, T1, I1, 'key', csrf)).rejects.toMatchObject({ code: 'invalid_response' });
});
