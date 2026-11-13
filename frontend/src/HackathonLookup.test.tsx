import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from './api';
import HackathonLookup from './components/HackathonLookup';
import { failure, H1, H2, hackathon, json } from './test/fixtures';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const ZERO = '00000000-0000-0000-0000-000000000000';
const TARGET = '6ed60838-e377-428b-a925-c4662c0d5c0a';

it.each([
  [TARGET, '6ed60838-e377-428b-a925-c4662c0d5c09'],
  ['80000000-0000-0000-0000-000000000000', '7fffffff-ffff-ffff-ffff-ffffffffffff'],
  ['ffffffff-ffff-ffff-ffff-ffffffffffff', 'ffffffff-ffff-ffff-ffff-fffffffffffe'],
  [H1, ZERO], [ZERO, null],
])('looks up %s with exact 128-bit predecessor %s', async (id, predecessor) => {
  const fetch = vi.fn().mockResolvedValue(json({ items: [hackathon(id)], next_cursor: null }));
  vi.stubGlobal('fetch', fetch);
  expect((await api.lookupHackathon(id.toUpperCase()))?.id).toBe(id);
  expect(fetch.mock.calls[0][0]).toBe('/api/hackathons?limit=1' + (predecessor === null ? '' : '&cursor=' + predecessor));
  expect(fetch.mock.calls[0][1]).toMatchObject({ method: 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } });
  expect(fetch.mock.calls[0][1]).not.toHaveProperty('body');
});
it.each(['', 'challenge', H1.replaceAll('-', ''), H1 + '&cursor=' + H2, ' ' + H1, H1 + '\n', H1 + '\r', H1 + '\r\n', H1 + '\u2028', H1 + '\u2029'])('rejects noncanonical input without fetching: %s', async id => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  await expect(api.lookupHackathon(id)).rejects.toMatchObject({ status: 422 });
  expect(fetch).not.toHaveBeenCalled();
});
it.each([{ items: [] }, { items: [hackathon(H2)] }])('does not confuse an empty/neighbor result with the requested ID %#', async ({ items }) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ items, next_cursor: null })));
  expect(await api.lookupHackathon(H1)).toBe(null);
});
it('rejects a response exceeding the requested limit', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ items: [hackathon(), hackathon(H2)], next_cursor: null })));
  await expect(api.lookupHackathon(H1)).rejects.toMatchObject({ code: 'invalid_response' });
});
function input(id: string) {
  fireEvent.change(screen.getByLabelText('Hackathon UUID'), { target: { value: id } });
  fireEvent.click(screen.getByRole('button', { name: 'Look up UUID' }));
}
it('announces loading, displays a verified result and selects only on explicit action', async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const choose = vi.fn(); render(<HackathonLookup choose={choose} onExpired={vi.fn()} />);
  input(H1); expect(screen.getByRole('status').textContent).toContain('Looking up');
  expect(choose).not.toHaveBeenCalled();
  await act(async () => finish(json({ items: [hackathon()], next_cursor: null })));
  expect(screen.getByRole('status').textContent).toContain(H1);
  expect(choose).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Select hackathon' }));
  expect(choose).toHaveBeenCalledExactlyOnceWith(hackathon());
});
it('shows accessible validation and not-found states without selecting a neighbor', async () => {
  const fetch = vi.fn().mockResolvedValue(json({ items: [hackathon(H2)], next_cursor: null }));
  vi.stubGlobal('fetch', fetch); const choose = vi.fn();
  render(<HackathonLookup choose={choose} onExpired={vi.fn()} />);
  input('bad'); expect(screen.getByRole('alert').textContent).toContain('complete UUID'); expect(fetch).not.toHaveBeenCalled();
  input(H1); await screen.findByText('No hackathon matches that UUID.');
  expect(screen.queryByRole('button', { name: 'Select hackathon' })).toBe(null); expect(choose).not.toHaveBeenCalled();
});
it.each(['403', 'network'])('shows sanitized %s feedback with explicit retry and no selection', async mode => {
  const fetch = vi.fn().mockImplementation(() => mode === '403' ? Promise.resolve(failure(403, 'browser_scope_rejected')) : Promise.reject(new Error('private network detail')));
  vi.stubGlobal('fetch', fetch); const choose = vi.fn(), expired = vi.fn();
  render(<HackathonLookup choose={choose} onExpired={expired} />); input(H1);
  const alert = await screen.findByRole('alert'); expect(alert.textContent).not.toContain('private network detail');
  expect(within(alert).getByRole('button', { name: 'Try again' })).toBeTruthy();
  expect(choose).not.toHaveBeenCalled(); expect(expired).not.toHaveBeenCalled(); expect(fetch).toHaveBeenCalledTimes(1);
});
it.each([200, 401])('ignores stale %s after changing the input, even if transport ignores abort', async status => {
  let finish!: (response: Response) => void;
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const expired = vi.fn(); render(<HackathonLookup choose={vi.fn()} onExpired={expired} />);
  input(H1); fireEvent.change(screen.getByLabelText('Hackathon UUID'), { target: { value: H2 } });
  await act(async () => finish(status === 200 ? json({ items: [hackathon()], next_cursor: null }) : failure(401)));
  expect(screen.queryByRole('button', { name: 'Select hackathon' })).toBe(null); expect(expired).not.toHaveBeenCalled();
});
