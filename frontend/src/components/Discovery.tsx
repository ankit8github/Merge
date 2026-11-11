import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { api, type Hackathon, type Team } from '../api';
import { useRead } from '../hooks/useRead';
import { type TeamCreation } from '../hooks/useTeamCreation';
import CreateTeam from './CreateTeam';
import TeamAdmission from './Admission';
import type { Admission } from '../hooks/useAdmission';
import type { Invitations } from '../hooks/useInvitations';
import { InvitationIssuer, InvitationInbox } from './Invitations';
import { useWorkspaceSignal, type WorkspaceSignal } from '../hooks/useWorkspaceSignal';
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
    <p className="fine-print">Counts reflect the latest fetched snapshot. Open a team to request membership or review requests.</p>
  </>;
}
function TeamDetail({ hackathon, id, back, onExpired, admission, invitations, membership, restore, workspace }: {
  hackathon: Hackathon; id: string; back: () => void; onExpired: () => void; admission: Admission;
  membership: ReturnType<typeof useRead<Team | null>>; restore: () => void;
  invitations: Invitations;
  workspace: WorkspaceSignal;
}) {
  const load = useCallback((signal: AbortSignal) => api.team(hackathon.id, id, signal), [hackathon.id, id]);
  const { state, retry } = useRead(load, onExpired);
  const heading = useRef<HTMLHeadingElement>(null);
  // Set initial detail focus before paint; a deferred passive effect must not
  // steal focus after the user has already interacted with an invitation form.
  useLayoutEffect(() => { if (state.status === 'success') heading.current?.focus(); }, [state.status]);
  return <><button className="text-button back" onClick={back}>← Back to teams</button><h2 tabIndex={-1} ref={heading}>Team details</h2>
    {state.status === 'loading' && <Loading>Loading team details…</Loading>}
    {state.status === 'error' && <ErrorNotice error={state.error} retry={retry} />}
    {state.status === 'success' && <article className="panel detail-card"><TeamSummary team={state.data} />
      <dl><dt>Hackathon</dt><dd>{hackathon.name}</dd><dt>Created</dt><dd>{new Date(state.data.created_at).toLocaleDateString(undefined, { dateStyle: 'medium' })}</dd></dl>
      <TeamAdmission team={state.data} admission={admission} membership={membership} restore={restore} onExpired={onExpired} workspace={workspace} />
      <InvitationIssuer team={state.data} invitations={invitations} restore={restore} workspace={workspace} />
    </article>}
  </>;
}
function MyTeam({ hackathon, membership, open }: { hackathon: Hackathon; membership: ReturnType<typeof useRead<Team | null>>; open: (id: string) => void }) {
  const { state, retry } = membership;
  return <><div className="section-top"><div><span className="eyebrow">YOUR CORNER OF THE COMMUNITY</span><h2>My team</h2></div><button className="button secondary" onClick={retry}>Refresh membership</button></div>
    <p className="muted">Your current membership in {hackathon.name}.</p>
    {state.status === 'loading' && <Loading>Loading your team…</Loading>}
    {state.status === 'error' && <ErrorNotice error={state.error} retry={retry} />}
    {state.status === 'success' && (state.data === null ? <div className="panel empty"><span className="empty-symbol" aria-hidden="true">↗</span><h3>Your next chapter is open.</h3><p>You haven’t joined a team in this hackathon.</p><p className="muted">Create your own team or browse the community.</p></div> : <article className="panel detail-card"><TeamSummary team={state.data} /><button className="button secondary" onClick={() => { if (state.status === 'success' && state.data) open(state.data.id); }}>Open team and requests</button></article>)}
  </>;
}

function SelectedWorkspace({ hackathon, view, detail, creation, admission, invitations, restore, onExpired, open, back }: {
  hackathon: Hackathon; view: 'discover' | 'mine' | 'invitations'; detail: string | null; creation: TeamCreation;
  admission: Admission; invitations: Invitations;
  restore: () => void; onExpired: () => void; open: (id: string) => void; back: () => void;
}) {
  const creationWorkspace = useWorkspaceSignal(hackathon.id);
  const commandWorkspace = useWorkspaceSignal(`${view}:${detail ?? ''}`);
  const operation = creation.operation(hackathon.id);
  const revision = `${operation?.status === 'success' || operation?.status === 'assigned' ? operation.key : ''}:${admission.revision(hackathon.id)}:${invitations.revision(hackathon.id)}`;
  const load = useCallback((signal: AbortSignal) => api.myTeam(hackathon.id, signal), [hackathon.id, revision]);
  const membership = useRead(load, onExpired);
  return <>
    <CreateTeam hackathon={hackathon} creation={creation} membership={membership} restore={restore} workspace={creationWorkspace} />
    <div key={`${view}:${detail ?? ''}:${revision}`}>
      {view === 'mine' ? <MyTeam hackathon={hackathon} membership={membership} open={open} />
        : view === 'invitations' ? <InvitationInbox hackathon={hackathon} invitations={invitations} membership={membership} restore={restore} onExpired={onExpired} open={open} workspace={commandWorkspace} />
        : detail ? <TeamDetail hackathon={hackathon} id={detail} onExpired={onExpired} back={back} admission={admission} invitations={invitations} membership={membership} restore={restore} workspace={commandWorkspace} />
        : <TeamList hackathon={hackathon} onExpired={onExpired} open={open} />}
    </div>
  </>;
}

export default function Discovery({ onExpired, creation, admission, invitations, restore }: { onExpired: () => void; creation: TeamCreation; admission: Admission; invitations: Invitations; restore: () => void }) {
  const [selected, setSelected] = useState<Hackathon | null>(null);
  const [view, setView] = useState<'discover' | 'mine' | 'invitations'>('discover');
  const [detail, setDetail] = useState<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [navigation, setNavigation] = useState(0);
  useEffect(() => { if (navigation) heading.current?.focus(); }, [navigation]);
  const navigate = (next: 'discover' | 'mine' | 'invitations') => { setView(next); setDetail(null); setNavigation(old => old + 1); };
  return <>
    <section className="page-heading"><div><p className="eyebrow">A PLACE TO BUILD TOGETHER</p><h1 ref={heading} tabIndex={-1}>{selected?.name ?? 'Your next great team starts here.'}</h1><p className="muted">Discover people. Share a challenge. Make something matter.</p></div><span className="read-only-label">Build your team</span></section>
    <nav className="view-nav" aria-label="Workspace"><button aria-current={view === 'discover' ? 'page' : undefined} onClick={() => navigate('discover')}>Discover teams</button><button disabled={!selected} aria-current={view === 'mine' ? 'page' : undefined} onClick={() => navigate('mine')}>My team</button><button disabled={!selected} aria-current={view === 'invitations' ? 'page' : undefined} onClick={() => navigate('invitations')}>Invitations</button></nav>
    <div className="workspace"><Hackathons selected={selected} onExpired={onExpired} choose={item => { setSelected(item); navigate('discover'); }} />
      <section className="discovery-content" aria-label="Team workspace" key={selected?.id}>
        {!selected ? <div className="panel empty"><span className="empty-symbol" aria-hidden="true">✳</span><h2>Choose a hackathon.</h2><p>Every great collaboration starts with a shared challenge.<br />Pick one to explore its teams.</p></div>
          : <SelectedWorkspace hackathon={selected} view={view} detail={detail} creation={creation} admission={admission} invitations={invitations} restore={restore} onExpired={onExpired}
              back={() => { setDetail(null); setNavigation(old => old + 1); }} open={id => { setView('discover'); setDetail(id); setNavigation(old => old + 1); }} />}
      </section>
    </div>
  </>;
}
