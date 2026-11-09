"""Database-free checks; never import development settings or open a database."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_support import concurrency
from test_support.database import TestDatabaseSettings
from test_support.races import Outcome, RaceDatabase, database_error, workers


def test_worker_results_are_ordered_and_errors_are_sanitized(capsys):
    assert workers([lambda: Outcome('committed'), lambda: Outcome('rolled-back')]) == [Outcome('committed'), Outcome('rolled-back')]

    def fail():
        raise RuntimeError('synthetic-secret postgresql://sensitive')

    with pytest.raises(AssertionError, match='infrastructure'):
        workers([fail])
    output = capsys.readouterr().out
    assert 'synthetic-secret' not in output and 'postgresql://' not in output


def test_database_error_output_is_metadata_only():
    error = SimpleNamespace(orig=SimpleNamespace(sqlstate='40P01', diag=SimpleNamespace(constraint_name=None)))
    assert database_error(error) == Outcome('rejected', '40P01')
    error.orig.sqlstate = 'sensitive-value'
    error.orig.diag.constraint_name = 'postgresql://sensitive'
    assert database_error(error) == Outcome('rejected', 'UNKNOWN')


def test_runner_rejects_missing_opt_in_before_credentials(monkeypatch):
    monkeypatch.setattr('sys.argv', ['concurrency'])
    monkeypatch.setattr(concurrency, 'getpass', lambda *a: pytest.fail('Password prompt reached'))
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 2


@pytest.mark.parametrize('value', [None, ''])
def test_runner_fails_closed_without_private_credential(monkeypatch, value):
    monkeypatch.setattr('sys.argv', ['concurrency', '--confirm-merge-test'])
    if value is None:
        monkeypatch.delenv('MERGE_TEST_DB_PASSWORD', raising=False)
    else:
        monkeypatch.setenv('MERGE_TEST_DB_PASSWORD', value)
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    monkeypatch.setattr(concurrency, 'test_connection', lambda *a: pytest.fail('Connection attempted'))
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 2


def test_race_connections_reuse_only_guarded_test_helper(monkeypatch):
    from test_support import races
    settings = TestDatabaseSettings(confirmed=True, password='synthetic-only')
    calls = []

    @contextmanager
    def fake_connection(received):
        calls.append(received)
        yield 'guarded'

    monkeypatch.setattr(races, 'test_connection', fake_connection)
    database = RaceDatabase(settings)
    with database.connection() as connection:
        assert connection == 'guarded'
    assert calls == [settings]


@pytest.mark.parametrize(('suite', 'expected'), [(None, 'concurrency_tests'), ('services', 'service_tests'), ('auth', 'auth_schema_tests'), ('credentials', 'credential_tests'), ('sessions', 'session_tests')])
def test_runner_has_fixed_suite_and_safe_pytest_options(monkeypatch, suite, expected):
    arguments = ['concurrency', '--confirm-merge-test', '--repetitions', '2']
    if suite is not None:
        arguments += ['--suite', suite]
    revision = '0003_auth' if suite in ('auth', 'credentials', 'sessions') else '0002_domain'
    if suite in ('auth', 'credentials', 'sessions'):
        arguments += ['--revision', revision]
    monkeypatch.setattr('sys.argv', arguments)
    monkeypatch.setenv('MERGE_TEST_DB_PASSWORD', 'synthetic-only')
    for name in ('PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'):
        monkeypatch.setenv(name, '')

    @contextmanager
    def fake_connection(settings):
        assert settings.database == 'merge_test' and settings.confirmed
        class Connection:
            def execute(self, statement):
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [revision]))
        yield Connection()

    def fake_pytest(arguments, plugins):
        assert Path(arguments[0]).name == expected
        assert '--tb=no' in arguments and '--assert=plain' in arguments and '-x' in arguments
        assert '--confirm-merge-test' in arguments and '--race-repetitions=2' in arguments
        assert 'synthetic-only' not in ' '.join(arguments)
        assert plugins[0].settings.database == 'merge_test'
        return 0

    monkeypatch.setattr(concurrency, 'test_connection', fake_connection)
    monkeypatch.setattr(concurrency.pytest, 'main', fake_pytest)
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 0
