"""Reuse isolated fixture/scheduling infrastructure; verify every service connection."""
from concurrency_tests.conftest import db, pytest_addoption, pytest_generate_tests
import pytest
from sqlalchemy import event

from app.services.teams import TeamService
from test_support.database import assert_test_identity


@pytest.fixture
def service(db):
    with db.connection() as anchor:
        engine = anchor.engine

        def guard(connection):
            assert_test_identity(connection)
            connection.rollback()

        event.listen(engine, 'engine_connect', guard)
        try:
            yield TeamService(engine)
        finally:
            event.remove(engine, 'engine_connect', guard)
