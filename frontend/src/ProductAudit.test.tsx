import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { api, ApiError, errorMessage, type Profile } from './api';
import ProfilePanel from './components/Profile';
import TeamLifecycle from './components/Lifecycle';
import { InvitationInbox } from './components/Invitations';
import TeamAdmission from './components/Admission';
import type { Lifecycle } from './hooks/useLifecycle';
import type { Invitations } from './hooks/useInvitations';
import type { Admission } from './hooks/useAdmission';
import { H1, I1, invitation, session, team, U1 } from './test/fixtures';

const U2 = '00000000-0000-0000-0000-000000000022';
const profile = (): Profile => ({ ...session().identity, display_name: 'Builder', skills: ['python'], timezone: 'UTC', discoverable: false, version: 1 });
const workspace = () => new AbortController().signal;
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it.each([
  ['profile_changed', 'Your profile changed. Reload it before editing again.'],
  ['ranking_changed', 'Teammate rankings changed. Restart from the first page.'],
  ['username_unavailable', 'That username is unavailable. Choose another.'],
  ['unknown_conflict', 'This action conflicts with the current state. Refresh and check before trying again.'],
])('explains the actual 409 %s conflict', (code, message) => {
  expect(errorMessage(new ApiError(409, code))).toBe(message);
});

it('keeps the profile draft editable after a definite validation rejection, with no reload or automatic retry', async () => {
  const get = vi.spyOn(api, 'profile').mockResolvedValue(profile());
  const save = vi.spyOn(api, 'saveProfile').mockRejectedValueOnce(new ApiError(422, 'invalid_request'))
    .mockResolvedValue({ ...profile(), skills: ['sql'], version: 2 });
  render(<ProfilePanel session={session()} signal={workspace()} onExpired={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  fireEvent.change(await screen.findByLabelText('Skills'), { target: { value: 'sql' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));
  await screen.findByText(/Check your skills and time zone/);
  const submit = screen.getByRole('button', { name: 'Save profile' });
  expect(submit.matches(':disabled')).toBe(false);
  expect((screen.getByLabelText('Skills') as HTMLInputElement).value).toBe('sql');
  expect(screen.queryByText(/Reload your profile before editing again/)).toBeNull();
  expect(save).toHaveBeenCalledTimes(1); expect(get).toHaveBeenCalledTimes(1);
  fireEvent.click(submit); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[1][1]).toMatchObject({ skills: ['sql'], version: 1 });
});

it('announces local profile validation errors and focuses the invalid field without saving', async () => {
  vi.spyOn(api, 'profile').mockResolvedValue(profile()); const save = vi.spyOn(api, 'saveProfile');
  render(<ProfilePanel session={session()} signal={workspace()} onExpired={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' }));
  const skills = await screen.findByLabelText('Skills');
  fireEvent.change(skills, { target: { value: 'bad skill' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' }));
  expect(screen.getByRole('alert').textContent).toContain('comma-separated skills');
  expect(document.activeElement).toBe(skills); expect(save).not.toHaveBeenCalled();
});

function lifecycle(): Lifecycle {
  return { actor: U1, operation: vi.fn(() => null), commands: vi.fn(() => []), revision: vi.fn(() => 0), submit: vi.fn() };
}
it.each(['leave', 'remove'])('returns keyboard focus to the %s trigger after Cancel without submitting', async kind => {
  const control = lifecycle(); vi.spyOn(api, 'members').mockResolvedValue({ items: [{ user_id: U2, display_name: 'Sam', joined_at: '2026-11-14T00:00:00Z' }], next_cursor: null });
  render(<TeamLifecycle team={team()} lifecycle={control} workspace={workspace} onExpired={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Manage membership' }));
  const trigger = kind === 'leave' ? screen.getByRole('button', { name: 'Leave team' }) : await screen.findByRole('button', { name: 'Remove Sam' });
  trigger.focus(); fireEvent.click(trigger);
  expect(screen.getByRole('button', { name: kind === 'leave' ? 'Confirm leave' : 'Confirm removal' })).toBeTruthy();
  const cancel = screen.getByRole('button', { name: 'Cancel' });
  expect(document.activeElement).toBe(cancel);
  fireEvent.click(cancel);
  expect(document.activeElement).toBe(trigger); expect(control.submit).not.toHaveBeenCalled();
});
it('withdraws a removal confirmation when canonical leadership is lost without a mutation', async () => {
  const control = lifecycle(); const expired = vi.fn();
  vi.spyOn(api, 'members').mockResolvedValue({ items: [{ user_id: U2, display_name: 'Sam', joined_at: '2026-11-14T00:00:00Z' }], next_cursor: null });
  const { rerender } = render(<TeamLifecycle team={team()} lifecycle={control} workspace={workspace} onExpired={expired} />);
  fireEvent.click(screen.getByRole('button', { name: 'Manage membership' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Remove Sam' }));
  expect(screen.getByRole('button', { name: 'Confirm removal' })).toBeTruthy();
  rerender(<TeamLifecycle team={{ ...team(), leader: { user_id: U2, display_name: 'Sam' } }} lifecycle={control} workspace={workspace} onExpired={expired} />);
  expect(screen.queryByRole('button', { name: 'Confirm removal' })).toBeNull();
  expect(control.submit).not.toHaveBeenCalled(); expect(screen.getByRole('button', { name: 'Leave team' })).toBeTruthy();
  rerender(<TeamLifecycle team={team()} lifecycle={control} workspace={workspace} onExpired={expired} />);
  expect(screen.queryByRole('button', { name: 'Confirm removal' })).toBeNull();
});

it('uses the invited team name for headings and accessible actions while retaining technical references', async () => {
  vi.spyOn(api, 'invitations').mockResolvedValue({ items: [invitation({ team_name: 'Named team' })], next_cursor: null });
  const controls = { actor: U1, operation: () => null, redemptions: () => [], refresh: vi.fn(), submit: vi.fn() } as unknown as Invitations;
  const open = vi.fn();
  render(<InvitationInbox hackathon={{ id: H1, name: 'Challenge', min_team_size: 2, max_team_size: 4 }} invitations={controls}
    membership={{ state: { status: 'success', data: null }, retry: vi.fn() }} restore={vi.fn()} onExpired={vi.fn()} open={open} workspace={workspace} />);
  const heading = await screen.findByRole('heading', { name: 'Invitation to Named team' });
  expect(heading.textContent).not.toContain(I1);
  fireEvent.click(screen.getByRole('button', { name: 'Redeem invitation to Named team' }));
  expect(controls.submit).toHaveBeenCalledWith('redeem', H1, team().id, I1, expect.any(AbortSignal));
  fireEvent.click(screen.getByRole('button', { name: 'View invited team Named team' })); expect(open).toHaveBeenCalledWith(team().id);
  expect(within(heading.closest('li')!).getByText(/Invitation ID:/).textContent).toContain(I1);
});

it('names approval actions using the applicant label while submitting the unchanged request ID', async () => {
  const row = { id: I1, hackathon_id: H1, team_id: team().id, requester_id: U2, status: 'pending' as const,
    created_at: '2026-11-14T00:00:00Z', resolved_at: null, requester_display_name: 'Sam', requester_username: 'sam_dev' };
  vi.spyOn(api, 'pendingRequests').mockResolvedValue({ items: [row], next_cursor: null });
  const control = { actor: U1, decisions: () => [], operation: () => null, refresh: vi.fn(), submit: vi.fn() } as unknown as Admission;
  render(<TeamAdmission team={team()} admission={control} membership={{ state: { status: 'success', data: team() }, retry: vi.fn() }}
    restore={vi.fn()} onExpired={vi.fn()} workspace={workspace} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Approve applicant Sam (@sam_dev)' }));
  expect(control.submit).toHaveBeenCalledWith(H1, team().id, expect.any(AbortSignal), I1, 'approve');
  expect(screen.getByRole('button', { name: 'Reject applicant Sam (@sam_dev)' })).toBeTruthy();
});

it.each([true, false])('announces confirmed redemption once with the inbox row present=%s', async present => {
  const command = { kind: 'redeem' as const, hackathon: H1, team: team().id, target: I1, key: 'original-key', status: 'success' as const, uncertain: false, error: null };
  vi.spyOn(api, 'invitations').mockResolvedValue({ items: present ? [invitation({ team_name: 'Named team', status: 'redeemed', redeemed_at: '2026-11-11T01:00:00Z', available: false })] : [], next_cursor: null });
  const controls = { actor: U1, operation: () => command, redemptions: () => [command], refresh: vi.fn(), submit: vi.fn() } as unknown as Invitations;
  render(<InvitationInbox hackathon={{ id: H1, name: 'Challenge', min_team_size: 2, max_team_size: 4 }} invitations={controls}
    membership={{ state: { status: 'success', data: team() }, retry: vi.fn() }} restore={vi.fn()} onExpired={vi.fn()} open={vi.fn()} workspace={workspace} />);
  if (present) await screen.findByRole('heading', { name: 'Invitation to Named team' });
  else await screen.findByText('No invitations on this page.');
  expect(screen.getAllByText(/Redemption confirmed\.|A redemption command was confirmed\./)).toHaveLength(1);
});

it('requires reload on an unrecognized 422 response and submits the reloaded profile version only on an explicit save', async () => {
  const get = vi.spyOn(api, 'profile').mockResolvedValueOnce(profile()).mockResolvedValue({ ...profile(), skills: ['react'], version: 4 });
  const save = vi.spyOn(api, 'saveProfile').mockRejectedValueOnce(new ApiError(422, 'request_failed'))
    .mockResolvedValue({ ...profile(), skills: ['react'], version: 5 });
  render(<ProfilePanel session={session()} signal={workspace()} onExpired={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Edit skills and time zone' })); await screen.findByLabelText('Skills');
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Reload your profile before editing again/);
  expect(screen.getByRole('button', { name: 'Save profile' }).matches(':disabled')).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Reload profile' }));
  const skills = await screen.findByLabelText('Skills'); expect((skills as HTMLInputElement).value).toBe('react');
  expect(get).toHaveBeenCalledTimes(2); expect(save).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Save profile' })); await screen.findByText(/Profile saved/);
  expect(save.mock.calls[1][1]).toMatchObject({ skills: ['react'], version: 4 });
});
