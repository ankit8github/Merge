"""Exercise guarded schedule control flow with no SQL, engine or live fixtures.

These doubles check transaction ownership/cleanup, not PostgreSQL visibility.
The real idempotency ownership guard validates each private lifecycle call.
"""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.idempotency import _active_transaction


class ScheduleFailure(Exception):
    pass


class Transaction:
    def __init__(self, harness):
        self.harness = harness
        self.is_active = True

    def __enter__(self):
        return self

    def rollback(self):
        assert self.is_active
        self.harness.events.append('rollback')
        self.is_active = False
        self.harness.pending = False
        self.harness.handle.transaction = None

    def __exit__(self, kind, value, traceback):
        if not self.is_active:
            return
        if kind is not None:
            self.rollback()
            return
        try:
            self.harness.fail('commit')
            self.harness.events.append('commit')
            self.harness.revision += 1
            self.harness.deleted = True
            self.harness.pending = False
            self.is_active = False
            self.harness.handle.transaction = None
        except BaseException:
            self.rollback()
            raise


class Connection:
    dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
    connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))

    def __init__(self, harness):
        self.harness = harness
        self.transaction = None  # Same state as the real post-preflight handle.

    def begin(self):
        assert self.transaction is None
        self.harness.events.append('begin')
        self.transaction = Transaction(self.harness)
        return self.transaction

    def get_transaction(self):
        return self.transaction

    def in_transaction(self):
        return self.transaction is not None and self.transaction.is_active

    def in_nested_transaction(self):
        return False

    def get_isolation_level(self):
        return 'READ COMMITTED'


class Harness:
    def __init__(self, failure=None):
        self.failure = failure
        self.events = []
        self.revision = 0
        self.pending = self.deleted = self.open = False
        self.handle = Connection(self)
        self.subject = (uuid4(), uuid4(), [(uuid4(), None) for _ in range(3)])
        self.reply = SimpleNamespace(body=lambda: b'synthetic-stable-reply')
        self.lifecycle = SimpleNamespace(_change=self.change, leave=self.replay)

    def fail(self, phase):
        if self.failure == phase:
            raise ScheduleFailure(phase)

    @contextmanager
    def connection(self):
        self.open = True
        self.events.append('open')
        try:
            yield self.handle
        finally:
            # Do not silently compensate for missing transaction cleanup.
            assert not self.handle.in_transaction()
            self.open = False
            self.events.append('close')

    def change(self, connection, scope, team, actor, removing):
        assert self.open and connection is self.handle and not removing
        assert _active_transaction(connection) is connection.transaction
        self.events.append('change')
        self.pending = True
        self.fail('change')
        return self.reply

    def snapshots(self, db, subject):
        assert db is self and subject is self.subject
        if self.pending:
            self.fail('observer')
        self.events.append(f'snapshot:{self.revision}')
        return [self.revision] * 3

    def post(self, path, **values):
        assert self.pending and self.handle.in_transaction()
        self.fail('other_team')
        self.events.append('other_team_commit')
        self.revision += 1
        return SimpleNamespace(status_code=201)

    def replay(self, **values):
        assert self.deleted and not self.open and not self.pending
        self.events.append('replay')
        return self.reply

    def roster(self, team):
        assert not self.open
        return set() if self.deleted else {self.subject[2][0][0]}

    def team(self, team):
        assert not self.open
        return None, object() if self.deleted else None


@pytest.fixture
def schedules(monkeypatch):
    # Import definitions; invoke schedules with doubles, never live fixtures.
    path = Path(__file__).resolve().parents[1] / 'realtime_tests/test_realtime.py'
    spec = importlib.util.spec_from_file_location('offline_realtime_schedules', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'headers', lambda *a: {})
    return module


def run_schedule(module, harness, schedule, monkeypatch):
    monkeypatch.setattr(module, 'snapshots', harness.snapshots)
    if schedule == 'rollback':
        module.test_uncommitted_departure_and_rollback_are_invisible(harness, harness.subject)
    else:
        module.test_late_commit_after_another_team_and_exact_replay(harness, harness, harness.subject)


@pytest.mark.parametrize('schedule', ['rollback', 'late_commit'])
def test_private_lifecycle_schedule_owns_transaction_and_preserves_order(schedules, schedule, monkeypatch):
    harness = Harness()
    run_schedule(schedules, harness, schedule, monkeypatch)
    middle = ['snapshot:0', 'rollback'] if schedule == 'rollback' else [
        'snapshot:0', 'other_team_commit', 'snapshot:1', 'commit']
    tail = ['snapshot:0'] if schedule == 'rollback' else ['snapshot:2', 'replay', 'snapshot:2']
    assert harness.events == ['snapshot:0', 'open', 'begin', 'change', *middle, 'close', *tail]
    assert not harness.open and not harness.pending and harness.handle.get_transaction() is None


@pytest.mark.parametrize('schedule,failure', [
    ('rollback', 'change'), ('rollback', 'observer'),
    ('late_commit', 'change'), ('late_commit', 'observer'),
    ('late_commit', 'other_team'), ('late_commit', 'commit'),
])
def test_schedule_failure_rolls_back_before_connection_release(schedules, schedule, failure, monkeypatch):
    harness = Harness(failure)
    with pytest.raises(ScheduleFailure, match=failure):
        run_schedule(schedules, harness, schedule, monkeypatch)
    assert harness.events[-2:] == ['rollback', 'close']
    assert 'commit' not in harness.events and not harness.deleted
    assert not harness.open and not harness.pending and harness.handle.get_transaction() is None
