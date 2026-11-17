import { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError, type Profile } from './api';
import ProfilePanel, { validateProfile } from './components/Profile';
import { csrf, json, session, U1 } from './test/fixtures';

const zones = ['Asia/Calcutta', 'Asia/Kolkata', 'Europe/London', 'UTC'];
const profile = (values: Partial<Profile> = {}): Profile => ({ ...session().identity, display_name: 'Builder', skills: [], timezone: null, discoverable: false, version: 0, ...values });
const deferred = <T,>() => { let resolve!: (value: T) => void, reject!: (error: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
beforeEach(() => { vi.spyOn(api, 'profileTimezones').mockResolvedValue(zones); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
async function open(initial = profile()) {
  const get = vi.spyOn(api, 'profile').mockResolvedValue(initial);
  const save = vi.spyOn(api, 'saveProfile').mockImplementation(async (_actor, body) => ({ ...initial, ...body, version: body.version + 1 }));
  const scope = new AbortController(), expired = vi.fn();
  const view = render(<StrictMode><ProfilePanel session={session()} signal={scope.signal} onExpired={expired} /></StrictMode>);
  expect(get).not.toHaveBeenCalled(); expect(api.profileTimezones).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  const skills = await screen.findByLabelText('Skills') as HTMLInputElement;
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save profile' }).matches(':disabled')).toBe(false));
  return { get, save, scope, expired, view, skills };
}
function selectZone(query: string, key = 'ArrowDown') {
  const input = screen.getByRole('combobox');
  fireEvent.change(input, { target: { value: query } });
  fireEvent.keyDown(input, { key }); fireEvent.keyDown(input, { key: 'Enter' });
}

it.each([
  [' Data   Science, data-science, PYTHON ', ['data-science', 'python']],
  ['C++, C#, .net', null], ['C++, C#, node.js, foo--bar', ['c#', 'c++', 'foo--bar', 'node.js']],
  ['a'.repeat(32), ['a'.repeat(32)]], ['a'.repeat(31) + ' b', null],
  ['a'.repeat(30) + ' b', ['a'.repeat(30) + '-b']],
  ['a'.repeat(29) + ' b', ['a'.repeat(29) + '-b']],
  [Array(20).fill('Data Science').join(','), ['data-science']],
  [Array(21).fill('python').join(','), null], ['', []], ['   ', []],
  ['a,,b', null], [',a', null], ['a,', null], ['a,   ,b', null], ['a/b', null],
  ['é', null], ['a\tb', null], ['a\nb', null], ['a\u00a0b', null], ['a'.repeat(33), null],
])('normalizes natural skill boundary %j without truncation', (input, expected) => {
  const result = validateProfile(input as string, '', false, zones);
  if (expected === null) expect(result.fields.skills).toBeTruthy();
  else { expect(result.fields).toEqual({}); expect(result.values.skills).toEqual(expected); }
});

it.each(zones)('accepts exact server zone %s without browser canonicalization', zone => {
  expect(validateProfile('', zone, true, zones).fields).toEqual({});
});
it.each(['asia/kolkata', 'Mars/Base', 'UTC ', '+05:30', 'Factory', 'localtime'])('rejects non-catalogue zone %s', zone => {
  expect(validateProfile('', zone, false, zones).fields.timezone).toBeTruthy();
});

it('uses same-origin GET with no write payload for authoritative zone choices', async () => {
  vi.mocked(api.profileTimezones).mockRestore();
  const fetch = vi.fn().mockResolvedValue(json({ items: zones })); vi.stubGlobal('fetch', fetch);
  expect(await api.profileTimezones()).toEqual(zones);
  expect(fetch).toHaveBeenCalledWith('/api/profile/timezones', expect.objectContaining({ method: 'GET', credentials: 'same-origin', cache: 'no-store' }));
  expect(fetch.mock.calls[0][1]).not.toHaveProperty('body');
});
it.each([null, [], {}, { items: [] }, { items: 'UTC' }, { items: ['UTC', 'UTC'] }, { items: ['UTC', 'Asia/Kolkata'] },
  { items: [null] }, { items: [42] }, { items: ['Mars Base'] }, { items: ['Factory'] }, { items: ['localtime'] },
  { items: ['../UTC'] }, { items: ['UTC/'] }, { items: ['a'.repeat(65)] }, { items: zones, next_cursor: null }, { items: Array(2049).fill('UTC') },
])('rejects malformed timezone catalogue %#', async value => {
  vi.mocked(api.profileTimezones).mockRestore(); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(value)));
  await expect(api.profileTimezones()).rejects.toMatchObject({ code: 'invalid_response' });
});

it('previews canonical skills, clears corrected errors and submits only canonical values', async () => {
  const { skills, save } = await open();
  fireEvent.change(skills, { target: { value: 'bad/skill' } }); fireEvent.blur(skills);
  expect(skills.getAttribute('aria-invalid')).toBe('true');
  fireEvent.change(skills, { target: { value: 'Data   Science, data-science, Python' } });
  expect(skills.getAttribute('aria-invalid')).toBe('false');
  expect(screen.getByText('Will save as: data-science, python')).toBeTruthy();
  expect(screen.queryByText(/Profile saved/)).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save).toHaveBeenCalledWith(U1, { skills: ['data-science', 'python'], timezone: null, discoverable: false, version: 0 }, csrf, expect.any(AbortSignal));
});

it('distinguishes saved state, search and explicit keyboard selection with required-zone focus', async () => {
  const { save } = await open(); const input = screen.getByRole('combobox') as HTMLInputElement;
  expect(screen.getByText('No time zone saved.')).toBeTruthy(); expect(input.value).toBe('');
  expect(input.placeholder).toBe('Search time zones…');
  fireEvent.click(screen.getByLabelText('Show me in teammate rankings'));
  expect(input.getAttribute('aria-invalid')).toBe('true');
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); expect(document.activeElement).toBe(input);
  fireEvent.change(input, { target: { value: 'Kolkata' } });
  expect(screen.getByRole('option', { name: 'Kolkata — Asia/Kolkata' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); expect(save).not.toHaveBeenCalled();
  fireEvent.keyDown(input, { key: 'ArrowDown' });
  expect(document.getElementById(input.getAttribute('aria-activedescendant')!)?.textContent).toBe('Kolkata — Asia/Kolkata');
  fireEvent.keyDown(input, { key: 'Enter' }); expect(input.value).toBe('');
  expect(input.getAttribute('aria-invalid')).toBe('false'); expect(save).not.toHaveBeenCalled();
  expect(screen.getByText('Selected time zone: Kolkata — Asia/Kolkata')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[0][1].timezone).toBe('Asia/Kolkata');
});

it('handles Up/Escape/Tab, no results and explicit cancel without changing saved alias', async () => {
  const { save } = await open(profile({ timezone: 'Asia/Calcutta', version: 4 }));
  const input = screen.getByRole('combobox'); fireEvent.focus(input);
  fireEvent.keyDown(input, { key: 'ArrowUp' }); expect(document.getElementById(input.getAttribute('aria-activedescendant')!)?.textContent).toContain('UTC');
  fireEvent.keyDown(input, { key: 'Escape' }); expect(input.getAttribute('aria-expanded')).toBe('false');
  fireEvent.focus(input); fireEvent.keyDown(input, { key: 'Tab' }); expect(input.getAttribute('aria-expanded')).toBe('false');
  fireEvent.change(input, { target: { value: 'Neverland' } }); expect(screen.getByText('No matching time zones.')).toBeTruthy();
  fireEvent.blur(input); expect(input.getAttribute('aria-invalid')).toBe('true');
  fireEvent.click(screen.getByRole('button', { name: 'Cancel time zone search' })); expect(input.getAttribute('aria-invalid')).toBe('false');
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[0][1]).toMatchObject({ timezone: 'Asia/Calcutta', version: 4 });
});

it('supports pointer selection, opt-out clearing and responsive requirement changes', async () => {
  const { save } = await open(); const input = screen.getByRole('combobox');
  fireEvent.click(screen.getByLabelText('Show me in teammate rankings'));
  fireEvent.focus(input); fireEvent.mouseDown(screen.getByRole('option', { name: 'London — Europe/London' }));
  fireEvent.click(screen.getByRole('option', { name: 'London — Europe/London' }));
  expect(input.getAttribute('aria-invalid')).toBe('false'); expect(screen.getByRole('button', { name: 'Clear time zone' }).matches(':disabled')).toBe(true);
  fireEvent.click(screen.getByLabelText('Show me in teammate rankings'));
  fireEvent.click(screen.getByRole('button', { name: 'Clear time zone' }));
  expect(screen.getByText('No time zone selected.')).toBeTruthy();
  fireEvent.click(screen.getByLabelText('Show me in teammate rankings')); expect(input.getAttribute('aria-invalid')).toBe('true');
  fireEvent.click(screen.getByLabelText('Show me in teammate rankings')); expect(input.getAttribute('aria-invalid')).toBe('false');
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[0][1]).toMatchObject({ timezone: null, discoverable: false });
});

it.each(['UTC', 'Mars/Base'])('suggests browser zone %s only if accepted, never automatically', async browser => {
  vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({ resolvedOptions: () => ({ timeZone: browser }) } as Intl.DateTimeFormat);
  await open(); expect(screen.getByText('No time zone selected.')).toBeTruthy();
  const button = screen.queryByRole('button', { name: `Use browser time zone (${browser})` });
  if (browser === 'UTC') { expect(button).toBeTruthy(); fireEvent.click(button!); expect(screen.getByText('Selected time zone: UTC — UTC')).toBeTruthy(); }
  else expect(button).toBeNull();
});

it('keeps drafts, search and field errors across close/reopen without refetching', async () => {
  const { get, skills } = await open();
  fireEvent.change(skills, { target: { value: 'unfinished/' } }); fireEvent.blur(skills);
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Lon' } });
  fireEvent.click(screen.getByRole('button', { name: 'Close profile' })); expect(screen.queryByRole('form')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  expect((screen.getByLabelText('Skills') as HTMLInputElement).value).toBe('unfinished/');
  expect((screen.getByRole('combobox') as HTMLInputElement).value).toBe('Lon');
  expect(screen.getByLabelText('Skills').getAttribute('aria-invalid')).toBe('true'); expect(get).toHaveBeenCalledTimes(1);
});

it.each(['conflict', 'unknown', 'unrecognized422', 'forbidden', 'invalidAck'])('retains draft and requires explicit version adoption after %s', async kind => {
  const { get, save, skills } = await open(profile({ skills: ['python'], version: 2 }));
  save.mockRejectedValueOnce(kind === 'conflict' ? new ApiError(409, 'profile_changed') : kind === 'unrecognized422' ? new ApiError(422, 'request_failed') : kind === 'forbidden' ? new ApiError(403, 'invalid_csrf') : kind === 'invalidAck' ? new ApiError(0, 'invalid_response') : new Error('offline'));
  fireEvent.change(skills, { target: { value: 'Data Science' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Reload your profile before editing again/);
  expect(skills.value).toBe('Data Science'); expect(skills.matches(':disabled')).toBe(true);
  get.mockResolvedValue(profile({ skills: ['react'], version: 5 }));
  fireEvent.click(screen.getByRole('button', { name: 'Reload profile' }));
  const canonical = await screen.findByRole('region', { name: 'Current saved profile' }); expect(within(canonical).getByText(/Saved skills: react/)).toBeTruthy();
  expect(skills.value).toBe('Data Science'); expect(save).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); expect(save).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Keep draft for a new save' })); expect(save).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[1][1]).toMatchObject({ skills: ['data-science'], version: 5 });
});

it('retains draft after failed reload, and discards it only on explicit choice', async () => {
  const { get, save, skills } = await open(profile({ skills: ['python'], version: 1 }));
  fireEvent.change(skills, { target: { value: 'Data Science' } });
  get.mockRejectedValueOnce(new ApiError(503));
  fireEvent.click(screen.getByRole('button', { name: 'Reload profile' })); await screen.findByRole('alert');
  expect(skills.value).toBe('Data Science'); expect(skills.matches(':disabled')).toBe(true);
  get.mockResolvedValue(profile({ skills: ['react'], timezone: 'Asia/Calcutta', version: 9 }));
  fireEvent.click(screen.getByRole('button', { name: 'Reload profile' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Discard draft and use saved profile' }));
  expect(skills.value).toBe('react'); expect(screen.getByText('Saved time zone: Asia/Calcutta')).toBeTruthy(); expect(save).not.toHaveBeenCalled();
});

it('preserves a definite server rejection across blur, search and equivalent canonical edits', async () => {
  const { save, skills } = await open(profile({ skills: ['python'], version: 3 }));
  save.mockRejectedValueOnce(new ApiError(422, 'invalid_request'));
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/The server rejected this edit/);
  fireEvent.blur(skills); fireEvent.change(skills, { target: { value: ' Python ' } });
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'UTC' } });
  expect(screen.getByText(/The server rejected this edit/)).toBeTruthy();
  fireEvent.change(skills, { target: { value: 'sql' } }); expect(screen.queryByText(/The server rejected this edit/)).toBeNull();
  expect(screen.queryByText(/Profile saved/)).toBeNull();
});

it('blocks saving while zone options are unavailable and recovers through explicit GET retry', async () => {
  vi.mocked(api.profileTimezones).mockRejectedValueOnce(new ApiError(503)).mockResolvedValue(zones);
  vi.spyOn(api, 'profile').mockResolvedValue(profile()); const save = vi.spyOn(api, 'saveProfile');
  render(<ProfilePanel session={session()} signal={new AbortController().signal} onExpired={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' })); await screen.findByLabelText('Skills'); await screen.findByRole('alert');
  expect(screen.getByRole('button', { name: 'Save profile' }).matches(':disabled')).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save profile' }).matches(':disabled')).toBe(false)); expect(save).not.toHaveBeenCalled();
});

it.each(['profile', 'zones', 'save'])('expires the current scope on a %s 401', async kind => {
  if (kind === 'zones') vi.mocked(api.profileTimezones).mockRejectedValueOnce(new ApiError(401));
  const get = vi.spyOn(api, 'profile').mockResolvedValue(profile()); if (kind === 'profile') get.mockRejectedValueOnce(new ApiError(401));
  vi.spyOn(api, 'saveProfile').mockRejectedValue(new ApiError(401)); const expired = vi.fn();
  render(<ProfilePanel session={session()} signal={new AbortController().signal} onExpired={expired} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  if (kind === 'save') { await screen.findByLabelText('Skills'); fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); }
  await waitFor(() => expect(expired).toHaveBeenCalledTimes(1));
});

it.each(['profile', 'zones', 'save'])('aborts and fences late %s after logout/unmount', async kind => {
  const pending = deferred<Profile & string[]>();
  const get = vi.spyOn(api, 'profile').mockResolvedValue(profile());
  const save = vi.spyOn(api, 'saveProfile').mockResolvedValue(profile({ version: 1 }));
  if (kind === 'profile') get.mockReturnValue(pending.promise);
  if (kind === 'zones') vi.mocked(api.profileTimezones).mockReturnValue(pending.promise);
  if (kind === 'save') save.mockReturnValue(pending.promise);
  const expired = vi.fn(), scope = new AbortController();
  const view = render(<ProfilePanel session={session()} signal={scope.signal} onExpired={expired} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  if (kind === 'save') { await screen.findByLabelText('Skills'); fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); }
  const transport = kind === 'profile' ? get.mock.calls[0][1]! : kind === 'zones' ? vi.mocked(api.profileTimezones).mock.calls[0][0]! : save.mock.calls[0][3]!;
  act(() => scope.abort()); expect(transport.aborted).toBe(true); view.unmount();
  await act(async () => pending.reject(new ApiError(401))); expect(expired).not.toHaveBeenCalled();
});

it.each(['identity', 'credentials'])('isolates replacement %s even without an outer React key', async kind => {
  const { skills, view, scope, get } = await open(); fireEvent.change(skills, { target: { value: 'Private draft' } });
  const replacement = { ...session(), csrf_token: 'b'.repeat(43), identity: kind === 'identity' ? { user_id: '00000000-0000-0000-0000-000000000022', username: 'other_user' } : session().identity };
  get.mockResolvedValue(profile({ ...replacement.identity }));
  view.rerender(<StrictMode><ProfilePanel session={replacement} signal={scope.signal} onExpired={vi.fn()} /></StrictMode>);
  expect(screen.queryByLabelText('Skills')).toBeNull(); fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  expect((await screen.findByLabelText('Skills') as HTMLInputElement).value).toBe('');
});

it.each(['profile', 'zones', 'save'])('ignores late successful %s from a replaced account', async kind => {
  const oldProfile = deferred<Profile>(), oldZones = deferred<string[]>(), oldSave = deferred<Profile>();
  const get = vi.spyOn(api, 'profile').mockResolvedValue(profile());
  const save = vi.spyOn(api, 'saveProfile').mockReturnValue(oldSave.promise);
  if (kind === 'profile') get.mockReturnValueOnce(oldProfile.promise);
  if (kind === 'zones') vi.mocked(api.profileTimezones).mockReturnValueOnce(oldZones.promise);
  const expired = vi.fn(), scope = new AbortController();
  const view = render(<ProfilePanel session={session()} signal={scope.signal} onExpired={expired} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  if (kind === 'save') {
    fireEvent.change(await screen.findByLabelText('Skills'), { target: { value: 'Private Draft' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));
  }
  const transport = kind === 'profile' ? get.mock.calls[0][1]! : kind === 'zones' ? vi.mocked(api.profileTimezones).mock.calls[0][0]! : save.mock.calls[0][3]!;
  const next = { ...session(), identity: { user_id: '00000000-0000-0000-0000-000000000022', username: 'other_user' } };
  get.mockResolvedValue(profile({ ...next.identity }));
  view.rerender(<ProfilePanel session={next} signal={new AbortController().signal} onExpired={expired} />);
  expect(transport.aborted).toBe(true);
  await act(async () => { oldProfile.resolve(profile({ skills: ['private'] })); oldZones.resolve(['America/New_York']); oldSave.resolve(profile({ skills: ['private-draft'], version: 1 })); });
  expect(screen.queryByText(/Profile saved/)).toBeNull(); expect(screen.queryByLabelText('Skills')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  expect((await screen.findByLabelText('Skills') as HTMLInputElement).value).toBe(''); expect(expired).not.toHaveBeenCalled();
});

it('keeps canonical alias selection when browser Intl is unavailable', async () => {
  vi.spyOn(Intl, 'DateTimeFormat').mockImplementation(() => { throw new Error('unsupported'); });
  const { save } = await open(profile({ timezone: 'Asia/Kolkata', discoverable: true, version: 2 }));
  expect(screen.queryByRole('button', { name: /Use browser time zone/ })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[0][1].timezone).toBe('Asia/Kolkata');
});

it('exposes the displayed result bound and permits finding a zone beyond the first page', async () => {
  vi.mocked(api.profileTimezones).mockResolvedValue(Array.from({ length: 70 }, (_, n) => `Area/City${String(n).padStart(2, '0')}`));
  await open(); const input = screen.getByRole('combobox'); fireEvent.focus(input);
  expect(screen.getAllByRole('option')).toHaveLength(50); expect(screen.getByText(/Showing 50 of 70/)).toBeTruthy();
  selectZone('City69'); expect(screen.getByText('Selected time zone: City69 — Area/City69')).toBeTruthy();
});

it('round-trips existing canonical punctuation, aliases and opt-in state', async () => {
  const initial = profile({ skills: ['c#', 'c++', 'data-science', 'foo--bar', 'node.js'], timezone: 'Asia/Calcutta', discoverable: true, version: 8 });
  const { save } = await open(initial);
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[0][1]).toEqual({ skills: initial.skills, timezone: initial.timezone, discoverable: true, version: 8 });
});

it('keeps an uncertain save locked even when the canonical read matches the attempted values', async () => {
  const { get, save, skills } = await open(); save.mockRejectedValueOnce(new Error('lost reply'));
  fireEvent.change(skills, { target: { value: 'Data Science' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Reload your profile before editing again/);
  get.mockResolvedValue(profile({ skills: ['data-science'], version: 1 }));
  fireEvent.click(screen.getByRole('button', { name: 'Reload profile' })); await screen.findByRole('region', { name: 'Current saved profile' });
  expect(skills.value).toBe('Data Science'); expect(skills.matches(':disabled')).toBe(true); expect(save).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(/Profile saved/)).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Discard draft and use saved profile' }));
  expect(skills.value).toBe('data-science'); expect(save).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[1][1].version).toBe(1);
});

it('keeps the original in-flight save on close/reopen without starting another write', async () => {
  const { save, skills } = await open(); const pending = deferred<Profile>(); save.mockReturnValueOnce(pending.promise);
  fireEvent.change(skills, { target: { value: 'Data Science' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); const transport = save.mock.calls[0][3]!;
  fireEvent.click(screen.getByRole('button', { name: 'Close profile' }));
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  expect(skills.matches(':disabled')).toBe(true); expect(save).toHaveBeenCalledTimes(1); expect(transport.aborted).toBe(false);
  await act(async () => pending.resolve(profile({ skills: ['data-science'], version: 1 })));
  expect(screen.getByText(/Profile saved/)).toBeTruthy(); expect(skills.value).toBe('data-science');
});

it('updates touched zone validation when a delayed authoritative catalogue arrives', async () => {
  const pending = deferred<string[]>(); vi.mocked(api.profileTimezones).mockReturnValueOnce(pending.promise);
  vi.spyOn(api, 'profile').mockResolvedValue(profile({ timezone: 'Asia/Kolkata', version: 1 }));
  render(<ProfilePanel session={session()} signal={new AbortController().signal} onExpired={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' })); await screen.findByLabelText('Skills');
  fireEvent.click(screen.getByLabelText('Show me in teammate rankings'));
  expect(screen.getByRole('combobox').getAttribute('aria-invalid')).toBe('true');
  await act(async () => pending.resolve(zones));
  expect(screen.getByRole('combobox').getAttribute('aria-invalid')).toBe('false');
});

it('decodes the complete catalogue at the maximum response bound', async () => {
  vi.mocked(api.profileTimezones).mockRestore();
  const values = Array.from({ length: 2048 }, (_, n) => `Area/City${String(n).padStart(4, '0')}`);
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ items: values })));
  expect(await api.profileTimezones()).toEqual(values);
});
