import { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { created, csrf, failure, H1, H2, hackathon, json, session, T1, T2, team, U1 } from './test/fixtures';

type Handler = (url: string, options: RequestInit) => Response | Promise<Response> | undefined;
function server(handler: Handler) {
  const fetch = vi.fn((url: string, options: RequestInit) => {
    const custom = handler(url, options);
    if (custom) return Promise.resolve(custom);
    if (url === '/health') return Promise.resolve(json({ status: 'ok' }));
    if (url === '/auth/session' || url === '/auth/login') return Promise.resolve(json(session()));
    if (url === '/auth/logout') return Promise.resolve(new Response(null, { status: 204 }));
    if (url === '/api/hackathons?limit=20') return Promise.resolve(json({ items: [hackathon(), hackathon(H2)], next_cursor: null }));
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({ items: [], next_cursor: null }));
    if (url.endsWith('/me/team')) return Promise.resolve(json({ team: null }));
    throw new Error('Unexpected mocked request');
  });
  vi.stubGlobal('fetch', fetch); return fetch;
}
const path = (id = H1) => `/api/hackathons/${id}/teams`;
async function choose(second = false) { fireEvent.click(await screen.findByRole('button', { name: second ? /Second Challenge/ : /Test Challenge/ })); await screen.findByLabelText('Team name'); }
const button = () => screen.getByRole('button', { name: 'Create team' }) as HTMLButtonElement;
const field = () => screen.getByLabelText('Team name') as HTMLInputElement;
const form = () => screen.getByRole('form', { name: 'Create team' });
async function submit(name = 'New real command') {
  await waitFor(() => expect(button().disabled).toBe(false));
  fireEvent.change(field(), { target: { value: name } }); fireEvent.click(button());
}
function login() {
  fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'test_builder' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'test-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: /Sign in to Merge/ }));
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

it('creates with a secure key and session CSRF, then refetches first-page discovery and My Team', async () => {
  let saved = false;
  const fetch = server((url, options) => {
    if (url === path() && options.method === 'POST') { saved = true; return json(created(), 201); }
    if (url === path()+'?limit=20') return json({ items: saved ? [team()] : [], next_cursor: saved ? null : T1 });
    if (url.includes('cursor='+T1)) return json({ items: [team(T2)], next_cursor: null });
    if (url.endsWith('/me/team')) return json({ team: saved ? team() : null });
  });
  const random = vi.spyOn(globalThis.crypto, 'getRandomValues');
  render(<App />); await choose();
  const workspace = within(screen.getByRole('region', { name: 'Team workspace' }));
  await waitFor(() => expect((workspace.getByRole('button', { name: /Next page/ }) as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(workspace.getByRole('button', { name: /Next page/ })); await screen.findByRole('heading', { name: 'Test Team Beta' });
  await submit(' Exact team name '); await screen.findByText(/Team creation confirmed/);
  await screen.findByRole('heading', { name: 'Test Team Alpha' });
  expect(random).toHaveBeenCalledTimes(1);
  const posts = fetch.mock.calls.filter(([,options]) => options.method === 'POST');
  expect(posts).toHaveLength(1);
  expect(posts[0][1]).toMatchObject({ body: '{"name":" Exact team name "}', headers: { 'X-CSRF-Token': csrf, 'Idempotency-Key': expect.stringMatching(/^[0-9a-f]{64}$/) } });
  expect(fetch.mock.calls.filter(([url]) => url.endsWith('/me/team'))).toHaveLength(2);
  expect(fetch.mock.calls.filter(([url]) => url === path()+'?limit=20')).toHaveLength(2);
  expect((workspace.getByRole('button', { name: 'Previous page' }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  await screen.findByRole('heading', { name: 'Test Team Alpha' });
  expect(screen.getByText('2/4 members')).toBeTruthy(); // Canonical GET, not the stored founder count.
  expect(button().disabled).toBe(true);
  expect(document.body.textContent).not.toContain(csrf);
});

it('refreshes membership while My Team is open and invalidates the list for its next activation', async () => {
  let saved = false;
  const fetch = server((url,options) => {
    if (url === path() && options.method === 'POST') { saved = true; return json(created(),201); }
    if (url.endsWith('/me/team')) return json({team:saved ? team() : null});
    if (url === path()+'?limit=20') return json({items:saved ? [team()] : [],next_cursor:null});
  });
  render(<App />); await choose(); fireEvent.click(screen.getByRole('button',{name:'My team'}));
  await submit(); await screen.findByText(/Team creation confirmed/); await screen.findByRole('heading',{name:'Test Team Alpha'});
  expect(fetch.mock.calls.filter(([url]) => url.endsWith('/me/team'))).toHaveLength(2);
  fireEvent.click(screen.getByRole('button',{name:'Discover teams'})); await screen.findByRole('heading',{name:'Test Team Alpha'});
  expect(fetch.mock.calls.filter(([url]) => url === path()+'?limit=20')).toHaveLength(2);
});

it('keeps a confirmed 201 successful when refresh fails and retries only the canonical read', async () => {
  let saved = false, failingRead = true;
  const fetch = server((url,options) => {
    if (url === path() && options.method === 'POST') { saved=true; return json(created(),201); }
    if (url.endsWith('/me/team') && saved) return failingRead ? failure(503,'service_unavailable') : json({team:team()});
  });
  render(<App />); await choose(); await submit(); await screen.findByText(/Team creation confirmed/);
  fireEvent.click(screen.getByRole('button',{name:'My team'})); await screen.findByRole('alert');
  expect(screen.getByText(/Team creation confirmed/)).toBeTruthy();
  failingRead=false; fireEvent.click(screen.getByRole('button',{name:'Try again'})); await screen.findByRole('heading',{name:'Test Team Alpha'});
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(1);
});

it.each(['outcome_uncertain','network','bad-reply'])('retains the same key/name across %s and explicit replay', async kind => {
  let attempts = 0;
  const fetch = server((url, options) => {
    if (url === path() && options.method === 'POST') {
      if (++attempts === 1) return kind === 'network' ? Promise.reject(new Error('private transport'))
        : kind === 'bad-reply' ? json(created(), 200) : failure(503, 'outcome_uncertain', true);
      return json(created(), 201);
    }
  });
  const storage = vi.spyOn(Storage.prototype, 'setItem');
  render(<App />); await choose(); await submit('Original name');
  await screen.findByText(/The original operation must be resolved/);
  expect(field().readOnly).toBe(true);
  fireEvent.change(field(), { target: { value: 'Changed name' } });
  expect(field().value).toBe('Original name');
  fireEvent.click(screen.getByRole('button', { name: 'My team' }));
  fireEvent.click(screen.getByRole('button', { name: 'Discover teams' }));
  expect(attempts).toBe(1);
  fireEvent.click(screen.getByRole('button', { name: 'Retry original request' }));
  await screen.findByText(/Team creation confirmed/);
  const posts = fetch.mock.calls.filter(([,options]) => options.method === 'POST');
  expect(posts).toHaveLength(2);
  expect(posts[0][1].body).toBe(posts[1][1].body);
  expect(posts[0][1].headers).toEqual(posts[1][1].headers);
  expect(storage).not.toHaveBeenCalled();
  expect(document.body.textContent).not.toMatch(/private transport|Untrusted upstream/);
});

it('blocks double-click and keyboard duplicates until the first response settles', async () => {
  let finish!: (response: Response) => void;
  const fetch = server((url, options) => url === path() && options.method === 'POST' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(<App />); await choose(); await submit();
  fireEvent.submit(form()); fireEvent.submit(form());
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(1);
  expect((screen.getByRole('button', { name: /Creating team/ }) as HTMLButtonElement).disabled).toBe(true);
  const warning = new Event('beforeunload', { cancelable: true }); fireEvent(window, warning); expect(warning.defaultPrevented).toBe(true);
  await act(async () => finish(json(created(), 201))); await screen.findByText(/Team creation confirmed/);
  const cleared = new Event('beforeunload', { cancelable: true }); fireEvent(window, cleared); expect(cleared.defaultPrevented).toBe(false);
});

it.each([400, 422])('allows a new edited command/key after definite validation %s', async status => {
  let attempts = 0;
  const fetch = server((url, options) => url === path() && options.method === 'POST'
    ? ++attempts === 1 ? failure(status, 'invalid_request') : json(created(), 201) : undefined);
  render(<App />); await choose(); await submit('Rejected name'); await screen.findByText(/The team request was rejected/);
  expect(field().readOnly).toBe(false);
  await submit('Corrected name'); await screen.findByText(/Team creation confirmed/);
  const posts = fetch.mock.calls.filter(([,options]) => options.method === 'POST');
  expect((posts[0][1].headers as Record<string,string>)['Idempotency-Key']).not.toBe((posts[1][1].headers as Record<string,string>)['Idempotency-Key']);
});

it('handles denied CSRF without false success, and offers session restoration', async () => {
  let attempts = 0;
  const fetch = server((url, options) => url === path() && options.method === 'POST'
    ? ++attempts === 1 ? failure(403, 'invalid_csrf') : json(created(), 201) : undefined);
  render(<App />); await choose(); await submit(); await screen.findByText(/Creation was denied/);
  expect(screen.getByRole('button', { name: 'Restore session' })).toBeTruthy();
  await submit(); await screen.findByText(/Team creation confirmed/);
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(2);
});

it('refreshes already-assigned membership without claiming this request created a team', async () => {
  let assigned = false;
  const fetch = server((url, options) => {
    if (url === path() && options.method === 'POST') { assigned = true; return failure(409, 'already_assigned'); }
    if (url.endsWith('/me/team')) return json({ team: assigned ? team() : null });
  });
  render(<App />); await choose(); await submit(); await screen.findByText(/You already belong to a team/);
  expect(button().disabled).toBe(true); expect(screen.queryByText(/Team creation confirmed/)).toBe(null);
  fireEvent.click(screen.getByRole('button', { name: 'My team' })); await screen.findByRole('heading', { name: 'Test Team Alpha' });
  expect(fetch.mock.calls.filter(([url]) => url.endsWith('/me/team'))).toHaveLength(2);
});

it.each([['idempotency_mismatch',409],['service_unavailable',503]] as const)('keeps %s unresolved and never rotates the key automatically', async (code,status) => {
  const fetch = server((url, options) => url === path() && options.method === 'POST' ? failure(status,code,false) : undefined);
  render(<App />); await choose(); await submit(); await screen.findByText(/The original operation must be resolved/);
  expect(field().readOnly).toBe(true); expect(screen.queryByText(/Team creation confirmed/)).toBe(null);
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(1);
});

it('does not erase earlier uncertainty when a later retry is rejected before mutation', async () => {
  let attempts = 0;
  server((url, options) => url === path() && options.method === 'POST'
    ? ++attempts === 1 ? failure(503, 'outcome_uncertain', true) : failure(422, 'invalid_request') : undefined);
  render(<App />); await choose(); await submit(); await screen.findByText(/The original operation must be resolved/);
  fireEvent.click(screen.getByRole('button', { name: 'Retry original request' }));
  await screen.findByText(/The earlier operation is still unresolved/);
  expect(field().readOnly).toBe(true); expect(field().value).toBe('New real command');
});

it.each([400,422,403])('does not treat an undocumented error body at %s as rollback proof', async status => {
  const fetch = server((url,options) => url === path() && options.method === 'POST'
    ? new Response('private proxy response', {status}) : undefined);
  render(<App />); await choose(); await submit('Original ambiguous command');
  await screen.findByText(/The original operation must be resolved/);
  expect(field().readOnly).toBe(true);
  expect(document.body.textContent).not.toContain('private proxy response');
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(1);
});

it('retains explicit outcome_uncertain even when a response has an unexpected validation status', async () => {
  server((url,options) => url === path() && options.method === 'POST' ? failure(400,'outcome_uncertain',true) : undefined);
  render(<App />); await choose(); await submit(); await screen.findByText(/The original operation must be resolved/);
  expect(field().readOnly).toBe(true);
});

it('does not create when membership is present or unknown', async () => {
  let known = true;
  const fetch = server(url => url.endsWith('/me/team') ? known ? json({ team: team() }) : failure(503,'service_unavailable') : undefined);
  render(<App />); await choose(); await screen.findByText(/You already belong to a team/);
  expect(button().disabled).toBe(true); fireEvent.submit(form());
  known = false; await choose(true);
  await screen.findByText(/Creation stays unavailable until membership is confirmed/);
  expect(button().disabled).toBe(true); fireEvent.submit(form());
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(0);
});

it('permits only original-key resolution even if membership appears after an uncertain delivery', async () => {
  let attempts = 0;
  const fetch = server((url, options) => {
    if (url === path() && options.method === 'POST') return ++attempts === 1 ? failure(503,'outcome_uncertain',true) : json(created(),201);
    if (url.endsWith('/me/team')) return json({ team: attempts ? team() : null });
  });
  render(<App />); await choose(); await submit('Original'); await screen.findByText(/The original operation must be resolved/);
  await choose(true); await choose(); await screen.findByText(/You already belong to a team/);
  fireEvent.click(screen.getByRole('button', { name: 'Retry original request' })); await screen.findByText(/Team creation confirmed/);
  const posts = fetch.mock.calls.filter(([,options]) => options.method === 'POST');
  expect(posts[0][1].headers).toEqual(posts[1][1].headers);
});

it('keeps a pending result scoped when switching hackathons', async () => {
  let finish!: (response: Response) => void;
  const fetch = server((url,options) => {
    if (url === path() && options.method === 'POST') return new Promise(resolve => { finish = resolve; });
    if (url === path(H2) && options.method === 'POST') return json(created(H2,U1,T2),201);
  });
  render(<App />); await choose(); await submit('First challenge command'); await choose(true);
  expect(field().value).toBe(''); await submit('Second challenge command'); await screen.findByText(/Team creation confirmed/);
  // The success message can render before its own canonical read effects run.
  // Drain those two expected reads before measuring the older response's scope.
  await waitFor(() => expect(fetch.mock.calls.filter(([url]) => url.startsWith('/api/hackathons/'+H2))).toHaveLength(5));
  const secondReads = fetch.mock.calls.filter(([url]) => url.startsWith('/api/hackathons/'+H2)).length;
  await act(async () => finish(json(created(),201)));
  expect(screen.getByRole('heading', {level:1}).textContent).toBe('Second Challenge');
  expect(field().value).toBe('Second challenge command');
  expect(fetch.mock.calls.filter(([url]) => url.startsWith('/api/hackathons/'+H2))).toHaveLength(secondReads);
  await choose(); expect(field().value).toBe('First challenge command'); await screen.findByText(/Team creation confirmed/);
});

it.each([201,401])('ignores a stale mutation %s after logout and another account logs in', async status => {
  let finish!: (response: Response) => void;
  const other = { ...session(), identity: { user_id:H2, username:'other_builder' }, csrf_token:'B'.repeat(42)+'A' };
  let newUser = false;
  const fetch = server((url,options) => {
    if (url === '/auth/login') { newUser = true; return json(other); }
    if (url === path() && options.method === 'POST') return newUser ? json(created(H1,H2),201) : new Promise(resolve => { finish = resolve; });
  });
  render(<App />); await choose(); await submit('Old private draft');
  fireEvent.click(screen.getByRole('button', {name:'Sign out'})); await screen.findByLabelText('Username'); login(); await screen.findByText('@other_builder');
  await choose(); expect(field().value).toBe(''); await submit('New account team'); await screen.findByText(/Team creation confirmed/);
  await act(async () => finish(status === 201 ? json(created(),201) : failure(401,'invalid_session')));
  expect(screen.getByText('@other_builder')).toBeTruthy(); expect(field().value).toBe('New account team');
  expect(document.body.textContent).not.toContain('Old private draft');
  const posts = fetch.mock.calls.filter(([url,options]) => url === path() && options.method === 'POST');
  expect((posts[0][1].signal as AbortSignal).aborted).toBe(true);
  expect((posts[1][1].headers as Record<string,string>)['X-CSRF-Token']).toBe(other.csrf_token);
  expect((posts[0][1].headers as Record<string,string>)['Idempotency-Key']).not.toBe((posts[1][1].headers as Record<string,string>)['Idempotency-Key']);
});

it('retains the command/key through same-account logout/login with fresh CSRF', async () => {
  let attempts = 0, finish!: (response: Response) => void;
  const refreshed = { ...session(), csrf_token:'B'.repeat(42)+'A' };
  const fetch = server((url,options) => {
    if (url === '/auth/login') return json(refreshed);
    if (url === path() && options.method === 'POST') return ++attempts === 1 ? new Promise(resolve => { finish=resolve; }) : json(created(),201);
  });
  render(<App />); await choose(); await submit('Retained original');
  fireEvent.click(screen.getByRole('button', {name:'Sign out'})); await screen.findByLabelText('Username'); login(); await screen.findByText('@test_builder');
  await choose(); await screen.findByText(/The original operation must be resolved/);
  expect(field().value).toBe('Retained original');
  fireEvent.click(screen.getByRole('button', {name:'Retry original request'})); await screen.findByText(/Team creation confirmed/);
  const posts = fetch.mock.calls.filter(([url,options]) => url === path() && options.method === 'POST');
  expect(posts[0][1].body).toBe(posts[1][1].body);
  expect((posts[0][1].headers as Record<string,string>)['Idempotency-Key']).toBe((posts[1][1].headers as Record<string,string>)['Idempotency-Key']);
  expect((posts[1][1].headers as Record<string,string>)['X-CSRF-Token']).toBe(refreshed.csrf_token);
  await act(async () => finish(failure(401,'invalid_session')));
  expect(screen.getByText('@test_builder')).toBeTruthy();
});

it('expires a rejected session without an automatic mutation retry', async () => {
  const fetch = server((url, options) => url === path() && options.method === 'POST' ? failure(401,'invalid_session') : undefined);
  render(<App />); await choose(); await submit(); await screen.findByText('Your session has ended. Sign in again.');
  expect(screen.queryByLabelText('Team name')).toBe(null);
  expect(fetch.mock.calls.filter(([url,options]) => url === path() && options.method === 'POST')).toHaveLength(1);
});

it('retains the cooldown and key across navigation after 429, then recovers explicitly', async () => {
  let attempts = 0;
  const fetch = server((url,options) => url === path() && options.method === 'POST'
    ? ++attempts === 1 ? failure(429,'rate_limited',true,{'Retry-After':'2'}) : json(created(),201) : undefined);
  render(<App />); await choose(); await submit('Rate limited command'); await screen.findByText(/Too many attempts/);
  expect((screen.getByRole('button', {name:/Wait \d+s/}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.submit(form()); expect(attempts).toBe(1);
  await choose(true); await choose(); expect(attempts).toBe(1);
  await waitFor(() => expect(button().disabled).toBe(false), {timeout:3500});
  fireEvent.click(button()); await screen.findByText(/Team creation confirmed/);
  const posts = fetch.mock.calls.filter(([url,options]) => url === path() && options.method === 'POST');
  expect(posts[0][1].body).toBe(posts[1][1].body);
  expect(posts[0][1].headers).toEqual(posts[1][1].headers);
},10000);

it('keeps a pending command across foreground session revalidation and uses restored CSRF', async () => {
  let sessions = 0, attempts = 0, finish!: (response:Response) => void;
  const refreshed = { ...session(), csrf_token:'C'.repeat(42)+'A' };
  const fetch = server((url,options) => {
    if (url === '/auth/session') return json(++sessions === 1 ? session() : refreshed);
    if (url === path() && options.method === 'POST') return ++attempts === 1 ? new Promise(resolve => {finish=resolve;}) : json(created(),201);
  });
  render(<App />); await choose(); await submit('Before foreground');
  fireEvent(window,new Event('focus')); await screen.findByText('@test_builder'); await choose();
  await screen.findByText(/The original operation must be resolved/);
  fireEvent.click(screen.getByRole('button',{name:'Retry original request'})); await screen.findByText(/Team creation confirmed/);
  const posts = fetch.mock.calls.filter(([url,options]) => url === path() && options.method === 'POST');
  expect(posts[0][1].body).toBe(posts[1][1].body);
  expect((posts[0][1].headers as Record<string,string>)['Idempotency-Key']).toBe((posts[1][1].headers as Record<string,string>)['Idempotency-Key']);
  expect((posts[1][1].headers as Record<string,string>)['X-CSRF-Token']).toBe(refreshed.csrf_token);
  await act(async () => finish(failure(401,'invalid_session')));
  expect(screen.getByText('@test_builder')).toBeTruthy();
});

it('rejects a 201 result for another principal without refreshing or claiming creation', async () => {
  const fetch = server((url,options) => url === path() && options.method === 'POST' ? json(created(H1,H2),201) : undefined);
  render(<App />); await choose(); await submit(); await screen.findByText(/The original operation must be resolved/);
  expect(screen.queryByText(/Team creation confirmed/)).toBe(null);
  expect(field().readOnly).toBe(true);
  expect(fetch.mock.calls.filter(([url]) => url.endsWith('/me/team'))).toHaveLength(1);
});

it.each(['', '   ', 'a'.repeat(121), 'nul\0name', '\ud800'])('validates the exact name without POST and focuses a labelled field %#', async name => {
  const fetch = server(() => undefined); render(<App />); await choose(); await submit(name);
  await screen.findByRole('alert'); expect(field()).toBe(document.activeElement);
  expect(field().getAttribute('aria-invalid')).toBe('true'); expect(field().getAttribute('aria-describedby')).toContain('error');
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(0);
});

it('accepts 120 Unicode code points without trimming or treating emoji as two characters', async () => {
  const fetch = server((url,options) => url === path() && options.method === 'POST' ? json(created(),201) : undefined);
  render(<App />); await choose(); await submit('😀'.repeat(120)); await screen.findByText(/Team creation confirmed/);
  expect(JSON.parse(fetch.mock.calls.find(([url,options]) => url === path() && options.method === 'POST')![1].body as string).name).toBe('😀'.repeat(120));
});

it('fails closed without secure randomness, with no weak-key fallback', async () => {
  const fetch = server(() => undefined);
  vi.spyOn(globalThis.crypto, 'getRandomValues').mockImplementation(() => { throw new Error('private platform detail'); });
  render(<App />); await choose(); await submit(); await screen.findByText(/A secure request key could not be generated/);
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(0);
  expect(document.body.textContent).not.toContain('private platform detail');
});

it('submits creation once under StrictMode and exposes only guarded leader request reads', async () => {
  const fetch = server((url,options) => {
    if (url === path() && options.method === 'POST') return json(created(),201);
    if (url.endsWith('/teams?limit=20')) return json({items:[team()],next_cursor:null});
    if (url.endsWith('/teams/'+T1)) return json(team());
    if (url.endsWith('/join-requests?limit=20')) return json({items:[],next_cursor:null});
  });
  render(<StrictMode><App /></StrictMode>); await choose(); await submit(); await screen.findByText(/Team creation confirmed/);
  fireEvent.click(await screen.findByRole('button', {name:/View Test Team Alpha/}));
  await screen.findByText('No pending requests on this page.');
  expect(screen.queryByRole('button', {name:'Request membership'})).toBe(null);
  expect(fetch.mock.calls.filter(([,options]) => options.method === 'POST')).toHaveLength(1);
  expect(fetch.mock.calls.some(([url]) => /\/join(?:$|[/?])/.test(url))).toBe(false);
  expect(fetch.mock.calls.filter(([url]) => url.includes('/join-requests')).every(([,options]) => options.method === 'GET')).toBe(true);
});
