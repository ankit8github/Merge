"""Guarded PostgreSQL rollback/reconciliation tests; injected acknowledgement loss.

No network outage or naturally occurring deadlock is claimed. Server aborts are
real SQLSTATE failures; COMMIT hooks exercise both actual commit and rollback.
"""
from contextlib import contextmanager
from uuid import UUID

import psycopg
import pytest
from sqlalchemy import event

from app.services import transaction_retry as retry
from app.services.errors import DomainError, ErrorCode
from app.services.teams import TeamService
from team_mutation_tests.test_composition import create, join, snapshot


@contextmanager
def aborts(env, state, count):
    """Abort after membership/audit writes, before outbox; no schema objects."""
    assert state in ('40P01', '40001', '55P03', '57014', '08006', 'ZZ001')
    hits, observed, connections = [], [], []
    def inject(c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.idempotency_records' in statement:
            connections.append(c)
        if 'INSERT INTO public.outbox_events' in statement and len(hits) < count:
            hits.append(state)
            return ("DO $$ BEGIN RAISE EXCEPTION USING ERRCODE='" + state
                    + "', MESSAGE='injected test abort'; END $$", ())
        return statement, parameters
    def observe(context):
        observed.append(getattr(context.original_exception, 'sqlstate', None))
    event.listen(env.engine, 'before_cursor_execute', inject, retval=True)
    event.listen(env.engine, 'handle_error', observe)
    try:
        yield connections, hits, observed
    finally:
        event.remove(env.engine, 'before_cursor_execute', inject)
        event.remove(env.engine, 'handle_error', observe)


def assert_increment(before, after, kind):
    for table in ('memberships', 'idempotency_records', 'audit_events', 'outbox_events'):
        assert len(after[table]) == len(before[table]) + 1
    assert len(after['teams']) == len(before['teams']) + (kind == 'create')
    assert after['teams'][0]['version'] == (1 if kind == 'create' else 2)


@pytest.mark.parametrize('state', ['40P01', '40001'])
@pytest.mark.parametrize('kind', ['create', 'join'])
def test_confirmed_abort_restarts_entire_chain(environment, subject, state, kind):
    h, users = subject
    team = None
    if kind == 'join':
        team = UUID(create(environment, h, users[0]).body()['data']['team_id'])
    saved = snapshot(environment, h)
    with aborts(environment, state, 1) as (connections, hits, observed):
        reply = create(environment, h, users[0]) if kind == 'create' else join(environment, h, team, users[1])
    assert reply.http_status == (201 if kind == 'create' else 200)
    assert hits == observed == [state]
    assert len(connections) == 2 and connections[0] is not connections[1]
    assert all(c.closed for c in connections)
    assert_increment(saved, snapshot(environment, h), kind)


@pytest.mark.parametrize('state', ['40P01', '40001'])
def test_three_total_attempts_and_no_partial_chain(environment, subject, state):
    h, users = subject
    saved = snapshot(environment, h)
    with aborts(environment, state, 4) as (connections, hits, observed):
        with pytest.raises(DomainError) as caught:
            create(environment, h, users[0])
    assert caught.value.code == ErrorCode.TRANSACTION_CONFLICT
    assert hits == observed == [state] * 3 and len(connections) == 3
    assert len({id(c) for c in connections}) == 3 and all(c.closed for c in connections)
    assert snapshot(environment, h) == saved


def test_deadline_prevents_second_attempt(environment, subject, monkeypatch):
    h, users = subject
    ticks = [0.0]
    monkeypatch.setattr(retry, '_now', lambda: ticks[0])
    environment.service = TeamService(environment.engine,
        retry_policy=retry.TransactionRetryPolicy(total_seconds=1, jitter_ms=0))
    def expire(context):
        if getattr(context.original_exception, 'sqlstate', None) == '40P01':
            ticks[0] = 1
    event.listen(environment.engine, 'handle_error', expire)
    try:
        with aborts(environment, '40P01', 4) as (connections, hits, observed):
            with pytest.raises(DomainError) as caught:
                create(environment, h, users[0])
        assert caught.value.code == ErrorCode.TRANSACTION_DEADLINE
        assert hits == observed == ['40P01'] and len(connections) == 1
    finally:
        event.remove(environment.engine, 'handle_error', expire)
    assert all(not rows for rows in snapshot(environment, h).values())


@pytest.mark.parametrize('state,code', [('55P03', ErrorCode.LOCK_TIMEOUT),
    ('57014', ErrorCode.STATEMENT_TIMEOUT), ('08006', ErrorCode.DATABASE_FAILURE),
    ('ZZ001', ErrorCode.DATABASE_FAILURE)])
def test_non_retryable_work_failures(environment, subject, state, code):
    h, users = subject
    saved = snapshot(environment, h)
    with aborts(environment, state, 4) as (connections, hits, observed):
        with pytest.raises(DomainError) as caught:
            create(environment, h, users[0])
    assert caught.value.code == code
    assert hits == observed == [state] and len(connections) == 1
    assert snapshot(environment, h) == saved


def test_business_conflict_is_not_automatically_retried(environment):
    h, users, _ = environment.seed(maximum=1, teams=0)
    team = UUID(create(environment, h, users[0]).body()['data']['team_id'])
    saved = snapshot(environment, h)
    with aborts(environment, '40P01', 0) as (connections, hits, observed):
        with pytest.raises(DomainError) as caught:
            join(environment, h, team, users[1])
    assert caught.value.code == ErrorCode.TEAM_FULL
    assert len(connections) == 1 and hits == observed == []
    assert snapshot(environment, h) == saved


@pytest.mark.parametrize('kind', ['create', 'join'])
@pytest.mark.parametrize('committed', [True, False])
def test_lost_commit_ack_reconciles_same_key(environment, subject, monkeypatch, kind, committed):
    h, users = subject
    team = None
    if kind == 'join':
        team = UUID(create(environment, h, users[0]).body()['data']['team_id'])
    saved = snapshot(environment, h)
    original = environment.engine.dialect.do_commit
    commits, reservations, mutations = [], [], []
    def lose_ack(dbapi):
        commits.append(True)
        if len(commits) == 1:
            if committed:
                original(dbapi)  # Actually commit PostgreSQL before losing acknowledgement.
            raise psycopg.OperationalError('injected acknowledgement loss')
        original(dbapi)
    def observe(c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.idempotency_records' in statement:
            reservations.append((c, dict(context.compiled_parameters[0])))
        if 'INSERT INTO public.memberships' in statement:
            mutations.append(c)
    event.listen(environment.engine, 'before_cursor_execute', observe)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(environment.engine.dialect, 'do_commit', lose_ack)
            result = create(environment, h, users[0]) if kind == 'create' else join(environment, h, team, users[1])
    finally:
        event.remove(environment.engine, 'before_cursor_execute', observe)
    assert result.http_status == (201 if kind == 'create' else 200)
    assert len(commits) == len(reservations) == 2
    assert reservations[0][0] is not reservations[1][0]
    assert all(c.closed for c, p in reservations)
    for field in ('actor', 'operation', 'key', 'hackathon', 'fingerprint'):
        assert reservations[0][1][field] == reservations[1][1][field]
    assert len(mutations) == (1 if committed else 2)
    assert_increment(saved, snapshot(environment, h), kind)


def test_unresolved_commit_returns_uncertainty_and_same_key_can_recover(environment, subject, monkeypatch):
    h, users = subject
    saved = snapshot(environment, h)
    commits = []
    def lose_ack(dbapi):
        commits.append(True)
        raise psycopg.OperationalError('injected unknown commit outcome')
    with monkeypatch.context() as patch:
        patch.setattr(environment.engine.dialect, 'do_commit', lose_ack)
        with pytest.raises(DomainError) as caught:
            create(environment, h, users[0])
    assert caught.value.code == ErrorCode.OUTCOME_UNCERTAIN and caught.value.retryable
    assert str(caught.value) == 'outcome_uncertain' and len(commits) == 3
    assert snapshot(environment, h) == saved
    assert create(environment, h, users[0]).http_status == 201
    assert_increment(saved, snapshot(environment, h), 'create')


def test_actual_autocommit_guard_before_reservation(environment, subject):
    h, users = subject
    engine = environment.engine.execution_options(isolation_level='AUTOCOMMIT')
    writes = []
    def observe(c, cursor, statement, parameters, context, many):
        if statement.lstrip().startswith(('INSERT', 'UPDATE', 'DELETE')):
            writes.append(statement)
    event.listen(engine, 'before_cursor_execute', observe)
    try:
        service = TeamService(engine)
        with pytest.raises(DomainError) as caught:
            service.create_team_idempotent(hackathon_id=h, actor_id=users[0], name='Guard', key='guard')
        assert caught.value.code == ErrorCode.TRANSACTION_CONFIGURATION and writes == []
    finally:
        event.remove(engine, 'before_cursor_execute', observe)
    assert all(not rows for rows in snapshot(environment, h).values())
