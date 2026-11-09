"""Guarded, retained session fixtures. Collection never opens PostgreSQL."""
import secrets

import pytest
from sqlalchemy import event

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from credential_tests.conftest import CredentialEnvironment
from app.services.sessions import SessionService
from test_support.database import assert_test_identity, test_connection
from test_support.races import sql


class SessionEnvironment(CredentialEnvironment):
    def __init__(self, settings, engine):
        super().__init__(settings, engine)
        self.sessions = SessionService(engine)
        self.session_digests = set()

    def track_session(self, c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.auth_sessions' in statement:
            with self.mutex:
                self.session_digests.add(context.compiled_parameters[0]['digest'])

    def session_count(self):
        with self.connection() as c:
            sql(c, 'SET TRANSACTION READ ONLY')
            return sql(c, 'SELECT count(*) FROM public.auth_sessions WHERE user_id=ANY(:ids)', ids=list(self.ids)).scalar_one()

    def check(self):
        with self.connection() as c:
            sql(c, 'SET TRANSACTION READ ONLY')
            assert sql(c, 'SELECT version_num FROM public.alembic_version').scalar_one() == '0003_auth'
            ids = list(self.ids)
            if ids:
                assert sql(c, '''SELECT count(*) FROM public.auth_sessions s
                    LEFT JOIN public.users u ON u.id=s.user_id
                    LEFT JOIN public.account_credentials a ON a.user_id=s.user_id
                    WHERE s.user_id=ANY(:ids) AND (u.id IS NULL OR a.user_id IS NULL
                        OR octet_length(s.token_hash)<>32 OR octet_length(s.csrf_token)<>32
                        OR s.expires_at<>s.created_at+interval '8 hours'
                        OR s.revoked_at<s.created_at)''', ids=ids).scalar_one() == 0
                assert sql(c, 'SELECT count(*) FROM public.memberships WHERE user_id=ANY(:ids)', ids=ids).scalar_one() == 0
        print('Fresh session committed-state invariants verified; fixtures retained')


@pytest.fixture
def environment(request, repetition):
    settings = getattr(request.config, '_merge_concurrency_settings', None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded --suite sessions --revision 0003_auth; no database opened', pytrace=False)
    with test_connection(settings) as anchor:
        assert sql(anchor, 'SELECT version_num FROM public.alembic_version').scalar_one() == '0003_auth'
        anchor.rollback()

        def guard(c):
            assert_test_identity(c)
            assert sql(c, 'SELECT version_num FROM public.alembic_version').scalar_one() == '0003_auth'
            c.rollback()

        engine = anchor.engine
        env = SessionEnvironment(settings, engine)
        listeners = [('engine_connect', guard), ('after_cursor_execute', env.track),
                     ('after_cursor_execute', env.track_session)]
        for label, listener in listeners:
            event.listen(engine, label, listener)
        try:
            yield env
        finally:
            try:
                env.check()
            finally:
                for label, listener in reversed(listeners):
                    event.remove(engine, label, listener)


@pytest.fixture
def account(environment):
    password = secrets.token_urlsafe(32)
    identity = environment.service.register(username=environment.username(), password=password)
    return identity, password
