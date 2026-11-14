"""Pure guard tests: never open a database connection."""
import pytest
from test_support.database import TestDatabaseSettings, assert_test_identity


@pytest.mark.parametrize('override', [
    {'confirmed': False}, {'host': 'localhost'}, {'host': 'example.com'},
    {'database': 'merge_dev'}, {'database': 'postgres'}, {'port': 5433},
    {'user': 'postgres'},
])
def test_test_target_rejected(override):
    values = {'confirmed': True, **override}
    with pytest.raises(ValueError):
        TestDatabaseSettings(**values).url()


def test_explicit_target_and_secret_repr(monkeypatch):
    monkeypatch.setenv('MERGE_DB_NAME', 'merge_dev')
    settings = TestDatabaseSettings(confirmed=True, password='synthetic-only')
    assert settings.url().database == 'merge_test'
    assert 'synthetic-only' not in repr(settings)


class FakeConnection:
    def __init__(self, database='merge_test', isolation='READ COMMITTED'):
        self.database = database
        self.isolation = isolation

    def execute(self, statement):
        return self

    def one(self):
        return (self.database, 'merge_app', '127.0.0.1', 5432)

    def get_isolation_level(self):
        return self.isolation


def test_actual_identity_is_checked():
    assert_test_identity(FakeConnection())
    with pytest.raises(ValueError):
        assert_test_identity(FakeConnection(database='merge_dev'))
    with pytest.raises(ValueError):
        assert_test_identity(FakeConnection(isolation='REPEATABLE READ'))


def test_dedicated_migration_graph_uses_original_versions():
    from pathlib import Path
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    root = Path(__file__).resolve().parents[1]
    config = Config()
    config.set_main_option('path_separator', 'os')
    config.set_main_option('script_location', str(root / 'test_alembic'))
    config.set_main_option('version_locations', str(root / 'alembic' / 'versions'))
    scripts = ScriptDirectory.from_config(config)
    # Source discovery must see the owner-requested UNAPPLIED migration. This
    # is not an execution target: explicit guarded allowlists stay frozen below.
    assert scripts.get_current_head() == '0006_profiles'
    assert scripts.get_revision('0002_domain').down_revision == '0001_baseline'
    assert scripts.get_revision('0003_auth').down_revision == '0002_domain'
    assert scripts.get_revision('0004_admission').down_revision == '0003_auth'
    assert scripts.get_revision('0005_invitations').down_revision == '0004_admission'
    assert scripts.get_revision('0006_profiles').down_revision == '0005_invitations'
    from test_support.revisions import TARGET_REVISIONS, validate_migration_start
    assert TARGET_REVISIONS == ('0002_domain','0003_auth','0004_admission','0005_invitations')
    for target in ('0006_profiles','head'):
        with pytest.raises(ValueError, match='Unsupported explicit test migration target'):
            validate_migration_start(['0005_invitations'],target)
