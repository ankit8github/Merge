"""Guarded retained throttle fixtures. Collection opens no database."""
import secrets
from threading import Lock

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretBytes
from sqlalchemy import event

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from session_tests.conftest import environment, account
from app.auth import AuthServices, get_services
from app.main import create_app
from app.security.auth_policy import AuthSettings
from app.services.throttling import ThrottlePolicy, ThrottleService
from test_support.races import sql

ORIGIN = 'https://merge.example'


class ThrottleEnvironment:
    def __init__(self, env):
        self.env = env
        self.secret = SecretBytes(secrets.token_bytes(32))
        self.keys = set()
        self.mutex = Lock()

    def service(self, policy=None):
        return ThrottleService(self.env.engine, secret=self.secret,
                               policy=policy or ThrottlePolicy(window_seconds=3600))

    def track(self, c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.auth_throttle_buckets' in statement:
            values = context.compiled_parameters[0]
            with self.mutex:
                self.keys.add((values['scope'], values['key']))

    def rows(self):
        found = []
        with self.env.connection() as c:
            sql(c, 'SET TRANSACTION READ ONLY')
            assert sql(c, 'SELECT version_num FROM public.alembic_version').scalar_one() == '0003_auth'
            for scope, key in list(self.keys):
                found.extend(sql(c, '''SELECT scope,key_hash,attempts,window_start,expires_at
                    FROM public.auth_throttle_buckets WHERE scope=:scope AND key_hash=:key''', scope=scope, key=key).all())
        return found

    def client(self, policy=None, ip='192.0.2.1'):
        selected = policy or ThrottlePolicy(window_seconds=3600)
        settings = AuthSettings(origin=ORIGIN, throttle_secret=self.secret.get_secret_value().hex(),
            throttle_window_seconds=selected.window_seconds, login_account_limit=selected.login_account,
            login_ip_limit=selected.login_ip, register_ip_limit=selected.register_ip)
        app = create_app(settings)
        services = AuthServices(self.env.service, self.env.sessions, self.service(selected))
        app.dependency_overrides[get_services] = lambda: services
        return TestClient(app, base_url=ORIGIN, client=(ip, 50000))


@pytest.fixture
def throttle(environment):
    fixture = ThrottleEnvironment(environment)
    event.listen(environment.engine, 'after_cursor_execute', fixture.track)
    try:
        yield fixture
    finally:
        try:
            for row in fixture.rows():
                assert row.scope in ('auth:v1:login_ip', 'auth:v1:login_account', 'auth:v1:register_ip')
                assert len(row.key_hash) == 32 and 1 <= row.attempts <= 501
                assert 0 < (row.expires_at-row.window_start).total_seconds() <= 3600
            print('Fresh throttle committed-state invariants verified; fixtures retained')
        finally:
            event.remove(environment.engine, 'after_cursor_execute', fixture.track)
