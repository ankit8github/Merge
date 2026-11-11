import { useCallback, useId, useState } from 'react';
import { api, ApiError, type JoinRequest, type Team } from '../api';
import { type Admission, type AdmissionCommand } from '../hooks/useAdmission';
import { useRead } from '../hooks/useRead';
import type { WorkspaceSignal } from '../hooks/useWorkspaceSignal';
import { ErrorNotice, Loading, useCooldown } from './Feedback';

type Membership = ReturnType<typeof useRead<Team | null>>;
type Props = { team: Team; admission: Admission; membership: Membership; onExpired: () => void; restore: () => void; workspace: WorkspaceSignal };

function CommandFeedback({ command, restore }: { command: AdmissionCommand | null; restore: () => void }) {
  const failure = command?.error;
  let message = '';
  if (failure?.code === 'team_full') message = 'This team is full. The request was not approved by this attempt. Refresh before trying again.';
  else if (failure?.code === 'already_assigned') message = 'The participant already belongs to a team in this hackathon. Refresh the current membership and requests.';
  else if (failure?.code === 'request_resolved') message = 'This request was already resolved. Refresh to see the current state.';
  else if (failure?.code === 'forbidden') message = 'Current team leadership is required. Applicant details are hidden until permission is checked again.';
  else if (failure?.code === 'idempotency_mismatch') message = 'The original command could not be verified. Keep it unchanged and contact the owner if retry cannot resolve it.';
  else if (failure?.code === 'secure_random_unavailable') message = 'A secure request key could not be generated. Restore browser cryptography support before trying again.';
  else if (failure?.status === 403) message = 'The request was denied. Restore your session and check the application origin.';
  else if (failure?.status === 404) message = 'This team or request is no longer available. Refresh the workspace.';
  else if (failure?.status === 422) message = 'The command was rejected. Refresh the workspace before trying again.';
  else if (failure?.status === 429) message = 'Too many attempts. Wait before retrying.';
  else if (failure) message = 'Delivery is not confirmed. Retry the original command to establish its outcome.';
  return <>
    {command?.status === 'pending' && <p role="status">Sending command… Please wait.</p>}
    {command?.status === 'success' && <p className="notice success" role="status">Command confirmed. Current request and membership information comes from the refreshed server reads.</p>}
    {message && <div className="notice error" role="alert"><p>{message}</p>
      {failure?.status === 403 && <button className="text-button" onClick={restore}>Restore session</button>}</div>}
    {command?.uncertain && <p className="notice unresolved" role="status">The earlier outcome is still unknown. Keep this tab open. Only retry the original command with its original request key; a later rejection does not undo an earlier attempt.</p>}
  </>;
}

function MemberRequest({ team, admission, membership, onExpired, restore, workspace }: Props) {
  const h = team.hackathon_id, t = team.id;
  const load = useCallback((signal: AbortSignal) => api.ownRequest(h, t, signal).then(row => {
    if (row && row.requester_id !== admission.actor) throw new ApiError(0, 'invalid_response');
    return row;
  }), [h, t, admission.actor]);
  const own = useRead(load, onExpired);
  const command = admission.operation(h, t);
  const seconds = useCooldown(command?.error ?? null);
  const eligible = membership.state.status === 'success' && membership.state.data === null &&
    own.state.status === 'success' && own.state.data === null;
  const disabled = command?.status === 'pending' || command?.status === 'success' || seconds > 0 || (!command?.uncertain && !eligible);
  const status = own.state.status === 'success' ? own.state.data?.status : null;
  return <section className="admission" aria-label="Your join request">
    <h3>Your join request</h3>
    <p className="muted">Request a place on this team. Pending requests do not reserve a seat.</p>
    {own.state.status === 'loading' && <Loading>Checking your request…</Loading>}
    {own.state.status === 'error' && <ErrorNotice error={own.state.error} retry={own.retry} />}
    {status && <p className="notice" role="status">Current request status: <strong>{status}</strong>.
      {status === 'pending' ? ' Waiting for the current leader to decide.' : status === 'approved' ? ' Check My team for your current membership.' : ' This request is closed; a new request to this team is unavailable.'}</p>}
    {membership.state.status === 'success' && membership.state.data && <p className="muted">You already belong to a team in this hackathon. New requests are unavailable.</p>}
    {membership.state.status !== 'success' && <p className="muted">Membership must be verified before sending a new request.</p>}
    <CommandFeedback command={command} restore={restore} />
    <div className="admission-actions">
      <button className="button primary" disabled={disabled} onClick={() => { if (!disabled) admission.submit(h, t, workspace()); }}>
        {command?.status === 'pending' ? 'Request in progress…' : command?.uncertain ? 'Retry original join request' : 'Request membership'}
      </button>
      <button className="button secondary" onClick={() => admission.refresh(h)}>Refresh request and membership</button>
    </div>
    {seconds > 0 && <p role="status">Try again in {seconds} seconds.</p>}
  </section>;
}

function DecisionActions({ row, command, team, admission, restore, workspace }: {
  row: Pick<JoinRequest, 'id' | 'requester_id'>; command: AdmissionCommand | null;
  team: Team; admission: Admission; restore: () => void;
  workspace: WorkspaceSignal;
}) {
  const id = useId(), seconds = useCooldown(command?.error ?? null);
  const pending = command?.status === 'pending', settled = command?.status === 'success';
  return <li className="request-card" aria-labelledby={id} aria-busy={pending}>
    <h4 id={id}>{row.requester_id ? 'Applicant ' + row.requester_id : 'Original decision for request ' + row.id}</h4>
    <CommandFeedback command={command} restore={restore} />
    <div className="admission-actions">
      {command?.uncertain ? <button className="button primary" disabled={pending || seconds > 0}
        onClick={() => admission.submit(team.hackathon_id, team.id, workspace(), row.id, command.decision)}>
        Retry original {command.decision === 'approve' ? 'approval' : 'rejection'}
      </button> : <>
        <button className="button primary" disabled={pending || settled || seconds > 0}
          onClick={() => admission.submit(team.hackathon_id, team.id, workspace(), row.id, 'approve')} aria-label={`Approve applicant ${row.requester_id}`}>Approve</button>
        <button className="button secondary" disabled={pending || settled || seconds > 0}
          onClick={() => admission.submit(team.hackathon_id, team.id, workspace(), row.id, 'reject')} aria-label={`Reject applicant ${row.requester_id}`}>Reject</button>
      </>}
    </div>
    {seconds > 0 && <p role="status">Try again in {seconds} seconds.</p>}
  </li>;
}

function LeaderRequests({ team, admission, onExpired, restore, workspace }: Props) {
  const [history, setHistory] = useState<(string | null)[]>([null]);
  const cursor = history[history.length - 1], h = team.hackathon_id, t = team.id;
  const load = useCallback((signal: AbortSignal) => api.pendingRequests(h, t, cursor, signal), [h, t, cursor]);
  const list = useRead(load, onExpired);
  const commands = admission.decisions(h, t);
  const rows = list.state.status === 'success' ? list.state.data.items : [];
  // A completed decision can disappear from the pending page before its lost
  // acknowledgement is reconciled. Keep its exact original retry reachable.
  const recovery = commands.filter(c => (c.uncertain || c.status === 'pending') && !rows.some(row => row.id === c.requestId));
  const denied = list.state.status === 'error' && [403, 404].includes(list.state.error.status);
  return <section className="admission" aria-label="Leader join requests">
    <div className="section-top"><h3>Pending join requests</h3><button className="text-button" onClick={() => admission.refresh(h)}>Refresh requests and team</button></div>
    <p className="muted">Only the current leader may review applicants. The server checks permission on every read and decision.</p>
    {list.state.status === 'loading' && <Loading>Loading pending requests…</Loading>}
    {list.state.status === 'error' && (denied ? <p className="notice error" role="alert">Permission could not be confirmed. Applicant details are hidden. Refresh the team to check current leadership.</p>
      : <ErrorNotice error={list.state.error} retry={list.retry} />)}
    {list.state.status === 'error' && list.state.error.status === 422 && <button className="text-button" onClick={() => { setHistory([null]); list.retry(); }}>Restart request list</button>}
    {list.state.status === 'success' && <>
      {!rows.length && <p role="status">No pending requests on this page.</p>}
      <ul className="request-list">{rows.map(row => <DecisionActions key={row.id} row={row} team={team} admission={admission}
        command={admission.operation(h, t, row.id)} restore={restore} workspace={workspace} />)}</ul>
      <nav className="pagination" aria-label="Request pages">
        <button className="button secondary" disabled={history.length === 1} onClick={() => setHistory(old => old.slice(0, -1))}>Previous requests</button>
        <button className="button secondary" disabled={!list.state.data.next_cursor} onClick={() => {
          if (list.state.status === 'success' && list.state.data.next_cursor) setHistory(old => [...old, list.state.status === 'success' ? list.state.data.next_cursor : null]);
        }}>Next requests</button>
      </nav>
    </>}
    {list.state.status === 'success' && recovery.length > 0 && <><h4>Commands awaiting confirmation</h4><ul className="request-list">{recovery.map(command =>
      <DecisionActions key={command.requestId} row={{ id: command.requestId!, requester_id: '' }} command={command}
        team={team} admission={admission} restore={restore} workspace={workspace} />)}</ul></>}
    {list.state.status === 'success' && commands.filter(c => c.status === 'rejected' && !c.uncertain && !rows.some(row => row.id === c.requestId)).map(command =>
      <div key={command.requestId}><CommandFeedback command={command} restore={restore} /></div>)}
    {commands.some(c => c.status === 'success') && <p className="notice success" role="status">Decision confirmed. The pending list and team details are fetched again from the server.</p>}
  </section>;
}

export default function TeamAdmission(props: Props) {
  if (props.team.leader.user_id === props.admission.actor) return <LeaderRequests {...props} />;
  return <>{props.admission.decisions(props.team.hackathon_id, props.team.id).some(c => c.error?.code === 'forbidden') &&
    <p className="notice error" role="alert">Current team leadership is required. Applicant details are hidden.</p>}<MemberRequest {...props} /></>;
}
