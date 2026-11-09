"""Database-free transaction/error tests, not evidence of PostgreSQL correctness."""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.services.errors import DomainError, ErrorCode, map_database_error
from app.services.teams import TeamService


def driver_error(state, constraint=None):
    original = RuntimeError('synthetic-secret postgresql://sensitive')
    original.sqlstate = state
    original.diag = SimpleNamespace(constraint_name=constraint)
    return IntegrityError('sensitive-sql', {'secret': 'synthetic-only'}, original)


@pytest.mark.parametrize(('state', 'constraint', 'code', 'retryable'), [
    ('23505', 'pk_memberships', ErrorCode.ALREADY_ASSIGNED, False),
    ('23514', 'ct_team_capacity', ErrorCode.TEAM_FULL, False),
    ('23514', 'guard_team_deleted', ErrorCode.TEAM_DELETED, False),
    ('23505', 'pk_teams', ErrorCode.INTEGRITY_FAULT, False),
    ('23514', 'unknown_check', ErrorCode.INTEGRITY_FAULT, False),
    ('23503', 'fk_teams_leader_member', ErrorCode.INTEGRITY_FAULT, False),
    ('40P01', None, ErrorCode.TRANSACTION_CONFLICT, True),
    ('40001', None, ErrorCode.TRANSACTION_CONFLICT, True),
    ('55P03', None, ErrorCode.LOCK_TIMEOUT, True),
    ('57014', None, ErrorCode.STATEMENT_TIMEOUT, False),
    ('08006', None, ErrorCode.DATABASE_FAILURE, False),
    (None, None, ErrorCode.DATABASE_FAILURE, False),
])
def test_error_mapping_uses_state_and_constraint_without_driver_text(state, constraint, code, retryable):
    result = map_database_error(driver_error(state, constraint))
    assert result.code == code and result.retryable == retryable
    assert str(result) == code.value
    assert 'synthetic' not in repr(result) and 'postgresql' not in repr(result)


class FakeConnection:
    def __init__(self, fail_insert=False, fail_commit=False):
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.statements = []
        self.committed = False
        self.rolled_back = False
        self.fail_insert = fail_insert
        self.fail_commit = fail_commit

    def get_isolation_level(self):
        return 'READ COMMITTED'

    def in_transaction(self):
        return False

    @contextmanager
    def begin(self):
        try:
            yield
            if self.fail_commit:
                raise driver_error('23503', 'fk_teams_leader_member')
            self.committed = True
        except Exception:
            self.rolled_back = True
            raise

    def execute(self, statement, values):
        statement = str(statement)
        self.statements.append(statement)
        if 'INSERT INTO public.memberships' in statement and self.fail_insert:
            raise driver_error('23505', 'pk_memberships')
        if 'FROM public.hackathons' in statement:
            row = SimpleNamespace(min_team_size=1, max_team_size=2)
        elif 'FROM public.users' in statement:
            row = SimpleNamespace(id=uuid4())
        elif 'SELECT team_id FROM public.memberships' in statement:
            row = None
        elif 'FROM public.teams' in statement:
            row = SimpleNamespace(deleted_at=None, max_team_size=2)
        else:
            row = None
        return SimpleNamespace(one_or_none=lambda: row, scalar_one=lambda: 1)


def service_for(connection):
    engine = MagicMock(spec=Engine)
    engine.connect.return_value.__enter__.return_value = connection
    return TeamService(engine)


def test_success_is_returned_only_after_transaction_commits():
    c = FakeConnection()
    result = service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert c.committed and not c.rolled_back and result.member_count == 1
    with pytest.raises(FrozenInstanceError):
        result.member_count = 99


@pytest.mark.parametrize(('fail_insert', 'fail_commit', 'code'), [
    (True, False, ErrorCode.ALREADY_ASSIGNED),
    (False, True, ErrorCode.INTEGRITY_FAULT),
])
def test_statement_and_deferred_commit_errors_rollback_before_mapping(fail_insert, fail_commit, code):
    c = FakeConnection(fail_insert=fail_insert, fail_commit=fail_commit)
    with pytest.raises(DomainError) as result:
        service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert result.value.code == code and c.rolled_back and not c.committed
    assert any('INSERT INTO public.teams' in q for q in c.statements)


def test_join_locks_hackathon_then_user_then_team_before_count():
    c = FakeConnection()
    service_for(c).join_team(hackathon_id=uuid4(), actor_id=uuid4(), team_id=uuid4())
    sql = '\n'.join(c.statements)
    assert sql.index('FROM public.hackathons') < sql.index('FROM public.users') < sql.index('FROM public.teams') < sql.index('SELECT count(*)')
    assert 'FOR SHARE' in sql
    assert sql.count('FOR NO KEY UPDATE') == 2


def test_constructor_rejects_caller_connection_and_session():
    for value in (FakeConnection(), object()):
        with pytest.raises(TypeError):
            TeamService(value)


@pytest.mark.parametrize('invalid_name', ['', '   ', 'x' * 121, None])
def test_invalid_name_fails_before_database_access(invalid_name):
    engine = MagicMock(spec=Engine)
    with pytest.raises(DomainError) as result:
        TeamService(engine).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name=invalid_name)
    assert result.value.code == ErrorCode.INVALID_INPUT
    engine.connect.assert_not_called()


def test_non_read_committed_engine_rejected_before_writes():
    c = FakeConnection()
    c.get_isolation_level = lambda: 'REPEATABLE READ'
    with pytest.raises(DomainError) as result:
        service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert result.value.code == ErrorCode.TRANSACTION_CONFIGURATION
    assert not c.statements


def test_preexisting_transaction_rejected_before_writes():
    c = FakeConnection()
    c.in_transaction = lambda: True
    with pytest.raises(DomainError) as result:
        service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert result.value.code == ErrorCode.TRANSACTION_CONFIGURATION
    assert not c.statements


@pytest.mark.parametrize('operation', ['create', 'join'])
@pytest.mark.parametrize('state', [True, None, 0, 'False'])
def test_autocommit_or_ambiguous_state_rejected_before_any_service_sql(operation, state):
    c = FakeConnection()
    c.connection.dbapi_connection.autocommit = state
    # Reject even before the SQLAlchemy isolation metadata query or begin().
    c.get_isolation_level = lambda: pytest.fail('Isolation query reached')
    c.begin = lambda: pytest.fail('Transaction boundary reached')
    service = service_for(c)
    with pytest.raises(DomainError) as result:
        if operation == 'create':
            service.create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
        else:
            service.join_team(hackathon_id=uuid4(), team_id=uuid4(), actor_id=uuid4())
    assert result.value.code == ErrorCode.TRANSACTION_CONFIGURATION
    assert not c.statements and not c.committed and not c.rolled_back
    assert c.connection.dbapi_connection.autocommit is state


@pytest.mark.parametrize('missing', ['proxy', 'dbapi', 'autocommit', 'unreadable'])
def test_unavailable_actual_autocommit_state_fails_closed(missing):
    c = FakeConnection()
    if missing == 'proxy':
        del c.connection
    elif missing == 'dbapi':
        c.connection = SimpleNamespace()
    elif missing == 'autocommit':
        c.connection.dbapi_connection = SimpleNamespace()
    else:
        class Unreadable:
            @property
            def autocommit(self):
                raise RuntimeError('synthetic-secret')
        c.connection.dbapi_connection = Unreadable()
    with pytest.raises(DomainError) as result:
        service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert result.value.code == ErrorCode.TRANSACTION_CONFIGURATION
    assert 'synthetic' not in str(result.value) and not c.statements


@pytest.mark.parametrize(('attribute', 'value'), [('name', 'sqlite'), ('driver', 'unknown'), ('is_async', True)])
def test_unsupported_driver_configuration_fails_before_sql(attribute, value):
    c = FakeConnection()
    setattr(c.dialect, attribute, value)
    with pytest.raises(DomainError) as result:
        service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert result.value.code == ErrorCode.TRANSACTION_CONFIGURATION
    assert not c.statements


@pytest.mark.parametrize('attribute', ['name', 'driver', 'is_async'])
def test_missing_driver_configuration_fails_closed(attribute):
    c = FakeConnection()
    delattr(c.dialect, attribute)
    with pytest.raises(DomainError) as result:
        service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert result.value.code == ErrorCode.TRANSACTION_CONFIGURATION
    assert not c.statements


@pytest.mark.parametrize('mode', ['REPEATABLE READ', 'SERIALIZABLE', 'READ UNCOMMITTED', 'AUTOCOMMIT', None])
def test_unsupported_isolation_modes_fail_before_service_sql(mode):
    c = FakeConnection()
    c.get_isolation_level = lambda: mode
    with pytest.raises(DomainError) as result:
        service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert result.value.code == ErrorCode.TRANSACTION_CONFIGURATION
    assert not c.statements


def test_normal_transactional_state_is_accepted_and_unchanged():
    c = FakeConnection()
    result = service_for(c).create_team(hackathon_id=uuid4(), actor_id=uuid4(), name='Team')
    assert result.member_count == 1 and c.committed
    assert c.connection.dbapi_connection.autocommit is False
