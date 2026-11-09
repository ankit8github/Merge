"""Guarded real HTTP/service dependencies. No development Settings or cleanup."""
import pytest
import secrets
from fastapi.testclient import TestClient
from pydantic import SecretBytes

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from session_tests.conftest import environment, account
from app.auth import AuthServices, get_services
from app.main import create_app
from app.security.auth_policy import AuthSettings
from app.services.throttling import ThrottlePolicy, ThrottleService

ORIGIN = 'https://merge.example'


@pytest.fixture
def client(environment):
    # environment checks explicit opt-in, actual identity/revision on each
    # connection, and fresh scoped committed invariants after each case.
    key = secrets.token_bytes(32)  # Isolate retained regression fixtures, never runtime fallback.
    app = create_app(AuthSettings(origin=ORIGIN, throttle_secret=key.hex()))
    services = AuthServices(environment.service, environment.sessions,
                           ThrottleService(environment.engine, secret=SecretBytes(key), policy=ThrottlePolicy()))
    app.dependency_overrides[get_services] = lambda: services
    with TestClient(app, base_url=ORIGIN, client=('192.0.2.1', 50000)) as client:
        yield client
    assert app.state.auth_engine is None, 'Ordinary runtime engine was initialized'
