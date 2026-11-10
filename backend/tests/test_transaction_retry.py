"""Deterministic orchestration evidence; real PostgreSQL evidence is separate."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from app.services import team_mutations as composed, transaction_retry as retry
from app.services.errors import DomainError, ErrorCode
from app.services.teams import TeamService
from test_team_mutations import Connection, create, join, stage


def database_error(state):
    original = RuntimeError('synthetic private driver detail')
    original.sqlstate = state
    original.diag = SimpleNamespace(constraint_name=None)
    return OperationalError('synthetic SQL', {}, original)


class Clock:
    value = 0.0

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class Ledger:
    """Independent connection handles sharing only committed offline state."""
    def __init__(self):
        self.data = Connection().data
        self.connections = []
        self.active = False
        self.fault = lambda c, q: None
        self.commit_fault = lambda c: None
        self.after_close = lambda c: None
        self.open_fault = lambda: None

    @contextmanager
    def connect(self):
        assert not self.active, 'Previous owner did not unwind'
        self.open_fault()
        ledger = self

        class Handle(Connection):
            def execute(self, statement, parameters):
                result = super().execute(statement, parameters)
                ledger.fault(self, str(statement))
                return result

            @contextmanager
            def begin(self):
                with super().begin():
                    yield
                    ledger.commit_fault(self)  # Before actual commit: rollback on failure.
                ledger.after_commit(self)  # Actual success, then acknowledgement loss.

        c = Handle()
        c.data = deepcopy(self.data)
        self.connections.append(c)
        self.active = True
        try:
            yield c
        finally:
            assert not c.in_transaction()
            assert not c.info, 'Attempt metadata leaked into pool'
            self.data = deepcopy(c.data)
            self.active = False
            self.after_close(c)

    def after_commit(self, c):
        pass


@pytest.fixture
def harness(monkeypatch):
    clock, ledger = Clock(), Ledger()
    monkeypatch.setattr(retry, '_now', clock.now)
    monkeypatch.setattr(retry, '_sleep', clock.sleep)
    monkeypatch.setattr(retry, 'uniform', lambda low, high: high)
    engine = MagicMock(spec=Engine)
    engine.connect.side_effect = ledger.connect
    service = TeamService(engine, retry_policy=retry.TransactionRetryPolicy(jitter_ms=0))
    return service, ledger, clock, uuid4(), uuid4()


def assert_chain(ledger, count=1):
    assert len(ledger.data['teams']) == 1
    assert len(ledger.data['members']) == count
    assert len(ledger.data['reservations']) == len(ledger.data['audits']) == len(ledger.data['outbox']) == count
    assert all(r['state'] == 'completed' for r in ledger.data['reservations'].values())


@pytest.mark.parametrize('state', ['40P01', '40001'])
@pytest.mark.parametrize('kind', ['create', 'join'])
def test_full_transaction_retry_pins_scope_and_has_no_duplicate_effects(harness, monkeypatch, state, kind):
    service, ledger, clock, h, actor = harness
    if kind == 'join':
        first = create(service, h, actor)
        team, actor = next(iter(ledger.data['teams'])), uuid4()
    start = len(ledger.connections)
    scopes = []
    reserve = composed._reserve_in_tx
    def capture(c, scope):
        scopes.append(scope)
        return reserve(c, scope)
    monkeypatch.setattr(composed, '_reserve_in_tx', capture)
    def fault(c, q):
        if stage(q) == 'outbox' and len(ledger.connections) == start + 1:
            raise database_error(state)
    ledger.fault = fault
    reply = create(service, h, actor) if kind == 'create' else join(service, h, team, actor)
    assert reply.http_status == (201 if kind == 'create' else 200)
    assert len(ledger.connections) == start + 2
    assert scopes[0] is scopes[1]
    assert ledger.connections[start].events[-1] == 'rollback'
    assert ledger.connections[-1].events[-1] == 'commit'
    assert_chain(ledger, 1 if kind == 'create' else 2)
    assert next(iter(ledger.data['teams'].values()))['version'] == (1 if kind == 'create' else 2)


@pytest.mark.parametrize('state', ['40P01', '40001'])
@pytest.mark.parametrize('at_commit', [False, True])
def test_exactly_three_confirmed_abort_attempts(harness, state, at_commit):
    service, ledger, clock, h, actor = harness
    def fail(c):
        raise database_error(state)
    if at_commit:
        ledger.commit_fault = fail
    else:
        ledger.fault = lambda c, q: fail(c) if stage(q) == 'completion' else None
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.TRANSACTION_CONFLICT
    assert len(ledger.connections) == 3
    assert ledger.data == Connection().data
    assert all(c.events[-1] == 'rollback' for c in ledger.connections)


@pytest.mark.parametrize('state', ['55P03', '57014', '08006', 'ZZ001', None, '23514'])
def test_other_database_failures_do_not_retry(harness, state):
    service, ledger, clock, h, actor = harness
    def fail(c, q):
        if stage(q) == 'outbox':
            raise database_error(state)
    ledger.fault = fail
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code != ErrorCode.OUTCOME_UNCERTAIN
    assert len(ledger.connections) == 1 and ledger.data == Connection().data


@pytest.mark.parametrize('code', [ErrorCode.TEAM_FULL, ErrorCode.IDEMPOTENCY_MISMATCH,
                                      ErrorCode.INTEGRITY_FAULT, ErrorCode.TRANSACTION_CONFLICT])
def test_domain_retryable_flag_is_not_confirmed_sqlstate(harness, code):
    service, ledger, clock, h, actor = harness
    def fail(c, q):
        if stage(q) == 'outbox':
            raise DomainError(code, retryable=True)
    ledger.fault = fail
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == code and len(ledger.connections) == 1


def test_deadline_exhaustion_prevents_another_connection(harness):
    service, ledger, clock, h, actor = harness
    service._retry_policy = retry.TransactionRetryPolicy(total_seconds=1)
    def fail(c, q):
        if stage(q) == 'outbox':
            clock.value += 1
            raise database_error('40P01')
    ledger.fault = fail
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.TRANSACTION_DEADLINE
    assert len(ledger.connections) == 1 and not ledger.active


def test_jitter_outside_transaction_is_bounded_by_remaining_budget(harness, monkeypatch):
    service, ledger, clock, h, actor = harness
    service._retry_policy = retry.TransactionRetryPolicy(total_seconds=1, jitter_ms=250)
    waits = []
    def wait(seconds):
        assert not ledger.active
        waits.append(seconds)
        clock.sleep(seconds)
    monkeypatch.setattr(retry, '_sleep', wait)
    def fail(c, q):
        if stage(q) == 'outbox':
            clock.value = .9
            raise database_error('40001')
    ledger.fault = fail
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.TRANSACTION_DEADLINE
    assert len(waits) == 1 and 0 < waits[0] <= .1
    assert len(ledger.connections) == 1


@pytest.mark.parametrize('committed', [True, False])
def test_lost_ack_reconciles_by_same_key_reservation(harness, committed):
    service, ledger, clock, h, actor = harness
    def fail(c):
        if len(ledger.connections) == 1:
            raise database_error(None)
    if committed:
        ledger.after_commit = fail
    else:
        ledger.commit_fault = fail
    reply = create(service, h, actor)
    assert reply.http_status == 201 and len(ledger.connections) == 2
    assert_chain(ledger)
    first, second = ledger.connections
    assert first.events[-1] == ('commit' if committed else 'rollback')
    assert second.events.count('reservation') == 1
    assert second.events.count('membership') == (0 if committed else 1)
    assert not ledger.active


def test_unresolved_ambiguous_commit_is_uncertain_not_false_failure(harness):
    service, ledger, clock, h, actor = harness
    def fail(c):
        raise database_error(None)
    ledger.commit_fault = fail
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.OUTCOME_UNCERTAIN and caught.value.retryable
    assert str(caught.value) == 'outcome_uncertain'
    assert len(ledger.connections) == 3 and ledger.data == Connection().data
    ledger.commit_fault = lambda c: None
    assert create(service, h, actor).http_status == 201
    assert_chain(ledger)


def test_reconciliation_connection_failure_remains_uncertain(harness):
    service, ledger, clock, h, actor = harness
    def lost(c):
        ledger.open_fault = lambda: (_ for _ in ()).throw(database_error('08006'))
        raise database_error(None)
    ledger.after_commit = lost
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.OUTCOME_UNCERTAIN
    assert len(ledger.connections) == 1
    assert_chain(ledger)


def test_deadline_after_unknown_commit_returns_uncertainty(harness):
    service, ledger, clock, h, actor = harness
    service._retry_policy = retry.TransactionRetryPolicy(total_seconds=1)
    def lost(c):
        clock.value = 1
        raise database_error(None)
    ledger.after_commit = lost
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.OUTCOME_UNCERTAIN
    assert len(ledger.connections) == 1
    assert_chain(ledger)


@pytest.mark.parametrize('state', ['40P01', '40001'])
def test_confirmed_commit_abort_then_success_restarts_whole_transaction(harness, state):
    service, ledger, clock, h, actor = harness
    def abort(c):
        if len(ledger.connections) == 1:
            raise database_error(state)
    ledger.commit_fault = abort
    assert create(service, h, actor).http_status == 201
    assert len(ledger.connections) == 2
    assert all(c.events.count('completion') == 1 for c in ledger.connections)
    assert_chain(ledger)


def test_valid_replay_survives_unknown_read_transaction_commit_ack(harness):
    service, ledger, clock, h, actor = harness
    original = create(service, h, actor)
    def fail(c):
        raise database_error(None)
    ledger.after_commit = fail
    assert create(service, h, actor) == original
    assert len(ledger.connections) == 2 and not ledger.active
    assert_chain(ledger)


def test_confirmed_commit_survives_connection_cleanup_failure(harness):
    service, ledger, clock, h, actor = harness
    ledger.after_close = lambda c: (_ for _ in ()).throw(database_error(None))
    assert create(service, h, actor).http_status == 201
    assert len(ledger.connections) == 1
    assert_chain(ledger)


def test_cleanup_abort_cannot_replace_unknown_commit_evidence(harness):
    service, ledger, clock, h, actor = harness
    ledger.commit_fault = lambda c: (_ for _ in ()).throw(database_error(None))
    ledger.after_close = lambda c: (_ for _ in ()).throw(database_error('40001'))
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.OUTCOME_UNCERTAIN
    assert len(ledger.connections) == 3 and ledger.data == Connection().data


def test_deadline_before_commit_rolls_back_without_success(harness):
    service, ledger, clock, h, actor = harness
    service._retry_policy = retry.TransactionRetryPolicy(total_seconds=1)
    def expire(c, q):
        if stage(q) == 'completion':
            clock.value = 1
    ledger.fault = expire
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.TRANSACTION_DEADLINE
    assert ledger.data == Connection().data and len(ledger.connections) == 1


@pytest.mark.parametrize('state', ['40P01', '40001'])
def test_legacy_create_has_no_automatic_retry(harness, state):
    service, ledger, clock, h, actor = harness
    def fail(c, q):
        if stage(q) == 'membership':
            raise database_error(state)
    ledger.fault = fail
    with pytest.raises(DomainError) as caught:
        service.create_team(hackathon_id=h, actor_id=actor, name='Legacy')
    assert caught.value.code == ErrorCode.TRANSACTION_CONFLICT
    assert len(ledger.connections) == 1


@pytest.mark.parametrize('kwargs', [{'total_seconds': 0}, {'total_seconds': 61},
    {'total_seconds': float('inf')}, {'total_seconds': float('nan')}, {'total_seconds': True},
    {'total_seconds': 10**1000},
    {'jitter_ms': -1}, {'jitter_ms': 251}, {'jitter_ms': 1.5}, {'jitter_ms': True}])
def test_policy_rejects_unsafe_configuration(kwargs):
    with pytest.raises(ValueError, match='Invalid transaction retry policy'):
        retry.TransactionRetryPolicy(**kwargs)


@pytest.mark.parametrize('state', ['23bad-state', '08006', None, 'ZZ001'])
def test_unknown_commit_states_never_prove_abort(state):
    attempt = retry._Attempt(30, phase='commit')
    attempt.database_failure(database_error(state))
    assert attempt.ambiguous and not attempt.confirmed_abort and not attempt.confirmed_failure


@pytest.mark.parametrize('fault', ['autocommit', 'isolation'])
def test_composed_transaction_guard_is_not_retried(harness, monkeypatch, fault):
    service, ledger, clock, h, actor = harness
    if fault == 'autocommit':
        original = service._require_transactional_connection
        def reject(c):
            c.connection.dbapi_connection.autocommit = True
            original(c)
        monkeypatch.setattr(service, '_require_transactional_connection', reject)
    else:
        monkeypatch.setattr(Connection, 'get_isolation_level', lambda c: 'REPEATABLE READ')
    with pytest.raises(DomainError) as caught:
        create(service, h, actor)
    assert caught.value.code == ErrorCode.TRANSACTION_CONFIGURATION
    assert len(ledger.connections) == 1 and ledger.connections[0].events == []


def test_timeout_settings_are_clamped_to_remaining_budget(harness):
    service, ledger, clock, h, actor = harness
    service._retry_policy = retry.TransactionRetryPolicy(total_seconds=1)
    budgets = []
    original = Connection.execute
    # Capture actual bound values without replacing SQL/result behavior.
    def record(c, statement, p):
        if str(statement).startswith('SELECT set_config'):
            budgets.append(p.copy())
        return original(c, statement, p)
    from unittest.mock import patch
    with patch.object(Connection, 'execute', record):
        assert create(service, h, actor).http_status == 201
    assert budgets and all(p == {'statement': '1000ms', 'lock': '1000ms'} for p in budgets)
