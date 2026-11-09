"""Real PostgreSQL service tests; run only through the guarded owner runner."""
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.services.errors import DomainError, ErrorCode
from app.services.teams import TeamService
from test_support.races import Outcome, sql, workers


def reject(code, action):
    with pytest.raises(DomainError) as error:
        action()
    print('domain rejection:', error.value.code.value, flush=True)
    assert error.value.code == code


def test_create_team_with_exact_founder_membership(db, service):
    h, users, _ = db.seed(teams=0)
    result = service.create_team(hackathon_id=h, actor_id=users[0], name='Service team')
    assert result.hackathon_id == h and result.user_id == users[0] and result.member_count == 1
    assert db.roster(result.team_id) == {users[0]}
    assert db.team(result.team_id) == (users[0], None)
    with db.connection() as c:
        assert sql(c, 'SELECT count(*) FROM public.teams WHERE hackathon_id=:h', h=h).scalar_one() == 1
        for table in ('audit_events', 'idempotency_records'):
            assert sql(c, f'SELECT count(*) FROM public.{table} WHERE hackathon_id=:h', h=h).scalar_one() == 0


def test_creation_failure_after_team_insert_rolls_back(db, service):
    h, users, _ = db.seed(teams=0)
    with service._engine.connect() as c:
        assert c.connection.dbapi_connection.autocommit is False
        assert c.get_isolation_level() == 'READ COMMITTED'
    # Real SQL conversion failure at founder INSERT, after team INSERT succeeded.
    # SQLAlchemy event injects a failing statement only into this owned test engine.
    def fail_founder(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith('INSERT INTO public.memberships'):
            return "SELECT CAST('not-an-integer' AS integer)", ()
        return statement, parameters

    event.listen(service._engine, 'before_cursor_execute', fail_founder, retval=True)
    try:
        reject(ErrorCode.DATABASE_FAILURE,
               lambda: service.create_team(hackathon_id=h, actor_id=users[0], name='Will roll back'))
    finally:
        event.remove(service._engine, 'before_cursor_execute', fail_founder)
    with db.connection() as c:
        assert sql(c, 'SELECT count(*) FROM public.teams WHERE hackathon_id=:h', h=h).scalar_one() == 0
        assert sql(c, 'SELECT count(*) FROM public.memberships WHERE hackathon_id=:h', h=h).scalar_one() == 0
    # The same subject can successfully create after rollback; no capacity consumed.
    assert service.create_team(hackathon_id=h, actor_id=users[0], name='Retry after rollback').member_count == 1


def test_failed_creation_at_deferred_commit_rolls_back(db, service):
    h, users, _ = db.seed(teams=0)
    # Test-only SQL fault injection omits the founder write. Deferred FK/nonempty
    # validation must fail at COMMIT and roll back the already inserted team.
    def omit_founder(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith('INSERT INTO public.memberships'):
            return 'SELECT 1', ()
        return statement, parameters

    event.listen(service._engine, 'before_cursor_execute', omit_founder, retval=True)
    try:
        reject(ErrorCode.INTEGRITY_FAULT,
               lambda: service.create_team(hackathon_id=h, actor_id=users[0], name='Deferred failure'))
    finally:
        event.remove(service._engine, 'before_cursor_execute', omit_founder)
    with db.connection() as c:
        assert sql(c, 'SELECT count(*) FROM public.teams WHERE hackathon_id=:h', h=h).scalar_one() == 0
        assert sql(c, 'SELECT count(*) FROM public.memberships WHERE hackathon_id=:h', h=h).scalar_one() == 0


def test_join_returns_derived_count(db, service):
    h, users, teams = db.seed(maximum=3)
    result = service.join_team(hackathon_id=h, team_id=teams[0], actor_id=users[1])
    assert result.member_count == 2 and result.team_id == teams[0]
    assert db.roster(teams[0]) == {users[0], users[1]}


def test_full_team_conflict(db, service):
    h, users, teams = db.seed(maximum=1)
    reject(ErrorCode.TEAM_FULL,
           lambda: service.join_team(hackathon_id=h, team_id=teams[0], actor_id=users[1]))
    assert db.roster(teams[0]) == {users[0]}


def test_deleted_team_rejected(db, service):
    h, users, teams = db.seed()
    assert db.transaction(lambda c: db.depart(c, h, teams[0], users[0])) == Outcome('committed')
    reject(ErrorCode.TEAM_DELETED,
           lambda: service.join_team(hackathon_id=h, team_id=teams[0], actor_id=users[1]))
    assert not db.roster(teams[0])


def test_same_hackathon_assignment_rejects_join_and_creation(db, service):
    h, users, teams = db.seed(teams=2)
    reject(ErrorCode.ALREADY_ASSIGNED,
           lambda: service.join_team(hackathon_id=h, team_id=teams[1], actor_id=users[0]))
    reject(ErrorCode.ALREADY_ASSIGNED,
           lambda: service.create_team(hackathon_id=h, actor_id=users[0], name='Duplicate'))
    assert db.roster(teams[0]) == {users[0]} and db.roster(teams[1]) == {users[1]}


def test_repeat_join_conflicts_without_idempotency(db, service):
    h, users, teams = db.seed()
    reject(ErrorCode.ALREADY_ASSIGNED,
           lambda: service.join_team(hackathon_id=h, team_id=teams[0], actor_id=users[0]))
    assert db.roster(teams[0]) == {users[0]}


def test_different_hackathon_membership_allowed(db, service):
    _, users, _ = db.seed()
    other, _, teams = db.seed()
    assert service.join_team(hackathon_id=other, team_id=teams[0], actor_id=users[0]).member_count == 2
    assert users[0] in db.roster(teams[0])


def service_race(actions):
    barrier = Barrier(len(actions), timeout=8)

    def action(operation):
        barrier.wait()
        try:
            operation()
            return Outcome('committed')
        except DomainError as error:
            # Safe structured code only; unexpected codes cause strict assertions to fail.
            return Outcome('domain-error', constraint=error.code.value)
    return workers([lambda operation=operation: action(operation) for operation in actions])


def test_concurrent_service_final_seat(db, service):
    h, users, teams = db.seed()
    outcomes = service_race([lambda u=u: service.join_team(hackathon_id=h, team_id=teams[0], actor_id=u)
                             for u in users[1:9]])
    assert outcomes.count(Outcome('committed')) == 1
    assert outcomes.count(Outcome('domain-error', constraint='team_full')) == 7
    assert len(db.roster(teams[0])) == 2


def test_concurrent_same_user_service_joins(db, service):
    h, users, teams = db.seed(teams=2)
    outcomes = service_race([lambda t=t: service.join_team(hackathon_id=h, team_id=t, actor_id=users[2]) for t in teams])
    assert outcomes.count(Outcome('committed')) == 1
    assert outcomes.count(Outcome('domain-error', constraint='already_assigned')) == 1
    assert sum(users[2] in db.roster(t) for t in teams) == 1


def test_concurrent_same_user_creation(db, service):
    h, users, _ = db.seed(teams=0)
    outcomes = service_race([lambda: service.create_team(hackathon_id=h, actor_id=users[0], name='Concurrent') for _ in range(2)])
    assert outcomes.count(Outcome('committed')) == 1
    assert outcomes.count(Outcome('domain-error', constraint='already_assigned')) == 1
    with db.connection() as c:
        assert sql(c, 'SELECT count(*) FROM public.teams WHERE hackathon_id=:h', h=h).scalar_one() == 1


def test_wrong_hackathon_team_rejected(db, service):
    h, users, _ = db.seed()
    _, _, teams = db.seed()
    reject(ErrorCode.TEAM_NOT_FOUND,
           lambda: service.join_team(hackathon_id=h, team_id=teams[0], actor_id=users[1]))


def test_missing_subjects_and_team(db, service):
    h, users, _ = db.seed(teams=0)
    reject(ErrorCode.HACKATHON_NOT_FOUND,
           lambda: service.create_team(hackathon_id=uuid4(), actor_id=users[0], name='Missing'))
    reject(ErrorCode.USER_NOT_FOUND,
           lambda: service.create_team(hackathon_id=h, actor_id=uuid4(), name='Missing'))
    reject(ErrorCode.TEAM_NOT_FOUND,
           lambda: service.join_team(hackathon_id=h, team_id=uuid4(), actor_id=users[0]))


@pytest.mark.parametrize('operation', ['create', 'join'])
def test_actual_autocommit_engine_rejected_without_domain_sql(db, service, operation):
    h, users, teams = db.seed()

    def snapshot():
        with db.connection() as c:
            return (sql(c, 'SELECT count(*) FROM public.teams WHERE hackathon_id=:h', h=h).scalar_one(),
                    sql(c, 'SELECT count(*) FROM public.memberships WHERE hackathon_id=:h', h=h).scalar_one())

    before = snapshot()
    original_options = dict(service._engine.get_execution_options())
    # A separate SQLAlchemy OptionEngine explicitly exercises actual DBAPI
    # autocommit, while inheriting the test Engine's target-identity hook.
    autocommit_engine = service._engine.execution_options(isolation_level='AUTOCOMMIT')
    observed_states, statements = [], []

    def observe_connection(c):
        observed_states.append(c.connection.dbapi_connection.autocommit)

    def observe_statement(c, cursor, statement, parameters, context, executemany):
        # Retain only the classification, never query values/parameters.
        statements.append('domain' if 'public.' in statement or statement.lstrip().startswith('SET LOCAL') else 'metadata')

    event.listen(autocommit_engine, 'engine_connect', observe_connection)
    event.listen(autocommit_engine, 'before_cursor_execute', observe_statement)
    try:
        guarded = TeamService(autocommit_engine)
        if operation == 'create':
            reject(ErrorCode.TRANSACTION_CONFIGURATION,
                   lambda: guarded.create_team(hackathon_id=h, actor_id=users[1], name='Must not insert'))
        else:
            reject(ErrorCode.TRANSACTION_CONFIGURATION,
                   lambda: guarded.join_team(hackathon_id=h, team_id=teams[0], actor_id=users[1]))
    finally:
        event.remove(autocommit_engine, 'engine_connect', observe_connection)
        event.remove(autocommit_engine, 'before_cursor_execute', observe_statement)
    assert observed_states == [True], 'Actual service DBAPI connection was not AUTOCOMMIT'
    assert 'domain' not in statements, 'Service SQL reached AUTOCOMMIT connection'
    assert snapshot() == before
    assert db.roster(teams[0]) == {users[0]}
    assert dict(service._engine.get_execution_options()) == original_options
    # Verify pool return resets the original Engine's transactional configuration.
    with service._engine.connect() as c:
        assert c.connection.dbapi_connection.autocommit is False
