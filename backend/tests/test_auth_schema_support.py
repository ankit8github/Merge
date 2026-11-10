"""Auth metadata/offline migration and explicit target tests; no database access."""
from contextlib import contextmanager
import importlib.util
import inspect
import io
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy import MetaData
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

import app.models
from app.db.base import Base
from app.models import AccountCredential, AuthSession, AuthThrottleBucket
from test_support import database, concurrency
from test_support.revisions import AUTH_REVISION, DOMAIN_REVISION, validate_migration_start


def migration():
    path = Path(__file__).resolve().parents[1] / 'alembic' / 'versions' / '0003_auth.py'
    spec = importlib.util.spec_from_file_location('auth_revision', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_auth_metadata_has_explicit_names_and_no_raw_token_column():
    configure_mappers()
    assert AuthSession.__table__.c.token_hash.primary_key
    assert not {'token', 'raw_token', 'password'} & set(AuthSession.__table__.c.keys())
    assert {fk.target_fullname for fk in AuthSession.__table__.c.user_id.foreign_keys} == {'users.id', 'account_credentials.user_id'}
    assert {ix.name for ix in AuthSession.__table__.indexes} == {'ix_sessions_user', 'ix_sessions_expiry'}
    public_metadata = MetaData()
    for table in Base.metadata.tables.values():
        table.to_metadata(public_metadata, schema='public')
    for model in (AccountCredential, AuthSession, AuthThrottleBucket):
        assert all(constraint.name for constraint in model.__table__.constraints)
        assert 'public.' in str(CreateTable(public_metadata.tables['public.' + model.__tablename__]).compile(dialect=postgresql.dialect()))


def test_auth_migration_is_additive_frozen_and_offline_renderable():
    revision = migration()
    assert revision.revision == AUTH_REVISION and revision.down_revision == DOMAIN_REVISION
    assert 'app.models' not in Path(revision.__file__).read_text()
    stream = io.StringIO()
    context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': stream})
    with Operations.context(context):
        revision.upgrade()
    rendered = stream.getvalue()
    for table in ('account_credentials', 'auth_sessions', 'auth_throttle_buckets'):
        assert f'CREATE TABLE public.{table}' in rendered
        assert f'TRIGGER tr_{table}_no_truncate' in rendered
    assert 'SET search_path = pg_catalog, pg_temp' in rendered
    assert 'CREATE OR REPLACE' not in rendered and 'DROP TABLE' not in rendered
    with pytest.raises(RuntimeError, match='reviewed'):
        revision.downgrade()


@pytest.mark.parametrize(('start', 'target', 'accepted'), [
    ([], DOMAIN_REVISION, True), ([DOMAIN_REVISION], DOMAIN_REVISION, True),
    ([DOMAIN_REVISION], AUTH_REVISION, True), ([AUTH_REVISION], AUTH_REVISION, True),
    ([], AUTH_REVISION, False), ([AUTH_REVISION], DOMAIN_REVISION, False),
    (['unknown'], AUTH_REVISION, False), ([DOMAIN_REVISION, AUTH_REVISION], AUTH_REVISION, False),
    ([DOMAIN_REVISION], 'head', False),
])
def test_explicit_revision_transition_allowlist(start, target, accepted):
    if accepted:
        validate_migration_start(start, target)
    else:
        with pytest.raises(ValueError):
            validate_migration_start(start, target)


def test_legacy_target_default_is_preserved():
    assert inspect.signature(database.migrate).parameters['revision'].default == DOMAIN_REVISION
    assert inspect.signature(database.verify).parameters['revision'].default == DOMAIN_REVISION


@pytest.mark.parametrize('suite', ['auth', 'credentials', 'sessions', 'auth-api', 'throttles', 'idempotency', 'mutations', 'retries', 'reads', 'team-api'])
def test_auth_suite_requires_explicit_revision_before_credentials(monkeypatch, suite):
    monkeypatch.setattr('sys.argv', ['runner', '--confirm-merge-test', '--suite', suite])
    monkeypatch.setattr(concurrency, 'getpass', lambda *a: pytest.fail('Credential prompt reached'))
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 2


class MigrationConnection:
    def __init__(self, revision=DOMAIN_REVISION):
        self.revision = revision
        self.active = self.committed = self.rolled_back = False

    def execute(self, statement):
        query = str(statement)
        if 'current_database(), current_user' in query:
            return SimpleNamespace(one=lambda: ('merge_test', 'merge_app', '127.0.0.1', 5432))
        if 'has_database_privilege' in query:
            return SimpleNamespace(one=lambda: (True, True, True))
        if 'to_regclass' in query:
            return SimpleNamespace(scalar_one=lambda: True)
        if 'SELECT version_num' in query:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [self.revision]))

    def get_isolation_level(self):
        return 'READ COMMITTED'

    def rollback(self):
        self.active = False

    @contextmanager
    def begin(self):
        self.active = True
        try:
            yield
            self.committed = True
        except Exception:
            self.rolled_back = True
            raise
        finally:
            self.active = False


@pytest.mark.parametrize('preserved', [True, False])
def test_auth_runner_owns_atomic_migration_and_preservation_check(monkeypatch, preserved):
    c = MigrationConnection()
    calls = []
    snapshots = iter([{'users': (5, 'before')}, {'users': (5, 'before' if preserved else 'after')}])
    monkeypatch.setattr(database, 'domain_snapshot', lambda connection: next(snapshots))

    def upgrade(config, target):
        assert c.active
        assert config.attributes['merge_test_connection'] is c
        calls.append(target)

    monkeypatch.setattr(database.command, 'upgrade', upgrade)
    if preserved:
        database.migrate(c, revision=AUTH_REVISION)
        assert c.committed
    else:
        with pytest.raises(ValueError, match='rolling back'):
            database.migrate(c, revision=AUTH_REVISION)
        assert c.rolled_back and not c.committed
    assert calls == [AUTH_REVISION]


def test_legacy_runner_refuses_auth_database_without_revision_opt_in(monkeypatch):
    c = MigrationConnection(revision=AUTH_REVISION)
    monkeypatch.setattr(database.command, 'upgrade', lambda *a: pytest.fail('Upgrade reached'))
    with pytest.raises(ValueError):
        database.migrate(c)


@pytest.mark.parametrize(('actual', 'requested', 'accepted'), [
    (DOMAIN_REVISION, DOMAIN_REVISION, True),
    (AUTH_REVISION, AUTH_REVISION, True),
    (AUTH_REVISION, DOMAIN_REVISION, False),
    (DOMAIN_REVISION, AUTH_REVISION, False),
    ('unknown', AUTH_REVISION, False),
])
def test_verification_requires_exact_explicit_recorded_revision(actual, requested, accepted):
    c = MigrationConnection(revision=actual)
    if accepted:
        database.verify(c, revision=requested)
    else:
        with pytest.raises(database.DiagnosticFailure, match='migration-state'):
            database.verify(c, revision=requested)
