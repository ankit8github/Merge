"""Offline guard, overlap/failure-oracle, preservation and durable-attempt checks."""
from contextlib import contextmanager
from copy import deepcopy
from threading import Event, Lock
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from test_support.invitation_race import ArrivalGate, observe_overlap, assert_race_state
from test_support.races import Outcome
from test_support.revisions import validate_migration_start, invitation_snapshot


def test_gate_requires_all_distinct_authenticated_arrivals():
    actors=[uuid4() for _ in range(50)]; gate=ArrivalGate(actors); gate.release.set()
    for actor in actors[:-1]: gate.enter(actor)
    assert not gate.arrived.is_set()
    with pytest.raises(AssertionError): gate.verify()
    gate.enter(actors[-1]); assert gate.arrived.is_set(); gate.verify()
    with pytest.raises(AssertionError): gate.enter(actors[0])
    with pytest.raises(AssertionError): gate.verify()


def test_wrong_actor_and_arrival_timeout_fail_closed():
    actor=uuid4(); gate=ArrivalGate([actor],timeout=0)
    with pytest.raises(AssertionError): gate.enter(uuid4())
    with pytest.raises(AssertionError): gate.enter(actor)
    with pytest.raises(ValueError): ArrivalGate([actor,actor])


@pytest.mark.parametrize('kind',['success','one-waiter','unrelated-blockers','query-fault','lock-fault'])
def test_overlap_requires_observed_waiters_and_always_releases_workers(monkeypatch,kind):
    import test_support.invitation_race as module
    actors=[uuid4(),uuid4()]; gate=ArrivalGate(actors); gate.arrived.set()
    calls=[]; commits=[]; exits=[]
    class C:
        def execute(self,statement,parameters):
            q=str(statement); calls.append(q)
            if 'pg_backend_pid' in q: value=90
            elif 'FOR NO KEY UPDATE' in q:
                if kind=='lock-fault': raise RuntimeError('private exception')
                value=None
            else:
                assert gate.release.is_set()
                if kind=='query-fault': raise RuntimeError('private exception')
                value=2 if kind in ('success','unrelated-blockers') else 1
            edges=([{'pid':91,'blockers':[90]},{'pid':92,'blockers':[91]}] if kind=='success' else
                [{'pid':91,'blockers':[92]},{'pid':92,'blockers':[91]}] if kind=='unrelated-blockers' else
                [{'pid':91,'blockers':[90]}])
            return SimpleNamespace(scalar_one=lambda:value,mappings=lambda:SimpleNamespace(all=lambda:edges))
        def commit(self): commits.append(True)
    @contextmanager
    def connection():
        try: yield C()
        finally: exits.append(True)
    ticks=iter([0,.1,4]); monkeypatch.setattr(module,'monotonic',lambda:next(ticks))
    args=(gate,SimpleNamespace(connection=connection),uuid4(),dict(zip([91,92],actors)),Lock(),Event())
    if kind=='success': assert observe_overlap(*args)==2 and commits==[True]
    else:
        with pytest.raises((AssertionError,RuntimeError)): observe_overlap(*args)
        assert not commits
    assert exits and gate.release.is_set()


@pytest.fixture
def race_state():
    h,t,leader=[str(uuid4()) for _ in range(3)]
    ids=[str(uuid4()) for _ in range(50)]; actors=[str(uuid4()) for _ in range(50)]
    invitations=[dict(id=i,hackathon_id=h,team_id=t,recipient_id=u,issued_by=leader,
        status='redeemed' if n==0 else 'pending',redeemed_at='at' if n==0 else None) for n,(i,u) in enumerate(zip(ids,actors))]
    records=[dict(id=str(uuid4()),operation=op,state='completed',hackathon_id=h,
        actor_id=actors[0] if n==51 else leader,http_status=200 if n==51 else 201,
        response_headers={'content-type':'application/json','cache-control':'no-store'})
        for n,op in enumerate(['team.create.v1']+['invitation.issue.v1']*50+['invitation.redeem.v1'])]
    audits=[]
    for n,r in enumerate(records):
        won=n==51
        grant=invitations[0 if won or n==0 else n-1]
        data=(dict(team_id=t,hackathon_id=h,user_id=leader,member_count=1,team_version=1) if n==0 else
            dict(grant) if won else dict(grant,status='pending',redeemed_at=None))
        r['response_body']={'schema_version':1,'data':data}
        audits.append(dict(id=str(uuid4()),idempotency_record_id=r['id'],actor_id=actors[0] if won else leader,
            hackathon_id=h,team_id=t,action=r['operation'],team_version=n+1,
            old_state={'invitation':{'id':ids[0],'status':'pending'} if won else None},
            new_state={'team':{'member_count':2 if won else 1},'invitation':{'id':grant['id'],'status':'redeemed' if won else 'pending'},
                'subject':{'user_id':grant['recipient_id'],'member':won}}))
    state=dict(invitations=invitations,memberships=[dict(hackathon_id=h,team_id=t,user_id=u) for u in (leader,actors[0])],
        teams=[dict(id=t,hackathon_id=h,max_team_size=2,leader_user_id=leader,version=52)],idempotency_records=records,
        audit_events=audits,outbox_events=[dict(id=str(uuid4()),audit_event_id=a['id'],
            payload={'team_version':a['team_version'],'hackathon_id':h,'team_id':t}) for a in audits])
    return state,ids,[Outcome('200')]+[Outcome('409','team_full')]*49,leader,t


def test_race_oracle_accepts_complete_unique_winner(race_state): assert_race_state(*race_state)


@pytest.mark.parametrize('kind',['two-winners','forbidden-losers','consumed-loser','wrong-recipient',
    'duplicate-member','extra-record','version','missing-outbox','wrong-event-version','wrong-audit-actor',
    'wrong-issue-actor','wrong-reply-recipient','wrong-outbox-team','wrong-member-hackathon'])
def test_race_oracle_rejects_false_g1_evidence(race_state,kind):
    state,ids,outcomes,leader,t=deepcopy(race_state)
    if kind=='two-winners': outcomes[1]=Outcome('200')
    if kind=='forbidden-losers': outcomes[1]=Outcome('403','forbidden')
    if kind=='consumed-loser': state['invitations'][1]['redeemed_at']='at'
    if kind=='wrong-recipient': state['invitations'][1]['recipient_id']=state['invitations'][0]['recipient_id']
    if kind=='duplicate-member': state['memberships'].append(dict(state['memberships'][-1]))
    if kind=='extra-record': state['idempotency_records'].append(dict(state['idempotency_records'][-1]))
    if kind=='version': state['teams'][0]['version']=53
    if kind=='missing-outbox': state['outbox_events'].pop()
    if kind=='wrong-event-version': state['outbox_events'][-1]['payload']['team_version']=51
    if kind=='wrong-audit-actor': state['audit_events'][-1]['actor_id']=leader
    if kind=='wrong-issue-actor': state['audit_events'][1]['actor_id']=state['invitations'][0]['recipient_id']
    if kind=='wrong-reply-recipient': state['idempotency_records'][1]['response_body']['data']['recipient_id']=leader
    if kind=='wrong-outbox-team': state['outbox_events'][1]['payload']['team_id']=str(uuid4())
    if kind=='wrong-member-hackathon': state['memberships'][-1]['hackathon_id']=str(uuid4())
    with pytest.raises(AssertionError): assert_race_state(state,ids,outcomes,leader,t)


@pytest.mark.parametrize(('edges','actors','expected'),[
    ([(91,[90]),(92,[91])],[1,2],2),
    ([(91,[92]),(92,[91])],[1,2],0),
    ([(91,[90]),(92,[91])],[1,1],1),
    ([(91,[999]),(999,[90])],[1,2],0),
])
def test_blocker_graph_requires_observer_root_registered_pids_and_distinct_actors(edges,actors,expected):
    from test_support.invitation_race import rooted_waiters
    assert rooted_waiters([dict(pid=p,blockers=b) for p,b in edges],90,dict(zip([91,92],actors)))==expected


def test_scoped_backend_registration_and_invalidated_handle_cleanup():
    from test_support.invitation_race import tracked_caller,record_target_wait
    actor,h,t=uuid4(),uuid4(),uuid4(); gate=ArrivalGate([actor]); pids={}; lock=Lock(); changed=Event()
    saved={}; handle=SimpleNamespace(dbapi_connection=SimpleNamespace(info=SimpleNamespace(backend_pid=91)))
    class C:
        invalid=False
        connection=handle
        @property
        def info(self):
            if self.invalid: raise AssertionError('Invalidated handle was accessed')
            return saved
    c=C(); statement='SELECT id FROM public.teams WHERE id=:team AND hackathon_id=:h FOR NO KEY UPDATE'
    with pytest.raises(RuntimeError,match='original failure'):
        with tracked_caller(c,actor,pids,lock):
            record_target_wait(c,statement,{'h':h,'team':uuid4()},gate,h,t,pids,lock,changed)
            assert not pids and not changed.is_set()
            record_target_wait(c,statement,{'h':h,'team':t},gate,h,t,pids,lock,changed)
            assert pids=={91:actor} and changed.is_set()
            c.invalid=True
            raise RuntimeError('original failure')
    assert not saved and not pids


@pytest.mark.parametrize('start',[[],['0003_auth'],['unknown'],['0004_admission','0005_invitations']])
def test_migration_rejects_wrong_start(start):
    with pytest.raises(ValueError): validate_migration_start(start,'0005_invitations')


def test_migration_preserves_all_eleven_prior_tables():
    statements=[]
    def execute(statement):
        q=str(statement); statements.append(q)
        assert q.startswith(('LOCK TABLE','SELECT count(*)'))
        return SimpleNamespace(one=lambda:(7,'offline-fingerprint'))
    saved=invitation_snapshot(SimpleNamespace(execute=execute))
    assert len(saved)==11 and 'join_requests' in saved
    for revision in ('0004_admission','0005_invitations'):
        validate_migration_start([revision],'0005_invitations')


@pytest.mark.parametrize('revision',[['0005_invitations'],['0004_admission'],[],['0005_invitations','other']])
def test_new_connection_guard_exact_revision_and_invalidation(revision):
    from invitation_tests.conftest import guard
    c=MagicMock(); c.connection.dbapi_connection.autocommit=False
    c.get_execution_options.return_value={}; c.get_isolation_level.return_value='READ COMMITTED'
    def execute(statement,parameters=None):
        q=str(statement)
        if 'current_database()' in q: return SimpleNamespace(one=lambda:('merge_test','merge_app','127.0.0.1',5432))
        if 'version_num' in q: return SimpleNamespace(scalars=lambda:SimpleNamespace(all=lambda:revision))
        return SimpleNamespace(one=lambda:('5s','15s'))
    c.execute.side_effect=execute
    if revision==['0005_invitations']: guard(c); c.rollback.assert_called_once(); c.invalidate.assert_not_called()
    else:
        with pytest.raises(RuntimeError): guard(c)
        c.invalidate.assert_called_once()


@pytest.mark.parametrize(('suite','revision'),[('invitations','0004_admission'),('admission','0005_invitations'),
    ('auth-api','0005_invitations'),('schema','0005_invitations'),('services','0005_invitations')])
def test_suite_revision_mismatch_fails_before_credentials(monkeypatch,suite,revision):
    from test_support import concurrency
    monkeypatch.setattr('sys.argv',['runner','--confirm-merge-test','--suite',suite,'--revision',revision])
    monkeypatch.setattr(concurrency,'getpass',lambda *args:pytest.fail('Credential prompt reached'))
    with pytest.raises(SystemExit) as error: concurrency.main()
    assert error.value.code==2


@pytest.mark.parametrize('operation',['issue','redeem'])
@pytest.mark.parametrize('allowed',[True,False])
def test_durable_invitation_attempts_use_separate_account_scopes(operation,allowed):
    from pydantic import SecretBytes
    from sqlalchemy.engine import Engine
    from app.services.throttling import ThrottleService,ThrottlePolicy,ThrottleExceeded
    from test_throttling import Connection,row
    c=Connection(); c.rows.append(row(attempts=60 if allowed else 61))
    engine=MagicMock(spec=Engine); engine.hide_parameters=True; engine.echo=False
    engine.connect.return_value.__enter__.return_value=c
    service=ThrottleService(engine,secret=SecretBytes(b'x'*32),policy=ThrottlePolicy())
    actor=uuid4()
    if allowed: service.check_invitation(actor_id=actor,operation=operation)
    else:
        with pytest.raises(ThrottleExceeded): service.check_invitation(actor_id=actor,operation=operation)
    assert c.committed and c.charges[0]['scope']=='auth:v1:invitation_'+operation
    assert c.charges[0]['maximum']==60 and str(actor) not in str(c.charges)


@pytest.mark.parametrize('corrupt',[True,False])
def test_guarded_0005_migration_owns_preservation_check_and_rollback(monkeypatch,corrupt):
    from test_support import database
    from test_auth_schema_support import MigrationConnection
    c=MigrationConnection('0004_admission'); snapshots=[]
    def snapshot(connection):
        assert connection is c and c.active
        snapshots.append(True)
        return {'join_requests':(2,'changed' if corrupt and len(snapshots)==2 else 'unchanged')}
    def upgrade(config,revision):
        assert c.active and revision=='0005_invitations'
        assert config.attributes['merge_test_connection'] is c
    monkeypatch.setattr(database,'invitation_snapshot',snapshot)
    monkeypatch.setattr(database.command,'upgrade',upgrade)
    if corrupt:
        with pytest.raises(ValueError,match='rolling back'): database.migrate(c,'0005_invitations')
        assert c.rolled_back and not c.committed
    else: database.migrate(c,'0005_invitations'); assert c.committed
    assert len(snapshots)==2


def test_invitation_runner_selects_only_fixed_suite_with_private_settings(monkeypatch):
    from test_support import concurrency
    from argparse import Namespace,ArgumentParser
    from contextlib import contextmanager
    monkeypatch.setenv('MERGE_TEST_DB_PASSWORD','synthetic-unit-credential')
    @contextmanager
    def connection(settings):
        assert settings.confirmed and settings.database=='merge_test' and settings.user=='merge_app'
        yield SimpleNamespace(execute=lambda statement:SimpleNamespace(scalars=lambda:SimpleNamespace(all=lambda:['0005_invitations'])))
    monkeypatch.setattr(concurrency,'test_connection',connection)
    seen=[]
    def run(arguments,plugins):
        directories=[str(a) for a in arguments if str(a).endswith('_tests')]
        assert len(directories)==1 and directories[0].endswith('invitation_tests')
        assert '--race-repetitions=3' in arguments and '--assert=plain' in arguments
        assert plugins[0].settings.password=='synthetic-unit-credential'
        assert 'synthetic-unit-credential' not in repr(plugins[0])
        seen.append(True); return 0
    diagnostics=SimpleNamespace(data={},save=lambda:None,run_pytest=run)
    args=Namespace(suite='invitations',revision='0005_invitations',repetitions=3,confirm_merge_test=True)
    assert concurrency.run(args,diagnostics,ArgumentParser())==0 and seen
