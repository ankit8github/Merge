"""Credential-free collection; fixed-target, revision-guarded execution only."""
from contextlib import contextmanager

import pytest
from sqlalchemy import event

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from app.services.teams import TeamService
from test_support.database import assert_test_identity
from test_support.races import RaceDatabase, sql


def revision(connection):
    assert sql(connection, 'SELECT version_num FROM public.alembic_version').scalars().all() == ['0003_auth']


class IdempotencyDatabase(RaceDatabase):
    @contextmanager
    def connection(self):
        with super().connection() as connection:
            revision(connection)
            connection.rollback()
            yield connection

    def check_idempotency(self):
        with self.connection() as c:
            sql(c, 'SET TRANSACTION READ ONLY')
            for hackathon in self.hackathons:
                rows = sql(c, '''SELECT state,http_status,response_body,response_headers,
                    octet_length(request_hash),completed_at,created_at
                    FROM public.idempotency_records WHERE hackathon_id=:h''', h=hackathon).all()
                for state, status, body, headers, length, completed, created in rows:
                    assert state == 'completed' and 200 <= status <= 299 and length == 32
                    assert body['schema_version'] == 1 and isinstance(body['data'], dict)
                    assert set(headers) <= {'content-type', 'cache-control'}
                    assert completed is not None and created is not None
                for table in ('teams', 'memberships', 'audit_events'):
                    assert sql(c, f'SELECT count(*) FROM public.{table} WHERE hackathon_id=:h', h=hackathon).scalar_one() == 0
                assert sql(c, '''SELECT count(*) FROM public.outbox_events o
                    JOIN public.audit_events a ON a.id=o.audit_event_id
                    WHERE a.hackathon_id=:h''', h=hackathon).scalar_one() == 0
        self.check_invariants()
        print('Fresh idempotency committed-state invariants verified; fixtures retained', flush=True)


@pytest.fixture
def environment(request, repetition):
    settings = getattr(request.config, '_merge_concurrency_settings', None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded idempotency suite at explicit 0003_auth; no database opened', pytrace=False)
    database = IdempotencyDatabase(settings)
    try:
        with database.connection() as anchor:
            database.engine = anchor.engine

            def guard(connection):
                assert_test_identity(connection)
                revision(connection)
                connection.rollback()

            event.listen(database.engine, 'engine_connect', guard)
            try:
                database.service = TeamService(database.engine)
                yield database
            finally:
                event.remove(database.engine, 'engine_connect', guard)
    finally:
        database.check_idempotency()


@pytest.fixture
def subject(environment):
    h, users, _ = environment.seed(teams=0)
    return h, users[0]
