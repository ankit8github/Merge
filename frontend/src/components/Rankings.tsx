import { useCallback, useState } from 'react';
import { api, type Suggestion, type Team } from '../api';
import { useRead } from '../hooks/useRead';
import { ErrorNotice, Loading } from './Feedback';

function Results({ team, actor, onExpired, choose }: { team: Team; actor: string; onExpired: () => void; choose: (person: Suggestion) => void }) {
  const [history, setHistory] = useState<(string | null)[]>([null]);
  const cursor = history.at(-1)!;
  const load = useCallback((signal: AbortSignal) => api.suggestions(team.hackathon_id, team.id, actor, cursor, signal), [team.hackathon_id, team.id, actor, cursor]);
  const { state, retry } = useRead(load, onExpired);
  const restart = () => { setHistory([null]); retry(); };
  return <>
    <button className="text-button" onClick={restart}>Refresh teammate rankings</button>
    <p>70% new skills plus 30% shared working hours, assuming 09:00–17:00 local. These are deterministic suggestions. Profiles are self-reported; invitations still require an available seat.</p>
    {state.status === 'loading' && <Loading>Ranking eligible participants…</Loading>}
    {state.status === 'error' && <><ErrorNotice error={state.error} />
      <p role="status">{state.error.code === 'ranking_changed' ? 'Profiles, membership or the scoring day changed. Restart the ranking.' : state.error.status === 403 ? 'Only the current leader can see rankings.' : 'Rankings are unavailable. Refresh to check current eligibility.'}</p>
      <button className="button secondary" onClick={restart}>Restart rankings</button></>}
    {state.status === 'success' && <>
      <p>Team skills: {state.data.team_skills.join(', ') || 'none recorded'}. Time-zone reference: <time dateTime={state.data.reference_at}>{state.data.reference_at}</time>.</p>
      {!state.data.items.length && <p role="status">No eligible discoverable participants on this page, or the team is full. Participants can opt in using their profile.</p>}
      <ul className="request-list">{state.data.items.map(person => <li className="request-card" key={person.user_id}>
        <h4>{person.display_name} (@{person.username}) — {person.score.toFixed(2)}/100</h4>
        <p>New skills: {person.new_skills.join(', ') || 'none'}. Skills: {person.skills.join(', ') || 'none recorded'}. Time zone: {person.timezone}.</p>
        <p>Skill complement {person.skill_complement.toFixed(4)} × 70 = {person.skill_points.toFixed(2)} points. Time-zone overlap {person.timezone_overlap.toFixed(4)} × 30 = {person.timezone_points.toFixed(2)} points.</p>
        <button className="button secondary" onClick={() => choose(person)}>Select {person.display_name} for invitation</button>
      </li>)}</ul>
      <nav className="pagination" aria-label="Ranking pages">
        <button className="button secondary" disabled={history.length === 1} onClick={() => setHistory(old => old.slice(0, -1))}>Previous rankings</button>
        <button className="button secondary" disabled={!state.data.next_cursor} onClick={() => { if (state.status === 'success' && state.data.next_cursor) setHistory(old => [...old, state.data.next_cursor]); }}>Next rankings</button>
      </nav>
    </>}
  </>;
}

export default function Rankings(props: { team: Team; actor: string; onExpired: () => void; choose: (person: Suggestion) => void }) {
  const [open, setOpen] = useState(false);
  if (props.team.leader.user_id !== props.actor) return null;
  return <section className="admission" aria-label="Teammate rankings">
    <button className="button secondary" aria-expanded={open} onClick={() => setOpen(v => !v)}>{open ? 'Hide teammate rankings' : 'Find teammates'}</button>
    {open && <Results {...props} />}
  </section>;
}
