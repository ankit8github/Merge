"""Credential-free diagnostic tests; no real engine or database connection."""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from test_support import database as db


@pytest.mark.parametrize(('state', 'expected'), [
    ('28P01', 'authentication'), ('28000', 'authentication'),
    ('08001', 'connection'), ('42501', 'permission'),
    ('42P01', 'migration-state'), (None, 'migration-state'),
])
def test_error_classification_never_formats_exception(state, expected):
    error = RuntimeError('synthetic-secret postgresql://sensitive')
    error.orig = SimpleNamespace(sqlstate=state)
    message = db.safe_failure_message(error, 'migration-state')
    assert f'[{expected}]' in message
    assert 'synthetic-secret' not in message
    assert 'postgresql://' not in message


def test_missing_driver_and_untrusted_labels_are_sanitized():
    assert '[driver-configuration]' in db.safe_failure_message(ImportError('sensitive'), 'connection')
    assert '[verification]' in db.safe_failure_message(db.DiagnosticFailure('sensitive'), 'sensitive')


class PreMigrationConnection:
    def __init__(self, permissions=(True, True, True), revision_exists=False):
        self.permissions = permissions
        self.revision_exists = revision_exists
        self.queries = []
        self.rolled_back = False

    def execute(self, statement):
        query = str(statement)
        self.queries.append(query)
        if 'current_database(), current_user' in query:
            return SimpleNamespace(one=lambda: ('merge_test', 'merge_app', '127.0.0.1', 5432))
        if 'has_database_privilege' in query:
            return SimpleNamespace(one=lambda: self.permissions)
        if 'to_regclass' in query:
            return SimpleNamespace(scalar_one=lambda: self.revision_exists)
        if 'SELECT version_num' in query:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: ['unexpected']))

    def get_isolation_level(self):
        return 'READ COMMITTED'

    def rollback(self):
        self.rolled_back = True


def test_verify_works_before_first_migration(capsys):
    connection = PreMigrationConnection()
    db.verify(connection)
    assert 'base (no recorded revision)' in capsys.readouterr().out
    assert not any('SELECT version_num' in q for q in connection.queries)
    assert connection.queries[0] == 'SET TRANSACTION READ ONLY'
    assert connection.rolled_back


def test_permission_and_migration_state_have_separate_categories():
    with pytest.raises(db.DiagnosticFailure, match='^permission$'):
        db.verify(PreMigrationConnection(permissions=(True, False, True)))
    with pytest.raises(db.DiagnosticFailure, match='^migration-state$'):
        db.verify(PreMigrationConnection(revision_exists=True))


def test_url_preserves_special_characters_without_manual_encoding():
    password = 'synthetic@:/?#% value'
    url = db.TestDatabaseSettings(confirmed=True, password=password).url()
    assert url.password == password
    assert url.database == 'merge_test'


def test_cli_suppresses_raw_connection_failure(monkeypatch, capsys):
    monkeypatch.setenv('MERGE_TEST_DB_PASSWORD', 'synthetic-only')
    monkeypatch.setattr('sys.argv', ['database', 'verify', '--confirm-merge-test'])

    @contextmanager
    def failed_connection(settings):
        error = RuntimeError('synthetic-only postgresql://sensitive')
        error.orig = SimpleNamespace(sqlstate='28P01')
        raise error
        yield  # Keep this a context manager without creating any connection.

    monkeypatch.setattr(db, 'test_connection', failed_connection)
    with pytest.raises(SystemExit) as result:
        db.main()
    assert result.value.code == 1
    output = capsys.readouterr()
    assert '[authentication]' in output.out
    assert 'synthetic-only' not in output.out + output.err
    assert 'postgresql://' not in output.out + output.err
