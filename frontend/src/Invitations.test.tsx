import { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import type { InboxInvitation, Session, Team } from './api';
import { created, csrf, failure, H1, H2, hackathon, I1, I2, invitation, json, session, T1, T2, team, U1 } from './test/fixtures';

const OTHER = '00000000-0000-0000-0000-000000000022';
const issuePath = (t = T1, h = H1) => `/api/hackathons/${h}/teams/${t}/invitations`;
const redeemPath = () => issuePath() + '/' + I1 + '/redeem';
type Handler = (url: string, options: RequestInit) => Response | Promise<Response> | undefined;
function server(leader = false, handler: Handler = () => undefined) {
  const model = { session: session() as Session, leader: leader ? U1 : OTHER,
    inbox: [invitation({ issued_by: OTHER })] as InboxInvitation[], membership: null as Team | null, count: 2 };
  const publicTeam = (id = T1, h = H1) => ({ ...team(id, h), leader: { user_id: model.leader, display_name: 'Public leader' }, member_count: model.count });
  const fetch = vi.fn((url: string, options: RequestInit) => {
    const custom = handler(url, options); if (custom) return Promise.resolve(custom);
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/auth/session' || url === '/auth/login') return Promise.resolve(json(model.session));
    if (url === '/auth/logout') return Promise.resolve(new Response(null, { status: 204 }));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon(), hackathon(H2)], next_cursor: null }));
    const h = url.includes(H2) ? H2 : H1, t = url.includes(T2) ? T2 : T1;
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: [publicTeam(T1, h), publicTeam(T2, h)], next_cursor: null }));
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: model.membership?.hackathon_id === h ? model.membership : null }));
    if (url.endsWith('/teams/' + t)) return Promise.resolve(json(publicTeam(t, h)));
    if (url.endsWith('/join-requests/mine')) return Promise.resolve(json({ request: null }));
    if (url.includes('/join-requests?')) return Promise.resolve(json({ items: [], next_cursor: null }));
    if (url.includes('/invitations/mine?')) return Promise.resolve(json({ items: model.inbox.filter(r => r.hackathon_id === h && r.recipient_id === model.session.identity.user_id), next_cursor: null }));
    if (url.endsWith('/invitations') && options.method === 'POST') return Promise.resolve(json({ schema_version: 1,
      data: invitation({ hackathon_id: h, team_id: t, recipient_id: JSON.parse(String(options.body)).recipient_id, issued_by: model.session.identity.user_id }) }, 201));
    if (url.endsWith('/redeem') && options.method === 'POST') {
      const id = url.split('/').at(-2)!;
      const saved = model.inbox.find(r => r.id === id)!;
      const row = { ...saved, status: 'redeemed' as const, redeemed_at: '2026-11-11T01:00:00Z', available: false };
      model.inbox = model.inbox.map(r => r.id === id ? row : r); model.count = 3; model.membership = publicTeam(t, h);
      return Promise.resolve(json({ schema_version: 1, data: row }));
    }
    throw new Error('Unexpected mocked endpoint');
  });
  vi.stubGlobal('fetch', fetch);
  return { model, fetch, posts: () => fetch.mock.calls.filter(([url, options]) => url.includes('/invitations') && options.method === 'POST') };
}
async function choose(second = false) {
  fireEvent.click(await screen.findByRole('button', { name: second ? /Second Challenge/ : /Test Challenge/ }));
  await screen.findByRole('button', { name: /View Test Team Alpha/ });
}
async function open(second = false) {
  fireEvent.click(await screen.findByRole('button', { name: second ? /View Test Team Beta/ : /View Test Team Alpha/ }));
  await screen.findByText('Public leader');
}
async function inbox() {
  fireEvent.click(screen.getByRole('button', { name: 'Invitations' }));
  await screen.findByRole('heading', { name: 'Your invitations' });
}
const issueButton = () => screen.getByRole('button', { name: 'Issue invitation' });
const redeemButton = (id = I1) => screen.getByRole('button', { name: 'Redeem invitation ' + id });
async function ready() { await waitFor(() => expect((redeemButton() as HTMLButtonElement).disabled).toBe(false)); }
function recipient(value = OTHER) { fireEvent.change(screen.getByLabelText('Recipient account UUID'), { target: { value } }); }
function login() {
  fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'test_builder' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'synthetic invitation password' } });
  fireEvent.click(screen.getByRole('button', { name: /Sign in to Merge/ }));
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

it('issues from an accessible UUID-only leader form, prevents duplicate clicks and refreshes canonical detail', async () => {
  const s = server(true); const storage = vi.spyOn(Storage.prototype, 'setItem'); render(<App />); await choose(); await open();
  const input = screen.getByLabelText('Recipient account UUID'); input.focus(); expect(document.activeElement).toBe(input);
  expect(screen.getByText(/Username search is not available/)).toBeTruthy(); recipient();
  const button = issueButton();
  fireEvent.submit(screen.getByRole('form', { name: 'Issue invitation' })); fireEvent.click(button);
  await screen.findByText(/Invitation issuance confirmed/);
  expect(s.posts()).toHaveLength(1); expect(s.posts()[0][0]).toBe(issuePath());
  expect(s.posts()[0][1]).toMatchObject({ body: JSON.stringify({ recipient_id: OTHER }), headers: {
    Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'Idempotency-Key': expect.stringMatching(/^[0-9a-f]{64}$/),
  } });
  expect(s.fetch.mock.calls.filter(([url]) => url.endsWith('/teams/' + T1)).length).toBeGreaterThanOrEqual(2);
  expect(document.body.textContent).not.toContain(csrf); expect(storage).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Start another invitation' })); recipient(); fireEvent.click(issueButton());
  await screen.findByText(/Invitation issuance confirmed/);
  const keys = s.posts().map(([, o]) => (o.headers as Record<string, string>)['Idempotency-Key']);
  expect(keys).toHaveLength(2); expect(keys[0]).not.toBe(keys[1]);
});

it('hides issuance from nonleaders and makes no speculative user-search or inbox reads', async () => {
  const s = server(); render(<App />); await choose(); await open();
  expect(screen.queryByLabelText('Recipient account UUID')).toBe(null);
  expect(s.fetch.mock.calls.some(([url]) => /users|search|invitations\/mine/.test(url))).toBe(false);
});

it.each(['username', '', ' ' + OTHER, OTHER + ' '])('focuses invalid UUID entry without a mutation: %j', async value => {
  const s = server(true); render(<App />); await choose(); await open(); recipient(value); fireEvent.click(issueButton());
  await screen.findByText(/Enter a complete account UUID/); expect(document.activeElement).toBe(screen.getByLabelText('Recipient account UUID'));
  expect(s.posts()).toHaveLength(0);
});

it('displays only canonical own inbox state/expiry and opens real team details', async () => {
  const s = server(); render(<App />); await choose(); await inbox(); await ready();
  expect(screen.getByText('pending')).toBeTruthy(); expect(screen.getByText(/Your recipient account UUID/)).toBeTruthy();
  expect(document.querySelector('time')?.getAttribute('datetime')).toBe('2026-11-12T00:00:00Z');
  expect(s.fetch.mock.calls.some(([url]) => url === `/api/hackathons/${H1}/invitations/mine?limit=20`)).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'View invited team ' + T1 })); await screen.findByText('Public leader');
  expect(screen.getByRole('heading', { name: 'Test Team Alpha' })).toBeTruthy();
});

it('redeems once and refreshes canonical inbox, membership and discovery without an optimistic roster', async () => {
  const s = server(); render(<App />); await choose(); await inbox(); await ready();
  const button = redeemButton(); button.focus(); expect(document.activeElement).toBe(button);
  fireEvent.click(button); fireEvent.click(button); await screen.findByText('redeemed');
  expect(s.posts()).toHaveLength(1); expect(s.posts()[0][0]).toBe(redeemPath()); expect(s.posts()[0][1].body).toBe('{}');
  expect(s.fetch.mock.calls.filter(([url]) => url.endsWith('/me/team')).length).toBeGreaterThanOrEqual(2);
  fireEvent.click(screen.getByRole('button', { name: 'My team' })); await screen.findByText('3/4 members');
  fireEvent.click(screen.getByRole('button', { name: 'Discover teams' }));
  await screen.findByRole('button', { name: /View Test Team Alpha/ });
  expect(s.fetch.mock.calls.filter(([url]) => url.endsWith('/teams?limit=20')).length).toBeGreaterThanOrEqual(2);
});

it('does not substitute a successful stored reply for canonical current inbox or membership', async () => {
  const s = server(false, (url, options) => url.endsWith('/redeem') && options.method === 'POST'
    ? json({ schema_version: 1, data: invitation({ status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z' }) }) : undefined);
  render(<App />); await choose(); await inbox(); await ready(); fireEvent.click(redeemButton());
  await screen.findByText(/^Redemption confirmed/); expect(screen.getByText('pending')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'My team' })); await screen.findByText('You haven’t joined a team in this hackathon.');
  expect(s.posts()).toHaveLength(1);
});

it.each(['issue', 'redeem'])('keeps exact %s command/key across a lost response and explicit retry', async kind => {
  let attempts = 0;
  const s = server(kind === 'issue', (url, options) => options.method === 'POST' && url.includes('/invitations') && ++attempts === 1
    ? Promise.reject(new Error('private driver message')) : undefined);
  render(<App />); await choose();
  if (kind === 'issue') { await open(); recipient(); fireEvent.click(issueButton()); }
  else { await inbox(); await ready(); fireEvent.click(redeemButton()); }
  const retry = await screen.findByRole('button', { name: kind === 'issue' ? 'Retry original invitation' : 'Retry original redemption ' + I1 });
  if (kind === 'issue') { recipient(U1); expect((screen.getByLabelText('Recipient account UUID') as HTMLInputElement).value).toBe(OTHER); }
  fireEvent.click(retry); await screen.findByText(kind === 'issue' ? /Invitation issuance confirmed/ : /^Redemption confirmed/);
  expect(s.posts()).toHaveLength(2); expect(s.posts()[0][0]).toBe(s.posts()[1][0]);
  expect(s.posts()[0][1].body).toBe(s.posts()[1][1].body); expect(s.posts()[0][1].headers).toEqual(s.posts()[1][1].headers);
  expect(document.body.textContent).not.toContain('private driver');
});

it('retains uncertain redemption when an inbox refresh removes its invitation and membership has changed', async () => {
  let attempts = 0;
  const s = server(false, (url, options) => {
    if (url.endsWith('/redeem') && options.method === 'POST') {
      if (++attempts === 1) { s.model.inbox = []; s.model.membership = team(); return failure(503, 'outcome_uncertain', true); }
      return json({ schema_version: 1, data: invitation({ status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z' }) });
    }
  });
  render(<App />); await choose(); await inbox(); await ready(); fireEvent.click(redeemButton());
  await screen.findByRole('button', { name: 'Retry original redemption ' + I1 });
  fireEvent.click(screen.getByRole('button', { name: 'Refresh inbox and membership' })); await screen.findByText('No invitations on this page.');
  fireEvent.click(screen.getByRole('button', { name: 'Retry original redemption ' + I1 })); await screen.findByText(/A redemption command was confirmed/);
  expect(s.posts()).toHaveLength(2); expect(s.posts()[0][1].headers).toEqual(s.posts()[1][1].headers);
});

it.each(['invitation_expired', 'invitation_stale', 'team_full', 'already_assigned', 'invitation_redeemed'])('handles %s without marking an unsuccessful grant redeemed', async code => {
  const s = server(false, (url, options) => url.endsWith('/redeem') && options.method === 'POST' ? failure(409, code) : undefined);
  render(<App />); await choose(); await inbox(); await ready(); fireEvent.click(redeemButton()); await screen.findByRole('alert');
  await waitFor(() => expect(document.body.textContent).toMatch({ invitation_expired: /has expired/, invitation_stale: /no longer current/,
    team_full: /no available seat/, already_assigned: /already belong/, invitation_redeemed: /already redeemed/ }[code]!));
  expect(await screen.findByText('pending')).toBeTruthy(); expect(screen.queryByText(/^Redemption confirmed/)).toBe(null); expect(s.posts()).toHaveLength(1);
});

it('keeps uncertainty sticky after a later permission denial and never unlocks another issue payload', async () => {
  let attempts = 0;
  const s = server(true, (url, o) => url === issuePath() && o.method === 'POST'
    ? ++attempts === 1 ? failure(503, 'outcome_uncertain', true) : failure(403, 'forbidden') : undefined);
  render(<App />); await choose(); await open(); recipient(); fireEvent.click(issueButton());
  fireEvent.click(await screen.findByRole('button', { name: 'Retry original invitation' }));
  await screen.findByText(/Only the current team leader can issue invitations. Refresh/);
  expect((screen.getByLabelText('Recipient account UUID') as HTMLInputElement).readOnly).toBe(true);
  expect(screen.queryByRole('button', { name: 'Start another invitation' })).toBe(null); expect(s.posts()).toHaveLength(2);
});

it('hides issuance after the server rejects stale leadership and canonical team leadership changes', async () => {
  const s = server(true, (url, o) => { if (url === issuePath() && o.method === 'POST') { s.model.leader = OTHER; return failure(403, 'forbidden'); } });
  render(<App />); await choose(); await open(); recipient(); fireEvent.click(issueButton());
  await screen.findByText('Only the current team leader can issue invitations.'); expect(screen.queryByLabelText('Recipient account UUID')).toBe(null);
});

it.each([403, 404, 503])('shows inbox access/service failure %s without fabricated invitations', async status => {
  server(false, url => url.includes('/invitations/mine?') ? failure(status) : undefined);
  render(<App />); await choose(); await inbox(); await screen.findByRole('alert'); expect(screen.queryByText('Invitation ' + I1)).toBe(null);
});

it('rejects a foreign recipient row before rendering its identifiers', async () => {
  server(false, url => url.includes('/invitations/mine?') ? json({ items: [invitation({ id: I2, recipient_id: OTHER })], next_cursor: null }) : undefined);
  render(<App />); await choose(); await inbox(); await screen.findByText(/unexpected response/);
  expect(document.body.textContent).not.toContain(I2); expect(document.body.textContent).not.toContain(OTHER);
});

it('uses bounded inbox pages and restarts an invalid cursor', async () => {
  let invalid = false;
  server(false, url => url.includes('/invitations/mine?') ? url.includes('cursor=')
    ? invalid ? failure(422, 'invalid_request') : json({ items: [invitation({ id: I2 })], next_cursor: null })
    : json({ items: [invitation()], next_cursor: I1 }) : undefined);
  render(<App />); await choose(); await inbox(); await ready(); fireEvent.click(screen.getByRole('button', { name: 'Next invitations' }));
  await screen.findByText('Invitation ' + I2); expect(screen.queryByText('Invitation ' + I1)).toBe(null);
  fireEvent.click(screen.getByRole('button', { name: 'Previous invitations' })); await screen.findByText('Invitation ' + I1);
  invalid = true; fireEvent.click(screen.getByRole('button', { name: 'Next invitations' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Restart invitation inbox' })); await screen.findByText('Invitation ' + I1);
  expect((screen.getByRole('button', { name: 'Previous invitations' }) as HTMLButtonElement).disabled).toBe(true);
});

it.each(['unavailable', 'redeemed', 'assigned'])('blocks new redemption for %s canonical state', async kind => {
  const s = server(); if (kind === 'assigned') s.model.membership = team();
  else s.model.inbox = [invitation(kind === 'redeemed' ? { status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z', available: false } : { available: false })];
  render(<App />); await choose(); await inbox(); await screen.findByText('Invitation ' + I1);
  expect((redeemButton() as HTMLButtonElement).disabled).toBe(true); fireEvent.click(redeemButton()); expect(s.posts()).toHaveLength(0);
});

it.each([200, 401])('discards old inbox response %s on hackathon switching', async status => {
  let finish!: (r: Response) => void;
  server(false, url => url === `/api/hackathons/${H1}/invitations/mine?limit=20` ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await inbox(); await screen.findByText('Loading your invitations…');
  await choose(true); await inbox(); await screen.findByText('No invitations on this page.');
  await act(async () => finish(status === 401 ? failure(401, 'invalid_session') : json({ items: [invitation()], next_cursor: null })));
  expect(screen.getByText('@test_builder')).toBeTruthy(); expect(screen.getByRole('heading', { name: 'Second Challenge' })).toBeTruthy();
  expect(screen.queryByText('Invitation ' + I1)).toBe(null);
});

it.each([['issue', 201], ['issue', 401], ['redeem', 200], ['redeem', 401]] as const)('ignores delayed %s %s after logout and a different account signs in', async (kind, status) => {
  let finish!: (r: Response) => void;
  const s = server(kind === 'issue', (url, o) => url.includes('/invitations') && o.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose();
  if (kind === 'issue') { await open(); recipient(); fireEvent.click(issueButton()); } else { await inbox(); await ready(); fireEvent.click(redeemButton()); }
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' })); await screen.findByLabelText('Username');
  s.model.session = { ...session(), identity: { user_id: OTHER, username: 'other_account' } }; s.model.leader = OTHER; login();
  await screen.findByText('@other_account'); await choose(); await inbox(); await screen.findByText('No invitations on this page.');
  await act(async () => finish(status === 401 ? failure(401, 'invalid_session') : json({ schema_version: 1, data: kind === 'issue'
    ? invitation({ recipient_id: OTHER, issued_by: U1 }) : invitation({ status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z' }) }, status)));
  expect(screen.getByText('@other_account')).toBeTruthy(); expect(screen.queryByText(/Original redemption for invitation/)).toBe(null);
  if (kind === 'issue') { fireEvent.click(screen.getByRole('button', { name: 'Discover teams' })); await open(); expect((screen.getByLabelText('Recipient account UUID') as HTMLInputElement).value).toBe(''); }
  expect(s.posts()).toHaveLength(1);
});

it.each(['issue', 'redeem'])('retries original %s with fresh CSRF after same-account reauthentication', async kind => {
  let attempts = 0;
  const s = server(kind === 'issue', (url, o) => url.includes('/invitations') && o.method === 'POST' && ++attempts === 1 ? new Promise<Response>(() => {}) : undefined);
  render(<App />); await choose();
  if (kind === 'issue') { await open(); recipient(); fireEvent.click(issueButton()); } else { await inbox(); await ready(); fireEvent.click(redeemButton()); }
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' })); await screen.findByLabelText('Username');
  s.model.session = { ...session(), csrf_token: 'C'.repeat(42) + 'A' }; login(); await screen.findByText('@test_builder'); await choose();
  if (kind === 'issue') await open(); else await inbox();
  fireEvent.click(await screen.findByRole('button', { name: kind === 'issue' ? 'Retry original invitation' : 'Retry original redemption ' + I1 }));
  await screen.findByText(kind === 'issue' ? /Invitation issuance confirmed/ : /^Redemption confirmed/);
  expect(s.posts()).toHaveLength(2);
  const headers = s.posts().map(([, o]) => o.headers as Record<string, string>);
  expect(headers[0]['Idempotency-Key']).toBe(headers[1]['Idempotency-Key']); expect(headers[1]['X-CSRF-Token']).toBe(s.model.session.csrf_token);
});

it('does not show an old-team issuance result in another team or hackathon', async () => {
  let finish!: (r: Response) => void;
  const s = server(true, (url, o) => url === issuePath() && o.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await open(); recipient(); fireEvent.click(issueButton());
  fireEvent.click(screen.getByRole('button', { name: /Back to teams/ })); await open(true);
  expect((screen.getByLabelText('Recipient account UUID') as HTMLInputElement).value).toBe('');
  await choose(true); await open();
  await act(async () => finish(json({ schema_version: 1, data: invitation({ recipient_id: OTHER, issued_by: U1 }) }, 201)));
  expect(screen.queryByText(/Invitation issuance confirmed/)).toBe(null);
  expect(screen.getByRole('heading', { name: 'Second Challenge' })).toBeTruthy(); expect(s.posts()).toHaveLength(1);
});

it('keeps cooldown across navigation and makes no automatic mutation retry', async () => {
  const s = server(false, (url, o) => url.endsWith('/redeem') && o.method === 'POST' ? failure(429, 'rate_limited', false, { 'Retry-After': '30' }) : undefined);
  render(<App />); await choose(); await inbox(); await ready(); fireEvent.click(redeemButton()); await screen.findByText(/Too many invitation attempts/);
  fireEvent.click(screen.getByRole('button', { name: 'Discover teams' })); await inbox(); await screen.findByText('Invitation ' + I1);
  expect((redeemButton() as HTMLButtonElement).disabled).toBe(true); expect(s.posts()).toHaveLength(1);
});

it('fails closed if secure key generation fails and exposes no platform details', async () => {
  const s = server(true); vi.spyOn(crypto, 'getRandomValues').mockImplementation(() => { throw new Error('private entropy detail'); });
  render(<App />); await choose(); await open(); recipient(); fireEvent.click(issueButton());
  await screen.findByText(/secure request key could not be generated/); expect(s.posts()).toHaveLength(0);
  expect(document.body.textContent).not.toContain('private entropy detail');
});

it.each(['invitation_expired', 'team_full'])('retains uncertain original redemption after a later %s', async code => {
  let attempts = 0;
  const s = server(false, (url, o) => url.endsWith('/redeem') && o.method === 'POST'
    ? ++attempts === 1 ? failure(503, 'outcome_uncertain', true) : failure(409, code) : undefined);
  render(<App />); await choose(); await inbox(); await ready(); fireEvent.click(redeemButton());
  fireEvent.click(await screen.findByRole('button', { name: 'Retry original redemption ' + I1 })); await screen.findByRole('alert');
  expect(screen.getByRole('button', { name: 'Retry original redemption ' + I1 })).toBeTruthy();
  expect(screen.getByText(/earlier outcome is still unknown/)).toBeTruthy();
  expect(s.posts()).toHaveLength(2); expect(s.posts()[0][1].headers).toEqual(s.posts()[1][1].headers);
});

it.each(['issue', 'redeem'])('does not confirm %s when a stored reply identifies another actor', async kind => {
  const s = server(kind === 'issue', (url, o) => url.includes('/invitations') && o.method === 'POST'
    ? json({ schema_version: 1, data: kind === 'issue' ? invitation({ recipient_id: OTHER, issued_by: OTHER })
      : invitation({ recipient_id: OTHER, status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z' }) }, kind === 'issue' ? 201 : 200) : undefined);
  render(<App />); await choose();
  if (kind === 'issue') { await open(); recipient(); fireEvent.click(issueButton()); } else { await inbox(); await ready(); fireEvent.click(redeemButton()); }
  await screen.findByText(/earlier outcome is still unknown/);
  expect(screen.queryByText(/issuance confirmed|^Redemption confirmed/)).toBe(null); expect(s.posts()).toHaveLength(1);
});

it('allows a corrected recipient after definite rejection with a distinct key', async () => {
  let attempts = 0;
  const s = server(true, (url, o) => url === issuePath() && o.method === 'POST' && ++attempts === 1 ? failure(404, 'recipient_not_found') : undefined);
  render(<App />); await choose(); await open(); recipient(); fireEvent.click(issueButton());
  await screen.findByText(/No recipient was found/); recipient(U1); fireEvent.click(issueButton()); await screen.findByText(/Invitation issuance confirmed/);
  expect(s.posts()).toHaveLength(2); expect(s.posts().map(([, o]) => o.body)).toEqual([JSON.stringify({ recipient_id: OTHER }), JSON.stringify({ recipient_id: U1 })]);
  const keys = s.posts().map(([, o]) => (o.headers as Record<string, string>)['Idempotency-Key']); expect(keys[0]).not.toBe(keys[1]);
});

it('gives distinct redemption commands different secure keys while guarding each pending invitation', async () => {
  const s = server(false, (url, o) => url.endsWith('/redeem') && o.method === 'POST' ? new Promise<Response>(() => {}) : undefined);
  s.model.inbox.push(invitation({ id: I2, team_id: T2 })); render(<App />); await choose(); await inbox(); await ready();
  const a = redeemButton(), b = redeemButton(I2); fireEvent.click(a); fireEvent.click(a); fireEvent.click(b); fireEvent.click(b);
  await waitFor(() => expect(s.posts()).toHaveLength(2));
  const keys = s.posts().map(([, o]) => (o.headers as Record<string, string>)['Idempotency-Key']);
  expect(keys.every(key => /^[0-9a-f]{64}$/.test(key))).toBe(true); expect(keys[0]).not.toBe(keys[1]);
});

it.each(['issue', 'redeem'])('does not let an old-hackathon %s 401 clear a newer selected workspace', async kind => {
  let finish!: (response: Response) => void;
  const s = server(kind === 'issue', (url, options) => url.includes('/invitations') && options.method === 'POST'
    ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose();
  if (kind === 'issue') { await open(); recipient(); fireEvent.click(issueButton()); }
  else { await inbox(); await ready(); fireEvent.click(redeemButton()); }
  await choose(true);
  expect(screen.queryByRole('heading', { name: 'Second Challenge' })).not.toBe(null);
  await act(async () => finish(failure(401, 'invalid_session')));
  expect(screen.queryByText('@test_builder')).not.toBe(null);
  expect(screen.queryByRole('heading', { name: 'Second Challenge' })).not.toBe(null);
  expect(s.posts()).toHaveLength(1);
});

it.each(['create', 'request', 'approve'])('does not let a related old-hackathon %s 401 clear a newer workspace', async kind => {
  let finish!: (response: Response) => void;
  const requestId = '00000000-0000-0000-0000-000000000031';
  server(kind === 'approve', (url, options) => {
    if (options.method === 'POST' && url.startsWith('/api/')) return new Promise(resolve => { finish = resolve; });
    if (kind === 'approve' && url.includes('/join-requests?')) return json({ items: [{ id: requestId,
      hackathon_id: H1, team_id: T1, requester_id: OTHER, status: 'pending', created_at: '2026-11-11T00:00:00Z', resolved_at: null }], next_cursor: null });
  });
  render(<App />); await choose();
  if (kind === 'create') {
    const button = screen.getByRole('button', { name: 'Create team' });
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    fireEvent.change(screen.getByLabelText('Team name'), { target: { value: 'Original creation' } }); fireEvent.click(button);
  } else {
    await open();
    const button = await screen.findByRole('button', { name: kind === 'request' ? 'Request membership' : 'Approve applicant ' + OTHER });
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(button);
  }
  await choose(true);
  expect(screen.queryByRole('heading', { name: 'Second Challenge' })).not.toBe(null);
  await act(async () => finish(failure(401, 'invalid_session')));
  expect(screen.queryByText('@test_builder')).not.toBe(null);
  expect(screen.queryByRole('heading', { name: 'Second Challenge' })).not.toBe(null);
});

type MutationKind = 'issue' | 'redeem' | 'create' | 'request' | 'approve';
const kinds: MutationKind[] = ['issue', 'redeem', 'create', 'request', 'approve'];
const requestRow = { id: '00000000-0000-0000-0000-000000000031', hackathon_id: H1, team_id: T1,
  requester_id: OTHER, status: 'pending', created_at: '2026-11-11T00:00:00Z', resolved_at: null };
function commandServer(kind: MutationKind, handler: Handler) {
  return server(kind === 'issue' || kind === 'approve', (url, options) => {
    const result = handler(url, options); if (result) return result;
    if (kind === 'approve' && url.includes('/join-requests?')) return json({ items: url.includes(T1) ? [requestRow] : [], next_cursor: null });
  });
}
async function startCommand(kind: MutationKind) {
  await choose();
  if (kind === 'create') {
    const button = screen.getByRole('button', { name: 'Create team' });
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    fireEvent.change(screen.getByLabelText('Team name'), { target: { value: 'Original creation' } }); fireEvent.click(button);
  } else if (kind === 'redeem') { await inbox(); await ready(); fireEvent.click(redeemButton()); }
  else {
    await open();
    if (kind === 'issue') { recipient(); fireEvent.click(issueButton()); }
    else {
      const button = await screen.findByRole('button', { name: kind === 'request' ? 'Request membership' : 'Approve applicant ' + OTHER });
      await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(button);
    }
  }
}
function commandReply(kind: MutationKind) {
  if (kind === 'create') return json(created(), 201);
  const row = kind === 'issue' ? invitation({ recipient_id: OTHER, issued_by: U1 })
    : kind === 'redeem' ? invitation({ status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z' })
    : { ...requestRow, requester_id: kind === 'request' ? U1 : OTHER, status: kind === 'request' ? 'pending' : 'approved',
      resolved_at: kind === 'request' ? null : '2026-11-11T01:00:00Z' };
  return json({ schema_version: 1, data: row }, kind === 'issue' || kind === 'request' ? 201 : 200);
}

it.each(kinds)('still expires a current-workspace %s after a documented 401', async kind => {
  commandServer(kind, (url, options) => options.method === 'POST' && url.startsWith('/api/') ? failure(401, 'invalid_session') : undefined);
  render(<App />); await startCommand(kind);
  await screen.findByText('Your session has ended. Sign in again.');
  expect(screen.queryByText('@test_builder')).toBe(null); expect(screen.getByLabelText('Username')).toBeTruthy();
});

it.each(['issue', 'redeem'] as const)('recovers the original uncertain %s after navigation away/back, a stale 401 and fresh CSRF', async kind => {
  let attempts = 0, finish!: (response: Response) => void;
  const s = commandServer(kind, (url, options) => {
    if (options.method === 'POST' && url.startsWith('/api/')) {
      attempts++;
      if (attempts === 1) return failure(503, 'outcome_uncertain', true);
      if (attempts === 2) return new Promise(resolve => { finish = resolve; });
      return commandReply(kind);
    }
  });
  render(<App />); await startCommand(kind);
  const retryName = kind === 'issue' ? 'Retry original invitation' : 'Retry original redemption ' + I1;
  fireEvent.click(await screen.findByRole('button', { name: retryName }));
  await choose(true); await choose(); if (kind === 'issue') await open(); else await inbox();
  await act(async () => finish(failure(401, 'invalid_session')));
  expect(screen.getByText('@test_builder')).toBeTruthy(); await screen.findByRole('button', { name: retryName });
  s.model.session = { ...session(), csrf_token: 'C'.repeat(42) + 'A' };
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' })); await screen.findByLabelText('Username'); login();
  await screen.findByText('@test_builder'); await choose(); if (kind === 'issue') await open(); else await inbox();
  fireEvent.click(await screen.findByRole('button', { name: retryName }));
  await screen.findByText(kind === 'issue' ? /Invitation issuance confirmed/ : /^Redemption confirmed/);
  const posts = s.posts(); expect(posts).toHaveLength(3);
  expect(new Set(posts.map(([url]) => url)).size).toBe(1); expect(new Set(posts.map(([, o]) => o.body)).size).toBe(1);
  expect(new Set(posts.map(([, o]) => (o.headers as Record<string, string>)['Idempotency-Key'])).size).toBe(1);
  expect((posts[2][1].headers as Record<string, string>)['X-CSRF-Token']).toBe(s.model.session.csrf_token);
});

it.each([201, 401, 409])('keeps the selected team draft and reads unchanged after an old-team issue response %s', async status => {
  let finish!: (response: Response) => void;
  const s = commandServer('issue', (url, options) => url === issuePath() && options.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await startCommand('issue');
  fireEvent.click(screen.getByRole('button', { name: /Back to teams/ })); await open(true); recipient(U1);
  const reads = () => s.fetch.mock.calls.filter(([url, o]) => url.startsWith('/api/') && o.method === 'GET').length;
  const before = reads();
  await act(async () => finish(status === 201 ? commandReply('issue') : failure(status, status === 401 ? 'invalid_session' : 'idempotency_mismatch')));
  expect(screen.getByText('@test_builder')).toBeTruthy(); expect(screen.getByRole('heading', { name: 'Test Team Beta' })).toBeTruthy();
  expect((screen.getByLabelText('Recipient account UUID') as HTMLInputElement).value).toBe(U1);
  expect(reads()).toBe(before); expect(screen.queryByText(/Invitation issuance confirmed/)).toBe(null);
});

it.each([200, 409])('does not refresh selected detail after an old-inbox redemption response %s', async status => {
  let finish!: (response: Response) => void;
  const s = commandServer('redeem', (url, options) => url.endsWith('/redeem') && options.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await startCommand('redeem'); fireEvent.click(screen.getByRole('button', { name: 'View invited team ' + T1 }));
  await screen.findByText('Public leader');
  await waitFor(() => expect((screen.getByRole('button', { name: 'Request membership' }) as HTMLButtonElement).disabled).toBe(false));
  const reads = () => s.fetch.mock.calls.filter(([url, o]) => url.startsWith('/api/') && o.method === 'GET').length;
  const before = reads(); await act(async () => finish(status === 200 ? commandReply('redeem') : failure(409, 'team_full')));
  expect(reads()).toBe(before); expect(screen.getByRole('heading', { name: 'Test Team Alpha' })).toBeTruthy();
  expect(screen.queryByText(/^Redemption confirmed/)).toBe(null);
});

it('keeps current 401 handling after an inbox refresh replaces read components', async () => {
  let finish!: (response: Response) => void;
  commandServer('redeem', (url, options) => url.endsWith('/redeem') && options.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await startCommand('redeem'); fireEvent.click(screen.getByRole('button', { name: 'Refresh inbox and membership' }));
  await screen.findByText('Invitation ' + I1); await act(async () => finish(failure(401, 'invalid_session')));
  await screen.findByLabelText('Username'); expect(screen.queryByText('@test_builder')).toBe(null);
});

it('owns a committed workspace after StrictMode setup-cleanup-setup', async () => {
  const s = commandServer('issue', () => undefined); render(<StrictMode><App /></StrictMode>); await startCommand('issue');
  await screen.findByText(/Invitation issuance confirmed/); expect(s.posts()).toHaveLength(1);
});
