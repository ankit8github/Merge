import { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { emptyNavigation, NAVIGATION_KEY, useDiscoveryNavigation } from './hooks/useDiscoveryNavigation';
import { failure, H1, H2, hackathon, json, session, T1, T2, team, U1 } from './test/fixtures';

const OTHER = '00000000-0000-0000-0000-000000000022';
const ZERO = '00000000-0000-0000-0000-000000000000';
type Handler = (url: string, options: RequestInit) => Response | Promise<Response> | undefined;
function server(handler: Handler = () => undefined) {
  const model = { user: U1, valid: true };
  const fetch = vi.fn((url: string, options: RequestInit) => {
    const custom = handler(url, options); if (custom) return Promise.resolve(custom);
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/auth/session') return Promise.resolve(model.valid ? json({ ...session(), identity: { user_id: model.user, username: model.user === U1 ? 'test_builder' : 'another_builder' } }) : failure(401));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon()], next_cursor: H1 }));
    if (url === '/api/hackathons?limit=20&cursor=' + H1) return Promise.resolve(json({ items: [hackathon(H2)], next_cursor: null }));
    if (url.startsWith('/api/hackathons?limit=1&cursor=')) {
      const id = url.endsWith(ZERO) ? H1 : H2;
      return Promise.resolve(json({ items: [hackathon(id)], next_cursor: null }));
    }
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: null }));
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: [team()], next_cursor: T1 }));
    if (url.endsWith('/teams?limit=20&cursor=' + T1)) return Promise.resolve(json({ items: [team(T2)], next_cursor: null }));
    if (url.endsWith('/teams/' + T1)) return Promise.resolve(json(team()));
    if (url.endsWith('/join-requests?limit=20')) return Promise.resolve(json({ items: [], next_cursor: null }));
    if (url.endsWith('/invitations/mine?limit=20')) return Promise.resolve(json({ items: [], next_cursor: null }));
    throw new Error('Unexpected offline test URL');
  });
  vi.stubGlobal('fetch', fetch); return { model, fetch };
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const catalog = () => within(screen.getByRole('complementary', { name: 'Hackathons' }));
const workspace = () => within(screen.getByRole('region', { name: 'Team workspace' }));
async function choose() {
  await screen.findByRole('complementary', { name: 'Hackathons' });
  fireEvent.click(await catalog().findByRole('button', { name: /Test Challenge/ }));
  await workspace().findByRole('heading', { name: 'Test Team Alpha' });
}
const stored = () => JSON.parse(window.sessionStorage.getItem(NAVIGATION_KEY)!);
function seed(value = { ...emptyNavigation(), hackathon: H1 }) {
  window.sessionStorage.setItem(NAVIGATION_KEY, JSON.stringify({ version: 1, owner: U1, generation: 7, value }));
}

it('restores selection and My team after a reload-style remount only after fresh permission checks', async () => {
  let permission!: (response: Response) => void, check = false;
  const { fetch } = server(url => check && url.endsWith('/me/team') ? new Promise<Response>(resolve => { permission = resolve; }) : undefined);
  const first = render(<App />); await choose(); fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  await screen.findByText('Your current membership in Test Challenge.'); first.unmount(); check = true;
  render(<App />); await screen.findByText('Restoring hackathon access…');
  await waitFor(() => expect(permission).toBeTypeOf('function'));
  expect(screen.queryByLabelText('Team name')).toBe(null);
  check = false; await act(async () => permission(json({ team: null })));
  await screen.findByText('Your current membership in Test Challenge.');
  expect(fetch.mock.calls.some(([url]) => url === '/api/hackathons?limit=1&cursor=' + ZERO)).toBe(true);
  expect(fetch.mock.calls.every(([, options]) => !options.method || options.method === 'GET')).toBe(true);
});
it.each(['focus', 'pageshow', 'reload'])('preserves catalog/team pages and view across the %s session remount', async event => {
  server(); const app = render(<App />); await choose();
  fireEvent.click(workspace().getByRole('button', { name: /Next page/ })); await screen.findByRole('heading', { name: 'Test Team Beta' });
  fireEvent.click(catalog().getByRole('button', { name: /Next page/ })); await catalog().findByRole('button', { name: /Second Challenge/ });
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  if (event === 'reload') { app.unmount(); render(<App />); }
  else fireEvent(window, new Event(event));
  await screen.findByText('Your current membership in Test Challenge.');
  await catalog().findByRole('button', { name: /Second Challenge/ });
  fireEvent.click(screen.getByRole('button', { name: 'Discover teams' }));
  await screen.findByRole('heading', { name: 'Test Team Beta' });
  expect(stored().value).toMatchObject({ hackathon: H1, catalog: [null, H1], teams: [null, T1] });
});
it('restores Invitations view using fresh canonical reads', async () => {
  seed({ ...emptyNavigation(), hackathon: H1, view: 'invitations' });
  const { fetch } = server(); render(<App />);
  await screen.findByRole('heading', { name: 'Your invitations' });
  expect(fetch.mock.calls.some(([url]) => url.endsWith('/invitations/mine?limit=20'))).toBe(true);
});
it('uses browser Back/Forward history while revalidating the session and ignores former-account entries', async () => {
  const { fetch, model } = server(); render(<App />); await choose();
  const chosen = structuredClone(window.history.state);
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  const mine = structuredClone(window.history.state);
  const before = fetch.mock.calls.filter(([url]) => url === '/auth/session').length;
  fireEvent(window, new PopStateEvent('popstate', { state: chosen }));
  await screen.findByRole('heading', { name: 'Test Team Alpha' });
  expect(fetch.mock.calls.filter(([url]) => url === '/auth/session').length).toBeGreaterThan(before);
  fireEvent(window, new PopStateEvent('popstate', { state: mine }));
  await screen.findByText('Your current membership in Test Challenge.');
  model.user = OTHER; fireEvent(window, new Event('focus')); await screen.findByText('@another_builder');
  expect(stored().value.hackathon).toBe(null);
  fireEvent(window, new PopStateEvent('popstate', { state: chosen }));
  await screen.findByRole('heading', { name: 'Choose a hackathon.' });
  model.user = U1; fireEvent(window, new Event('focus')); await screen.findByText('@test_builder');
  fireEvent(window, new PopStateEvent('popstate', { state: mine }));
  await screen.findByRole('heading', { name: 'Choose a hackathon.' });
});
it.each(['missing', '403'])('discards a restored %s hackathon and never mounts mutation forms', async mode => {
  seed(); const { fetch } = server(url => {
    if (mode === 'missing' && url.startsWith('/api/hackathons?limit=1&')) return json({ items: [hackathon(H2)], next_cursor: null });
    if (mode === '403' && url.endsWith('/me/team')) return failure(403, 'browser_scope_rejected');
  });
  render(<App />); await screen.findByRole('alert');
  expect(screen.queryByLabelText('Team name')).toBe(null); expect(stored().value.hackathon).toBe(null);
  expect(fetch.mock.calls.every(([, options]) => !options.method || options.method === 'GET')).toBe(true);
});
it('retains the hint on a temporary network failure and requires explicit retry', async () => {
  seed(); let broken = true;
  const { fetch } = server(url => broken && url.startsWith('/api/hackathons?limit=1&') ? Promise.reject(new Error('private')) : undefined);
  render(<App />); const alert = await screen.findByRole('alert');
  expect(stored().value.hackathon).toBe(H1); expect(screen.queryByLabelText('Team name')).toBe(null);
  expect(fetch.mock.calls.filter(([url]) => url.startsWith('/api/hackathons?limit=1&'))).toHaveLength(1);
  broken = false; fireEvent.click(within(alert).getByRole('button', { name: 'Try again' }));
  await screen.findByRole('heading', { name: 'Test Team Alpha' });
});
it('does not let a late restored 401 sign out the next account', async () => {
  seed(); let finish!: (response: Response) => void;
  const { model } = server(url => url.startsWith('/api/hackathons?limit=1&') ? new Promise<Response>(resolve => { finish = resolve; }) : undefined);
  render(<App />); await waitFor(() => expect(finish).toBeTypeOf('function'));
  model.user = OTHER; fireEvent(window, new Event('focus')); await screen.findByText('@another_builder');
  await act(async () => finish(failure(401)));
  expect(screen.getByText('@another_builder')).toBeTruthy(); expect(stored().value.hackathon).toBe(null);
});
it('keeps lookup results separate from selected workspace and catalog page', async () => {
  const { fetch } = server(); render(<App />); await choose();
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  fireEvent.click(catalog().getByRole('button', { name: /Next page/ })); await catalog().findByRole('button', { name: /Second Challenge/ });
  fireEvent.change(screen.getByLabelText('Hackathon UUID'), { target: { value: H2 } });
  fireEvent.click(screen.getByRole('button', { name: 'Look up UUID' })); await screen.findByRole('button', { name: 'Select hackathon' });
  expect(screen.getByText('Your current membership in Test Challenge.')).toBeTruthy();
  expect(stored().value).toMatchObject({ hackathon: H1, view: 'mine', catalog: [null, H1] });
  expect(fetch.mock.calls.some(([url]) => url === `/api/hackathons/${H2}/me/team`)).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Select hackathon' }));
  await screen.findByRole('heading', { name: 'Second Challenge', level: 1 });
  expect(stored().value).toMatchObject({ hackathon: H2, view: 'discover', catalog: [null, H1], teams: [null] });
});
it.each(['invalid-json', 'bad-id', 'bad-cursor', 'oversized'])('rejects corrupt stored navigation: %s', async mode => {
  seed(); const record = stored();
  if (mode === 'bad-id') record.value.hackathon = 'not-an-id';
  if (mode === 'bad-cursor') record.value.catalog = [null, '/arbitrary/path'];
  window.sessionStorage.setItem(NAVIGATION_KEY, mode === 'invalid-json' ? '{' : mode === 'oversized' ? 'x'.repeat(256001) : JSON.stringify(record));
  const { fetch } = server(); render(<App />); await screen.findByRole('heading', { name: 'Choose a hackathon.' });
  expect(fetch.mock.calls.some(([url]) => url.includes('limit=1&'))).toBe(false);
});
it('persists only allowlisted public hints and clears them when authentication expires', async () => {
  const { model } = server(); render(<StrictMode><App /></StrictMode>); await choose();
  const text = window.sessionStorage.getItem(NAVIGATION_KEY)!;
  expect(Object.keys(stored()).sort()).toEqual(['generation', 'owner', 'value', 'version']);
  expect(Object.keys(stored().value).sort()).toEqual(['catalog', 'detail', 'hackathon', 'teams', 'view']);
  expect(text).not.toMatch(/csrf|password|session|token|idempotency|Test Challenge|Test Team/);
  expect(JSON.stringify(window.history.state)).not.toMatch(/csrf|password|session|token|idempotency/);
  model.valid = false; fireEvent(window, new Event('focus')); await screen.findByLabelText('Username');
  expect(stored().owner).toBe(null); expect(stored().value).toEqual(emptyNavigation());
});
it('continues in memory if browser storage/history writes are unavailable', async () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
  vi.spyOn(window.history, 'pushState').mockImplementation(() => { throw new Error('blocked'); });
  server(); render(<App />); await choose();
  fireEvent.click(screen.getByRole('button', { name: 'My team' })); await screen.findByText('Your current membership in Test Challenge.');
});
it('traverses real jsdom history entries with Back and Forward without reloading', async () => {
  const { fetch } = server(); render(<StrictMode><App /></StrictMode>); await choose();
  const pushes = vi.spyOn(window.history, 'pushState');
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  await screen.findByText('Your current membership in Test Challenge.');
  expect(pushes).toHaveBeenCalledTimes(1);
  await act(async () => { window.history.back(); });
  await screen.findByRole('heading', { name: 'Test Team Alpha' });
  await act(async () => { window.history.forward(); });
  await screen.findByText('Your current membership in Test Challenge.');
  expect(fetch.mock.calls.every(([, options]) => !options.method || options.method === 'GET')).toBe(true);
});
it('discards injected command/auth fields rather than restoring or rewriting them', async () => {
  seed(); const record = stored();
  record.session = { csrf_token: 'private-test-token' };
  record.value.pending = { operation: 'create_team', key: 'private-command-key', payload: { name: 'draft' } };
  window.sessionStorage.setItem(NAVIGATION_KEY, JSON.stringify(record));
  window.history.replaceState({ privateAuth: 'private-test-token', mergeDiscovery: record }, '');
  const { fetch } = server(); render(<App />); await screen.findByRole('heading', { name: 'Test Team Alpha' });
  const text = window.sessionStorage.getItem(NAVIGATION_KEY)!;
  expect(text).not.toMatch(/private|pending|payload|csrf|operation/);
  expect(JSON.stringify(window.history.state)).not.toMatch(/private|pending|payload|csrf|operation/);
  expect(fetch.mock.calls.every(([, options]) => !options.method || options.method === 'GET')).toBe(true);
});
it('requires a current session and clears navigation on a restored access 401', async () => {
  seed(); server(url => url.endsWith('/me/team') ? failure(401) : undefined);
  render(<App />); await screen.findByLabelText('Username');
  expect(stored().owner).toBe(null); expect(screen.queryByLabelText('Team name')).toBe(null);
});
it('handles a stale saved team cursor by showing an error and an explicit first-page recovery', async () => {
  seed({ ...emptyNavigation(), hackathon: H1, teams: [null, T1] });
  server(url => url.endsWith('/teams?limit=20&cursor=' + T1) ? failure(422, 'invalid_request') : undefined);
  render(<App />); await screen.findByRole('alert');
  fireEvent.click(screen.getByRole('button', { name: 'Restart from first page' }));
  await screen.findByRole('heading', { name: 'Test Team Alpha' }); expect(stored().value.teams).toEqual([null]);
});
it('validates a restored team detail through the scoped API and recovers from a stale team ID', async () => {
  seed({ ...emptyNavigation(), hackathon: H1, detail: T1 });
  const { fetch } = server(url => url.endsWith('/teams/' + T1) ? failure(404, 'team_not_found') : undefined);
  render(<App />); await screen.findByRole('alert');
  expect(screen.queryByRole('heading', { name: 'Test Team Alpha' })).toBe(null);
  fireEvent.click(screen.getByRole('button', { name: /Back to teams/ }));
  await screen.findByRole('heading', { name: 'Test Team Alpha' }); expect(stored().value.detail).toBe(null);
  expect(fetch.mock.calls.every(([, options]) => !options.method || options.method === 'GET')).toBe(true);
});
it('keeps newer navigation when an older workspace callback resets its page', () => {
  seed({ ...emptyNavigation(), hackathon: H1, teams: [null, T1] });
  const { result } = renderHook(() => useDiscoveryNavigation(U1));
  const oldReset = () => result.current.update(current => ({ ...current, teams: [null] }), false);
  act(() => {
    result.current.update(current => ({ ...current, view: 'mine' }));
    result.current.update(current => ({ ...current, catalog: [null, H1] }));
    oldReset();
  });
  expect(result.current.navigation).toMatchObject({ view: 'mine', catalog: [null, H1], teams: [null] });
});
it.each([U1, OTHER])('keeps the latest history destination and validated identity %s during session checking', async user => {
  let checking = false;
  const replies: ((response: Response) => void)[] = [];
  server(url => checking && url === '/auth/session' ? new Promise<Response>(resolve => { replies.push(resolve); }) : undefined);
  render(<App />); await choose();
  const discover = structuredClone(window.history.state);
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  const mine = structuredClone(window.history.state);
  fireEvent.click(screen.getByRole('button', { name: 'Invitations' }));
  await screen.findByRole('heading', { name: 'Your invitations' });
  checking = true;
  fireEvent(window, new PopStateEvent('popstate', { state: mine }));
  await screen.findByText('Restoring your session...');
  fireEvent(window, new PopStateEvent('popstate', { state: discover }));
  expect(stored().value.view).toBe('discover');
  expect(replies).toHaveLength(2);
  checking = false;
  await act(async () => replies[1](json({ ...session(), identity: { user_id: user, username: user === U1 ? 'test_builder' : 'another_builder' } })));
  if (user === U1) await screen.findByRole('heading', { name: 'Test Team Alpha' });
  else await screen.findByRole('heading', { name: 'Choose a hackathon.' });
  // The older request may ignore abort; its old identity must not win.
  await act(async () => replies[0](json({ ...session(), identity: { user_id: user === U1 ? OTHER : U1, username: user === U1 ? 'another_builder' : 'test_builder' } })));
  expect(screen.getByText(user === U1 ? '@test_builder' : '@another_builder')).toBeTruthy();
  expect(stored().owner).toBe(user);
  expect(stored().value.view).toBe('discover');
  expect(stored().value.hackathon).toBe(user === U1 ? H1 : null);
});
it.each([204, 503])('does not interrupt logout or restore old hints through history when logout returns %s', async status => {
  let finish!: (response: Response) => void;
  const { fetch } = server(url => url === '/auth/logout' ? new Promise<Response>(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); const old = structuredClone(window.history.state);
  const checks = fetch.mock.calls.filter(([url]) => url === '/auth/session').length;
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  await screen.findByRole('heading', { name: 'Signing out' });
  fireEvent(window, new Event('focus')); fireEvent(window, new Event('pageshow'));
  fireEvent(window, new PopStateEvent('popstate', { state: old }));
  expect(fetch.mock.calls.filter(([url]) => url === '/auth/session')).toHaveLength(checks);
  expect(stored().owner).toBe(null); expect(stored().value).toEqual(emptyNavigation());
  await act(async () => finish(status === 204 ? new Response(null, { status }) : failure(status)));
  if (status === 204) await screen.findByLabelText('Username');
  else await screen.findByText(/Sign-out is not confirmed/);
  expect(stored().value).toEqual(emptyNavigation());
  expect(fetch.mock.calls.filter(([, options]) => options.method === 'POST').map(([url]) => url)).toEqual(['/auth/logout']);
});
it.each(['missing', '403', 'network'])('leaves the selected workspace and page histories unchanged after lookup %s', async mode => {
  const { fetch } = server(url => {
    if (!url.startsWith('/api/hackathons?limit=1&')) return;
    if (mode === 'network') return Promise.reject(new Error('private transport'));
    return mode === '403' ? failure(403) : json({ items: [], next_cursor: null });
  });
  render(<App />); await choose(); fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  await screen.findByText('Your current membership in Test Challenge.');
  const before = structuredClone(stored().value);
  fireEvent.change(screen.getByLabelText('Hackathon UUID'), { target: { value: H2 } });
  fireEvent.click(screen.getByRole('button', { name: 'Look up UUID' }));
  if (mode === 'missing') await screen.findByText('No hackathon matches that UUID.');
  else await screen.findByRole('alert');
  expect(stored().value).toEqual(before);
  expect(screen.getByText('Your current membership in Test Challenge.')).toBeTruthy();
  expect(fetch.mock.calls.every(([, options]) => !options.method || options.method === 'GET')).toBe(true);
});
it.each([200, 401])('ignores a late catalog page %s after resetting pagination', async status => {
  let finish!: (response: Response) => void;
  const { fetch } = server(url => url === '/api/hackathons?limit=20&cursor=' + H1 ? new Promise<Response>(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose();
  fireEvent.click(catalog().getByRole('button', { name: /Next page/ }));
  await waitFor(() => expect(finish).toBeTypeOf('function'));
  fireEvent.click(catalog().getByRole('button', { name: 'Refresh' }));
  await catalog().findByRole('button', { name: /Test Challenge/ });
  await act(async () => finish(status === 200 ? json({ items: [hackathon(H2)], next_cursor: null }) : failure(401)));
  expect(catalog().queryByRole('button', { name: /Second Challenge/ })).toBe(null);
  expect(stored().value).toMatchObject({ hackathon: H1, catalog: [null] });
  expect(screen.getByText('@test_builder')).toBeTruthy();
  expect(fetch.mock.calls.every(([, options]) => !options.method || options.method === 'GET')).toBe(true);
});
it.each([200, 401, 403])('ignores a restored permission reply %s after an explicit new selection', async status => {
  seed(); let finish!: (response: Response) => void;
  const { fetch } = server(url => {
    if (url === `/api/hackathons/${H1}/me/team`) return new Promise<Response>(resolve => { finish = resolve; });
    if (url === `/api/hackathons/${H2}/teams?limit=20`) return json({ items: [], next_cursor: null });
  });
  render(<App />); await waitFor(() => expect(finish).toBeTypeOf('function'));
  fireEvent.click(catalog().getByRole('button', { name: /Next page/ }));
  fireEvent.click(await catalog().findByRole('button', { name: /Second Challenge/ }));
  await screen.findByRole('heading', { name: 'Second Challenge', level: 1 });
  await act(async () => finish(status === 200 ? json({ team: null }) : failure(status)));
  expect(stored().value.hackathon).toBe(H2);
  expect(screen.getByRole('heading', { name: 'Second Challenge', level: 1 })).toBeTruthy();
  expect(screen.getByText('@test_builder')).toBeTruthy();
  expect(fetch.mock.calls.every(([, options]) => !options.method || options.method === 'GET')).toBe(true);
});
it.each(['focus', 'pageshow'])('rechecks identity when %s arrives during a pending session check', async event => {
  seed(); const replies: ((response: Response) => void)[] = [];
  const { fetch } = server(url => url === '/auth/session' ? new Promise<Response>(resolve => { replies.push(resolve); }) : undefined);
  render(<App />); await waitFor(() => expect(replies).toHaveLength(1));
  fireEvent(window, new Event(event)); expect(replies).toHaveLength(2);
  await act(async () => replies[1](json({ ...session(), identity: { user_id: OTHER, username: 'another_builder' } })));
  await screen.findByText('@another_builder');
  await act(async () => replies[0](json(session())));
  expect(screen.getByText('@another_builder')).toBeTruthy();
  expect(stored().owner).toBe(OTHER); expect(stored().value).toEqual(emptyNavigation());
  expect(fetch.mock.calls.some(([url]) => url.includes('limit=1&') || url.includes('/me/team'))).toBe(false);
});
