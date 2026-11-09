"""Rollback-only auth schema fixtures on the explicit guarded target."""
from uuid import uuid4

import pytest
from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from test_support.database import test_connection
from test_support.races import sql


@pytest.fixture
def connection(request, repetition):
    settings = getattr(request.config, '_merge_concurrency_settings', None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded runner --suite auth --revision 0003_auth; no connection opened', pytrace=False)
    with test_connection(settings) as c:
        assert sql(c, 'SELECT version_num FROM public.alembic_version').scalar_one() == '0003_auth'
        c.rollback()
        transaction = c.begin()
        try:
            yield c
        finally:
            if transaction.is_active:
                transaction.rollback()
            c.rollback()


@pytest.fixture
def user(connection):
    identity = uuid4()
    sql(connection, "INSERT INTO public.users(id,display_name) VALUES (:id,'auth-schema-test')", id=identity)
    return identity
