"""Offline credential handoff and fixed-profile safety; no real DB sockets."""
import getpass
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import psycopg
import pytest

from release_support import profile_inspection as inspection


SECRET = 'synthetic-handoff-only'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for name in ('MERGE_RELEASE_DB_PASSWORD', 'PGPASSWORD'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(socket, 'socket', Mock(side_effect=AssertionError('Network forbidden')))
    monkeypatch.setattr(inspection.psycopg, 'connect', Mock(side_effect=AssertionError('Database forbidden')))
    monkeypatch.setattr(inspection, 'source', lambda: {'head': 'offline', 'files': {}})


def report(capsys):
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err
    return json.loads(captured.out)


def run():
    return inspection.main(['--confirm-profile-test'])


@pytest.mark.parametrize('name', ['MERGE_RELEASE_DB_PASSWORD', 'PGPASSWORD'])
def test_existing_process_password_skips_prompt(name, monkeypatch):
    monkeypatch.setenv(name, SECRET)
    prompt = Mock(side_effect=AssertionError('Unexpected prompt'))
    monkeypatch.setattr(inspection.getpass, 'getpass', prompt)
    assert inspection.acquire_password() == SECRET
    prompt.assert_not_called()


def test_release_password_has_precedence(monkeypatch):
    monkeypatch.setenv('MERGE_RELEASE_DB_PASSWORD', SECRET)
    monkeypatch.setenv('PGPASSWORD', 'other-synthetic-value')
    assert inspection.acquire_password() == SECRET


def test_missing_process_password_uses_hidden_prompt_without_persistence(monkeypatch, capsys):
    before = dict(os.environ)
    prompt = Mock(return_value=SECRET)
    monkeypatch.setattr(inspection.getpass, 'getpass', prompt)
    assert inspection.acquire_password() == SECRET
    prompt.assert_called_once_with('Existing merge_app password (hidden): ')
    assert set(os.environ) == set(before)
    assert all(os.environ[name] == value for name, value in before.items())
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


@pytest.mark.parametrize('failure', ['empty', 'eof', 'cancel', 'echo_fallback'])
def test_missing_or_unsafe_interactive_input_stops_before_connection(failure, monkeypatch, capsys):
    if failure == 'empty':
        prompt = Mock(return_value='')
    elif failure == 'eof':
        prompt = Mock(side_effect=EOFError(SECRET))
    elif failure == 'cancel':
        prompt = Mock(side_effect=KeyboardInterrupt(SECRET))
    else:
        # Exercises the real warning-before-echo fallback, not a synthetic warning.
        prompt = getpass.fallback_getpass
    monkeypatch.setattr(inspection.getpass, 'getpass', prompt)
    assert run() == 1
    data = report(capsys)
    assert data['failure']['stage'] == 'credential_preflight'
    assert data['connection_attempts'] == data['query_count'] == 0
    assert data['status'] == 'blocked'
    inspection.psycopg.connect.assert_not_called()


def test_authentication_failure_is_sanitized_and_never_retried(monkeypatch, capsys):
    monkeypatch.setattr(inspection.getpass, 'getpass', Mock(return_value=SECRET))
    connect = Mock(side_effect=psycopg.errors.InvalidPassword(SECRET))
    monkeypatch.setattr(inspection.psycopg, 'connect', connect)
    assert run() == 1
    data = report(capsys)
    connect.assert_called_once()
    assert data['failure'] == {'stage': 'connect', 'exception_class': 'InvalidPassword', 'sqlstate': '28P01'}
    assert data['connection_attempts'] == 1 and data['query_count'] == 0
    assert data['status'] == 'blocked'


@pytest.mark.parametrize('method', ['prompt', 'release_env', 'pg_env'])
def test_password_handoff_retains_readonly_connection_and_identity_guard(method, monkeypatch, capsys):
    if method == 'prompt':
        monkeypatch.setattr(inspection.getpass, 'getpass', Mock(return_value=SECRET))
    else:
        monkeypatch.setenv('MERGE_RELEASE_DB_PASSWORD' if method == 'release_env' else 'PGPASSWORD', SECRET)
        monkeypatch.setattr(inspection.getpass, 'getpass', Mock(side_effect=AssertionError('Unexpected prompt')))
    # An inherited libpq address must not redirect the explicitly fixed target.
    monkeypatch.setenv('PGHOSTADDR', '192.0.2.99')
    identity = dict(database='merge_dev', role='merge_app', session_role='merge_app', host='127.0.0.1', port=5432)
    connection = SimpleNamespace(autocommit=False, execute=Mock(return_value=SimpleNamespace(fetchall=lambda: [identity])), rollback=Mock(), close=Mock())
    connect = Mock(return_value=connection)
    monkeypatch.setattr(inspection.psycopg, 'connect', connect)
    before = dict(os.environ)
    assert run() == 1  # The identity guard rejects this fake wrong database.
    data = report(capsys)
    assert set(os.environ) == set(before)
    assert all(os.environ[name] == value for name, value in before.items())
    connect.assert_called_once()
    kwargs = connect.call_args.kwargs
    assert {k: kwargs[k] for k in ('host', 'hostaddr', 'port', 'dbname', 'user')} == dict(host='127.0.0.1', hostaddr='127.0.0.1', port=5432, dbname='merge_profile_test', user='merge_app')
    assert kwargs['password'] == SECRET
    assert kwargs['autocommit'] is False and kwargs['connect_timeout'] == 5
    assert kwargs['options'] == '-c default_transaction_read_only=on -c statement_timeout=15000 -c lock_timeout=5000 -c search_path=pg_catalog'
    assert connection.read_only is True
    assert connection.isolation_level == psycopg.IsolationLevel.REPEATABLE_READ
    assert data['checks']['actual_identity'] is False
    assert data['query_count'] == 1
    assert connection.execute.call_args.args[0].startswith('SELECT ')
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


@pytest.mark.parametrize('overrides', [
    {'dbname': 'merge_dev'}, {'dbname': 'merge_test'}, {'host': 'localhost'},
    {'host': '192.0.2.99'}, {'port': 5433}, {'user': 'postgres'},
])
def test_invalid_target_rejected_before_password_or_connection(overrides, monkeypatch, capsys):
    monkeypatch.setattr(inspection, 'TARGET', inspection.TARGET | overrides)
    prompt = Mock(side_effect=AssertionError('Prompt before fixed target check'))
    monkeypatch.setattr(inspection.getpass, 'getpass', prompt)
    assert run() == 1
    data = report(capsys)
    assert data['checks']['fixed_profile_target'] is False
    assert data['connection_attempts'] == data['query_count'] == 0
    prompt.assert_not_called()
    inspection.psycopg.connect.assert_not_called()


def test_confirmation_required_before_prompt_or_connection(monkeypatch):
    prompt = Mock(side_effect=AssertionError('Unexpected prompt'))
    monkeypatch.setattr(inspection.getpass, 'getpass', prompt)
    with pytest.raises(SystemExit) as exit_info:
        inspection.main([])
    assert exit_info.value.code == 2
    prompt.assert_not_called()
    inspection.psycopg.connect.assert_not_called()


@pytest.mark.parametrize('failure', ['superuser', 'membership', 'transaction_mode', 'timeout'])
def test_handoff_does_not_bypass_role_or_transaction_checks(failure, monkeypatch, capsys):
    monkeypatch.setattr(inspection.getpass, 'getpass', Mock(return_value=SECRET))
    identity = dict(database='merge_profile_test', role='merge_app', session_role='merge_app', host='127.0.0.1', port=5432,
                    read_only='on', default_read_only='on', isolation='repeatable read', statement_timeout='15s', lock_timeout='5s')
    role = dict(rolcanlogin=True, rolsuper=False, rolcreatedb=False, rolcreaterole=False, rolreplication=False, rolbypassrls=False)
    members = []
    if failure == 'superuser':
        role['rolsuper'] = True
    elif failure == 'membership':
        members = [{'parent_role': 'unexpected'}]
    elif failure == 'transaction_mode':
        identity['read_only'] = 'off'
    else:
        identity['statement_timeout'] = '0'
    responses = iter([[identity], [role], members])
    def execute(query, params):
        assert query.startswith('SELECT ')
        rows = next(responses)
        return SimpleNamespace(fetchall=lambda: rows)
    connection = SimpleNamespace(autocommit=False, execute=Mock(side_effect=execute), rollback=Mock(), close=Mock())
    monkeypatch.setattr(inspection.psycopg, 'connect', Mock(return_value=connection))
    assert run() == 1
    data = report(capsys)
    guard = 'restricted_readonly_transaction' if failure in ('transaction_mode', 'timeout') else 'unprivileged_login_role'
    assert data['checks'][guard] is False
    assert data['status'] == 'blocked'
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


def test_echo_fallback_is_fatal_in_a_separate_process():
    # No network import or database attempt: only the credential helper executes.
    script = '''import getpass
import release_support.profile_inspection as p
p.getpass.getpass = getpass.fallback_getpass
try:
    p.acquire_password()
except getpass.GetPassWarning:
    raise SystemExit(0)
raise SystemExit(9)
'''
    env = {k: v for k, v in os.environ.items() if k not in ('MERGE_RELEASE_DB_PASSWORD', 'PGPASSWORD')}
    result = subprocess.run([sys.executable, '-B', '-c', script], cwd=Path(inspection.__file__).resolve().parents[1], env=env, input='must-never-be-read\n', text=True, capture_output=True, timeout=10)
    assert result.returncode == 0
    assert result.stdout == result.stderr == ''
