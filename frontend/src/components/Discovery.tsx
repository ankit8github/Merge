import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type Hackathon, type Team } from '../api';
import { useRead } from '../hooks/useRead';
import { ErrorNotice, Loading } from './Feedback';

function Pager({ cursor, next, previous, advance }: { cursor: string | null; next: string | null; previous: () => void; advance: () => void }) {
  return <nav className="pagination" aria-label="Pagination">
    <button className="button secondary" disabled={!cursor} onClick={previous}>Previous page</button>
    <button className="button secondary" disabled={!next} onClick={advance}>Next page <span aria-hidden="true">→</span></button>
  </nav>;
}
function usePage() {
  const [history, setHistory] = useState<(string | null)[]>([null]);
  return { cursor: history[history.length - 1], reset: () => setHistory([null]),
    previous: () => setHistory(old => old.length > 1 ? old.slice(0, -1) : old),
    advance: (next: string | null) => { if (next) setHistory(old => [...old, next]); } };
}
function Hackathons({ selected, choose, onExpired }: { selected: Hackathon | null; choose: (item: Hackathon) => void; onExpired: () => void }) {
  const page = usePage();
  const load = useCallback((signal: AbortSignal) => api.hackathons(page.cursor, signal), [page.cursor]);
  const { state, retry } = useRead(load, onExpired);
  return <aside className="panel hackathons" aria-labelledby="hackathons-title">
    <div className="section-top"><h2 id="hackathons-title">Hackathons</h2><button className="text-button" onClick={() => { page.reset(); retry(); }}>Refresh</button></div>
    <p className="muted">Choose your next challenge.</p>
    {state.status === 'loading' && <Loading>Loading hackathons…</Loading>}
    {state.status === 'error' && <ErrorNotice error={state.error} retry={retry} />}
    {state.status === 'success' && <>
      {!state.data.items.length && <p className="empty">No hackathons on this page yet. Check back soon.</p>}
      <ul className="hackathon-list">{state.data.items.map(item => <li key={item.id}>
        <button aria-pressed={selected?.id === item.id} onClick={() => choose(item)}>
          <span className="event-icon" aria-hidden="true">↗</span><span><strong>{item.name}</strong><small>{item.min_team_size}–{item.max_team_size} per team</small></span>
        </button>
      </li>)}</ul>
      <Pager cursor={page.cursor} next={state.data.next_cursor} previous={page.previous} advance={() => page.advance(state.data.next_cursor)} />
    </>}
  </aside>;
}
export function TeamSummary({ team }: { team: Team }) {
  return <>
    <div className="section-top"><span className={`badge ${team.readiness}`}>{team.readiness === 'ready' ? 'Ready' : 'Forming'}</span><span className="muted">{team.member_count}/{team.max_team_size} members</span></div>
    <h3>{team.name}</h3>
    <div className="capacity" role="img" aria-label={`${team.member_count} of ${team.max_team_size} places filled`}><span style={{ width: `${100 * team.member_count / team.max_team_size}%` }} /></div>
    <p className="muted">Team size {team.min_team_size}–{team.max_team_size}</p>
    <div className="leader"><span className="avatar" aria-hidden="true">{Array.from(team.leader.display_name)[0]}</span><span><small>Team leader</small><strong>{team.leader.display_name}</strong></span></div>
  </>;
}
function TeamList({ hackathon, open, onExpired }: { hackathon: Hackathon; open: (id: string) => void; onExpired: () => void }) {
  const page = usePage();
  const load = useCallback((signal: AbortSignal) => api.teams(hackathon.id, page.cursor, signal), [hackathon.id, page.cursor]);
  const { state, retry } = useRead(load, onExpired);
  return <>
    <div className="section-top"><div><span className="eyebrow">DISCOVER THE POSSIBILITIES</span><h2>Find your team</h2></div>
      <button className="button secondary" onClick={() => { page.reset(); retry(); }}>Refresh teams</button></div>
    <p className="muted">Explore teams in {hackathon.name}. A good connection starts here.</p>
    {state.status === 'loading' && <Loading>Loading teams…</Loading>}
    {state.status === 'error' && <><ErrorNotice error={state.error} retry={retry} /><button className="text-button" onClick={() => { page.reset(); retry(); }}>Restart from first page</button></>}
    {state.status === 'success' && <>
      {!state.data.items.length && <div className="panel empty"><h3>A little quiet here.</h3><p>No teams on this page. Refresh or check another hackathon.</p></div>}
      <div className="team-grid">{state.data.items.map(team => <article className="panel team-card" key={team.id}>
        <TeamSummary team={team} /><button className="button secondary full" onClick={() => open(team.id)}>View {team.name}<span aria-hidden="true">↗</span></button>
      </article>)}</div>
      <Pager cursor={page.cursor} next={state.data.next_cursor} previous={page.previous} advance={() => page.advance(state.data.next_cursor)} />
    </>}
    <p className="fine-print">Counts reflect the latest fetched snapshot. Membership actions are not available yet.</p>
  </>;
}
function TeamDetail({ hackathon, id, back, onExpired }: { hackathon: Hackathon; id: string; back: () => void; onExpired: () => void }) {
  const load = useCallback((signal: AbortSignal) => api.team(hackathon.id, id, signal), [hackathon.id, id]);
  const { state, retry } = useRead(load, onExpired);
  return <><button className="text-button back" onClick={back}>← Back to teams</button><h2>Team details</h2>
    {state.status === 'loading' && <Loading>Loading team details…</Loading>}
    {state.status === 'error' && <ErrorNotice error={state.error} retry={retry} />}
    {state.status === 'success' && <article className="panel detail-card"><TeamSummary team={state.data} />
      <dl><dt>Hackathon</dt><dd>{hackathon.name}</dd><dt>Created</dt><dd>{new Date(state.data.created_at).toLocaleDateString(undefined, { dateStyle: 'medium' })}</dd></dl>
      <button className="button primary full" disabled aria-describedby="join-help">Join team · Coming later</button>
      <p className="fine-print" id="join-help">Discovery is read-only. Joining and invitations are not available yet.</p>
    </article>}
  </>;
}
function MyTeam({ hackathon, onExpired }: { hackathon: Hackathon; onExpired: () => void }) {
  const load = useCallback((signal: AbortSignal) => api.myTeam(hackathon.id, signal), [hackathon.id]);
  const { state, retry } = useRead(load, onExpired);
  return <><div className="section-top"><div><span className="eyebrow">YOUR CORNER OF THE COMMUNITY</span><h2>My team</h2></div><button className="button secondary" onClick={retry}>Refresh membership</button></div>
    <p className="muted">Your current membership in {hackathon.name}.</p>
    {state.status === 'loading' && <Loading>Loading your team…</Loading>}
    {state.status === 'error' && <ErrorNotice error={state.error} retry={retry} />}
    {state.status === 'success' && (state.data === null ? <div className="panel empty"><span className="empty-symbol" aria-hidden="true">↗</span><h3>Your next chapter is open.</h3><p>You haven’t joined a team in this hackathon.</p><p className="muted">Browse the community while membership actions are being prepared.</p></div> : <article className="panel detail-card"><TeamSummary team={state.data} /></article>)}
  </>;
}

export default function Discovery({ onExpired }: { onExpired: () => void }) {
  const [selected, setSelected] = useState<Hackathon | null>(null);
  const [view, setView] = useState<'discover' | 'mine'>('discover');
  const [detail, setDetail] = useState<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [navigation, setNavigation] = useState(0);
  useEffect(() => { if (navigation) heading.current?.focus(); }, [navigation]);
  const navigate = (next: 'discover' | 'mine') => { setView(next); setDetail(null); setNavigation(old => old + 1); };
  return <>
    <section className="page-heading"><div><p className="eyebrow">A PLACE TO BUILD TOGETHER</p><h1 ref={heading} tabIndex={-1}>{selected?.name ?? 'Your next great team starts here.'}</h1><p className="muted">Discover people. Share a challenge. Make something matter.</p></div><span className="read-only-label">Discovery preview</span></section>
    <nav className="view-nav" aria-label="Workspace"><button aria-current={view === 'discover' ? 'page' : undefined} onClick={() => navigate('discover')}>Discover teams</button><button disabled={!selected} aria-current={view === 'mine' ? 'page' : undefined} onClick={() => navigate('mine')}>My team</button></nav>
    <div className="workspace"><Hackathons selected={selected} onExpired={onExpired} choose={item => { setSelected(item); navigate('discover'); }} />
      <section className="discovery-content" aria-label="Team workspace" key={`${selected?.id}:${view}:${detail ?? ''}`}>
        {!selected ? <div className="panel empty"><span className="empty-symbol" aria-hidden="true">✳</span><h2>Choose a hackathon.</h2><p>Every great collaboration starts with a shared challenge.<br />Pick one to explore its teams.</p></div>
          : view === 'mine' ? <MyTeam hackathon={selected} onExpired={onExpired} />
          : detail ? <TeamDetail hackathon={selected} id={detail} onExpired={onExpired} back={() => { setDetail(null); setNavigation(old => old + 1); }} />
          : <TeamList hackathon={selected} onExpired={onExpired} open={id => { setDetail(id); setNavigation(old => old + 1); }} />}
      </section>
    </div>
  </>;
}
