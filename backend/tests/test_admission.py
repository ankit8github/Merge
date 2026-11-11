"""Offline transaction/control-flow regressions, never PostgreSQL race evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.dialects import postgresql

from app.services.admission import AdmissionService, AdmissionError, _command
from app.services.errors import DomainError, ErrorCode
from test_team_mutations import Connection as BaseConnection, InjectedFailure
from test_support.revisions import validate_migration_start


def result(value):
    return SimpleNamespace(scalar_one_or_none=lambda:value, scalar_one=lambda:value,
        one_or_none=lambda:value, one=lambda:value,
        mappings=lambda:SimpleNamespace(one=lambda:value, one_or_none=lambda:value))


class Connection(BaseConnection):
    def __init__(self):
        super().__init__()
        self.data['requests'] = {}
        self.sql = []

    def execute(self, statement, p):
        q = str(statement)
        statement.compile(dialect=postgresql.dialect()).construct_params(p)
        self.sql.append((q, dict(p)))
        if 'SELECT t.id, (SELECT row_to_json(r)' in q:
            team=self.data['teams'].get(p['team'])
            row=next((r for r in self.data['requests'].values() if r['hackathon_id']==p['h'] and r['team_id']==p['team'] and r['requester_id']==p['actor']),None)
            return result(None if team is None else dict(id=p['team'],request=row))
        if 'SELECT t.leader_user_id,' in q:
            team=self.data['teams'].get(p['team'])
            rows=sorted((r for r in self.data['requests'].values() if r['hackathon_id']==p['h'] and r['team_id']==p['team']),key=lambda r:r['id'])
            selected=[r for r in rows if r['status']=='pending' and (p['cursor'] is None or r['id']>p['cursor'])][:p['size']]
            return result(None if team is None else dict(leader_user_id=team['leader_user_id'],
                cursor_ok=p['cursor'] is None or any(r['id']==p['cursor'] for r in rows),items=selected))
        if q=='SET TRANSACTION READ ONLY': return result(None)
        if 'SELECT id FROM public.hackathons' in q:
            self.events.append('hackathon-share')
            return result(SimpleNamespace(id=p['h']))
        if 'SELECT id,leader_user_id,deleted_at,max_team_size' in q:
            self.events.append('team-no-key-update')
            team = self.data['teams'].get(p['team'])
            return result(None if team is None else SimpleNamespace(**team))
        if 'FROM public.join_requests' in q:
            rows = [r for r in self.data['requests'].values() if r['hackathon_id']==p['h'] and r['team_id']==p['team']]
            row = next((r for r in rows if r['id']==p['id']), None) if 'id' in p else next((r for r in rows if r['requester_id']==p['actor']),None)
            if 'FOR NO KEY UPDATE' in q: self.events.append('request-no-key-update')
            return result(None if row is None else row['requester_id'] if 'SELECT requester_id' in q else dict(row))
        if 'INSERT INTO public.join_requests' in q:
            row = dict(id=p['id'], hackathon_id=p['h'], team_id=p['team'], requester_id=p['actor'],
                status='pending', created_at=datetime.now(timezone.utc), resolved_at=None)
            self.data['requests'][row['id']] = row
            self.events.append('request-write')
            if self.fail_after == 'request': raise InjectedFailure('request')
            return result(dict(row))
        if 'UPDATE public.join_requests' in q:
            row = self.data['requests'][p['id']]
            row.update(status=p['status'], resolved_at=datetime.now(timezone.utc))
            self.events.append('request-write')
            if self.fail_after == 'request': raise InjectedFailure('request')
            return result(dict(row))
        if 'SELECT EXISTS(SELECT 1 FROM public.memberships' in q:
            return result(any(m['hackathon']==p['h'] and m['team']==p['team'] and m['actor']==p['actor'] for m in self.data['members']))
        return super().execute(statement, p)


@pytest.fixture
def db():
    c = Connection()
    engine = MagicMock(spec=Engine)
    engine.connect.return_value.__enter__.return_value = c
    service = AdmissionService(engine)
    h, leader, user = uuid4(), uuid4(), uuid4()
    reply = service.create_team_idempotent(hackathon_id=h, actor_id=leader, name='Test team', key='founder')
    team = next(iter(c.data['teams']))
    return SimpleNamespace(c=c, service=service, h=h, leader=leader, user=user, team=team, created=reply)


def create(d, **override):
    return d.service.create_request(**(dict(hackathon_id=d.h,team_id=d.team,actor_id=d.user,key='request')|override))


def decide(d, request, **override):
    return d.service.decide_request(**(dict(hackathon_id=d.h,team_id=d.team,actor_id=d.leader,
        request_id=request,decision='approve',key='decision')|override))


def test_request_approval_chain_and_exact_replays(db):
    d=db
    request=create(d)
    assert request.http_status==201 and request.body()['data']['status']=='pending'
    request_id=next(iter(d.c.data['requests']))
    saved=deepcopy(d.c.data)
    assert create(d)==request and d.c.data==saved
    duplicate=create(d,key='another-request')
    assert duplicate.http_status==200 and duplicate.body()==request.body()
    approved=decide(d,request_id)
    assert approved.http_status==200 and approved.body()['data']['status']=='approved'
    assert len(d.c.data['members'])==2
    assert len(d.c.data['audits'])==len(d.c.data['outbox'])==3
    saved=deepcopy(d.c.data)
    assert decide(d,request_id)==approved and d.c.data==saved
    last=d.c.data['audits'][-1]
    assert last['actor']==d.leader and last['action']=='request.decide.v1'
    import json
    old,new=json.loads(last['before']),json.loads(last['after'])
    assert old['subject']==dict(user_id=str(d.user),member=False)
    assert new['subject']==dict(user_id=str(d.user),member=True)
    assert new['team']['member_count']==2 and old['team']['member_count']==1


def test_sorted_users_before_team_and_request_locks(db):
    d=db; r=create(d); start=len(d.c.sql)
    decide(d,next(iter(d.c.data['requests'])))
    queries=d.c.sql[start:]
    users=[(i,p['actor']) for i,(q,p) in enumerate(queries) if 'FROM public.users' in q]
    assert [u for _,u in users]==sorted([d.leader,d.user])
    team=next(i for i,(q,_) in enumerate(queries) if 'FROM public.teams' in q and 'FOR NO KEY UPDATE' in q)
    req=next(i for i,(q,_) in enumerate(queries) if 'FROM public.join_requests' in q and 'FOR NO KEY UPDATE' in q)
    assert max(i for i,_ in users)<team<req
    assert 'INSERT INTO public.idempotency_records' in queries[3][0] or any('INSERT INTO public.idempotency_records' in q for q,_ in queries[:team])


@pytest.mark.parametrize('decision', ['approve','reject'])
def test_terminal_other_key_conflicts_and_rejection_never_admits(db,decision):
    create(db); request=next(iter(db.c.data['requests']))
    first=decide(db,request,decision=decision)
    assert len(db.c.data['members'])==(2 if decision=='approve' else 1)
    saved=deepcopy(db.c.data)
    with pytest.raises(AdmissionError) as error: decide(db,request,key='different',decision=decision)
    assert error.value.code==ErrorCode.REQUEST_RESOLVED and db.c.data==saved
    assert decide(db,request,decision=decision)==first


@pytest.mark.parametrize('kind',['new','replay','stale'])
def test_leader_authorization_precedes_decision_and_replay(db,kind):
    create(db); request=next(iter(db.c.data['requests']))
    if kind=='replay': decide(db,request)
    if kind in ('replay','stale'): db.c.data['teams'][db.team]['leader_user_id']=uuid4()
    actor=db.leader if kind in ('replay','stale') else uuid4()
    saved=deepcopy(db.c.data)
    with pytest.raises(AdmissionError) as error: decide(db,request,actor_id=actor)
    assert error.value.code==ErrorCode.FORBIDDEN and db.c.data==saved


@pytest.mark.parametrize('kind',['full','assigned','wrong-team','missing-request'])
def test_failed_approval_retains_pending_and_rolls_back_reserved_chain(db,kind):
    create(db); request=next(iter(db.c.data['requests']))
    if kind=='full': db.c.data['teams'][db.team]['max_team_size']=1
    if kind=='assigned': db.c.data['members'].append(dict(hackathon=db.h,team=uuid4(),actor=db.user))
    args={}
    if kind=='wrong-team': args['team_id']=uuid4()
    if kind=='missing-request': request=uuid4()
    saved=deepcopy(db.c.data)
    with pytest.raises(DomainError) as error: decide(db,request,**args)
    expected={'full':ErrorCode.TEAM_FULL,'assigned':ErrorCode.ALREADY_ASSIGNED,
        'wrong-team':ErrorCode.TEAM_NOT_FOUND,'missing-request':ErrorCode.REQUEST_NOT_FOUND}[kind]
    assert error.value.code==expected and db.c.data==saved


@pytest.mark.parametrize(('kind','fault'), [(kind,fault)
    for kind in ('create','approve','reject')
    for fault in ('request','membership','version','audit','outbox','completion','commit')
    if kind=='approve' or fault!='membership'])
def test_failure_unwinds_request_membership_and_entire_record_chain(db,kind,fault):
    if kind!='create': create(db)
    saved=deepcopy(db.c.data)
    db.c.fail_after=None if fault=='commit' else fault
    db.c.fail_commit=fault=='commit'
    with pytest.raises((InjectedFailure,DomainError)):
        create(db) if kind=='create' else decide(db,next(iter(db.c.data['requests'])),decision=kind)
    assert db.c.data==saved and db.c.events[-1]=='rollback'


def test_changed_decision_key_mismatch_before_writes(db):
    create(db); request=next(iter(db.c.data['requests']))
    decide(db,request,decision='reject')
    saved=deepcopy(db.c.data)
    with pytest.raises(DomainError) as error: decide(db,request,decision='approve')
    assert error.value.code==ErrorCode.IDEMPOTENCY_MISMATCH and db.c.data==saved


def test_admission_migration_frozen_additive_and_renderable():
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0004_admission.py'
    spec=importlib.util.spec_from_file_location('admission_revision',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    stream=io.StringIO()
    context=MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':stream})
    with Operations.context(context): module.upgrade()
    ddl=stream.getvalue()
    assert module.down_revision=='0003_auth' and module.revision=='0004_admission'
    for token in ['fk_requests_team_hackathon','uq_requests_team_user','ck_requests_state','guard_request_identity','guard_request_terminal','BEFORE TRUNCATE','ct_request_admitted','DEFERRABLE INITIALLY DEFERRED','SECURITY INVOKER','SET search_path = pg_catalog, pg_temp']:
        assert token in ddl
    assert 'DROP ' not in ddl and 'CREATE OR REPLACE' not in ddl and 'GRANT ' not in ddl
    with pytest.raises(RuntimeError): module.downgrade()


@pytest.mark.parametrize('start',[[],['0002_domain'],['unknown'],['0003_auth','0004_admission']])
def test_new_revision_refuses_wrong_start(start):
    with pytest.raises(ValueError): validate_migration_start(start,'0004_admission')


def test_new_revision_allows_only_predecessor_or_repeat():
    validate_migration_start(['0003_auth'],'0004_admission')
    validate_migration_start(['0004_admission'],'0004_admission')


def test_invalid_decision_and_security_inputs_never_connect(db):
    db.service._engine.connect.reset_mock()
    for changes in [dict(decision='join'),dict(request_id='fake'),dict(actor_id='fake'),dict(key='bad\tkey')]:
        with pytest.raises(DomainError): decide(db,uuid4(),**changes)
    db.service._engine.connect.assert_not_called()


def test_private_reads_use_single_snapshot_and_filter_decider_fields(db):
    d=db
    params=dict(hackathon_id=d.h,team_id=d.team,actor_id=d.user)
    assert d.service.own_request(**params)=={'request':None}
    create(d)
    start=len(d.c.sql)
    own=d.service.own_request(**params)['request']
    assert own['requester_id']==str(d.user) and 'resolved_by' not in own
    reads=[q for q,_ in d.c.sql[start:] if 'FROM public.teams' in q]
    assert len(reads)==1 and 'r.requester_id=:actor' in reads[0]
    assert d.service.own_request(**(params|dict(actor_id=d.leader)))=={'request':None}
    leader=params|dict(actor_id=d.leader)
    assert d.service.pending_requests(**leader)['items']==[own]
    with pytest.raises(AdmissionError) as error: d.service.pending_requests(**params)
    assert error.value.code==ErrorCode.FORBIDDEN


def test_pending_cursor_is_scoped_bounded_and_terminal_rows_not_listed(db):
    d=db
    for _ in range(3): create(d,actor_id=uuid4(),key=uuid4().hex)
    params=dict(hackathon_id=d.h,team_id=d.team,actor_id=d.leader,limit=2)
    first=d.service.pending_requests(**params)
    assert len(first['items'])==2 and first['next_cursor']==first['items'][-1]['id']
    from uuid import UUID
    second=d.service.pending_requests(**params,cursor=UUID(first['next_cursor']))
    assert len(second['items'])==1 and second['next_cursor'] is None
    with pytest.raises(AdmissionError): d.service.pending_requests(**params,cursor=uuid4())
    decide(d,UUID(first['items'][0]['id']),decision='reject')
    assert len(d.service.pending_requests(**params)['items'])==2


@pytest.mark.parametrize('preserved',[True,False])
def test_guarded_admission_migration_preserves_auth_and_domain_atomically(monkeypatch,preserved):
    from test_auth_schema_support import MigrationConnection
    from test_support import database
    c=MigrationConnection(revision='0003_auth')
    snapshots=iter([{'auth_sessions':(1,'before')},{'auth_sessions':(1,'before' if preserved else 'after')}])
    monkeypatch.setattr(database,'admission_snapshot',lambda connection:next(snapshots))
    def upgrade(config,target):
        assert c.active and config.attributes['merge_test_connection'] is c and target=='0004_admission'
    monkeypatch.setattr(database.command,'upgrade',upgrade)
    if preserved:
        database.migrate(c,revision='0004_admission'); assert c.committed
    else:
        with pytest.raises(ValueError): database.migrate(c,revision='0004_admission')
        assert c.rolled_back and not c.committed


@pytest.mark.parametrize('revision',[None,'0002_domain','0003_auth'])
def test_guarded_admission_runner_requires_revision_before_prompt_or_connection(monkeypatch,revision):
    from test_support import concurrency
    args=['runner','--confirm-merge-test','--suite','admission']
    if revision: args+=['--revision',revision]
    monkeypatch.setattr('sys.argv',args)
    monkeypatch.setattr(concurrency,'getpass',lambda *a:pytest.fail('Prompt reached'))
    monkeypatch.setattr(concurrency,'test_connection',lambda *a:pytest.fail('Connection reached'))
    with pytest.raises(SystemExit) as error: concurrency.main()
    assert error.value.code==2


@pytest.mark.parametrize('method',['create','decide','own','pending'])
def test_all_admission_facades_reject_actual_dbapi_autocommit_before_sql(db,method):
    d=db
    d.c.connection.dbapi_connection.autocommit=True
    start=len(d.c.sql)
    params=dict(hackathon_id=d.h,team_id=d.team,actor_id=d.user)
    with pytest.raises(DomainError) as error:
        if method=='create': d.service.create_request(**params,key='guard')
        elif method=='decide': d.service.decide_request(**params,request_id=uuid4(),decision='approve',key='guard')
        elif method=='own': d.service.own_request(**params)
        else: d.service.pending_requests(**params)
    assert error.value.code==ErrorCode.TRANSACTION_CONFIGURATION and len(d.c.sql)==start


def test_fingerprints_bind_team_hackathon_request_decision_and_actor():
    h,t,u,r=uuid4(),uuid4(),uuid4(),uuid4()
    original=_command(h,t,u,'key',r,'approve')
    assert original.fingerprint==_command(h,t,u,'different-key',r,'approve').fingerprint
    for args in [(uuid4(),t,u,r,'approve'),(h,uuid4(),u,r,'approve'),(h,t,uuid4(),r,'approve'),
        (h,t,u,uuid4(),'approve'),(h,t,u,r,'reject')]:
        assert original.fingerprint!=_command(*args[:3],'key',*args[3:]).fingerprint


def test_admission_metadata_matches_frozen_column_and_constraint_contract():
    from app.models.admission import JoinRequest
    from sqlalchemy.schema import CreateTable
    ddl=str(CreateTable(JoinRequest.__table__).compile(dialect=postgresql.dialect()))
    assert set(JoinRequest.__table__.c.keys())=={'id','hackathon_id','team_id','requester_id','status','created_at','resolved_at','resolved_by'}
    assert all(constraint.name for constraint in JoinRequest.__table__.constraints)
    for name in ('fk_requests_team_hackathon','uq_requests_team_user','ck_requests_state','ck_requests_time'):
        assert name in ddl


@pytest.mark.parametrize('kind',['create','approve','reject'])
@pytest.mark.parametrize('failure',['conflict','lost-commit-ack'])
def test_whole_operation_retry_and_ambiguous_commit_preserve_one_chain(db,monkeypatch,kind,failure):
    from contextlib import contextmanager
    from test_transaction_retry import database_error
    d=db
    if kind!='create': create(d)
    original_begin=d.c.begin
    original_execute=d.c.execute
    fired=False
    if failure=='lost-commit-ack':
        @contextmanager
        def begin():
            nonlocal fired
            with original_begin(): yield
            if not fired:
                fired=True
                raise database_error('08006')
        monkeypatch.setattr(d.c,'begin',begin)
    else:
        def execute(statement,parameters):
            nonlocal fired
            value=original_execute(statement,parameters)
            if not fired and 'INSERT INTO public.outbox_events' in str(statement):
                fired=True
                raise database_error('40P01')
            return value
        monkeypatch.setattr(d.c,'execute',execute)
    reply=create(d) if kind=='create' else decide(d,next(iter(d.c.data['requests'])),decision=kind)
    assert fired and reply.http_status==(201 if kind=='create' else 200)
    assert len(d.c.data['requests'])==1
    assert len(d.c.data['members'])==(2 if kind=='approve' else 1)
    assert len(d.c.data['audits'])==len(d.c.data['outbox'])==(2 if kind=='create' else 3)


def test_deferred_capacity_error_keeps_admission_error_contract_and_rolls_back(db,monkeypatch):
    from contextlib import contextmanager
    from sqlalchemy.exc import IntegrityError
    create(db); request=next(iter(db.c.data['requests'])); saved=deepcopy(db.c.data)
    original=db.c.begin
    @contextmanager
    def begin():
        with original():
            yield
            driver=SimpleNamespace(sqlstate='23514',diag=SimpleNamespace(constraint_name='ct_team_capacity'))
            raise IntegrityError('synthetic statement',{},driver)
    monkeypatch.setattr(db.c,'begin',begin)
    with pytest.raises(AdmissionError) as error: decide(db,request)
    assert error.value.code==ErrorCode.TEAM_FULL and db.c.data==saved
