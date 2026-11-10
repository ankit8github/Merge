"""Guarded retained HTTP mutation fixtures; collection never connects."""
from threading import Lock
from uuid import uuid4
import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretBytes
from sqlalchemy import event

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from session_tests.conftest import account
from team_mutation_tests.conftest import MutationDatabase, revision
from app.auth import AuthServices, encode_token, get_services
from app.main import create_app
from app.read_api import get_read_service
from app.security.auth_policy import AuthSettings
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.team_reads import TeamReadService
from app.services.teams import TeamService
from app.services.throttling import ThrottlePolicy, ThrottleService
from app.team_api import get_team_service
from test_support.database import assert_test_identity
from test_support.races import sql

ORIGIN = 'https://merge.example'


class TeamApiEnvironment(MutationDatabase):
    def __init__(self, settings):
        super().__init__(settings)
        self.ids, self.mutex = set(), Lock()

    @staticmethod
    def username():
        return 'teamapi_' + uuid4().hex[:24]

    def track(self, c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.users' in statement:
            values = context.compiled_parameters[0]
            with self.mutex:
                self.ids.add(values.get('u') or values.get('id'))

    def check(self):
        self.check_chains()  # Fresh independently guarded domain/record observer.
        with self.connection() as c:
            sql(c, 'SET TRANSACTION READ ONLY')
            ids = list(self.ids)
            if ids:
                assert sql(c, '''SELECT count(*) FROM public.auth_sessions s
                    LEFT JOIN public.users u ON u.id=s.user_id
                    LEFT JOIN public.account_credentials a ON a.user_id=s.user_id
                    WHERE s.user_id=ANY(:ids) AND (u.id IS NULL OR a.user_id IS NULL
                      OR octet_length(s.token_hash)<>32 OR octet_length(s.csrf_token)<>32
                      OR s.expires_at<>s.created_at+interval '8 hours' OR s.revoked_at<s.created_at)''',
                    ids=ids).scalar_one() == 0
        print('Fresh HTTP team/account/session invariants verified; fixtures retained', flush=True)


@pytest.fixture
def environment(request, repetition):
    settings = getattr(request.config, '_merge_concurrency_settings', None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded --suite team-api --revision 0003_auth; no database opened', pytrace=False)
    env = TeamApiEnvironment(settings)
    with env.connection() as anchor:
        env.engine = anchor.engine
        def guard(c):
            assert c.connection.dbapi_connection.autocommit is False
            assert_test_identity(c)
            revision(c)
            c.rollback()
        event.listen(env.engine, 'engine_connect', guard)
        event.listen(env.engine, 'after_cursor_execute', env.track)
        env.service, env.sessions = CredentialService(env.engine), SessionService(env.engine)
        env.teams, env.reads = TeamService(env.engine), TeamReadService(env.engine)
        try:
            yield env
        finally:
            try:
                env.check()
            finally:
                event.remove(env.engine, 'after_cursor_execute', env.track)
                event.remove(env.engine, 'engine_connect', guard)


@pytest.fixture
def subject(environment):
    h, users, _ = environment.seed(maximum=3, teams=0)
    return h, users


@pytest.fixture
def client(environment):
    secret = secrets.token_bytes(32)
    app = create_app(AuthSettings(origin=ORIGIN, throttle_secret=secret.hex()))
    services = AuthServices(environment.service, environment.sessions,
        ThrottleService(environment.engine, secret=SecretBytes(secret), policy=ThrottlePolicy()))
    # Every database dependency is replaced; no ordinary Settings/Engine fallback.
    app.dependency_overrides[get_services] = lambda: services
    app.dependency_overrides[get_read_service] = lambda: environment.reads
    app.dependency_overrides[get_team_service] = lambda: environment.teams
    with TestClient(app, base_url=ORIGIN, client=('192.0.2.1', 50000)) as client:
        yield client
    assert app.state.auth_engine is None, 'Ordinary runtime database was initialized'


@pytest.fixture
def authorized(client, environment, account):
    issued = environment.sessions.login(username=account[0].username, password=account[1])
    client.cookies.set('__Host-merge_session', encode_token(issued.session_token.get_secret_value()))
    return client, issued
