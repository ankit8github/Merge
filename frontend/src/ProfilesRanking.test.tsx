import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { api, type Profile, type Rankings } from './api';
import ProfilePanel, { validateProfile } from './components/Profile';
import RankingsPanel from './components/Rankings';
import AuthForm from './components/AuthForm';
import { ReadInvalidation } from './hooks/useRealtime';
import { csrf, failure, H1, H2, hackathon, invitation, json, session, T1, T2, team, U1 } from './test/fixtures';

const U2 = '00000000-0000-0000-0000-000000000022';
const profile = (): Profile => ({ user_id: U1, username: 'test_builder', display_name: 'Builder', skills: [], timezone: null, discoverable: false, version: 0 });
const ranking = (): Rankings => ({ hackathon_id: H1, team_id: T1, user_id: U1, reference_at: '2026-11-14T12:00:00Z',
  team_skills: ['python'], skill_weight: .7, timezone_weight: .3, next_cursor: null,
  items: [{ user_id: U2, username: 'sam_dev', display_name: 'Sam', skills: ['sql'], timezone: 'UTC', new_skills: ['sql'],
    skill_complement: 1, timezone_overlap: 1, skill_points: 70, timezone_points: 30, score: 100 }] });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it('normalizes skills, permits empty private profiles and gives field-specific errors', () => {
  expect(validateProfile(' React, python,react ', 'UTC', true)).toEqual({ fields: {}, values: { skills: ['python','react'], timezone: 'UTC', discoverable: true } });
  expect(validateProfile('', '', false).fields).toEqual({});
  expect(validateProfile('', '', true).fields.timezone).toBeTruthy();
  expect(validateProfile('a,,b', 'Mars/Bad', true).fields).toHaveProperty('skills');
  expect(validateProfile('a,,b', 'Mars/Bad', true).fields).toHaveProperty('timezone');
  expect(validateProfile(Array(21).fill('a').join(','), 'UTC', true).fields.skills).toBeTruthy();
});

it('uses cookie/CSRF own-profile replacement with version, no actor selector or automatic key', async () => {
  const value = { ...profile(), skills: ['python'], timezone: 'UTC', discoverable: true, version: 1 };
  const fetch = vi.fn(() => Promise.resolve(json(value))); vi.stubGlobal('fetch', fetch);
  const edit = { skills: [' Python '], timezone: 'UTC', discoverable: true, version: 0 };
  expect(await api.saveProfile(U1, edit, csrf)).toEqual(value);
  expect(fetch).toHaveBeenCalledWith('/api/me/profile', expect.objectContaining({ method: 'POST', credentials: 'same-origin',
    body: JSON.stringify(edit), headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': csrf } }));
});

it.each(['actor','version','skills','timezone','discovery'])('rejects mismatched profile save %s acknowledgements', async kind => {
  const value = { ...profile(), version: 1 };
  if (kind === 'actor') value.user_id = U2;
  if (kind === 'version') value.version = 0;
  if (kind === 'skills') value.skills = ['unexpected'];
  if (kind === 'timezone') value.timezone = 'UTC';
  if (kind === 'discovery') { value.discoverable = true; value.timezone = 'UTC'; }
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(json(value))));
  await expect(api.saveProfile(U1, { skills: [], timezone: null, discoverable: false, version: 0 }, csrf)).rejects.toMatchObject({ code: 'invalid_response' });
});

it.each(['actor','scope','weights','score','components','duplicate','cursor','self'])('rejects invalid ranking %s responses', async kind => {
  const value = ranking();
  if (kind === 'actor') value.user_id = U2;
  if (kind === 'scope') value.hackathon_id = H2;
  if (kind === 'weights') (value as { skill_weight: number }).skill_weight = .6;
  if (kind === 'score') value.items[0].score = 99;
  if (kind === 'components') value.items[0].skill_complement = .5;
  if (kind === 'duplicate') value.items.push(value.items[0]);
  if (kind === 'cursor') value.next_cursor = 'bad!';
  if (kind === 'self') value.items[0].user_id = U1;
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(json(value))));
  await expect(api.suggestions(H1, T1, U1, null)).rejects.toMatchObject({ code: 'invalid_response' });
});

it('loads profile only on explicit opening, focuses invalid fields and saves normalized data', async () => {
  const get = vi.spyOn(api, 'profile').mockResolvedValue(profile());
  const save = vi.spyOn(api, 'saveProfile').mockResolvedValue({ ...profile(), skills: ['python'], timezone: 'UTC', discoverable: true, version: 1 });
  render(<ProfilePanel session={session()} signal={new AbortController().signal} onExpired={vi.fn()} />);
  expect(get).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  const skills = await screen.findByLabelText('Skills');
  fireEvent.change(skills, { target: { value: 'bad skill' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));
  expect(document.activeElement).toBe(skills); expect(skills.getAttribute('aria-invalid')).toBe('true'); expect(save).not.toHaveBeenCalled();
  fireEvent.change(skills, { target: { value: ' Python, python ' } });
  fireEvent.change(screen.getByLabelText('Time zone'), { target: { value: 'UTC' } });
  fireEvent.click(screen.getByLabelText('Show me in teammate rankings'));
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));
  await screen.findByText(/Profile saved/);
  expect(save).toHaveBeenCalledWith(U1, { skills: ['python'], timezone: 'UTC', discoverable: true, version: 0 }, csrf, expect.any(AbortSignal));
});

it.each(['conflict','unknown'])('requires canonical profile reload after %s delivery and never auto-retries', async kind => {
  const get = vi.spyOn(api, 'profile').mockResolvedValue(profile());
  const save = vi.spyOn(api, 'saveProfile').mockRejectedValue(kind === 'conflict' ? new (await import('./api')).ApiError(409,'profile_changed') : new Error('offline'));
  render(<ProfilePanel session={session()} signal={new AbortController().signal} onExpired={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' })); await screen.findByLabelText('Skills');
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Reload your profile before editing again/);
  expect(screen.getByRole('button', { name: 'Save profile' }).matches(':disabled')).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); expect(save).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Reload profile' }));
  await waitFor(() => expect(get).toHaveBeenCalledTimes(2)); await waitFor(() => expect((screen.getByRole('button', { name: 'Save profile' }) as HTMLButtonElement).disabled).toBe(false));
});

it('ignores old-account profile saves and aborts their transport', async () => {
  vi.spyOn(api, 'profile').mockResolvedValue(profile());
  let finish!: (p: Profile) => void;
  const save = vi.spyOn(api, 'saveProfile').mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const expired = vi.fn();
  const { rerender } = render(<ProfilePanel key="first" session={session()} signal={new AbortController().signal} onExpired={expired} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' })); await screen.findByLabelText('Skills');
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));
  const signal = save.mock.calls[0][3]!;
  rerender(<ProfilePanel key="second" session={{ ...session(), identity: { user_id: U2, username: 'other' } }} signal={new AbortController().signal} onExpired={expired} />);
  expect(signal.aborted).toBe(true); await act(async () => finish({ ...profile(), version: 1 }));
  expect(screen.queryByText(/Profile saved/)).toBeNull(); expect(expired).not.toHaveBeenCalled();
});

it('shows explained rankings, selects a named recipient, and restarts stale pages', async () => {
  const get = vi.spyOn(api, 'suggestions').mockResolvedValue({ ...ranking(), next_cursor: 'valid_cursor' });
  const choose = vi.fn();
  render(<RankingsPanel team={team()} actor={U1} onExpired={vi.fn()} choose={choose} />);
  expect(get).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole('button', { name: 'Find teammates' }));
  await screen.findByText(/Sam \(@sam_dev\).*100.00/);
  expect(screen.getByText(/Skill complement 1.0000 × 70 = 70.00 points/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Select Sam for invitation' })); expect(choose).toHaveBeenCalledWith(ranking().items[0]);
  get.mockRejectedValueOnce(new (await import('./api')).ApiError(409,'ranking_changed'));
  fireEvent.click(screen.getByRole('button', { name: 'Next rankings' })); await screen.findByText(/Profiles, membership or the scoring day changed/);
  expect(screen.queryByText(/Sam \(@sam_dev\)/)).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Restart rankings' })); await screen.findByText(/Sam \(@sam_dev\)/);
  expect(get.mock.calls.at(-1)?.[3]).toBeNull();
});

it('does not expose rankings to nonleaders', () => {
  const get = vi.spyOn(api, 'suggestions');
  render(<RankingsPanel team={team()} actor={U2} onExpired={vi.fn()} choose={vi.fn()} />);
  expect(screen.queryByRole('button', { name: 'Find teammates' })).toBeNull(); expect(get).not.toHaveBeenCalled();
});

it('fences old-workspace ranking 401 responses', async () => {
  let reject!: (e: Error) => void;
  vi.spyOn(api, 'suggestions').mockImplementationOnce(() => new Promise((_, r) => { reject = r; })).mockResolvedValue({ ...ranking(), team_id: T2 });
  const expired = vi.fn();
  const { rerender } = render(<RankingsPanel key={T1} team={team()} actor={U1} onExpired={expired} choose={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Find teammates' }));
  rerender(<RankingsPanel key={T2} team={team(T2)} actor={U1} onExpired={expired} choose={vi.fn()} />);
  await act(async () => reject(new (await import('./api')).ApiError(401,'invalid_session')));
  expect(expired).not.toHaveBeenCalled();
});

it('refreshes mounted rankings on SSE invalidation without replacing recipient input', async () => {
  const get = vi.spyOn(api, 'suggestions').mockResolvedValue(ranking());
  const expired = vi.fn(), choose = vi.fn(), currentTeam = team();
  const view = (revision: number) => <ReadInvalidation.Provider value={revision}><input aria-label="Draft recipient" defaultValue="kept" /><RankingsPanel team={currentTeam} actor={U1} onExpired={expired} choose={choose} /></ReadInvalidation.Provider>;
  const { rerender } = render(view(0)); fireEvent.click(screen.getByRole('button', { name: 'Find teammates' })); await screen.findByText(/Sam \(@sam_dev\)/);
  const input = screen.getByLabelText('Draft recipient');
  rerender(view(1)); await waitFor(() => expect(get).toHaveBeenCalledTimes(2));
  expect(screen.getByLabelText('Draft recipient')).toBe(input);
});

it.each(['username','password','display_name'])('shows registration %s error and focuses that field without HTTP', async field => {
  const fetch = vi.fn(); vi.stubGlobal('fetch',fetch);
  render(<AuthForm onSession={vi.fn()} restore={vi.fn()} />); fireEvent.click(screen.getByRole('button',{name:'Register'}));
  fireEvent.change(screen.getByLabelText('Username'),{target:{value:field==='username'?'Invalid USER':'valid_user'}});
  fireEvent.change(screen.getByLabelText('Password'),{target:{value:field==='password'?'short':'a valid long password'}});
  fireEvent.change(screen.getByLabelText(/Display name/),{target:{value:field==='display_name'?'   ':'Valid Name'}});
  fireEvent.click(screen.getByRole('button',{name:/Create account/}));
  const target = screen.getByLabelText(field==='username'?'Username':field==='password'?'Password':/Display name/);
  expect(document.activeElement).toBe(target); expect(target.getAttribute('aria-invalid')).toBe('true'); expect(fetch).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toBeTruthy();
});

it('integrates labelled ranking selection with the unchanged UUID invitation command', async () => {
  const fetch = vi.fn((url: string) => {
    if (url==='/auth/session') return Promise.resolve(json(session()));
    if (url==='/health') return Promise.resolve(json({status:'ok'}));
    if (url==='/api/hackathons?limit=20') return Promise.resolve(json({items:[hackathon()],next_cursor:null}));
    if (url.endsWith('/me/team')) return Promise.resolve(json({team:team()}));
    if (url.endsWith('/teams?limit=20')) return Promise.resolve(json({items:[team()],next_cursor:null}));
    if (url.endsWith('/teams/'+T1)) return Promise.resolve(json(team()));
    if (url.includes('/join-requests?')) return Promise.resolve(json({items:[],next_cursor:null}));
    if (url.endsWith('/suggestions?limit=20')) return Promise.resolve(json(ranking()));
    if (url.endsWith('/invitations')) return Promise.resolve(json({schema_version:1,data:invitation({recipient_id:U2,issued_by:U1})},201));
    return Promise.resolve(failure(404));
  }); vi.stubGlobal('fetch',fetch);
  render(<App/>); fireEvent.click(await screen.findByRole('button',{name:/Test Challenge/}));
  fireEvent.click(await screen.findByRole('button',{name:/View Test Team Alpha/}));
  fireEvent.click(await screen.findByRole('button',{name:'Find teammates'}));
  fireEvent.click(await screen.findByRole('button',{name:'Select Sam for invitation'}));
  expect((screen.getByLabelText('Recipient account UUID') as HTMLInputElement).value).toBe(U2);
  expect(screen.getByText('Recipient: Sam (@sam_dev). Team: Test Team Alpha.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Issue invitation'})); await screen.findByText(/Invitation issuance confirmed/);
  const call = fetch.mock.calls.find(([url])=>url.endsWith('/invitations'))!;
  expect(call[0]).toBe(`/api/hackathons/${H1}/teams/${T1}/invitations`);
});
