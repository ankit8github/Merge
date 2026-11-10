"""Atomic real-PostgreSQL service tests; no cleanup or permissive race outcomes."""
from queue import Queue
from threading import Barrier, Event
from time import monotonic, sleep
from uuid import UUID

import pytest
from sqlalchemy import event

from app.services.errors import DomainError, ErrorCode
from app.services.teams import TeamService
from test_support.races import Outcome, sql, wait, workers


def create(env,h,actor,key='create',name='Composed fixture'):
    return env.service.create_team_idempotent(hackathon_id=h,actor_id=actor,name=name,key=key)


def join(env,h,team,actor,key='join'):
    return env.service.join_team_idempotent(hackathon_id=h,team_id=team,actor_id=actor,key=key)


def snapshot(env,h):
    with env.connection() as c:
        sql(c,'SET TRANSACTION READ ONLY')
        data={}
        for table in ('teams','memberships','idempotency_records','audit_events'):
            order='user_id' if table=='memberships' else 'id'
            data[table]=sql(c,f'SELECT to_jsonb(t) FROM public.{table} t WHERE hackathon_id=:h ORDER BY {order}',h=h).scalars().all()
        data['outbox_events']=sql(c,'''SELECT to_jsonb(o) FROM public.outbox_events o
            JOIN public.audit_events a ON a.id=o.audit_event_id WHERE a.hackathon_id=:h ORDER BY o.id''',h=h).scalars().all()
        return data


def test_atomic_create_and_join_versions_and_exact_record_chains(environment,subject):
    h,users=subject
    first=create(environment,h,users[0])
    team=UUID(first.body()['data']['team_id'])
    second=join(environment,h,team,users[1])
    state=snapshot(environment,h)
    assert first.http_status==201 and first.body()['data']['team_version']==1
    assert second.http_status==200 and second.body()['data']['team_version']==2
    assert second.body()['data']['member_count']==2
    assert len(state['teams'])==1 and len(state['memberships'])==2
    assert len(state['idempotency_records'])==len(state['audit_events'])==len(state['outbox_events'])==2
    assert state['teams'][0]['version']==2 and state['teams'][0]['leader_user_id']==str(users[0])


@pytest.mark.parametrize('kind',['create','join'])
def test_replay_after_team_changes_returns_original_state(environment,subject,kind,monkeypatch):
    from app.services import team_mutations
    h,users=subject
    original=create(environment,h,users[0])
    team=UUID(original.body()['data']['team_id'])
    if kind=='join':
        original=join(environment,h,team,users[1])
    join(environment,h,team,users[2],key='later')
    saved=snapshot(environment,h)
    def forbidden(*a,**k):
        pytest.fail('Replay allocated an outcome ID or invoked domain mutation')
    monkeypatch.setattr(team_mutations,'uuid4',forbidden)
    monkeypatch.setattr(environment.service,'_create_team_in_tx',forbidden)
    monkeypatch.setattr(environment.service,'_join_team_in_tx',forbidden)
    replay=create(environment,h,users[0]) if kind=='create' else join(environment,h,team,users[1])
    assert replay==original and snapshot(environment,h)==saved


@pytest.mark.parametrize('changed',['name','hackathon','team'])
def test_mismatch_has_no_effect(environment,subject,changed):
    h,users=subject
    first=create(environment,h,users[0])
    team=UUID(first.body()['data']['team_id'])
    if changed=='team':
        join(environment,h,team,users[1])
        # A different validated UUID is sufficient; mismatch precedes target lookup.
        from uuid import uuid4
        action=lambda:join(environment,h,uuid4(),users[1])
    elif changed=='hackathon':
        other_h,_,_=environment.seed(teams=0)
        action=lambda:create(environment,other_h,users[0])
    else:
        action=lambda:create(environment,h,users[0],name='Different')
    saved=snapshot(environment,h)
    with pytest.raises(DomainError) as caught:
        action()
    assert caught.value.code==ErrorCode.IDEMPOTENCY_MISMATCH and not caught.value.retryable
    assert snapshot(environment,h)==saved


class InjectedFailure(Exception):
    pass


FAULTS=[('create',stage) for stage in ('reservation','membership','audit','outbox','completion')]
FAULTS += [('join',stage) for stage in ('reservation','membership','version','audit','outbox','completion')]


@pytest.mark.parametrize('kind,stage',FAULTS)
def test_injected_stage_failure_rolls_back_every_table(environment,subject,kind,stage):
    h,users=subject
    team=None
    if kind=='join':
        team=UUID(create(environment,h,users[0]).body()['data']['team_id'])
    saved=snapshot(environment,h)
    token={'reservation':'INSERT INTO public.idempotency_records', 'membership':'INSERT INTO public.memberships',
           'version':'UPDATE public.teams SET version','audit':'INSERT INTO public.audit_events',
           'outbox':'INSERT INTO public.outbox_events','completion':'UPDATE public.idempotency_records'}[stage]
    hits=[]
    def fail(c,cursor,statement,parameters,context,many):
        if token in statement:
            hits.append(stage)
            raise InjectedFailure(stage)
    event.listen(environment.engine,'after_cursor_execute',fail)
    try:
        with pytest.raises(InjectedFailure) as caught:
            create(environment,h,users[0]) if kind=='create' else join(environment,h,team,users[1])
        assert str(caught.value)==stage and hits==[stage]
    finally:
        event.remove(environment.engine,'after_cursor_execute',fail)
    assert snapshot(environment,h)==saved
    # Same key can reserve again; no failed outcome or membership charge survived.
    result=create(environment,h,users[0]) if kind=='create' else join(environment,h,team,users[1])
    assert result.http_status==(201 if kind=='create' else 200)


@pytest.mark.parametrize('kind',['create','join'])
def test_real_deferred_commit_failure_unwinds_entire_chain(environment,subject,kind):
    h,users=subject
    team=None
    if kind=='join':
        team=UUID(create(environment,h,users[0]).body()['data']['team_id'])
    saved=snapshot(environment,h)
    failures=[]
    def corrupt(c,cursor,statement,parameters,context,many):
        if 'UPDATE public.idempotency_records' in statement:
            reservation_id=context.compiled_parameters[0]['id']
            sql(c,'''UPDATE public.teams SET leader_user_id=:bad
                WHERE id=(SELECT team_id FROM public.audit_events WHERE idempotency_record_id=:r)''',bad=users[-1],r=reservation_id)
    def observe(context):
        original=context.original_exception
        failures.append((getattr(original,'sqlstate',None),getattr(getattr(original,'diag',None),'constraint_name',None)))
    event.listen(environment.engine,'after_cursor_execute',corrupt)
    event.listen(environment.engine,'handle_error',observe)
    returned=[]
    try:
        with pytest.raises(DomainError) as caught:
            returned.append(create(environment,h,users[0]) if kind=='create' else join(environment,h,team,users[1]))
        assert caught.value.code==ErrorCode.INTEGRITY_FAULT and returned==[]
        assert failures==[('23503','fk_teams_leader_member')]
    finally:
        event.remove(environment.engine,'after_cursor_execute',corrupt)
        event.remove(environment.engine,'handle_error',observe)
    assert snapshot(environment,h)==saved


@pytest.mark.parametrize('kind',['create','join'])
def test_concurrent_duplicate_waits_replays_and_outbox_is_uncommitted(environment,subject,kind):
    h,users=subject
    team=None
    actor=users[0]
    if kind=='join':
        team=UUID(create(environment,h,users[0]).body()['data']['team_id'])
        actor=users[1]
    saved=snapshot(environment,h)
    held,release,returned=Event(),Event(),Event()
    pids=Queue()
    replies=Queue()
    def hold(c,cursor,statement,parameters,context,many):
        if 'UPDATE public.idempotency_records' in statement and not held.is_set():
            pids.put(('holder',sql(c,'SELECT pg_backend_pid()').scalar_one()))
            held.set()
            wait(release)
    def identify(c,cursor,statement,parameters,context,many):
        if 'INSERT INTO public.idempotency_records' in statement and held.is_set():
            pids.put(('contender',sql(c,'SELECT pg_backend_pid()').scalar_one()))
    def call(contender=False):
        if contender:
            wait(held)
        result=create(environment,h,actor) if kind=='create' else join(environment,h,team,actor)
        replies.put(result)
        returned.set()
        return Outcome('returned')
    def observer():
        try:
            wait(held)
            received=dict(pids.get(timeout=8) for _ in range(2))
            assert set(received)=={'holder','contender'} and received['holder']!=received['contender']
            assert not returned.is_set() and snapshot(environment,h)==saved
            with environment.connection() as c:
                sql(c,'SET TRANSACTION READ ONLY')
                deadline=monotonic()+3
                while monotonic()<deadline:
                    if received['holder'] in sql(c,'SELECT pg_blocking_pids(:pid)',pid=received['contender']).scalar_one():
                        return Outcome('blocking-observed')
                    sleep(0.02)
                raise AssertionError('Required database blocking not observed')
        finally:
            release.set()
    event.listen(environment.engine,'after_cursor_execute',hold)
    event.listen(environment.engine,'before_cursor_execute',identify)
    try:
        assert workers([call,lambda:call(True),observer])==[Outcome('returned'),Outcome('returned'),Outcome('blocking-observed')]
    finally:
        release.set()
        event.remove(environment.engine,'after_cursor_execute',hold)
        event.remove(environment.engine,'before_cursor_execute',identify)
    assert replies.qsize()==2 and replies.get(timeout=1)==replies.get(timeout=1)
    state=snapshot(environment,h)
    for name in ('idempotency_records','audit_events','outbox_events','memberships'):
        assert len(state[name])==len(saved[name])+1
    assert state['teams'][0]['version']==(1 if kind=='create' else 2)


@pytest.mark.parametrize('race',['capacity','same-user'])
def test_different_keys_preserve_capacity_and_one_team_per_user(environment,race):
    h,users,_=environment.seed(maximum=2,teams=0)
    team=UUID(create(environment,h,users[0]).body()['data']['team_id'])
    other=UUID(create(environment,h,users[1],key='other').body()['data']['team_id']) if race=='same-user' else team
    barrier=Barrier(2,timeout=8)
    def call(target,actor,key):
        barrier.wait()
        try:
            join(environment,h,target,actor,key)
            return Outcome('joined')
        except DomainError as error:
            assert error.code==(ErrorCode.TEAM_FULL if race=='capacity' else ErrorCode.ALREADY_ASSIGNED)
            return Outcome(error.code.value)
    actions=[lambda:call(team,users[2],'one'),lambda:call(other,users[3] if race=='capacity' else users[2],'two')]
    results=workers(actions)
    assert sorted(r.status for r in results)==sorted(['joined','team_full' if race=='capacity' else 'already_assigned'])


@pytest.mark.parametrize('kind',['create','join'])
def test_one_owner_connection_commit_and_lock_order(environment,subject,kind):
    h,users=subject
    team=None
    if kind=='join':
        team=UUID(create(environment,h,users[0]).body()['data']['team_id'])
    begins,commits,queries=[],[],[]
    def begin(c): begins.append(c)
    def commit(c): commits.append(c)
    def observe(c,cursor,statement,parameters,context,many): queries.append((c,statement))
    for name,hook in [('begin',begin),('commit',commit),('before_cursor_execute',observe)]:
        event.listen(environment.engine,name,hook)
    try:
        result=create(environment,h,users[0]) if kind=='create' else join(environment,h,team,users[1])
        assert result.http_status==(201 if kind=='create' else 200)
        assert len(commits)==1 and begins==commits*2  # Initial read guard rolls back, then one owner.
        assert all(c is commits[0] for c,q in queries)
        statements=[q for c,q in queries]
        tokens=['INSERT INTO public.idempotency_records','FOR SHARE','FROM public.users',
                'INSERT INTO public.teams' if kind=='create' else 'FOR NO KEY UPDATE',
                'INSERT INTO public.memberships','INSERT INTO public.audit_events','INSERT INTO public.outbox_events',
                'UPDATE public.idempotency_records']
        # The user SELECT itself contains FOR NO KEY UPDATE; team lock must be
        # distinguished by its teams source rather than matching that first lock.
        if kind=='join': tokens[3]='SELECT id,deleted_at,max_team_size'
        indices=[next(i for i,q in enumerate(statements) if token in q) for token in tokens]
        assert indices==sorted(indices)
    finally:
        for name,hook in [('begin',begin),('commit',commit),('before_cursor_execute',observe)]:
            event.remove(environment.engine,name,hook)


@pytest.mark.parametrize('kind',['create','join'])
def test_real_dbapi_autocommit_rejected_before_any_composition_write(environment,subject,kind):
    h,users=subject
    engine=environment.engine.execution_options(isolation_level='AUTOCOMMIT')
    writes=[]
    def observe(c,cursor,statement,parameters,context,many):
        if statement.lstrip().startswith(('INSERT','UPDATE','DELETE')): writes.append(statement)
    event.listen(engine,'before_cursor_execute',observe)
    try:
        with engine.connect() as c:
            assert c.connection.dbapi_connection.autocommit is True
        service=TeamService(engine)
        with pytest.raises(DomainError) as caught:
            if kind=='create': service.create_team_idempotent(hackathon_id=h,actor_id=users[0],name='Example',key='key')
            else: service.join_team_idempotent(hackathon_id=h,team_id=users[-1],actor_id=users[0],key='key')
        assert caught.value.code==ErrorCode.TRANSACTION_CONFIGURATION and writes==[]
    finally:
        event.remove(engine,'before_cursor_execute',observe)
    assert all(not rows for rows in snapshot(environment,h).values())
