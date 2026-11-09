"""Guarded real HTTP/service dependencies. No development Settings or cleanup."""
import pytest
from fastapi.testclient import TestClient

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from session_tests.conftest import environment, account
from app.auth import AuthServices, get_services
from app.main import create_app
from app.security.auth_policy import AuthSettings

ORIGIN = 'https://merge.example'


@pytest.fixture
def client(environment):
    # environment checks explicit opt-in, actual identity/revision on each
    # connection, and fresh scoped committed invariants after each case.
    app = create_app(AuthSettings(origin=ORIGIN))
    services = AuthServices(environment.service, environment.sessions)
    app.dependency_overrides[get_services] = lambda: services
    with TestClient(app, base_url=ORIGIN) as client:
        yield client
    assert app.state.auth_engine is None, 'Ordinary runtime engine was initialized'
