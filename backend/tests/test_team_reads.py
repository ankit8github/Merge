"""SQL/transaction/response construction checks; not PostgreSQL snapshot proof."""
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from app.services.team_reads import ReadError, TeamReadService


class Connection:
    def __init__(self):
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.active = False
        self.events = []
        self.rows = []
        self.queries = []
        self.fail_commit = False
        self.isolation = 'READ COMMITTED'

    def in_transaction(self): return self.active
    def get_isolation_level(self): return self.isolation

    @contextmanager
    def begin(self):
        assert not self.active
        self.active = True
        self.events.append('begin')
        try:
            yield
            if self.fail_commit: raise OperationalError('private-sql', {}, RuntimeError('private-driver'))
            self.events.append('commit')
        except Exception:
            self.events.append('rollback')
            raise
        finally: self.active = False

    def execute(self, statement, parameters=None):
        assert self.active
        p = parameters or {}
        statement.compile(dialect=postgresql.dialect()).construct_params(p)
        q = str(statement)
        self.queries.append((q,p))
        if q.startswith('SELECT'):
            assert [s for s,p in self.queries[:3]] == [
                'SET TRANSACTION READ ONLY', "SET LOCAL lock_timeout='5s'", "SET LOCAL statement_timeout='15s'"]
            assert 'FOR UPDATE' not in q and 'FOR SHARE' not in q and 'FOR NO KEY UPDATE' not in q
        return SimpleNamespace(mappings=lambda:SimpleNamespace(
            all=lambda:self.rows, one_or_none=lambda:self.rows[0] if self.rows else None))


@pytest.fixture
def setup():
    c, engine = Connection(), MagicMock(spec=Engine)
    engine.connect.return_value.__enter__.return_value = c
    return TeamReadService(engine), c, uuid4(), uuid4()


def row(h, t):
    return dict(scope_id=h, team_id=t, name='Read team', min_team_size=2, max_team_size=3,
        leader_user_id=uuid4(), leader_name='Display', member_count=1,
        created_at=datetime.now(timezone.utc), cursor_id=None)


@pytest.mark.parametrize('method', ['teams','team','my_team'])
def test_single_readonly_snapshot_and_materialized_result(setup, method):
    service,c,h,t = setup
    c.rows = [row(h,t)]
    reply = service.teams(h) if method=='teams' else service.team(h,t) if method=='team' else service.my_team(h,uuid4())
    view = reply.items[0] if method=='teams' else reply.team if method=='my_team' else reply
    assert view.member_count == 1 and view.readiness == 'forming' and view.id == t
    assert set(view.model_dump()) == {'id','hackathon_id','name','min_team_size','max_team_size','member_count','readiness','leader','created_at'}
    assert c.events == ['begin','commit'] and not c.active
    selects = [(q,p) for q,p in c.queries if q.startswith('SELECT')]
    assert len(selects) == 1 and 'SELECT count(*) FROM public.memberships' in selects[0][0]
    assert selects[0][1]['hackathon'] == h


def test_page_overflow_sets_last_returned_cursor(setup):
    service,c,h,t = setup
    c.rows = [row(h,t), row(h,uuid4()), row(h,uuid4())]
    response = service.teams(h,limit=2)
    assert len(response.items)==2 and response.next_cursor==c.rows[1]['team_id']
    assert c.queries[-1][1]['fetch']==3
    assert 'ORDER BY t.created_at DESC,t.id DESC LIMIT :fetch' in c.queries[-1][0]


def test_hackathon_page_uses_primary_key_order_and_bounded_fetch(setup):
    service,c,h,t = setup
    c.rows = [dict(id=h,name='First',min_team_size=1,max_team_size=3),
              dict(id=t,name='Second',min_team_size=1,max_team_size=3)]
    response = service.hackathons(limit=1,cursor=t)
    assert len(response.items)==1 and response.next_cursor==h
    assert c.queries[-1][1] == dict(cursor=t,fetch=2)
    assert 'ORDER BY id ASC LIMIT :fetch' in c.queries[-1][0]


@pytest.mark.parametrize('method', ['teams','team','my_team'])
def test_missing_hackathon_is_not_empty_list(setup, method):
    service,c,h,t = setup
    with pytest.raises(ReadError,match='hackathon_not_found'):
        if method=='teams': service.teams(h)
        elif method=='team': service.team(h,t)
        else: service.my_team(h,t)
    assert c.events[-1]=='rollback'


def test_existing_hackathon_empty_team_and_current_membership(setup):
    service,c,h,t = setup
    c.rows=[dict(scope_id=h,team_id=None,cursor_id=None)]
    assert service.teams(h).items == []
    assert service.my_team(h,t).team is None
    with pytest.raises(ReadError,match='team_not_found'): service.team(h,t)
    with pytest.raises(ReadError,match='invalid_request'): service.teams(h,cursor=uuid4())


@pytest.mark.parametrize('limit', [0,101,-1,True,'20',1.5])
def test_invalid_limit_rejected_before_connection(setup, limit):
    service,c,h,t = setup
    for call in (lambda:service.hackathons(limit=limit),lambda:service.teams(h,limit=limit)):
        with pytest.raises(ReadError,match='invalid_request'): call()
    service._engine.connect.assert_not_called()


@pytest.mark.parametrize('fault', ['autocommit','isolation','active','driver','unreadable'])
def test_actual_transaction_configuration_guard_precedes_sql(setup, fault):
    service,c,h,t = setup
    if fault=='autocommit': c.connection.dbapi_connection.autocommit=True
    if fault=='isolation': c.isolation='REPEATABLE READ'
    if fault=='active': c.active=True
    if fault=='driver': c.dialect.driver='other'
    if fault=='unreadable': c.connection=None
    with pytest.raises(ReadError,match='service_unavailable'): service.hackathons()
    assert c.queries==[] and c.events==[]


def test_failed_read_commit_returns_no_result_or_driver_details(setup):
    service,c,h,t = setup
    c.rows=[row(h,t)]
    c.fail_commit=True
    returned=[]
    with pytest.raises(ReadError) as caught:
        returned.append(service.team(h,t))
    assert returned==[] and str(caught.value)=='service_unavailable'
    assert c.events==['begin','rollback']
