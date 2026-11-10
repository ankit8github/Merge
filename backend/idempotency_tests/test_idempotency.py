"""Real PostgreSQL primitives exercised only through the existing owner.

The sole simulated effect is on a UUID-scoped fixture user's display name.
No team mutation, audit or outbox write belongs to this milestone.
"""
from queue import Queue
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import _command, _reserve_in_tx, _complete_in_tx, _Reservation, _StoredReply
from app.services.teams import TeamService, _CreateTeamCommand, _JoinTeamCommand
from test_support.races import Outcome, sql, wait, workers


def command(subject, key='Key', name='Example'):
    h, actor = subject
    return _command(_CreateTeamCommand(h, actor, name, uuid4()), key)


def reply():
    return _StoredReply._from_values(201, {'schema_version': 1, 'data': {
        'test_effect': 'completed', 'limits': [-(2**63), 2**63-1],
        'name': ' é ', 'ready': True, 'optional': None}},
                                    {'content-type': 'application/json', 'cache-control': 'no-store'})


def effect(c, cmd):
    sql(c, 'UPDATE public.users SET display_name=display_name || :effect WHERE id=:u',
        effect=':effect', u=cmd.actor_id)


def compose(environment, cmd):
    def operation(c):
        result = _reserve_in_tx(c, cmd)
        if isinstance(result, _StoredReply):
            return 'replayed', result
        effect(c, cmd)
        return 'completed', _complete_in_tx(c, result, reply())
    return environment.service._execute(operation)


def snapshot(environment, subject):
    h, actor = subject
    with environment.connection() as c:
        sql(c, 'SET TRANSACTION READ ONLY')
        count = sql(c, 'SELECT count(*) FROM public.idempotency_records WHERE actor_id=:u AND hackathon_id=:h', u=actor, h=h).scalar_one()
        name = sql(c, 'SELECT display_name FROM public.users WHERE id=:u', u=actor).scalar_one()
        return count, name


def test_first_completion_and_matching_replay_has_one_effect(environment, subject):
    cmd = command(subject)
    assert compose(environment, cmd) == ('completed', reply())
    assert compose(environment, command(subject)) == ('replayed', reply())
    assert snapshot(environment, subject) == (1, 'race-test:effect')


@pytest.mark.parametrize('changed', ['fingerprint', 'hackathon'])
def test_same_scope_changed_input_is_stable_mismatch(environment, subject, changed):
    assert compose(environment, command(subject))[0] == 'completed'
    if changed == 'fingerprint':
        other = command(subject, name='Changed')
    else:
        h, _, _ = environment.seed(teams=0)
        other = command((h, subject[1]))
    with pytest.raises(DomainError) as caught:
        compose(environment, other)
    assert caught.value.code == ErrorCode.IDEMPOTENCY_MISMATCH
    assert str(caught.value) == 'idempotency_mismatch' and not caught.value.retryable
    assert snapshot(environment, subject) == (1, 'race-test:effect')


def test_case_sensitive_and_untrimmed_keys_are_distinct(environment, subject):
    for key in ('Key', 'key', ' Key ', ' ', ' '*128):
        assert compose(environment, command(subject, key))[0] == 'completed'
    assert snapshot(environment, subject) == (5, 'race-test' + ':effect'*5)


def test_operation_scope_is_separate(environment, subject):
    cmd = command(subject)
    assert compose(environment, cmd)[0] == 'completed'
    join = _command(_JoinTeamCommand(subject[0], uuid4(), subject[1]), cmd.key)
    assert compose(environment, join)[0] == 'completed'
    assert snapshot(environment, subject) == (2, 'race-test:effect:effect')


class InjectedFailure(Exception):
    pass


@pytest.mark.parametrize('rollback_first', [False, True])
def test_waiting_contender_replays_or_reserves_after_rollback(environment, subject, rollback_first):
    held, release = Event(), Event()
    pids = Queue()
    cmd = command(subject)

    def holder():
        def operation(c):
            reserved = _reserve_in_tx(c, cmd)
            assert isinstance(reserved, _Reservation)
            pids.put(('holder', sql(c, 'SELECT pg_backend_pid()').scalar_one()))
            effect(c, cmd)
            held.set()
            wait(release)
            if rollback_first:
                raise InjectedFailure()
            return _complete_in_tx(c, reserved, reply())
        try:
            result = environment.service._execute(operation)
        except InjectedFailure:
            assert rollback_first
            return Outcome('rolled-back')
        assert result == reply() and not rollback_first
        return Outcome('completed')

    def contender():
        wait(held)
        def operation(c):
            pids.put(('contender', sql(c, 'SELECT pg_backend_pid()').scalar_one()))
            result = _reserve_in_tx(c, cmd)
            if isinstance(result, _StoredReply):
                assert result == reply() and not rollback_first
                return Outcome('replayed')
            assert rollback_first and isinstance(result, _Reservation)
            effect(c, cmd)
            _complete_in_tx(c, result, reply())
            return Outcome('completed')
        return environment.service._execute(operation)

    def observer():
        try:
            wait(held)
            received = dict(pids.get(timeout=8) for _ in range(2))
            assert set(received) == {'holder', 'contender'}
            assert received['holder'] != received['contender']
            with environment.connection() as c:
                sql(c, 'SET TRANSACTION READ ONLY')
                # Uncommitted rows are invisible on this separate connection.
                assert sql(c, 'SELECT count(*) FROM public.idempotency_records WHERE actor_id=:u', u=cmd.actor_id).scalar_one() == 0
                deadline = monotonic() + 3
                while monotonic() < deadline:
                    blockers = sql(c, 'SELECT pg_blocking_pids(:pid)', pid=received['contender']).scalar_one()
                    if received['holder'] in blockers:
                        return Outcome('blocking-observed')
                    sleep(0.02)
                raise AssertionError('Required PostgreSQL blocking was not observed')
        finally:
            release.set()

    results = workers([holder, contender, observer])
    assert results == [Outcome('rolled-back' if rollback_first else 'completed'),
                       Outcome('completed' if rollback_first else 'replayed'), Outcome('blocking-observed')]
    assert snapshot(environment, subject) == (1, 'race-test:effect')


def test_visible_pending_is_fault_and_everything_rolls_back(environment, subject):
    cmd = command(subject)
    def operation(c):
        assert isinstance(_reserve_in_tx(c, cmd), _Reservation)
        effect(c, cmd)
        # The deferred constraint prevents committed pending rows. Our own pending
        # row is visible and exercises the same fail-closed replay branch safely.
        _reserve_in_tx(c, cmd)
    with pytest.raises(DomainError) as caught:
        environment.service._execute(operation)
    assert caught.value.code == ErrorCode.INTEGRITY_FAULT
    assert snapshot(environment, subject) == (0, 'race-test')


def test_unfinished_reservation_cannot_commit(environment, subject):
    failures = []
    def observe(context):
        original = context.original_exception
        failures.append((getattr(original, 'sqlstate', None),
                         getattr(getattr(original, 'diag', None), 'constraint_name', None)))
    event.listen(environment.engine, 'handle_error', observe)
    try:
        with pytest.raises(DomainError) as caught:
            environment.service._execute(lambda c: _reserve_in_tx(c, command(subject)))
        assert caught.value.code == ErrorCode.INTEGRITY_FAULT
        assert failures == [('23514', 'ct_idempotency_completed')]
    finally:
        event.remove(environment.engine, 'handle_error', observe)
    assert snapshot(environment, subject) == (0, 'race-test')


@pytest.mark.parametrize('key', ['', 'x'*129, '\x00', '\n', '\x7f', 'é'])
def test_invalid_key_rejected_before_reservation_sql(environment, subject, key):
    statements = []
    def observe(c, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(environment.engine, 'before_cursor_execute', observe)
    try:
        with pytest.raises(DomainError) as caught:
            compose(environment, command(subject, key))
        assert caught.value.code == ErrorCode.INVALID_INPUT and statements == []
    finally:
        event.remove(environment.engine, 'before_cursor_execute', observe)
    assert snapshot(environment, subject) == (0, 'race-test')


def test_supplied_guarded_connection_and_one_owner_commit(environment, subject):
    connections, commits, begins, reservation_connections = [], [], [], []
    def begin(c):
        begins.append(c)
    def commit(c):
        commits.append(c)
    def observe(c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.idempotency_records' in statement or 'UPDATE public.idempotency_records' in statement:
            reservation_connections.append(c)
    def operation(c):
        connections.append(c)
        reserved = _reserve_in_tx(c, command(subject))
        assert reserved.connection is c and reserved.transaction is c.get_transaction()
        assert c.connection.dbapi_connection.autocommit is False
        return _complete_in_tx(c, reserved, reply())
    for name, hook in [('begin', begin), ('commit', commit), ('before_cursor_execute', observe)]:
        event.listen(environment.engine, name, hook)
    try:
        assert environment.service._execute(operation) == reply()
        # The connection's identity/revision guard owns an initial read transaction
        # which rolls back. Only the owner's following transaction commits.
        assert len(connections) == 1 and commits == connections
        assert begins == connections * 2 and reservation_connections == connections * 2
    finally:
        for name, hook in [('begin', begin), ('commit', commit), ('before_cursor_execute', observe)]:
            event.remove(environment.engine, name, hook)
    assert snapshot(environment, subject) == (1, 'race-test')


@pytest.mark.parametrize('direct_helper', [False, True])
def test_actual_dbapi_autocommit_rejected_before_reservation_sql(environment, subject, direct_helper):
    cmd = command(subject)
    engine = environment.engine.execution_options(isolation_level='AUTOCOMMIT')
    writes = []
    def observe(c, cursor, statement, parameters, context, many):
        if 'idempotency_records' in statement:
            writes.append(statement)
    event.listen(engine, 'before_cursor_execute', observe)
    try:
        with engine.connect() as c:
            assert c.connection.dbapi_connection.autocommit is True
            if direct_helper:
                # SQLAlchemy begin() does not change DBAPI AUTOCOMMIT.
                with c.begin(), pytest.raises(DomainError) as caught:
                    _reserve_in_tx(c, cmd)
            else:
                with pytest.raises(DomainError) as caught:
                    TeamService(engine)._execute(lambda owned: _reserve_in_tx(owned, cmd))
            assert caught.value.code == ErrorCode.TRANSACTION_CONFIGURATION
        assert writes == []
    finally:
        event.remove(engine, 'before_cursor_execute', observe)
    assert snapshot(environment, subject) == (0, 'race-test')


def test_failed_completion_rolls_back_reservation_and_effect(environment, subject):
    cmd = command(subject)
    def operation(c):
        reserved = _reserve_in_tx(c, cmd)
        effect(c, cmd)
        invalid = _StoredReply._from_values(500, {'schema_version': 1, 'data': {}}, {})
        _complete_in_tx(c, reserved, invalid)
    with pytest.raises(DomainError) as caught:
        environment.service._execute(operation)
    assert caught.value.code == ErrorCode.INTEGRITY_FAULT
    assert snapshot(environment, subject) == (0, 'race-test')
    assert compose(environment, cmd)[0] == 'completed'


def test_failure_after_completion_still_rolls_back_every_effect(environment, subject):
    cmd = command(subject)
    def operation(c):
        reserved = _reserve_in_tx(c, cmd)
        effect(c, cmd)
        _complete_in_tx(c, reserved, reply())
        raise InjectedFailure()
    with pytest.raises(InjectedFailure):
        environment.service._execute(operation)
    assert snapshot(environment, subject) == (0, 'race-test')
    assert compose(environment, cmd) == ('completed', reply())
