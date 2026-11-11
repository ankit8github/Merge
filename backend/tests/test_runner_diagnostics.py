"""Real installed pytest reporting with synthetic inputs; no PostgreSQL access."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from test_support import concurrency
from test_support.diagnostics import Diagnostics


CANARY = 'PRIVATE_DIAGNOSTIC_CANARY'
ROOT = Path(__file__).resolve().parents[1]


def run_synthetic(tmp_path, source):
    suite = tmp_path / 'admission_tests'
    suite.mkdir()
    (suite / 'test_safe.py').write_text(source, encoding='utf-8')
    script = '''
from pathlib import Path
from test_support.diagnostics import Diagnostics
d = Diagnostics(Path.cwd(), 'admission', '0004_admission', 3)
try:
    code = d.run_pytest(['admission_tests', '-q', '-x', '--tb=no', '--assert=plain',
        '-s', '--show-capture=no', '-rN', '--disable-warnings',
        '-p', 'no:cacheprovider', '-o', 'addopts=', '-o', 'log_cli=false',
        '-o', 'log_file=' + __import__('os').devnull], [d])
except KeyboardInterrupt:
    code = 2
    d.data['status'] = 'interrupted'
d.finish(code)
__import__('os').write(1, b'FD_STDOUT_RESTORED')
__import__('os').write(2, b'FD_STDERR_RESTORED')
'''
    env = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}
    env.pop('PYTEST_ADDOPTS', None)
    env.pop('PYTEST_PLUGINS', None)
    result = subprocess.run([sys.executable, '-c', script], cwd=tmp_path, env=env,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout == 'FD_STDOUT_RESTORED'
    assert result.stderr == 'FD_STDERR_RESTORED'
    reports = list((tmp_path / 'test-results' / 'guarded').glob('*.json'))
    assert len(reports) == 1
    text = reports[0].read_text(encoding='utf-8')
    assert CANARY not in text + result.stdout + result.stderr
    assert reports[0].stat().st_size < 16384
    return json.loads(text)


def test_real_pytest_success_after_fixture_teardown(tmp_path):
    report = run_synthetic(tmp_path, '''
import pytest
@pytest.fixture
def resource():
    yield
    assert True
def test_success(resource):
    assert True
''')
    assert report['status'] == 'passed' and report['exit_code'] == 0
    assert report['invariant_verification'] == 'suite_and_fixture_checks_completed'
    assert report['teardowns_completed'] == report['collected'] == 1


@pytest.mark.parametrize('phase', ['call', 'setup', 'teardown'])
def test_real_pytest_failure_phase_and_no_private_rendering(tmp_path, phase):
    statement = f"raise AssertionError('{CANARY} postgresql://private:password@host/db')"
    fixture = statement if phase == 'setup' else 'yield\n    ' + (statement if phase == 'teardown' else 'assert True')
    body = statement if phase == 'call' else 'assert True'
    report = run_synthetic(tmp_path, f'''
import logging, os, pytest, warnings
@pytest.fixture
def resource():
    {fixture}
def test_failure(resource):
    print('{CANARY} Cookie: session; X-CSRF-Token: secret')
    os.write(2, b'{CANARY} Authorization: Bearer secret')
    logging.error('{CANARY} SQL parameters/password')
    warnings.warn('{CANARY} auth-secret')
    {body}
def test_must_not_run():
    raise RuntimeError('fail-fast broken')
''')
    assert report['exit_code'] == 1 and report['status'] == 'failed'
    assert report['invariant_verification'] == 'not_certified'
    assert report['failures'] == [{
        'node_id': 'admission_tests/test_safe.py::test_failure',
        'phase': phase, 'category': 'assertion',
    }]
    assert report['teardowns_completed'] == 1  # No retry/second test.


def test_real_pytest_interrupt_is_uncertified(tmp_path):
    report = run_synthetic(tmp_path, f"def test_interrupt():\n    raise KeyboardInterrupt('{CANARY}')\n")
    assert report['exit_code'] == 2 and report['status'] == 'interrupted'
    assert report['invariant_verification'] == 'not_certified'
    assert report['active_node'] == 'admission_tests/test_safe.py::test_interrupt'


def test_real_collection_error_is_sanitized(tmp_path):
    report = run_synthetic(tmp_path, f"raise RuntimeError('{CANARY}')\n")
    assert report['exit_code'] != 0
    assert report['failures'][0]['category'] == 'collection_error'
    assert report['failures'][0]['node_id'] == 'admission_tests/test_safe.py'
    assert report['invariant_verification'] == 'not_certified'


def test_real_parameter_secrets_are_withheld(tmp_path):
    report = run_synthetic(tmp_path, f'''
import pytest
@pytest.mark.parametrize('value', [1], ids=['{CANARY}'])
def test_private_parameter(value):
    raise ValueError('{CANARY}')
''')
    assert report['failures'][0] == {
        'node_id': 'admission_tests/test_safe.py::test_private_parameter[parameter_id_withheld]',
        'phase': 'call', 'category': 'exception',
    }


def test_exact_reviewed_node_ids_and_rejected_paths():
    for node in (
        'team_api_tests/test_team_creation.py::test_real_deferred_commit_failure_is_not_success[0]',
        'admission_tests/test_admission.py::test_real_failure_rolls_back_or_reconciles_same_key[0-ambiguous-commit]',
    ):
        assert Diagnostics.node_id(node) == node
    assert Diagnostics.node_id('../private.py::test_secret') == 'node_withheld'
    assert Diagnostics.node_id('admission_tests/test_safe.py::test_ok\nsecret') == 'node_withheld'


def test_unique_bounded_files_and_initial_incomplete_state(tmp_path):
    reports = [Diagnostics(tmp_path, 'admission', '0004_admission', 3) for _ in range(2)]
    assert reports[0].path != reports[1].path
    assert json.loads(reports[0].path.read_text())['status'] == 'incomplete'
    assert json.loads(reports[0].path.read_text())['exit_code'] is None
    for _ in range(100):
        reports[0].failure('admission_tests/test_safe.py::test_failure', 'call', 'assertion')
    assert len(reports[0].data['failures']) == 16
    assert reports[0].path.stat().st_size < 16384


@pytest.mark.parametrize('transient', [True, False])
def test_atomic_rename_retry_is_bounded_and_preserves_evidence(tmp_path, monkeypatch, transient):
    report = Diagnostics(tmp_path, 'admission', '0004_admission', 3)
    original = Path.replace
    attempts = []
    def replace(path, target):
        attempts.append(target)
        if not transient or len(attempts) == 1:
            raise PermissionError(CANARY)
        return original(path, target)
    monkeypatch.setattr(Path, 'replace', replace)
    monkeypatch.setattr('test_support.diagnostics.time.sleep', lambda seconds: None)
    if transient:
        report.save()
        assert len(attempts) == 2
    else:
        with pytest.raises(PermissionError):
            report.save()
        assert len(attempts) == 4
    assert json.loads(report.path.read_text())['status'] == 'incomplete'


@pytest.fixture
def guarded_main(monkeypatch, tmp_path):
    monkeypatch.setattr(concurrency, 'Diagnostics', lambda *args: Diagnostics(tmp_path, *args[1:]))
    monkeypatch.setattr(sys, 'argv', ['runner', '--confirm-merge-test', '--suite', 'admission',
                                     '--revision', '0004_admission'])
    monkeypatch.setenv('MERGE_TEST_DB_PASSWORD', CANARY)
    @contextmanager
    def connection(settings):
        assert settings.database == 'merge_test' and settings.user == 'merge_app'
        yield SimpleNamespace(execute=lambda statement: SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: ['0004_admission'])))
    monkeypatch.setattr(concurrency, 'test_connection', connection)
    return tmp_path


@pytest.mark.parametrize('code', [0, 1, 2, 3, 4, 5])
def test_launcher_preserves_pytest_exit_codes(guarded_main, monkeypatch, capsys, code):
    def fake_pytest(arguments, plugins):
        assert '-x' in arguments and '--tb=no' in arguments
        assert '-s' in arguments and '--show-capture=no' in arguments
        assert '-p' in arguments and 'no:cacheprovider' in arguments
        print(CANARY)
        return code
    monkeypatch.setattr(concurrency.pytest, 'main', fake_pytest)
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == code
    assert CANARY not in capsys.readouterr().out


@pytest.mark.parametrize('code', [None, False, 'private', -1, 6])
def test_unexpected_pytest_result_cannot_exit_successfully(guarded_main, monkeypatch, code):
    monkeypatch.setattr(concurrency.pytest, 'main', lambda *a, **k: code)
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 1


def test_launcher_interrupt_preserves_failure(guarded_main, monkeypatch):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt(CANARY)
    monkeypatch.setattr(concurrency.pytest, 'main', interrupt)
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 2
    report = json.loads(next((guarded_main / 'test-results/guarded').glob('*.json')).read_text())
    assert report['status'] == 'interrupted'
    assert report['invariant_verification'] == 'not_certified'


def test_preflight_revision_failure_never_enters_pytest(guarded_main, monkeypatch):
    @contextmanager
    def wrong_revision(settings):
        yield SimpleNamespace(execute=lambda statement: SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: ['0003_auth'])))
    monkeypatch.setattr(concurrency, 'test_connection', wrong_revision)
    monkeypatch.setattr(concurrency.pytest, 'main', lambda *a, **k: pytest.fail('Pytest reached'))
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 2
    report = json.loads(next((guarded_main / 'test-results/guarded').glob('*.json')).read_text())
    assert report['stage'] == 'preflight' and report['status'] == 'failed'
    assert report['invariant_verification'] == 'not_certified'


def test_launcher_internal_exception_is_metadata_only(guarded_main, monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise RuntimeError(CANARY)
    monkeypatch.setattr(concurrency.pytest, 'main', fail)
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 1
    output = capsys.readouterr()
    assert CANARY not in output.out + output.err
    report = json.loads(next((guarded_main / 'test-results/guarded').glob('*.json')).read_text())
    assert report['status'] == 'internal_error'
    assert report['invariant_verification'] == 'not_certified'


def test_destination_redirect_is_rejected(tmp_path, monkeypatch):
    original = Path.resolve
    def resolve(path, *args, **kwargs):
        if path == tmp_path / 'test-results':
            return tmp_path / 'redirected'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'resolve', resolve)
    with pytest.raises(ValueError, match='Unsafe diagnostic destination'):
        Diagnostics(tmp_path, 'admission', '0004_admission', 3)


def test_diagnostic_creation_failure_precedes_credentials(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['runner', '--confirm-merge-test'])
    def fail(*args):
        raise OSError(CANARY)
    monkeypatch.setattr(concurrency, 'Diagnostics', fail)
    monkeypatch.setattr(concurrency, 'getpass', lambda *args: pytest.fail('Prompt reached'))
    monkeypatch.setattr(concurrency, 'test_connection', lambda *args: pytest.fail('DB reached'))
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == 1


@pytest.mark.parametrize('original_code', [0, 1, 2])
@pytest.mark.parametrize('error_type', [OSError, KeyboardInterrupt])
def test_finalization_error_never_converts_failure_to_success(guarded_main, monkeypatch, capsys, original_code, error_type):
    def fail(self, code):
        raise error_type(CANARY)
    monkeypatch.setattr(Diagnostics, 'finish', fail)
    monkeypatch.setattr(concurrency.pytest, 'main', lambda *a, **k: original_code)
    with pytest.raises(SystemExit) as result:
        concurrency.main()
    assert result.value.code == (original_code or 1)
    assert CANARY not in capsys.readouterr().out
    report = json.loads(next((guarded_main / 'test-results/guarded').glob('*.json')).read_text())
    assert report['status'] == 'diagnostics_incomplete'
    assert report['invariant_verification'] == 'not_certified'
