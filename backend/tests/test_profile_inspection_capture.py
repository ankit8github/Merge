"""Offline capture persistence and integrity; synthetic reports, no DB/worker run."""
from copy import deepcopy
import ast
import json
from pathlib import Path
import runpy
import socket
import subprocess
from unittest.mock import Mock

import pytest

from release_support import profile_inspection as worker
from release_support import profile_inspection_capture as capture


SECRET = 'synthetic-never-save-this-value'


@pytest.fixture
def offline(tmp_path, monkeypatch):
    (tmp_path / 'backend/test-results').mkdir(parents=True)
    monkeypatch.setattr(capture, 'ROOT', tmp_path)
    monkeypatch.setattr(socket, 'socket', Mock(side_effect=AssertionError('Network forbidden')))
    monkeypatch.setattr(worker.psycopg, 'connect', Mock(side_effect=AssertionError('Database forbidden')))
    manifest = dict(head='a' * 40, files={
        'backend/release_support/profile_inspection.py': capture.digest(Path(worker.__file__)),
        'backend/release_support/profile_inspection_capture.py': capture.digest(Path(capture.__file__)),
    })
    monkeypatch.setattr(worker, 'source', lambda: deepcopy(manifest))
    observed = {key: [] for key in capture.OBSERVED}
    for key in ('columns', 'constraints', 'indexes', 'triggers', 'internal_triggers', 'relations',
                'functions', 'types', 'database_acl', 'schema_acl', 'relation_acl'):
        observed[key] = [{'definition': 'synthetic inventory requiring independent review'}]
    data = dict(schema_version=1, kind='profile_0005_readonly_inspection', started_at='offline',
                completed_at='offline', target=worker.TARGET.copy(), source=manifest,
                collector_sha256=manifest['files']['backend/release_support/profile_inspection.py'],
                checks={key: True for key in capture.CHECKS}, observed=observed,
                query_count=31, connection_attempts=1, status='snapshot_complete_requires_definition_review',
                stage='snapshot_complete', expected_ddl=[], exit_intent=0)
    calls = []
    class Process:
        returncode = 0
        output = None
        timeout = False
        def communicate(self, timeout=None):
            if self.timeout:
                self.timeout = False
                raise subprocess.TimeoutExpired('synthetic worker', 600)
            return self.output if self.output is not None else json.dumps(data).encode(), SECRET.encode()
        def kill(self):
            self.returncode = -9
    process = Process()
    def popen(command, **kwargs):
        calls.append((command, kwargs))
        return process
    monkeypatch.setattr(capture.subprocess, 'Popen', popen)
    return tmp_path, manifest, data, process, calls


def directory(root):
    paths = list((root / 'backend/test-results').iterdir())
    assert len(paths) == 1
    return paths[0]


def saved(path, name):
    return json.loads((path / name).read_text())


def test_success_retains_snapshot_native_exit_source_and_hashes(offline, capsys):
    root, manifest, data, process, calls = offline
    assert capture.main(['--confirm-profile-test']) == 0
    path = directory(root)
    assert set(p.name for p in path.iterdir()) == {'started.json', 'source-manifest.json', 'database-snapshot.json', 'process-receipt.json'}
    assert saved(path, 'database-snapshot.json') == data
    receipt = saved(path, 'process-receipt.json')
    assert receipt['native_exit_code'] == process.returncode == 0
    assert receipt['snapshot_sha256'] == capture.digest(path / 'database-snapshot.json')
    assert receipt['source_manifest_sha256'] == capture.digest(path / 'source-manifest.json')
    assert receipt['source_unchanged'] is True
    assert capture.validate_capture(path, manifest) == capture.REVIEW_REQUIRED
    assert receipt['final_certified'] is False and receipt['definition_review_required'] is True
    assert len(calls) == 1 and calls[0][1]['stdin'] is None
    assert SECRET not in repr(calls)
    for item in path.iterdir():
        assert SECRET not in item.read_text()
    output = capsys.readouterr()
    assert SECRET not in output.out + output.err


def test_failed_inspection_retains_failure_snapshot_and_actual_exit(offline):
    root, manifest, data, process, calls = offline
    process.returncode = 1
    data.update(status='blocked', stage='connect', checks={'fixed_profile_target': True}, observed={},
                query_count=0, exit_intent=1,
                failure=dict(stage='connect', exception_class='InvalidPassword', sqlstate='28P01'))
    assert capture.main(['--confirm-profile-test']) == 1
    path = directory(root)
    assert saved(path, 'database-snapshot.json') == data
    assert saved(path, 'process-receipt.json')['native_exit_code'] == 1
    assert len(calls) == 1
    with pytest.raises(ValueError):
        capture.validate_capture(path, manifest)


@pytest.mark.parametrize('output', [b'', b'not JSON', b'{"password":"synthetic-never-save-this-value"}', b'{"a":1,"a":2}'])
def test_missing_or_unapproved_stdout_never_saved_as_snapshot(offline, capsys, output):
    root, manifest, data, process, calls = offline
    process.output = output
    assert capture.main(['--confirm-profile-test']) == 1
    path = directory(root)
    assert not (path / 'database-snapshot.json').exists()
    assert saved(path, 'process-receipt.json')['native_exit_code'] == 0
    assert all(SECRET not in p.read_text() for p in path.iterdir())
    assert SECRET not in capsys.readouterr().out


@pytest.mark.parametrize('field', ['password', 'dsn', 'exception_message'])
def test_secret_bearing_worker_output_is_not_persisted(offline, field):
    root, manifest, data, process, calls = offline
    data[field] = SECRET
    assert capture.main(['--confirm-profile-test']) == 1
    assert not (directory(root) / 'database-snapshot.json').exists()


@pytest.mark.parametrize('name', ['started.json', 'source-manifest.json', 'database-snapshot.json', 'process-receipt.json'])
def test_missing_evidence_cannot_pass_offline_gate(offline, name):
    root, manifest, data, process, calls = offline
    assert capture.main(['--confirm-profile-test']) == 0
    path = directory(root)
    (path / name).rename(path / (name + '.missing'))
    with pytest.raises((ValueError, FileNotFoundError)):
        capture.validate_capture(path, manifest)


@pytest.mark.parametrize('mutation', ['native_false', 'native_one', 'source_changed', 'check_missing', 'check_false', 'check_integer', 'definitions_missing', 'file_corruption'])
def test_ambiguous_or_tampered_capture_cannot_pass(offline, mutation):
    root, manifest, data, process, calls = offline
    if mutation == 'source_changed':
        monkey_source = deepcopy(manifest)
        monkey_source['head'] = 'b' * 40
        assert capture.main(['--confirm-profile-test']) == 0
        with pytest.raises(ValueError):
            capture.validate_capture(directory(root), monkey_source)
        return
    if mutation == 'native_false': process.returncode = False
    if mutation == 'native_one': process.returncode = 1
    if mutation == 'check_missing': data['checks'].pop('exact_0005_revision')
    if mutation == 'check_false': data['checks']['exact_0005_revision'] = False
    if mutation == 'check_integer': data['checks']['exact_0005_revision'] = 1
    if mutation == 'definitions_missing': data['observed']['constraints'] = []
    expected = 0 if mutation == 'file_corruption' else 1
    assert capture.main(['--confirm-profile-test']) == expected
    path = directory(root)
    if mutation == 'file_corruption':
        with (path / 'database-snapshot.json').open('a') as stream:
            stream.write(' ')
    with pytest.raises(ValueError):
        capture.validate_capture(path, manifest)


@pytest.mark.parametrize('filename', ['source-manifest.json', 'started.json', 'database-snapshot.json', 'process-receipt.json'])
def test_persistence_failure_returns_nonzero_and_cannot_certify(offline, monkeypatch, capsys, filename):
    root, manifest, data, process, calls = offline
    write = capture.write_json
    def fail(path, value):
        if path.name == filename:
            raise OSError(SECRET)
        write(path, value)
    monkeypatch.setattr(capture, 'write_json', fail)
    assert capture.main(['--confirm-profile-test']) == 1
    with pytest.raises((ValueError, FileNotFoundError)):
        capture.validate_capture(directory(root), manifest)
    output = capsys.readouterr()
    assert SECRET not in output.out + output.err


def test_timeout_records_killed_process_and_never_retries(offline):
    root, manifest, data, process, calls = offline
    process.timeout = True
    assert capture.main(['--confirm-profile-test']) == 1
    receipt = saved(directory(root), 'process-receipt.json')
    assert receipt['interrupted'] is True and receipt['native_exit_code'] == -9
    assert len(calls) == 1


def test_new_run_preserves_previous_directory(offline):
    root, manifest, data, process, calls = offline
    assert capture.main(['--confirm-profile-test']) == 0
    first = directory(root)
    before = {p.name: p.read_bytes() for p in first.iterdir()}
    assert capture.main(['--confirm-profile-test']) == 0
    assert len(list(first.parent.iterdir())) == 2
    assert {p.name: p.read_bytes() for p in first.iterdir()} == before


def test_confirmation_required_before_any_worker(offline):
    root, manifest, data, process, calls = offline
    with pytest.raises(SystemExit) as error:
        capture.main([])
    assert error.value.code == 2 and calls == []
    assert list((root / 'backend/test-results').iterdir()) == []


def test_old_owner_module_command_now_enters_capture_supervisor(offline, monkeypatch):
    entry = Mock(return_value=7)
    monkeypatch.setattr(capture, 'main', entry)
    with pytest.warns(RuntimeWarning), pytest.raises(SystemExit) as result:
        runpy.run_module('release_support.profile_inspection', run_name='__main__')
    assert result.value.code == 7
    entry.assert_called_once_with()


def test_source_changes_during_capture_fail_closed(offline, monkeypatch):
    root, manifest, data, process, calls = offline
    changed = deepcopy(manifest)
    changed['head'] = 'b' * 40
    monkeypatch.setattr(worker, 'source', Mock(side_effect=[manifest, changed, changed]))
    assert capture.main(['--confirm-profile-test']) == 1
    receipt = saved(directory(root), 'process-receipt.json')
    assert receipt['native_exit_code'] == 0 and receipt['source_unchanged'] is False
    assert receipt['status'] == 'incomplete' and len(calls) == 1


def test_process_start_failure_retains_unknown_exit_without_raw_error(offline, monkeypatch, capsys):
    root, manifest, data, process, calls = offline
    popen = Mock(side_effect=OSError(SECRET))
    monkeypatch.setattr(capture.subprocess, 'Popen', popen)
    assert capture.main(['--confirm-profile-test']) == 1
    path = directory(root)
    receipt = saved(path, 'process-receipt.json')
    assert receipt['native_exit_code'] is None and receipt['failure_stage'] == 'worker_process'
    assert all(SECRET not in p.read_text() for p in path.iterdir())
    assert SECRET not in capsys.readouterr().out
    popen.assert_called_once()


def test_dsn_in_output_is_never_persisted(offline):
    root, manifest, data, process, calls = offline
    data['observed']['functions'][0]['definition'] = 'postgresql://synthetic:synthetic@invalid.invalid/example'
    assert capture.main(['--confirm-profile-test']) == 1
    path = directory(root)
    assert not (path / 'database-snapshot.json').exists()
    assert all('postgresql://' not in p.read_text() for p in path.iterdir())


def test_receipt_writer_never_overwrites_existing_evidence(tmp_path):
    path = tmp_path / 'existing.json'
    path.write_text('original')
    with pytest.raises(FileExistsError):
        capture.write_json(path, {'replacement': True})
    assert path.read_text() == 'original'


def test_capture_requires_all_nineteen_worker_conditions():
    tree = ast.parse(Path(worker.__file__).read_text())
    names = {node.args[0].value for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == 'check' and node.args and isinstance(node.args[0], ast.Constant)}
    assert len(names) == 19 and names == capture.CHECKS
