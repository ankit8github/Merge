"""Guarded credential tests retain UUID-scoped accounts; no destructive cleanup."""
import secrets
from threading import Lock
from uuid import uuid4

import pytest
from sqlalchemy import event

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from app.services.credentials import CredentialService
from test_support.database import assert_test_identity, test_connection
from test_support.races import sql


class CredentialEnvironment:
    def __init__(self, settings, engine):
        self.settings = settings
        self.engine = engine
        self.service = CredentialService(engine)
        self.ids = set()
        self.states = []
        self.mutex = Lock()

    @staticmethod
    def username():
        return 'c_' + uuid4().hex[:24]

    def connection(self):
        return test_connection(self.settings)

    def track(self, c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.users' in statement:
            with self.mutex:
                self.ids.add(context.compiled_parameters[0]['u'])

    def record_error(self, context):
        original = context.original_exception
        state = getattr(original, 'sqlstate', None)
        constraint = getattr(getattr(original, 'diag', None), 'constraint_name', None)
        # Retain only the fixed expected username conflict; never driver text,
        # SQL/parameters, hashes, exception objects or arbitrary server fields.
        with self.mutex:
            self.states.append(('23505', 'uq_credentials_username')
                               if (state, constraint) == ('23505', 'uq_credentials_username')
                               else ('unexpected', ''))

    def counts(self):
        with self.connection() as c:
            sql(c, 'SET TRANSACTION READ ONLY')
            with self.mutex:
                ids = list(self.ids)
            if not ids:
                return 0, 0
            return tuple(sql(c, '''SELECT count(*),count(a.user_id)
                FROM public.users u LEFT JOIN public.account_credentials a ON a.user_id=u.id
                WHERE u.id=ANY(:ids)''', ids=ids).one())

    def check(self):
        with self.connection() as c:
            sql(c, 'SET TRANSACTION READ ONLY')
            assert sql(c, 'SELECT version_num FROM public.alembic_version').scalar_one() == '0003_auth'
            with self.mutex:
                ids = list(self.ids)
            if ids:
                assert sql(c, '''SELECT count(*) FROM public.account_credentials a
                    LEFT JOIN public.users u ON u.id=a.user_id
                    WHERE a.user_id=ANY(:ids) AND u.id IS NULL''', ids=ids).scalar_one() == 0
                assert sql(c, 'SELECT count(*) FROM public.auth_sessions WHERE user_id=ANY(:ids)', ids=ids).scalar_one() == 0
                assert sql(c, 'SELECT count(*) FROM public.memberships WHERE user_id=ANY(:ids)', ids=ids).scalar_one() == 0
        print('Fresh credential committed-state checks verified; no cleanup performed')


@pytest.fixture
def environment(request, repetition):
    settings = getattr(request.config, '_merge_concurrency_settings', None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded --suite credentials --revision 0003_auth; no database opened', pytrace=False)
    with test_connection(settings) as anchor:
        assert sql(anchor, 'SELECT version_num FROM public.alembic_version').scalar_one() == '0003_auth'
        anchor.rollback()

        def guard(c):
            assert_test_identity(c)
            assert sql(c, 'SELECT version_num FROM public.alembic_version').scalar_one() == '0003_auth'
            c.rollback()

        engine = anchor.engine
        env = CredentialEnvironment(settings, engine)
        event.listen(engine, 'engine_connect', guard)
        event.listen(engine, 'after_cursor_execute', env.track)
        event.listen(engine, 'handle_error', env.record_error)
        try:
            yield env
        finally:
            try:
                env.check()
            finally:
                event.remove(engine, 'handle_error', env.record_error)
                event.remove(engine, 'after_cursor_execute', env.track)
                event.remove(engine, 'engine_connect', guard)


@pytest.fixture
def password():
    # Ephemeral test-only password, never a stored literal, argument or report.
    return secrets.token_urlsafe(32)
