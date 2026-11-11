import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { type JoinRequest, type Team, type Session } from './api';
import { csrf, failure, H1, H2, hackathon, json, session, T1, T2, team, U1 } from './test/fixtures';

const OTHER = '00000000-0000-0000-0000-000000000022';
const R1 = '00000000-0000-0000-0000-000000000031', R2 = '00000000-0000-0000-0000-000000000032';
const path = (t = T1, h = H1) => `/api/hackathons/${h}/teams/${t}/join-requests`;
function row(overrides: Partial<JoinRequest> = {}): JoinRequest {
  return { id: R1, hackathon_id: H1, team_id: T1, requester_id: U1, status: 'pending',
    created_at: '2026-11-11T00:00:00Z', resolved_at: null, ...overrides };
}
type Handler = (url: string, options: RequestInit) => Response | Promise<Response> | undefined;
function server(leader = false, handler: Handler = () => undefined) {
  const model = { session: session() as Session, leader: leader ? U1 : OTHER, own: null as JoinRequest | null,
    membership: null as Team | null, pending: [row({ requester_id: OTHER })], count: 2 };
  const fetch = vi.fn((url: string, options: RequestInit) => {
    const custom = handler(url, options);
    if (custom) return Promise.resolve(custom);
    const publicTeam = (id = T1, h = H1) => ({ ...team(id, h), leader: { user_id: model.leader, display_name: 'Public leader' }, member_count: model.count });
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/auth/session' || url === '/auth/login') return Promise.resolve(json(model.session));
    if (url === '/auth/logout') return Promise.resolve(new Response(null, { status: 204 }));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon(), hackathon(H2)], next_cursor: null }));
    const h = url.includes(H2) ? H2 : H1, t = url.includes(T2) ? T2 : T1;
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: [publicTeam(T1, h), publicTeam(T2, h)], next_cursor: null }));
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: model.membership }));
    if (url.endsWith('/teams/' + t)) return Promise.resolve(json(publicTeam(t, h)));
    if (url.endsWith('/join-requests/mine')) return Promise.resolve(json({ request: model.own?.team_id === t && model.own?.hackathon_id === h ? model.own : null }));
    if (url.includes('/join-requests?')) return Promise.resolve(json({ items: model.pending.filter(r => r.team_id === t && r.hackathon_id === h), next_cursor: null }));
    if (url.endsWith('/join-requests') && options.method === 'POST') {
      model.own = row({ team_id: t, hackathon_id: h, requester_id: model.session.identity.user_id });
      return Promise.resolve(json({ schema_version: 1, data: model.own }, 201));
    }
    if (url.endsWith('/decision') && options.method === 'POST') {
      const requestId = url.split('/').at(-2)!;
      const decision = JSON.parse(options.body as string).decision;
      const saved = model.pending.find(r => r.id === requestId)!;
      model.pending = model.pending.filter(r => r.id !== requestId);
      if (decision === 'approve') model.count = 3;
      return Promise.resolve(json({ schema_version: 1, data: { ...saved, status: decision === 'approve' ? 'approved' : 'rejected', resolved_at: '2026-11-11T01:00:00Z' } }));
    }
    throw new Error('Unexpected mocked endpoint');
  });
  vi.stubGlobal('fetch', fetch);
  return { model, fetch, posts: () => fetch.mock.calls.filter(([url, options]) => url.includes('/join-requests') && options.method === 'POST') };
}
async function choose(second = false) {
  fireEvent.click(await screen.findByRole('button', { name: second ? /Second Challenge/ : /Test Challenge/ }));
  await screen.findByRole('button', { name: /View Test Team Alpha/ });
}
async function open(second = false) {
  fireEvent.click(await screen.findByRole('button', { name: second ? /View Test Team Beta/ : /View Test Team Alpha/ }));
  await screen.findByText('Public leader');
}
async function memberReady() { await waitFor(() => expect((screen.getByRole('button', { name: 'Request membership' }) as HTMLButtonElement).disabled).toBe(false)); }
const approve = () => screen.getByRole('button', { name: 'Approve applicant ' + OTHER });
function login() {
  fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'test_builder' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'synthetic admission password' } });
  fireEvent.click(screen.getByRole('button', { name: /Sign in to Merge/ }));
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

it('requests with exact CSRF/key/body, refetches canonical status and prevents duplicate creation', async () => {
  const s = server(); render(<App />); await choose(); await open(); await memberReady();
  const storage = vi.spyOn(Storage.prototype, 'setItem');
  const button = screen.getByRole('button', { name: 'Request membership' }); button.focus();
  expect(document.activeElement).toBe(button); expect(button.tagName).toBe('BUTTON');
  fireEvent.click(button); fireEvent.click(button);
  await screen.findByText('pending');
  expect(s.posts()).toHaveLength(1);
  expect(s.posts()[0]).toEqual([path(), expect.objectContaining({ body: '{}', credentials: 'same-origin', headers: {
    Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'Idempotency-Key': expect.stringMatching(/^[0-9a-f]{64}$/) } })]);
  expect((screen.getByRole('button', { name: 'Request membership' }) as HTMLButtonElement).disabled).toBe(true);
  expect(s.fetch.mock.calls.filter(([url]) => url === path() + '/mine').length).toBeGreaterThanOrEqual(2);
  expect(s.fetch.mock.calls.some(([url]) => url === path() + '?limit=20')).toBe(false);
  expect(document.body.textContent).not.toContain(csrf); expect(storage).not.toHaveBeenCalled();
});

it.each(['pending', 'approved', 'rejected'] as const)('displays canonical %s status without creating or inventing membership', async status => {
  const s = server(); s.model.own = row({ status, resolved_at: status === 'pending' ? null : '2026-11-11T01:00:00Z' });
  render(<App />); await choose(); await open(); await screen.findByText(status);
  expect((screen.getByRole('button', { name: 'Request membership' }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  await screen.findByText('You haven’t joined a team in this hackathon.');
  expect(s.posts()).toHaveLength(0);
});

it.each(['present', 'unknown'])('blocks new requests with %s membership', async kind => {
  const s = server(false, url => kind === 'unknown' && url.endsWith('/me/team') ? failure(503, 'service_unavailable') : undefined);
  if (kind === 'present') s.model.membership = { ...team(), readiness: 'ready' };
  render(<App />); await choose(); await open();
  await screen.findByRole('heading', { name: 'Your join request' });
  expect((screen.getByRole('button', { name: 'Request membership' }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Request membership' })); expect(s.posts()).toHaveLength(0);
});

it('does not claim the stored response is canonical current status', async () => {
  const s = server(false, (url, options) => url === path() && options.method === 'POST'
    ? json({ schema_version: 1, data: row() }, 201) : undefined);
  render(<App />); await choose(); await open(); await memberReady(); fireEvent.click(screen.getByRole('button', { name: 'Request membership' }));
  await screen.findByText(/Command confirmed/);
  expect(screen.queryByText('pending')).toBe(null); expect(s.posts()).toHaveLength(1);
});

it.each(['approve', 'reject'])('lets a leader %s once and refreshes canonical detail/list/membership', async decision => {
  const s = server(true); render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER);
  const button = decision === 'approve' ? approve() : screen.getByRole('button', { name: 'Reject applicant ' + OTHER });
  fireEvent.click(button); fireEvent.click(button);
  await screen.findByText(/Decision confirmed/); await screen.findByText('No pending requests on this page.');
  expect(s.posts()).toHaveLength(1); expect(s.posts()[0][0]).toBe(path() + '/' + R1 + '/decision');
  expect(s.posts()[0][1].body).toBe(JSON.stringify({ decision }));
  expect(s.fetch.mock.calls.filter(([url]) => url.endsWith('/me/team')).length).toBeGreaterThanOrEqual(2);
  expect(s.fetch.mock.calls.filter(([url]) => url.endsWith('/teams/' + T1)).length).toBeGreaterThanOrEqual(2);
  fireEvent.click(screen.getByRole('button', { name: /Back to teams/ })); await screen.findByRole('heading', { name: 'Test Team Alpha' });
  expect(s.fetch.mock.calls.filter(([url]) => url.endsWith('/teams?limit=20')).length).toBeGreaterThanOrEqual(2);
  expect(screen.getAllByText(decision === 'approve' ? '3/4 members' : '2/4 members').length).toBeGreaterThan(0);
});

it('offers request review through canonical My Team', async () => {
  const s = server(true); s.model.membership = { ...team(), readiness: 'ready' }; render(<App />); await choose();
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Open team and requests' }));
  await screen.findByText('Applicant ' + OTHER); expect(approve()).toBeTruthy();
});

it.each([403, 404])('hides all applicants when pending access returns %s', async status => {
  const s = server(true, url => url.includes('/join-requests?') ? failure(status, 'forbidden') : undefined);
  render(<App />); await choose(); await open(); await screen.findByText(/Permission could not be confirmed/);
  expect(screen.queryByText('Applicant ' + OTHER)).toBe(null); expect(screen.queryByRole('button', { name: /Approve applicant/ })).toBe(null);
  expect(s.posts()).toHaveLength(0);
});

it.each(['team_full', 'already_assigned', 'request_resolved'])('handles documented conflict %s without a success claim', async code => {
  const s = server(true, (url, options) => {
    if (url.endsWith('/decision') && options.method === 'POST') {
      if (code === 'request_resolved') s.model.pending = [];
      return failure(409, code);
    }
  });
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER); fireEvent.click(approve());
  await screen.findByRole('alert');
  await waitFor(() => expect(document.body.textContent).toMatch(code === 'team_full' ? /team is full/ : code === 'already_assigned' ? /already belongs/ : /already resolved/));
  expect(screen.queryByText(/Decision confirmed/)).toBe(null); expect(s.posts()).toHaveLength(1);
});

it('removes applicant details immediately after a denied decision and leadership refresh', async () => {
  const s = server(true, (url, options) => {
    if (url.endsWith('/decision') && options.method === 'POST') { s.model.leader = OTHER; return failure(403, 'forbidden'); }
  });
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER); fireEvent.click(approve());
  await screen.findByText('Current team leadership is required. Applicant details are hidden.');
  expect(screen.queryByText('Applicant ' + OTHER)).toBe(null); expect(screen.queryByRole('button', { name: /Approve applicant/ })).toBe(null);
});

it.each(['outcome_uncertain', 'network', 'invalid-reply'])('preserves the exact request key after %s', async kind => {
  let calls = 0;
  const s = server(false, (url, options) => {
    if (url === path() && options.method === 'POST' && ++calls === 1) return kind === 'network' ? Promise.reject(new Error('private'))
      : kind === 'invalid-reply' ? json({ schema_version: 1, data: row({ requester_id: OTHER }) }, 201) : failure(503, 'outcome_uncertain', true);
  });
  render(<App />); await choose(); await open(); await memberReady(); fireEvent.click(screen.getByRole('button', { name: 'Request membership' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Retry original join request' })); await screen.findByText('pending');
  expect(s.posts()).toHaveLength(2); expect(s.posts()[0][1].headers).toEqual(s.posts()[1][1].headers);
  expect(s.posts()[0][1].body).toBe(s.posts()[1][1].body);
  expect(document.body.textContent).not.toContain('private');
});

it.each(['approve', 'reject'])('keeps uncertain %s reachable after the pending row disappears', async decision => {
  let calls = 0;
  const s = server(true, (url, options) => {
    if (url.endsWith('/decision') && options.method === 'POST') {
      if (++calls === 1) { s.model.pending = []; return failure(503, 'outcome_uncertain', true); }
      return json({ schema_version: 1, data: row({ requester_id: OTHER, status: decision === 'approve' ? 'approved' : 'rejected', resolved_at: '2026-11-11T01:00:00Z' }) });
    }
  });
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER);
  fireEvent.click(decision === 'approve' ? approve() : screen.getByRole('button', { name: 'Reject applicant ' + OTHER }));
  await screen.findByRole('button', { name: /Retry original/ }); fireEvent.click(screen.getByRole('button', { name: 'Refresh requests and team' }));
  await screen.findByText('No pending requests on this page.');
  expect(screen.queryByRole('button', { name: /Approve applicant/ })).toBe(null);
  fireEvent.click(screen.getByRole('button', { name: decision === 'approve' ? 'Retry original approval' : 'Retry original rejection' }));
  await screen.findByText(/Decision confirmed/);
  expect(s.posts()).toHaveLength(2); expect(s.posts()[0][1].body).toBe(s.posts()[1][1].body); expect(s.posts()[0][1].headers).toEqual(s.posts()[1][1].headers);
});

it('keeps uncertainty sticky across a later definite error and never enables the opposite decision', async () => {
  let calls = 0;
  const s = server(true, (url, options) => url.endsWith('/decision') && options.method === 'POST'
    ? ++calls === 1 ? failure(503, 'outcome_uncertain', true) : failure(409, 'team_full') : undefined);
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER); fireEvent.click(approve());
  fireEvent.click(await screen.findByRole('button', { name: 'Retry original approval' }));
  await screen.findByText(/team is full/); expect(screen.queryByRole('button', { name: /Reject applicant/ })).toBe(null);
  expect(await screen.findByRole('button', { name: 'Retry original approval' })).toBeTruthy(); expect(s.posts()).toHaveLength(2);
});

it.each(['team', 'hackathon'])('isolates delayed request completion during %s switching', async kind => {
  let finish!: (response: Response) => void;
  const s = server(false, (url, options) => url === path() && options.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await open(); await memberReady(); fireEvent.click(screen.getByRole('button', { name: 'Request membership' }));
  if (kind === 'team') { fireEvent.click(screen.getByRole('button', { name: /Back to teams/ })); await open(true); }
  else { await choose(true); await open(true); }
  await memberReady();
  await act(async () => finish(json({ schema_version: 1, data: row() }, 201)));
  await screen.findByText('Public leader');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Request membership' })).toBeTruthy());
  expect(screen.queryByText(/Command confirmed/)).toBe(null); expect(screen.queryByText('pending')).toBe(null);
  expect(s.posts()).toHaveLength(1); expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(kind === 'team' ? 'Test Challenge' : 'Second Challenge');
});

it.each([201, 401])('ignores late mutation %s after logout and another account signs in', async status => {
  let finish!: (response: Response) => void;
  const s = server(false, (url, options) => url === path() && options.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await open(); await memberReady(); fireEvent.click(screen.getByRole('button', { name: 'Request membership' }));
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' })); await screen.findByLabelText('Username');
  s.model.session = { ...session(), identity: { user_id: OTHER, username: 'other_account' } }; s.model.leader = U1;
  login(); await screen.findByText('@other_account'); await choose(); await open(); await memberReady();
  await act(async () => finish(status === 201 ? json({ schema_version: 1, data: row() }, 201) : failure(401, 'invalid_session')));
  expect(screen.getByText('@other_account')).toBeTruthy(); expect(screen.queryByRole('button', { name: 'Retry original join request' })).toBe(null);
  expect(screen.queryByText(/Command confirmed/)).toBe(null); expect(s.posts()).toHaveLength(1);
});

it('retries a cancelled same-account command with the original key and current session CSRF', async () => {
  let calls = 0;
  const s = server(false, (url, options) => url === path() && options.method === 'POST' && ++calls === 1 ? new Promise<Response>(() => {}) : undefined);
  render(<App />); await choose(); await open(); await memberReady(); fireEvent.click(screen.getByRole('button', { name: 'Request membership' }));
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' })); await screen.findByLabelText('Username');
  s.model.session = { ...session(), csrf_token: 'B'.repeat(42) + 'A' }; login(); await screen.findByText('@test_builder');
  await choose(); await open(); fireEvent.click(await screen.findByRole('button', { name: 'Retry original join request' })); await screen.findByText('pending');
  expect(s.posts()).toHaveLength(2);
  const headers = s.posts().map(([, options]) => options.headers as Record<string, string>);
  expect(headers[0]['Idempotency-Key']).toBe(headers[1]['Idempotency-Key']);
  expect(headers[1]['X-CSRF-Token']).toBe(s.model.session.csrf_token);
});

it('bounds leader pagination and clears applicants from previous pages', async () => {
  server(true, url => url.includes('/join-requests?') ? json(url.includes('cursor=')
    ? { items: [row({ id: R2, requester_id: H2 })], next_cursor: null }
    : { items: [row({ requester_id: OTHER })], next_cursor: R1 }) : undefined);
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER);
  fireEvent.click(screen.getByRole('button', { name: 'Next requests' })); await screen.findByText('Applicant ' + H2);
  expect(screen.queryByText('Applicant ' + OTHER)).toBe(null);
  fireEvent.click(screen.getByRole('button', { name: 'Previous requests' })); await screen.findByText('Applicant ' + OTHER);
  const panel = within(screen.getByRole('region', { name: 'Leader join requests' }));
  expect((panel.getByRole('button', { name: 'Previous requests' }) as HTMLButtonElement).disabled).toBe(true);
});

it('permits a different decision only after definite rollback and gives it a new key', async () => {
  let calls = 0;
  const s = server(true, (url, options) => url.endsWith('/decision') && options.method === 'POST' && ++calls === 1 ? failure(409, 'team_full') : undefined);
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER); fireEvent.click(approve());
  await screen.findByText(/team is full/); fireEvent.click(screen.getByRole('button', { name: 'Reject applicant ' + OTHER }));
  await screen.findByText(/Decision confirmed/);
  const headers = s.posts().map(([, options]) => options.headers as Record<string, string>);
  expect(headers[0]['Idempotency-Key']).not.toBe(headers[1]['Idempotency-Key']);
  expect(s.posts().map(([, options]) => options.body)).toEqual(['{"decision":"approve"}', '{"decision":"reject"}']);
});

it('blocks opposite and duplicate decisions while approval is in flight', async () => {
  let finish!: (response: Response) => void;
  const s = server(true, (url, options) => url.endsWith('/decision') && options.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER);
  const yes = approve(), no = screen.getByRole('button', { name: 'Reject applicant ' + OTHER });
  fireEvent.click(yes); fireEvent.click(no); fireEvent.click(yes);
  expect(s.posts()).toHaveLength(1); expect((no as HTMLButtonElement).disabled).toBe(true);
  s.model.pending = [];
  await act(async () => finish(json({ schema_version: 1, data: row({ requester_id: OTHER, status: 'approved', resolved_at: '2026-11-11T01:00:00Z' }) })));
  await screen.findByText(/Decision confirmed/);
});

it.each([200, 401])('does not let a late leader decision %s affect another account or show its applicants', async status => {
  let finish!: (response: Response) => void;
  const s = server(true, (url, options) => url.endsWith('/decision') && options.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER); fireEvent.click(approve());
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' })); await screen.findByLabelText('Username');
  s.model.session = { ...session(), identity: { user_id: OTHER, username: 'other_account' } };
  login(); await screen.findByText('@other_account'); await choose(); await open(); await memberReady();
  await act(async () => finish(status === 401 ? failure(401, 'invalid_session') : json({ schema_version: 1, data: row({ requester_id: OTHER, status: 'approved', resolved_at: '2026-11-11T01:00:00Z' }) })));
  expect(screen.getByText('@other_account')).toBeTruthy(); expect(screen.queryByRole('region', { name: 'Leader join requests' })).toBe(null);
  expect(screen.queryByText('Applicant ' + OTHER)).toBe(null); expect(s.posts()).toHaveLength(1);
});

it('restores the original leader decision after sign-in with a fresh CSRF token', async () => {
  let calls = 0;
  const s = server(true, (url, options) => url.endsWith('/decision') && options.method === 'POST' && ++calls === 1 ? new Promise<Response>(() => {}) : undefined);
  render(<App />); await choose(); await open(); await screen.findByText('Applicant ' + OTHER); fireEvent.click(approve());
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' })); await screen.findByLabelText('Username');
  s.model.session = { ...session(), csrf_token: 'C'.repeat(42) + 'A' }; login(); await screen.findByText('@test_builder');
  await choose(); await open(); fireEvent.click(await screen.findByRole('button', { name: 'Retry original approval' }));
  await screen.findByText(/Decision confirmed/);
  const headers = s.posts().map(([, options]) => options.headers as Record<string, string>);
  expect(headers[0]['Idempotency-Key']).toBe(headers[1]['Idempotency-Key']); expect(headers[1]['X-CSRF-Token']).toBe(s.model.session.csrf_token);
});

it('clears leader list reads on team navigation, including delayed unauthorized responses', async () => {
  let finish!: (response: Response) => void;
  server(true, url => url === path() + '?limit=20' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await open(); await screen.findByText('Loading pending requests…');
  fireEvent.click(screen.getByRole('button', { name: /Back to teams/ })); await open(true); await screen.findByText('No pending requests on this page.');
  await act(async () => finish(failure(401, 'invalid_session')));
  expect(screen.getByText('@test_builder')).toBeTruthy(); expect(screen.getByRole('heading', { name: 'Test Team Beta' })).toBeTruthy();
});

it('keeps a rate-limit cooldown across navigation without automatic resubmission', async () => {
  const s = server(false, (url, options) => url === path() && options.method === 'POST'
    ? failure(429, 'rate_limited', false, { 'Retry-After': '30' }) : undefined);
  render(<App />); await choose(); await open(); await memberReady(); fireEvent.click(screen.getByRole('button', { name: 'Request membership' }));
  await screen.findByText(/Too many attempts/);
  fireEvent.click(screen.getByRole('button', { name: /Back to teams/ })); await open();
  expect((screen.getByRole('button', { name: 'Request membership' }) as HTMLButtonElement).disabled).toBe(true);
  expect(s.posts()).toHaveLength(1);
});

it('does not render another account request returned by the own-status endpoint', async () => {
  const s = server(false, url => url.endsWith('/join-requests/mine') ? json({ request: row({ requester_id: OTHER }) }) : undefined);
  render(<App />); await choose(); await open(); await screen.findByText(/unexpected response/);
  expect(screen.queryByText('pending')).toBe(null); expect((screen.getByRole('button', { name: 'Request membership' }) as HTMLButtonElement).disabled).toBe(true);
  expect(document.body.textContent).not.toContain(OTHER); expect(s.posts()).toHaveLength(0);
});

it('discards pending applicants when switching to another team, including a late successful read', async () => {
  let finish!: (response: Response) => void;
  server(true, url => url === path() + '?limit=20' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await open(); await screen.findByText('Loading pending requests…');
  fireEvent.click(screen.getByRole('button', { name: /Back to teams/ })); await open(true); await screen.findByText('No pending requests on this page.');
  await act(async () => finish(json({ items: [row({ requester_id: OTHER })], next_cursor: null })));
  expect(screen.queryByText('Applicant ' + OTHER)).toBe(null); expect(screen.getByRole('heading', { name: 'Test Team Beta' })).toBeTruthy();
});

it('fails closed if secure key generation is unavailable', async () => {
  const s = server();
  vi.spyOn(globalThis.crypto, 'getRandomValues').mockImplementation(() => { throw new Error('private platform detail'); });
  render(<App />); await choose(); await open(); await memberReady(); fireEvent.click(screen.getByRole('button', { name: 'Request membership' }));
  await screen.findByText(/secure request key could not be generated/);
  expect(s.posts()).toHaveLength(0); expect(document.body.textContent).not.toContain('private platform detail');
});
