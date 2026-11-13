import { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { expectPublicNavigationOnly } from './test/navigationAssertions';
import { csrf, failure, H1, H2, hackathon, json, session, T1, T2, team, U1 } from './test/fixtures';

type Handler = (url: string, options: RequestInit) => Response | Promise<Response> | undefined;
function server(handler: Handler = () => undefined, authenticated = true) {
  const fetch = vi.fn((url: string, options: RequestInit) => {
    const custom = handler(url, options);
    if (custom) return Promise.resolve(custom);
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/auth/session') return Promise.resolve(authenticated ? json(session()) : failure(401, 'invalid_session'));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon(), hackathon(H2)], next_cursor: null }));
    if (url === '/api/hackathons?limit=1&cursor=00000000-0000-0000-0000-000000000000') return Promise.resolve(json({ items: [hackathon()], next_cursor: null }));
    if (url === '/api/hackathons?limit=1&cursor=' + H1) return Promise.resolve(json({ items: [hackathon(H2)], next_cursor: null }));
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: [team()], next_cursor: null }));
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: null }));
    if (url.endsWith('/teams/' + T1)) return Promise.resolve(json(team()));
    if (url.endsWith('/join-requests?limit=20')) return Promise.resolve(json({ items: [], next_cursor: null }));
    throw new Error('Unexpected test request: ' + url);
  });
  vi.stubGlobal('fetch', fetch); return fetch;
}
const workspace = () => within(screen.getByRole('region', { name: 'Team workspace' }));
async function choose() { fireEvent.click(await screen.findByRole('button', { name: /Test Challenge/ })); }
function fillForm() {
  fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'test_builder' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'test-only-password' } });
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

it('restores a cookie session after refresh without persisted auth data or exposed CSRF', async () => {
  const storage = vi.spyOn(Storage.prototype, 'setItem'); const fetch = server();
  const app = render(<App />);
  await screen.findByText('@test_builder');
  expect(screen.getByRole('main').id).toBe('main');
  expect(screen.getByRole('link', { name: 'Skip to content' }).getAttribute('href')).toBe('#main');
  expect(document.body.textContent).not.toContain(csrf);
  expectPublicNavigationOnly(storage, csrf);
  app.unmount(); render(<App />); await screen.findByText('@test_builder');
  expect(fetch.mock.calls.filter(([url]) => url === '/auth/session')).toHaveLength(2);
});
it('registers, requires explicit login, discovers teams, then signs out using in-memory CSRF', async () => {
  const fetch = server(url => {
    if (url === '/auth/register') return json({ user_id: U1, username: 'test_builder' }, 201);
    if (url === '/auth/login') return json(session());
    if (url === '/auth/logout') return new Response(null, { status: 204 });
  }, false);
  render(<App />); fireEvent.click(await screen.findByRole('button', { name: 'Register' }));
  fillForm(); fireEvent.change(screen.getByLabelText(/Display name/), { target: { value: 'Test public name' } });
  fireEvent.click(screen.getByRole('button', { name: /Create account/ }));
  await screen.findByText('Account created. Sign in with your new credentials.');
  expect(fetch.mock.calls.some(([url]) => url === '/auth/login')).toBe(false);
  expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('');
  fillForm(); fireEvent.click(screen.getByRole('button', { name: /Sign in to Merge/ }));
  await choose(); await screen.findByRole('heading', { name: 'Test Team Alpha' });
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  expect(screen.queryByText('Test Team Alpha')).toBe(null);
  await screen.findByText('You have signed out.');
  const logout = fetch.mock.calls.find(([url]) => url === '/auth/logout')!;
  expect(logout[1].headers).toMatchObject({ 'X-CSRF-Token': csrf });
  expect(logout[1].body).toBe('{}');
});
it.each([401, 403, 429, 503])('shows auth %s failures without retrying or exposing backend messages', async status => {
  const fetch = server(url => url === '/auth/login' ? failure(status, status === 401 ? 'invalid_credentials' : 'request_failed', true, { 'Retry-After': '1' }) : undefined, false);
  render(<App />); await screen.findByLabelText('Username'); fillForm();
  fireEvent.click(screen.getByRole('button', { name: /Sign in to Merge/ }));
  await screen.findByRole('alert');
  expect(document.body.textContent).not.toContain('Untrusted upstream');
  expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('');
  expect(fetch.mock.calls.filter(([url]) => url === '/auth/login')).toHaveLength(1);
  if (status === 429) expect((screen.getByRole('button', { name: /Wait/ }) as HTMLButtonElement).disabled).toBe(true);
});
it('preserves an auth rate-limit cooldown across form mode changes', async () => {
  server(url => url === '/auth/login' ? failure(429, 'rate_limited', false, { 'Retry-After': '30' }) : undefined, false);
  render(<App />); await screen.findByLabelText('Username'); fillForm(); fireEvent.click(screen.getByRole('button', { name: /Sign in to Merge/ }));
  await screen.findByRole('alert'); fireEvent.click(screen.getByRole('button', { name: 'Register' }));
  expect((screen.getByRole('button', { name: /Wait/ }) as HTMLButtonElement).disabled).toBe(true);
});
it('does not silently resubmit an ambiguous login network failure', async () => {
  const fetch = server(url => url === '/auth/login' ? Promise.reject(new Error('private network error')) : undefined, false);
  render(<App />); await screen.findByLabelText('Username'); fillForm(); fireEvent.click(screen.getByRole('button', { name: /Sign in to Merge/ }));
  await screen.findByText(/The request may have reached the server/);
  expect(fetch.mock.calls.filter(([url]) => url === '/auth/login')).toHaveLength(1);
  expect(document.body.textContent).not.toContain('private network error');
});
it('paginates by returned cursor, opens authorized request controls and sends no mutation during browsing', async () => {
  const fetch = server(url => {
    if (url.endsWith('/teams?limit=20')) return json({ items: [team()], next_cursor: T1 });
    if (url.endsWith('/teams?limit=20&cursor=' + T1)) return json({ items: [team(T2)], next_cursor: null });
  });
  render(<App />); await choose(); await screen.findByRole('heading', { name: 'Test Team Alpha' });
  expect((workspace().getByRole('button', { name: 'Previous page' }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(workspace().getByRole('button', { name: /Next page/ }));
  await screen.findByRole('heading', { name: 'Test Team Beta' });
  expect((workspace().getByRole('button', { name: /Next page/ }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(workspace().getByRole('button', { name: 'Previous page' }));
  await screen.findByRole('heading', { name: 'Test Team Alpha' });
  fireEvent.click(screen.getByRole('button', { name: /View Test Team Alpha/ }));
  await screen.findByRole('heading', { name: 'Team details' }); await screen.findByText('Test Leader');
  await screen.findByText('No pending requests on this page.');
  expect(screen.queryByRole('button', { name: /Join team/ })).toBe(null);
  expect(screen.getByRole('heading', { name: 'Team details' })).toBe(document.activeElement);
  fireEvent.click(screen.getByRole('button', { name: /Back to teams/ }));
  await screen.findByRole('heading', { name: 'Find your team' });
  expect(fetch.mock.calls.filter(([url]) => url.startsWith('/api/')).every(([, options]) => options.method === 'GET')).toBe(true);
});
it.each([true, false])('handles My Team membership present=%s with an explicit null empty state', async present => {
  server(url => url.endsWith('/me/team') ? json({ team: present ? team() : null }) : undefined);
  render(<App />); await choose(); fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  if (present) { await screen.findByRole('heading', { name: 'Test Team Alpha' }); expect(screen.getByText('2/4 members')).toBeTruthy(); }
  else await screen.findByText('You haven’t joined a team in this hackathon.');
});
it.each([200, 401])('clears data on read 401 and ignores late %s responses after logout/login', async status => {
  let finish!: (value: Response) => void;
  server(url => {
    if (url.endsWith('/teams?limit=20')) return new Promise<Response>(resolve => { finish = resolve; });
    if (url === '/auth/logout') return new Response(null, { status: 204 });
    if (url === '/auth/login') return json(session());
  });
  render(<App />); await choose(); await screen.findByText('Loading teams…');
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' })); await screen.findByLabelText('Username');
  fillForm(); fireEvent.click(screen.getByRole('button', { name: /Sign in to Merge/ })); await screen.findByText('@test_builder');
  await act(async () => finish(status === 200 ? json({ items: [team()], next_cursor: null }) : failure(401, 'invalid_session')));
  expect(screen.queryByLabelText('Username')).toBe(null); expect(screen.queryByText('Test Team Alpha')).toBe(null);
  fireEvent.click(await screen.findByRole('button', { name: /Test Challenge/ }));
  await screen.findByText('Loading teams…'); await act(async () => finish(failure(401, 'invalid_session')));
  await screen.findByText('Your session has ended. Sign in again.');
  expect(screen.queryByText('@test_builder')).toBe(null);
});
it('hides the workspace immediately and reports uncertainty when logout fails', async () => {
  server(url => url === '/auth/logout' ? Promise.reject(new Error('unavailable')) : undefined);
  render(<App />); await choose(); await screen.findByRole('heading', { name: 'Test Team Alpha' });
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  await screen.findByText(/Sign-out is not confirmed/);
  expect(screen.queryByText('Test Team Alpha')).toBe(null); expect(screen.queryByLabelText('Username')).toBe(null);
});
it.each([403, 429, 503])('shows denied/unavailable read state for %s', async status => {
  server(url => url.startsWith('/api/hackathons?') ? failure(status, 'request_failed') : undefined);
  render(<App />); await screen.findByRole('alert'); expect(document.body.textContent).not.toContain('Untrusted upstream');
});
it('recovers a network read failure by explicit retry', async () => {
  let fail = true;
  server(url => { if (url.startsWith('/api/hackathons?') && fail) { fail = false; return Promise.reject(new Error('network')); } });
  render(<App />); await screen.findByRole('alert'); fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
  await screen.findByRole('button', { name: /Test Challenge/ });
});
it('renders honest empty catalog and team states', async () => {
  server(url => url.startsWith('/api/hackathons?') ? json({ items: [], next_cursor: null }) : undefined);
  const app = render(<App />); await screen.findByText(/No hackathons on this page/); app.unmount();
  server(url => url.endsWith('/teams?limit=20') ? json({ items: [], next_cursor: null }) : undefined);
  render(<App />); await choose(); await screen.findByText('A little quiet here.');
});
it('discards an old hackathon response on navigation', async () => {
  let finish!: (value: Response) => void;
  server(url => {
    if (url === `/api/hackathons/${H1}/teams?limit=20`) return new Promise<Response>(resolve => { finish = resolve; });
    if (url === `/api/hackathons/${H2}/teams?limit=20`) return json({ items: [team(T2, H2)], next_cursor: null });
  });
  render(<App />); await choose(); await screen.findByText('Loading teams…');
  fireEvent.click(screen.getByRole('button', { name: /Second Challenge/ })); await screen.findByRole('heading', { name: 'Test Team Beta' });
  await act(async () => finish(json({ items: [team()], next_cursor: null })));
  expect(screen.queryByText('Test Team Alpha')).toBe(null);
});
it('revalidates on foreground focus and clears workspace if the cookie was revoked elsewhere', async () => {
  let valid = true;
  server(url => url === '/auth/session' && !valid ? failure(401, 'invalid_session') : undefined);
  render(<App />); await choose(); await screen.findByRole('heading', { name: 'Test Team Alpha' }); valid = false;
  fireEvent(window, new Event('focus')); await screen.findByLabelText('Username'); expect(screen.queryByText('Test Team Alpha')).toBe(null);
});
it('renders untrusted names as text and keeps labelled keyboard controls', async () => {
  server(url => url.endsWith('/teams?limit=20') ? json({ items: [{ ...team(), name: '<img src=x onerror=alert(1)>' }], next_cursor: null }) : undefined);
  render(<App />); await choose(); await screen.findByRole('heading', { name: '<img src=x onerror=alert(1)>' });
  expect(document.querySelector('img')).toBe(null);
  expect(screen.getByRole('navigation', { name: 'Workspace' })).toBeTruthy();
});
it('survives StrictMode bootstrap cleanup without an old request winning', async () => {
  server(); render(<StrictMode><App /></StrictMode>); await screen.findByText('@test_builder');
  expect(screen.queryByLabelText('Username')).toBe(null);
});

it('keeps private data hidden during bootstrap failure and restores on explicit retry', async () => {
  let fail = true;
  server(url => {
    if (url === '/auth/session' && fail) { fail = false; return failure(503, 'service_unavailable', true); }
  });
  render(<App />); await screen.findByRole('alert');
  expect(screen.queryByText('@test_builder')).toBe(null); expect(screen.queryByLabelText('Username')).toBe(null);
  fireEvent.click(screen.getByRole('button', { name: 'Try again' })); await screen.findByText('@test_builder');
});
it('expires the in-memory workspace at the advertised absolute expiry', async () => {
  vi.useFakeTimers();
  server(url => url === '/auth/session' ? json({ ...session(), expires_at: new Date(Date.now() + 5000).toISOString() }) : undefined);
  render(<App />);
  await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  expect(screen.getByText('@test_builder')).toBeTruthy();
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(screen.queryByText('@test_builder')).toBe(null);
  expect(screen.getByText('Your session has ended. Sign in again.')).toBeTruthy();
});
it('rejects an already-expired bootstrap reply', async () => {
  server(url => url === '/auth/session' ? json({ ...session(), expires_at: '2000-01-01T00:00:00Z' }) : undefined);
  render(<App />); await screen.findByLabelText('Username'); expect(screen.queryByText('@test_builder')).toBe(null);
});
it('paginates the hackathon catalog using its independent cursor', async () => {
  const fetch = server(url => {
    if (url === '/api/hackathons?limit=20') return json({ items: [hackathon()], next_cursor: H1 });
    if (url === '/api/hackathons?limit=20&cursor=' + H1) return json({ items: [hackathon(H2)], next_cursor: null });
  });
  render(<App />); await screen.findByRole('button', { name: /Test Challenge/ });
  const catalog = within(screen.getByRole('complementary', { name: 'Hackathons' }));
  fireEvent.click(catalog.getByRole('button', { name: /Next page/ })); await screen.findByRole('button', { name: /Second Challenge/ });
  expect(fetch.mock.calls.some(([url]) => url === '/api/hackathons?limit=20&cursor=' + H1)).toBe(true);
  expect(catalog.queryByRole('button', { name: /Test Challenge/ })).toBe(null);
});
it('does not request login after rejected registration or submit a too-short password', async () => {
  const fetch = server(url => url === '/auth/register' ? failure(409, 'username_unavailable') : undefined, false);
  render(<App />); fireEvent.click(await screen.findByRole('button', { name: 'Register' })); fillForm();
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'short' } });
  fireEvent.click(screen.getByRole('button', { name: /Create account/ })); await screen.findByRole('alert');
  expect(fetch.mock.calls.some(([url]) => url === '/auth/register')).toBe(false);
  fillForm(); fireEvent.click(screen.getByRole('button', { name: /Create account/ })); await screen.findByText('That username is unavailable. Choose another.');
  expect(fetch.mock.calls.some(([url]) => url === '/auth/login')).toBe(false);
});
it('reports a removed team without leaving stale detail data', async () => {
  server(url => url.endsWith('/teams/' + T1) ? failure(404, 'team_not_found') : undefined);
  render(<App />); await choose(); await screen.findByRole('heading', { name: 'Test Team Alpha' });
  fireEvent.click(screen.getByRole('button', { name: /View Test Team Alpha/ })); await screen.findByRole('alert');
  expect(screen.queryByRole('heading', { name: 'Test Team Alpha' })).toBe(null);
});
