"""Bounded test-only arrival proof and independent committed invitation oracle."""
from threading import Event, Lock
from time import monotonic
from contextlib import contextmanager
from collections.abc import Mapping


class ArrivalGate:
    def __init__(self, actors, timeout=15):
        self.expected=frozenset(actors)
        if len(self.expected)!=len(actors) or not actors: raise ValueError('Distinct actors required')
        self.arrivals=set(); self.lock=Lock(); self.arrived=Event(); self.release=Event()
        self.timeout=timeout; self.invalid=False

    def enter(self, actor):
        with self.lock:
            if actor not in self.expected or actor in self.arrivals:
                self.invalid=True
                raise AssertionError('Unexpected or duplicate authenticated caller')
            self.arrivals.add(actor)
            if self.arrivals==self.expected: self.arrived.set()
        if not self.release.wait(self.timeout): raise AssertionError('Authenticated arrival deadline exceeded')

    def verify(self):
        assert not self.invalid and self.arrivals==self.expected, 'Distinct authenticated callers incomplete'


@contextmanager
def tracked_caller(c, actor, pids, pid_lock):
    info=c.info  # Keep the original mapping: cleanup must not reconnect a failed handle.
    pid=c.connection.dbapi_connection.info.backend_pid
    info['g1_actor']=actor
    try:
        yield
    finally:
        info.pop('g1_actor',None)
        with pid_lock:
            if pids.get(pid)==actor: pids.pop(pid)


def record_target_wait(c, statement, parameters, gate, hackathon, team, pids, pid_lock, changed):
    actor=c.info.get('g1_actor')
    if (actor not in gate.expected or not isinstance(parameters,Mapping)
            or parameters.get('h')!=hackathon or parameters.get('team')!=team
            or 'FROM public.teams' not in statement or 'FOR NO KEY UPDATE' not in statement):
        return
    with pid_lock: pids[c.connection.dbapi_connection.info.backend_pid]=actor
    changed.set()


def rooted_waiters(rows, observer, candidates):
    """Count distinct registered actors reachable from this observer's lock."""
    rooted={observer}
    while True:
        additions={r['pid'] for r in rows if r['pid'] in candidates
                   and any(blocker in rooted for blocker in r['blockers'])}
        if additions<=rooted: break
        rooted.update(additions)
    return len({actor for pid,actor in candidates.items() if pid in rooted and pid!=observer})


def observe_overlap(gate, database, team, pids, pid_lock, changed, timeout=3):
    """Release an observer-held team lock only after two real backend waiters.

    Errors always release authenticated workers; callers still fail the run.
    Poll backoff is not evidence: only pg_blocking_pids observations count.
    """
    from test_support.races import sql
    try:
        assert gate.arrived.wait(15), 'Authenticated callers did not arrive'
        with database.connection() as c:
            blocker=sql(c,'SELECT pg_backend_pid()').scalar_one()
            sql(c,'SELECT id FROM public.teams WHERE id=:t FOR NO KEY UPDATE',t=team)
            gate.release.set()
            deadline=monotonic()+timeout
            while monotonic()<deadline:
                with pid_lock: candidates=dict(pids)
                if len(candidates)>=2:
                    rows=sql(c,'''SELECT pid,pg_blocking_pids(pid) AS blockers FROM pg_stat_activity
                        WHERE pid=ANY(CAST(:workers AS integer[]))
                        AND datname=current_database() AND usename=current_user
                        AND wait_event_type='Lock' ''',workers=list(candidates)).mappings().all()
                    count=rooted_waiters(rows,blocker,candidates)
                    if count>=2:
                        c.commit()
                        return count
                changed.wait(.01); changed.clear()
            raise AssertionError('No observed distinct-backend lock contention')
    finally:
        gate.release.set()


def assert_race_state(state, invitations, outcomes, leader, team):
    ids=[str(value) for value in invitations]
    assert len(ids)==len(set(ids))==len(outcomes)==50
    winners=[i for i,o in zip(ids,outcomes) if o.status=='200']
    assert len(winners)==1
    assert sum(o.status=='409' and o.state=='team_full' for o in outcomes)==49
    rows={r['id']:r for r in state['invitations']}
    assert set(rows)==set(ids) and len(state['invitations'])==50
    recipients={r['recipient_id'] for r in rows.values()}
    assert len(recipients)==50 and str(leader) not in recipients
    for i,r in rows.items():
        won=i==winners[0]
        assert r['team_id']==str(team) and r['issued_by']==str(leader)
        assert r['status']==('redeemed' if won else 'pending')
        assert (r['redeemed_at'] is not None)==won
    winner=rows[winners[0]]['recipient_id']
    memberships=state['memberships']
    assert len(memberships)==2 and {m['user_id'] for m in memberships}=={str(leader),winner}
    assert len({(m['hackathon_id'],m['user_id']) for m in memberships})==len(memberships)
    assert all(m['team_id']==str(team) for m in memberships)
    assert len(state['teams'])==1
    target=state['teams'][0]
    assert target['id']==str(team) and target['max_team_size']==2
    assert target['leader_user_id']==str(leader) and target['version']==52
    hackathon=target['hackathon_id']
    assert all(r['hackathon_id']==hackathon for r in rows.values())
    assert all(m['hackathon_id']==hackathon for m in memberships)
    records,audits,outbox=(state[k] for k in ('idempotency_records','audit_events','outbox_events'))
    assert len(records)==len(audits)==len(outbox)==52
    for operation,count in [('team.create.v1',1),('invitation.issue.v1',50),('invitation.redeem.v1',1)]:
        assert sum(r['operation']==operation for r in records)==count
    assert all(r['state']=='completed' for r in records)
    assert len({r['id'] for r in records})==len({a['id'] for a in audits})==len({o['id'] for o in outbox})==52
    decision=next(r for r in records if r['operation']=='invitation.redeem.v1')
    assert decision['actor_id']==winner and decision['http_status']==200
    assert decision['response_body']['data']['id']==winners[0]
    assert decision['response_body']['data']['status']=='redeemed'
    assert sorted(a['team_version'] for a in audits)==list(range(1,53))
    assert {a['idempotency_record_id'] for a in audits}=={r['id'] for r in records}
    assert {o['audit_event_id'] for o in outbox}=={a['id'] for a in audits}
    for a in audits:
        record=next(r for r in records if r['id']==a['idempotency_record_id'])
        assert a['action']==record['operation'] and a['actor_id']==record['actor_id']
        assert a['hackathon_id']==record['hackathon_id']==hackathon and a['team_id']==str(team)
        assert record['response_headers']=={'content-type':'application/json','cache-control':'no-store'}
        body=record['response_body']; assert body['schema_version']==1
        admitted=a['action']=='invitation.redeem.v1'
        assert a['new_state']['team']['member_count']==(2 if admitted else 1)
        if a['action']=='invitation.issue.v1':
            grant=rows[a['new_state']['invitation']['id']]
            assert a['actor_id']==str(leader) and record['http_status']==201
            assert a['old_state']['invitation'] is None
            assert a['new_state']['invitation']=={'id':grant['id'],'status':'pending'}
            assert a['new_state']['subject']=={'user_id':grant['recipient_id'],'member':False}
            assert all(body['data'][k]==grant[k] for k in ('id','hackathon_id','team_id','recipient_id','issued_by'))
            assert body['data']['status']=='pending' and body['data']['redeemed_at'] is None
        elif not admitted:
            assert a['action']=='team.create.v1' and a['actor_id']==str(leader) and a['team_version']==1
            assert record['http_status']==201
            assert body['data']['team_id']==str(team) and body['data']['hackathon_id']==hackathon
            assert body['data']['user_id']==str(leader) and body['data']['member_count']==body['data']['team_version']==1
        if admitted:
            assert a['actor_id']==winner and a['team_version']==52
            assert a['old_state']['invitation']=={'id':winners[0],'status':'pending'}
            assert a['new_state']['invitation']=={'id':winners[0],'status':'redeemed'}
            assert a['new_state']['subject']=={'user_id':winner,'member':True}
            assert all(body['data'][k]==rows[winners[0]][k] for k in ('id','hackathon_id','team_id','recipient_id','issued_by','status'))
        event=next(o for o in outbox if o['audit_event_id']==a['id'])
        assert event['payload']['team_version']==a['team_version']
        assert event['payload']['hackathon_id']==hackathon and event['payload']['team_id']==str(team)
