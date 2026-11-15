import { useCallback, useId, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, type Hackathon, type InboxInvitation, type Team, type Suggestion } from '../api';
import Rankings from './Rankings';
import { type Invitations, type InvitationCommand, validRecipient } from '../hooks/useInvitations';
import { useRead } from '../hooks/useRead';
import type { WorkspaceSignal } from '../hooks/useWorkspaceSignal';
import { ErrorNotice, Loading, useCooldown } from './Feedback';

type Membership = ReturnType<typeof useRead<Team | null>>;
type Shared = { invitations: Invitations; restore: () => void };

function CommandFeedback({ command, restore }: Shared & { command: InvitationCommand | null }) {
  const error = command?.error;
  let message = '';
  if (error?.code === 'recipient_not_found') message = 'No recipient was found for that UUID. Ask the recipient to share their account UUID.';
  else if (error?.code === 'invitation_expired') message = 'This invitation has expired. Check My team for any earlier membership; ask the current leader for a new invitation if needed.';
  else if (error?.code === 'invitation_stale') message = 'The issuing leader is no longer current. Refresh the team and ask its current leader about an invitation.';
  else if (error?.code === 'invitation_redeemed') message = 'This invitation was already redeemed. Refresh your inbox and My team.';
  else if (error?.code === 'team_full') message = 'The team currently has no available seat. Refresh availability before retrying.';
  else if (error?.code === 'already_assigned') message = 'You already belong to a team in this hackathon. Check My team for your current membership.';
  else if (error?.code === 'forbidden') message = 'Only the current team leader can issue invitations. Refresh the team to check leadership.';
  else if (error?.code === 'idempotency_mismatch') message = 'The original command could not be verified. Keep it unchanged and contact the owner if the original retry cannot resolve it.';
  else if (error?.code === 'secure_random_unavailable') message = 'A secure request key could not be generated. Restore browser cryptography support before trying again.';
  else if (error?.status === 403) message = 'The request was denied. Restore your session and check the application origin.';
  else if (error?.status === 404) message = 'The invitation or team is unavailable to this account. Refresh the inbox and team.';
  else if (error?.status === 422 || error?.status === 400) message = 'The invitation command was rejected. Check the recipient UUID and refresh the workspace.';
  else if (error?.status === 429) message = 'Too many invitation attempts. Wait before retrying.';
  else if (error) message = 'Delivery is not confirmed. Retry the original invitation command to establish its outcome.';
  return <>
    {command?.status === 'pending' && <p role="status">Sending invitation command… Keep this tab open.</p>}
    {command?.status === 'success' && <p className="notice success" role="status">{command.kind === 'issue'
      ? 'Invitation issuance confirmed. The recipient can check their inbox; no seat is reserved.'
      : 'Redemption confirmed. Check the refreshed inbox and My team for current membership.'}</p>}
    {message && <div className="notice error" role="alert"><p>{message}</p>
      {error?.status === 403 && <button className="text-button" onClick={restore}>Restore session</button>}</div>}
    {command?.uncertain && <p className="notice unresolved" role="status">The earlier outcome is still unknown. Keep this tab open. Retry only the original command with its original key; a later rejection does not undo an earlier attempt. Reload or crash loses this recovery state.</p>}
  </>;
}

export function InvitationIssuer({ team, invitations, restore, workspace, onExpired }: Shared & { team: Team; workspace: WorkspaceSignal; onExpired: () => void }) {
  const h = team.hackathon_id, t = team.id, id = useId();
  const command = invitations.operation('issue', h, t);
  const [recipient, setRecipient] = useState(command?.target ?? '');
  const [invalid, setInvalid] = useState(false);
  const [person, setPerson] = useState<Suggestion | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const seconds = useCooldown(command?.error ?? null);
  const pending = command?.status === 'pending', settled = command?.status === 'success';
  const locked = pending || settled || !!command?.uncertain;
  const value = locked ? command!.target : recipient;
  if (team.leader.user_id !== invitations.actor) return command?.error?.code === 'forbidden'
    ? <p className="notice error" role="alert">Only the current team leader can issue invitations.</p> : null;
  function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || settled || seconds > 0) return;
    const target = value.toLowerCase(); // Canonicalize once, then freeze the command.
    if (!validRecipient(target)) { setInvalid(true); input.current?.focus(); return; }
    setInvalid(false); invitations.submit('issue', h, t, target, workspace());
  }
  return <section className="admission invitation-issuer" aria-label="Leader invitations">
    <h3>Invite a participant</h3>
    <p className="muted">Only the current leader can issue invitations. The server checks authorization on every attempt.</p>
    {!locked && <Rankings team={team} actor={invitations.actor} onExpired={onExpired} choose={selected => {
      setPerson(selected); setRecipient(selected.user_id); setInvalid(false); input.current?.focus();
    }} />}
    {person && person.user_id === value && <p role="status">Recipient: {person.display_name} (@{person.username}). Team: {team.name}.</p>}
    <CommandFeedback invitations={invitations} command={command} restore={restore} />
    <form onSubmit={submit} noValidate aria-label="Issue invitation" aria-busy={pending}>
      <label htmlFor={`${id}-recipient`}>Recipient account UUID</label>
      <input id={`${id}-recipient`} ref={input} value={value} readOnly={locked} required autoComplete="off" spellCheck={false}
        aria-invalid={invalid} aria-describedby={`${id}-help${invalid ? ` ${id}-error` : ''}`}
        onChange={event => { if (!locked) { setRecipient(event.target.value); setPerson(null); setInvalid(false); } }} />
      <small id={`${id}-help`}>Choose a ranked participant above, or use the advanced UUID fallback: ask an existing participant to share their account UUID from Invitations. Username search is not available. Invitations do not reserve a seat.</small>
      {invalid && <p id={`${id}-error`} className="field-error" role="alert">Enter a complete account UUID, without surrounding spaces.</p>}
      <div className="admission-actions"><button className="button primary" type="submit" disabled={pending || settled || seconds > 0}>
        {pending ? 'Issuing invitation…' : command?.uncertain ? 'Retry original invitation' : 'Issue invitation'}</button>
        {settled && <button className="button secondary" type="button" onClick={() => {
          invitations.newIssue(h, t); setRecipient(''); setInvalid(false); input.current?.focus();
        }}>Start another invitation</button>}
        <button className="button secondary" type="button" onClick={() => invitations.refresh(h)}>Refresh invitations and team</button>
      </div>
      {seconds > 0 && <p role="status">Try again in {seconds} seconds.</p>}
    </form>
  </section>;
}

function RedemptionCard({ row, command, invitations, membership, restore, open, workspace }: Shared & {
  row?: InboxInvitation; command: InvitationCommand | null; membership: Membership; open: (id: string) => void;
  workspace: WorkspaceSignal;
}) {
  const id = useId(), seconds = useCooldown(command?.error ?? null);
  const h = row?.hackathon_id ?? command!.hackathon, t = row?.team_id ?? command!.team;
  const target = row?.id ?? command!.target;
  const pending = command?.status === 'pending', settled = command?.status === 'success';
  const eligible = !!row && row.status === 'pending' && row.available &&
    membership.state.status === 'success' && membership.state.data === null;
  const disabled = pending || settled || seconds > 0 || (!command?.uncertain && !eligible);
  const label = row?.team_name ? `to ${row.team_name}` : target;
  return <li className="request-card invitation-card" aria-labelledby={id} aria-busy={pending}>
    <h3 id={id}>{row ? 'Invitation ' : 'Original redemption for invitation '}{label}</h3>
    {row?.recipient_display_name && <p>Recipient: {row.recipient_display_name}{row.recipient_username ? ` (@${row.recipient_username})` : ''}</p>}
    <details><summary>Reference IDs</summary><p className="uuid">Invitation ID: {target}</p><p>Team UUID: <span className="uuid">{t}</span></p></details>
    {row && <><p>Current invitation state: <strong>{row.status}</strong></p>
      <p>Expires (your local time): <time dateTime={row.expires_at}>{new Date(row.expires_at).toLocaleString()}</time></p>
      {row.redeemed_at && <p>Redeemed (your local time): <time dateTime={row.redeemed_at}>{new Date(row.redeemed_at).toLocaleString()}</time></p>}
      {row.status === 'pending' && !row.available && <p className="notice">Not currently available. It may be expired or its issuing leader may have changed. Refresh to check again.</p>}</>}
    <CommandFeedback invitations={invitations} command={command} restore={restore} />
    <div className="admission-actions"><button className="button primary" disabled={disabled}
      onClick={() => { if (!disabled) invitations.submit('redeem', h, t, target, workspace()); }} aria-label={command?.uncertain ? `Retry original redemption ${label}` : `Redeem invitation ${label}`}>
      {pending ? 'Redeeming…' : command?.uncertain ? 'Retry original redemption' : 'Redeem invitation'}</button>
      <button className="button secondary" onClick={() => open(t)} aria-label={`View invited team ${row?.team_name ?? t}`}>View invited team</button>
    </div>
    {seconds > 0 && <p role="status">Try again in {seconds} seconds.</p>}
  </li>;
}

export function InvitationInbox({ hackathon, invitations, membership, restore, onExpired, open, workspace }: Shared & {
  hackathon: Hackathon; membership: Membership; onExpired: () => void; open: (id: string) => void;
  workspace: WorkspaceSignal;
}) {
  const h = hackathon.id;
  const [history, setHistory] = useState<(string | null)[]>([null]);
  const cursor = history[history.length - 1];
  const load = useCallback((signal: AbortSignal) => api.invitations(h, cursor, signal).then(page => {
    if (page.items.some(row => row.recipient_id !== invitations.actor)) throw new ApiError(0, 'invalid_response');
    return page;
  }), [h, cursor, invitations.actor]);
  const list = useRead(load, onExpired);
  const rows = list.state.status === 'success' ? list.state.data.items : [];
  const recovery = invitations.redemptions(h).filter(c => (c.uncertain || c.status === 'pending' || !!c.error) && !rows.some(row => row.id === c.target && row.team_id === c.team));
  return <section className="invitation-inbox" aria-label="Your invitations">
    <div className="section-top"><h2>Your invitations</h2><button className="button secondary" onClick={() => invitations.refresh(h)}>Refresh inbox and membership</button></div>
    <p>Invitations addressed to you in {hackathon.name}. Open an invited team for its current name and details.</p>
    <p className="muted">Your recipient account UUID: <span className="uuid">{invitations.actor}</span>. Share this identifier with a team leader; it does not grant access to your account.</p>
    <p className="muted">Availability is from the last server read, not a reserved seat. The server checks your authenticated identity, current grant, expiry and capacity when you redeem.</p>
    {membership.state.status === 'success' && membership.state.data !== null && <p className="notice">You already belong to a team in this hackathon. Check My team. An uncertain original command can still be retried.</p>}
    {membership.state.status !== 'success' && <p className="muted">Membership must be verified before a new redemption.</p>}
    {list.state.status === 'loading' && <Loading>Loading your invitations…</Loading>}
    {list.state.status === 'error' && <>
      {[403, 404].includes(list.state.error.status) ? <p role="alert" className="notice error">Your invitation inbox is unavailable to this session. Restore your session or refresh the selected hackathon.</p>
        : <ErrorNotice error={list.state.error} retry={list.retry} />}
      {[403, 404].includes(list.state.error.status) && <button className="text-button" onClick={restore}>Restore session</button>}
      {list.state.error.status === 422 && <button className="text-button" onClick={() => { setHistory([null]); list.retry(); }}>Restart invitation inbox</button>}
    </>}
    {list.state.status === 'success' && <>
      {!rows.length && <p role="status">No invitations on this page.</p>}
      <ul className="request-list">{rows.map(row => <RedemptionCard key={row.id} row={row} command={invitations.operation('redeem', h, row.team_id, row.id)} invitations={invitations} membership={membership} restore={restore} open={open} workspace={workspace} />)}</ul>
      <nav className="pagination" aria-label="Invitation pages">
        <button className="button secondary" disabled={history.length === 1} onClick={() => setHistory(old => old.slice(0, -1))}>Previous invitations</button>
        <button className="button secondary" disabled={!list.state.data.next_cursor} onClick={() => {
          if (list.state.status === 'success' && list.state.data.next_cursor) setHistory(old => [...old, list.state.status === 'success' ? list.state.data.next_cursor : null]);
        }}>Next invitations</button>
      </nav>
    </>}
    {recovery.length > 0 && <><h3>Original redemption commands</h3><p className="muted">These commands are retained independently of inbox pages. A missing row does not establish rollback.</p>
      <ul className="request-list">{recovery.map(command => <RedemptionCard key={command.target} command={command} invitations={invitations} membership={membership} restore={restore} open={open} workspace={workspace} />)}</ul></>}
    {invitations.redemptions(h).some(c => c.status === 'success' && !rows.some(row => row.id === c.target && row.team_id === c.team)) &&
      <p className="notice success" role="status">A redemption command was confirmed. Use the canonical inbox and My team for current state.</p>}
  </section>;
}
