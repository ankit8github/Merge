import { useCallback, useId, useLayoutEffect, useRef, useState } from 'react';
import { api, type Team } from '../api';
import { useRead } from '../hooks/useRead';
import { type Lifecycle, type LifecycleCommand } from '../hooks/useLifecycle';
import type { WorkspaceSignal } from '../hooks/useWorkspaceSignal';
import { ErrorNotice, Loading } from './Feedback';

function Feedback({ command }: { command: LifecycleCommand }) {
  return <>
    {command.status === 'pending' && <p role="status">Sending team change…</p>}
    {command.status === 'success' && <p role="status">Team change confirmed. {command.kind === 'remove' ? 'Member removal completed.' : 'Your departure completed. Leadership passes to a remaining member; a final departure deletes the team.'} Current membership comes from refreshed server reads.</p>}
    {command.error && <p role="alert">{command.error.code === 'forbidden' ? 'Current team permission is required.' :
      command.error.code === 'member_not_found' ? 'The participant is no longer on this team. Refresh current membership.' :
      command.error.code === 'team_not_found' ? 'This team is no longer available.' :
      command.uncertain ? 'Delivery is not confirmed. Keep this tab open and retry only the original command.' :
      'The team change was rejected. Refresh current state before trying again.'}</p>}
  </>;
}

export function LifecycleRecovery({ lifecycle, hackathon, workspace }: { lifecycle: Lifecycle; hackathon: string; workspace: WorkspaceSignal }) {
  return <>{lifecycle.commands(hackathon).map(c => <div key={`${c.team}:${c.kind}:${c.subject}`}>
    <Feedback command={c} />
    {c.uncertain && <div className="notice unresolved"><p>Original {c.kind} command for team {c.team}, participant {c.subject}. A later denial does not undo an earlier attempt.</p>
      <button className="button secondary" disabled={c.status === 'pending'} onClick={() => lifecycle.submit(c.kind, c.hackathon, c.team, c.subject, workspace(), true)}>Retry original {c.kind === 'leave' ? 'leave' : 'removal'}</button></div>}
  </div>)}</>;
}

function Roster({ team, lifecycle, workspace, onExpired, choose }: { team: Team; lifecycle: Lifecycle; workspace: WorkspaceSignal;
  onExpired: () => void; choose: (user: string, name: string, trigger: HTMLButtonElement) => void }) {
  const [history, setHistory] = useState<(string | null)[]>([null]); const cursor = history.at(-1)!;
  const load = useCallback((signal: AbortSignal) => api.members(team.hackathon_id, team.id, cursor, signal), [team.hackathon_id, team.id, cursor]);
  const { state, retry } = useRead(load, onExpired);
  return <>
    {state.status === 'loading' && <Loading>Loading current members…</Loading>}
    {state.status === 'error' && <><ErrorNotice error={state.error} retry={retry} /><button onClick={() => { setHistory([null]); retry(); }}>Restart member list</button></>}
    {state.status === 'success' && <><ul>{state.data.items.map(m => <li key={m.user_id}>{m.display_name}{m.user_id === team.leader.user_id ? ' (leader)' : ''}
      {team.leader.user_id === lifecycle.actor && m.user_id !== lifecycle.actor && <button className="button secondary" onClick={event => choose(m.user_id, m.display_name, event.currentTarget)}
        disabled={!!lifecycle.operation('remove', team.hackathon_id, team.id, m.user_id)?.uncertain}>Remove {m.display_name}</button>}</li>)}</ul>
      <nav aria-label="Member pages"><button disabled={history.length===1} onClick={() => setHistory(old => old.slice(0,-1))}>Previous members</button>
        <button disabled={!state.data.next_cursor} onClick={() => { if (state.status==='success' && state.data.next_cursor) setHistory(old => [...old,state.data.next_cursor]); }}>Next members</button></nav></>}
  </>;
}

export default function TeamLifecycle({ team, lifecycle, workspace, onExpired }: { team: Team; lifecycle: Lifecycle; workspace: WorkspaceSignal; onExpired: () => void }) {
  const id = useId(); const [manage, setManage] = useState(false);
  const [confirmation, setConfirmation] = useState<{ kind: 'leave' | 'remove'; subject: string; name: string } | null>(null);
  const trigger = useRef<HTMLButtonElement | null>(null), manageButton = useRef<HTMLButtonElement | null>(null);
  const cancelButton = useRef<HTMLButtonElement | null>(null);
  const leader = team.leader.user_id === lifecycle.actor;
  useLayoutEffect(() => {
    if (confirmation?.kind === 'remove' && !leader) {
      setConfirmation(null); manageButton.current?.focus();
    }
  }, [confirmation, leader]);
  useLayoutEffect(() => {
    if (manage && confirmation) cancelButton.current?.focus();
  }, [confirmation, manage]);
  function cancel() {
    setConfirmation(null);
    const destination = trigger.current;
    if (destination?.isConnected && !destination.disabled) destination.focus();
    else manageButton.current?.focus();
  }
  const outstanding = lifecycle.commands(team.hackathon_id).some(c => c.team===team.id && (c.status==='pending' || c.uncertain));
  return <section className="admission" aria-label="Team membership controls">
    <h3>Team membership</h3><button ref={manageButton} className="button secondary" onClick={() => { setManage(v => !v); setConfirmation(null); }} aria-expanded={manage}>Manage membership</button>
    {manage && <><p>Leaving as leader transfers leadership to the longest-standing remaining member, with account ID breaking ties. Leaving as the final member deletes the team.</p>
      <Roster team={team} lifecycle={lifecycle} workspace={workspace} onExpired={onExpired} choose={(subject,name,button) => { trigger.current = button; setConfirmation({kind:'remove',subject,name}); }} />
      <button className="button secondary" disabled={outstanding} onClick={event => { trigger.current = event.currentTarget; setConfirmation({kind:'leave',subject:lifecycle.actor,name:'your membership'}); }}>Leave team</button>
      {confirmation && (confirmation.kind === 'leave' || leader) && <fieldset aria-labelledby={id} disabled={outstanding}><legend id={id}>{confirmation.kind==='leave' ? `Leave ${team.name}?` : `Remove ${confirmation.name} from ${team.name}?`}</legend>
        <p>{confirmation.kind === 'remove' ? `${confirmation.name} will lose membership in ${team.name}.` : `You will leave ${team.name}. If you are the final member, the team will be deleted; otherwise leadership passes when needed.`} Cancel keeps membership unchanged. After confirmation, cancelling this screen cannot undo the change.</p>
        <button className="button primary" onClick={() => { lifecycle.submit(confirmation.kind,team.hackathon_id,team.id,confirmation.subject,workspace()); setConfirmation(null); }}>Confirm {confirmation.kind==='leave' ? 'leave' : 'removal'}</button>
        <button ref={cancelButton} className="button secondary" onClick={cancel}>Cancel</button></fieldset>}
    </>}
  </section>;
}
