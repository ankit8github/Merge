"""Offline orchestration/rollback checks, not PostgreSQL concurrency evidence."""
from contextlib import contextmanager
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.services import team_mutations as composed
from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import _command
from app.services.teams import TeamService, _CreateTeamCommand, _CreateTeamRequest


class InjectedFailure(Exception):
    pass


def stage(query):
    for name, token in [('reservation', 'INSERT INTO public.idempotency_records'),
                        ('membership', 'INSERT INTO public.memberships'),
                        ('version', 'UPDATE public.teams SET version'),
                        ('audit', 'INSERT INTO public.audit_events'),
                        ('outbox', 'INSERT INTO public.outbox_events'),
                        ('completion', 'UPDATE public.idempotency_records')]:
        if token in query:
            return name


class Connection:
    def __init__(self):
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.transaction = None
        self.data = dict(teams={}, members=[], reservations={}, audits=[], outbox=[])
        self.events = []
        self.fail_after = None
        self.fail_commit = False

    def get_transaction(self):
        return self.transaction

    def in_transaction(self):
        return self.transaction is not None

    def in_nested_transaction(self):
        return False

    def get_isolation_level(self):
        return 'READ COMMITTED'

    @contextmanager
    def begin(self):
        assert self.transaction is None, 'Nested owner'
        saved = deepcopy(self.data)
        self.transaction = SimpleNamespace(is_active=True)
        self.events.append('begin')
        try:
            yield
            if self.fail_commit:
                original = RuntimeError('synthetic-only')
                original.sqlstate = '23503'
                original.diag = SimpleNamespace(constraint_name='fk_teams_leader_member')
                raise IntegrityError('synthetic-only', {}, original)
            self.events.append('commit')
        except Exception:
            self.data = saved
            self.events.append('rollback')
            raise
        finally:
            self.transaction.is_active = False
            self.transaction = None

    def execute(self, statement, p):
        assert self.in_transaction(), 'SQL outside owner'
        # Exercise real text bind construction; do not repeat the R1 blind spot.
        statement.compile(dialect=postgresql.dialect()).construct_params(p)
        q, value = str(statement), None
        d = self.data
        if 'INSERT INTO public.idempotency_records' in q:
            scope = (p['actor'], p['operation'], p['key'])
            if scope not in d['reservations']:
                d['reservations'][scope] = dict(id=p['id'], actor_id=p['actor'],
                    hackathon_id=p['hackathon'], operation=p['operation'], key=p['key'],
                    request_hash=p['fingerprint'], state='pending')
                value = p['id']
        elif 'FROM public.idempotency_records' in q:
            value = d['reservations'].get((p['actor'], p['operation'], p['key']))
        elif 'FROM public.hackathons' in q:
            self.events.append('hackathon-share')
            value = SimpleNamespace(min_team_size=2, max_team_size=3)
        elif 'FROM public.users' in q:
            self.events.append('user-no-key-update')
            value = SimpleNamespace(id=p['actor'])
        elif 'INSERT INTO public.teams' in q:
            d['teams'][p['team']] = dict(version=1, leader_user_id=p['actor'],
                min_team_size=p['minimum'], max_team_size=p['maximum'], deleted_at=None)
        elif 'SELECT id,deleted_at,max_team_size' in q:
            self.events.append('team-no-key-update')
            row = d['teams'].get(p['team'])
            value = None if row is None else SimpleNamespace(**row)
        elif 'SELECT team_id FROM public.memberships' in q:
            value = next((m for m in d['members'] if m['hackathon']==p['hackathon'] and m['actor']==p['actor']), None)
        elif 'SELECT count(*)' in q:
            value = sum(m['team']==p['team'] for m in d['members'])
        elif 'INSERT INTO public.memberships' in q:
            d['members'].append(dict(p))
        elif 'SELECT version,leader_user_id' in q:
            value = d['teams'].get(p['team'])
        elif 'UPDATE public.teams SET version' in q:
            value = d['teams'][p['team']]
            if value['version'] < 2**63-1:
                value['version'] += 1
            else:
                value = None
        elif 'INSERT INTO public.audit_events' in q:
            d['audits'].append(dict(p))
            value = p['id']
        elif 'INSERT INTO public.outbox_events' in q:
            d['outbox'].append(dict(p))
            value = p['id']
        elif 'UPDATE public.idempotency_records' in q:
            row = d['reservations'][(p['actor'], p['operation'], p['key'])]
            row.update(state='completed', http_status=p['status'], response_body=json.loads(p['body']),
                       response_headers=json.loads(p['headers']))
            value = p['id']
        elif not q.startswith('SET LOCAL'):
            raise AssertionError('Unknown offline SQL')
        current = stage(q)
        if current:
            self.events.append(current)
        if current is not None and current == self.fail_after:
            raise InjectedFailure(current)
        return SimpleNamespace(scalar_one_or_none=lambda:value, scalar_one=lambda:value,
            one_or_none=lambda:value, mappings=lambda:SimpleNamespace(one_or_none=lambda:value))


@pytest.fixture
def setup():
    c = Connection()
    engine = MagicMock(spec=Engine)
    engine.connect.return_value.__enter__.return_value = c
    return TeamService(engine), c, uuid4(), uuid4()


def create(service, h, actor, key='create'):
    return service.create_team_idempotent(hackathon_id=h, actor_id=actor, name='Exact name', key=key)


def join(service, h, team, actor, key='join'):
    return service.join_team_idempotent(hackathon_id=h, team_id=team, actor_id=actor, key=key)


def test_create_join_chain_payload_and_version(setup):
    service, c, h, actor = setup
    first = create(service, h, actor)
    assert first.http_status == 201
    team = next(iter(c.data['teams']))
    subject = uuid4()
    second = join(service, h, team, subject)
    assert second.http_status == 200 and second.body()['data']['team_version'] == 2
    assert len(c.data['audits']) == len(c.data['outbox']) == len(c.data['reservations']) == 2
    a, b = c.data['audits']
    assert a['before'] is None and a['version'] == 1 and a['action'] == 'team.create.v1'
    before, after = json.loads(b['before']), json.loads(b['after'])
    assert b['actor'] == subject and b['version'] == 2 and b['action'] == 'team.join.v1'
    assert before['team']['member_count'] == before['team']['version'] == 1
    assert after['team']['member_count'] == after['team']['version'] == 2
    assert before['subject'] == {'user_id':str(subject),'member':False}
    assert after['subject'] == {'user_id':str(subject),'member':True}
    assert before['team']['readiness'] == 'forming' and after['team']['readiness'] == 'ready'
    assert json.loads(c.data['outbox'][1]['payload']) == {
        'team_id':str(team),'hackathon_id':str(h),'team_version':2}
    assert c.data['outbox'][1]['audit'] == b['id']
    assert c.events.count('begin') == c.events.count('commit') == 2
    assert c.events.index('reservation') < c.events.index('hackathon-share') < c.events.index('user-no-key-update')
    assert c.events.index('team-no-key-update') < c.events.index('version') < c.events.index('audit', c.events.index('version'))


@pytest.mark.parametrize('kind',['create','join'])
def test_replay_is_original_reply_without_mutation_or_outcome_id_allocation(setup, monkeypatch, kind):
    service, c, h, actor = setup
    original = create(service,h,actor)
    team = next(iter(c.data['teams']))
    subject = uuid4()
    if kind == 'join':
        original = join(service,h,team,subject)
    saved = deepcopy(c.data)
    def forbidden(*a, **k):
        pytest.fail('Replay invoked a mutation stage')
    for name in ('uuid4','_version_in_tx','_audit_in_tx','_outbox_in_tx'):
        monkeypatch.setattr(composed,name,forbidden)
    monkeypatch.setattr(service,'_create_team_in_tx',forbidden)
    monkeypatch.setattr(service,'_join_team_in_tx',forbidden)
    replayed = create(service,h,actor) if kind=='create' else join(service,h,team,subject)
    assert replayed == original and c.data == saved


@pytest.mark.parametrize('kind',['create','join'])
@pytest.mark.parametrize('fault',['reservation','membership','audit','outbox','completion','commit'])
def test_fault_unwinds_entire_chain_without_retry_or_early_return(setup,kind,fault):
    service, c, h, actor = setup
    if kind=='join':
        create(service,h,actor)
    team = next(iter(c.data['teams']),None)
    saved = deepcopy(c.data)
    before = c.events.count('begin')
    c.fail_after = None if fault=='commit' else fault
    c.fail_commit = fault=='commit'
    returned = []
    with pytest.raises(DomainError if fault=='commit' else InjectedFailure) as caught:
        returned.append(create(service,h,actor) if kind=='create' else join(service,h,team,uuid4()))
    if fault=='commit':
        assert caught.value.code == ErrorCode.INTEGRITY_FAULT
    assert returned == [] and c.data == saved
    assert c.events[-1] == 'rollback' and c.events.count('begin') == before+1


@pytest.mark.parametrize('exhausted',[False,True])
def test_join_version_failure_rolls_back_membership_and_reservation(setup,exhausted):
    service,c,h,actor=setup
    create(service,h,actor)
    team=next(iter(c.data['teams']))
    if exhausted:
        c.data['teams'][team]['version']=2**63-1
    else:
        c.fail_after='version'
    saved=deepcopy(c.data)
    with pytest.raises(DomainError if exhausted else InjectedFailure):
        join(service,h,team,uuid4())
    assert c.data==saved


@pytest.mark.parametrize('kind',['create','join'])
@pytest.mark.parametrize('field,value',[('actor_id','untrusted'),('hackathon_id',None),('key',''),('key','\n')])
def test_invalid_inputs_fail_before_connection(setup,kind,field,value):
    service,c,h,actor=setup
    kwargs=dict(hackathon_id=h,actor_id=actor,key='key')
    kwargs.update(name='Example') if kind=='create' else kwargs.update(team_id=uuid4())
    kwargs[field]=value
    with pytest.raises(DomainError) as caught:
        getattr(service,kind+'_team_idempotent')(**kwargs)
    assert caught.value.code==ErrorCode.INVALID_INPUT
    service._engine.connect.assert_not_called()


def test_request_without_outcome_uuid_has_identical_v1_fingerprint():
    h,actor=uuid4(),uuid4()
    assert _command(_CreateTeamRequest(h,actor,'Exact'),'key') == _command(
        _CreateTeamCommand(h,actor,'Exact',uuid4()),'key')


@pytest.mark.parametrize('kind',['create','join'])
def test_actual_flag_guard_precedes_reservation_sql(setup,kind):
    service,c,h,actor=setup
    c.connection.dbapi_connection.autocommit=True
    with pytest.raises(DomainError) as caught:
        create(service,h,actor) if kind=='create' else join(service,h,uuid4(),actor)
    assert caught.value.code==ErrorCode.TRANSACTION_CONFIGURATION and c.events==[]
