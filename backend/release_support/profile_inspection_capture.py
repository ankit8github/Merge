"""Capture one interactive inspection; no retries, raw diagnostics or certification."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from release_support import profile_inspection as worker

ROOT = worker.ROOT
CHECKS = frozenset((
    'fixed_profile_target', 'actual_identity', 'restricted_readonly_transaction',
    'unprivileged_login_role', 'exact_application_table_set',
    'no_unexpected_relation_kinds', 'relation_ownership_and_visibility',
    'exact_0005_revision', 'profile_objects_absent',
    'all_twelve_application_tables_empty', 'database_ownership', 'database_acl',
    'schema_ownership_and_grants', 'no_unexpected_table_grantees',
    'no_unexpected_default_acl', 'constraints_validated',
    'indexes_valid_and_ready', 'all_recorded_triggers_enabled', 'source_unchanged',
))
OBSERVED = frozenset((
    'identity', 'role', 'memberships', 'relations', 'revision_rows', 'profiles',
    'table_counts', 'columns', 'constraints', 'indexes', 'triggers',
    'internal_triggers', 'functions', 'types', 'database', 'database_acl',
    'schema', 'schema_acl', 'relation_acl', 'default_acl',
))
SNAPSHOT_FIELDS = frozenset((
    'schema_version', 'kind', 'started_at', 'completed_at', 'target', 'source',
    'collector_sha256', 'checks', 'observed', 'query_count', 'connection_attempts',
    'status', 'stage', 'expected_ddl', 'exit_intent', 'failure',
))
REVIEW_REQUIRED = 'capture_complete_requires_definition_review'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    # Never truncate/adopt an existing receipt, including a failed one.
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('Nonfinite JSON')
    if len(raw) > 2_000_000:
        raise ValueError('Evidence too large')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def snapshot_shape(data):
    """Accept only the worker report, never persist raw stdout/stderr or messages."""
    if (not isinstance(data, dict) or set(data) - SNAPSHOT_FIELDS
            or data.get('kind') != 'profile_0005_readonly_inspection'
            or data.get('schema_version') != 1 or data.get('target') != worker.TARGET
            or not isinstance(data.get('checks'), dict) or set(data['checks']) - CHECKS
            or not isinstance(data.get('observed'), dict) or set(data['observed']) - OBSERVED):
        raise ValueError('Unexpected snapshot shape')
    if 'failure' in data and (not isinstance(data['failure'], dict)
                             or set(data['failure']) != {'stage', 'exception_class', 'sqlstate'}):
        raise ValueError('Unapproved failure detail')
    def inspect(value):
        if isinstance(value, dict):
            if set(value) & {'password', 'dsn', 'connection_string', 'exception_message', 'traceback'}:
                raise ValueError('Secret-bearing field rejected')
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
        elif isinstance(value, str) and re.search(r'postgres(?:ql)?(?:\+\w+)?://', value, re.I):
            raise ValueError('Connection string rejected')
    inspect(data)
    return data


def complete_snapshot(data, source):
    snapshot_shape(data)
    if (data.get('status') != 'snapshot_complete_requires_definition_review'
            or data.get('stage') != 'snapshot_complete' or 'failure' in data
            or set(data['checks']) != CHECKS or any(v is not True for v in data['checks'].values())
            or data.get('source') != source or type(data.get('exit_intent')) is not int
            or data['exit_intent'] != 0 or type(data.get('connection_attempts')) is not int
            or data['connection_attempts'] != 1 or type(data.get('query_count')) is not int
            or data['query_count'] <= 0 or set(data['observed']) != OBSERVED):
        raise ValueError('Incomplete inspection')
    for name in ('columns', 'constraints', 'indexes', 'triggers', 'internal_triggers',
                 'relations', 'functions', 'types', 'database_acl', 'schema_acl', 'relation_acl'):
        if not isinstance(data['observed'][name], list) or not data['observed'][name]:
            raise ValueError('Definition inventory missing')


def evidence_directory():
    base = ROOT / 'backend/test-results'
    if base.resolve() != base or base.is_symlink():
        raise ValueError('Evidence redirect rejected')
    directory = base / ('profile-0005-readonly-' + uuid4().hex)
    directory.mkdir()  # UUID collision fails; never reuse a previous run.
    return directory


def validate_capture(directory, current_source):
    """Offline integrity gate only. A complete capture still needs definition review."""
    if (directory.parent != ROOT / 'backend/test-results'
            or not re.fullmatch(r'profile-0005-readonly-[0-9a-f]{32}', directory.name)
            or directory.resolve() != directory or directory.is_symlink()):
        raise ValueError('Evidence directory rejected')
    values = {}
    for name in ('started.json', 'source-manifest.json', 'database-snapshot.json', 'process-receipt.json'):
        path = directory / name
        if path.is_symlink() or path.resolve() != path:
            raise ValueError('Evidence file redirect rejected')
        values[name] = strict_json(path.read_bytes())
    receipt = values['process-receipt.json']
    snapshot = values['database-snapshot.json']
    manifest = values['source-manifest.json']
    if (receipt.get('kind') != 'profile_inspection_native_process'
            or type(receipt.get('native_exit_code')) is not int or receipt['native_exit_code'] != 0
            or receipt.get('status') != REVIEW_REQUIRED or receipt.get('interrupted') is not False
            or receipt.get('source_unchanged') is not True or receipt.get('final_certified') is not False
            or receipt.get('definition_review_required') is not True or manifest != current_source):
        raise ValueError('Failed, stale or ambiguous process evidence')
    for name, field in (('started.json', 'started_sha256'), ('source-manifest.json', 'source_manifest_sha256'),
                        ('database-snapshot.json', 'snapshot_sha256')):
        if receipt.get(field) != digest(directory / name):
            raise ValueError('Evidence hash mismatch')
    started = values['started.json']
    if (started.get('kind') != 'profile_inspection_started' or started.get('final_certified') is not False
            or started.get('source_manifest_sha256') != receipt['source_manifest_sha256']
            or started.get('worker_sha256') != snapshot.get('collector_sha256')
            or manifest.get('files', {}).get('backend/release_support/profile_inspection.py') != snapshot.get('collector_sha256')
            or manifest.get('files', {}).get('backend/release_support/profile_inspection_capture.py') != started.get('capture_sha256')):
        raise ValueError('Source binding incomplete')
    complete_snapshot(snapshot, manifest)
    return REVIEW_REQUIRED  # Never return a final certification/PASS.


def capture():
    directory = evidence_directory()
    receipt = dict(schema_version=1, kind='profile_inspection_native_process',
                   started_at=datetime.now(timezone.utc).isoformat(), native_exit_code=None,
                   status='incomplete', interrupted=False, source_unchanged=False,
                   final_certified=False, definition_review_required=True)
    stage = 'source_manifest'
    process = None
    try:
        before = worker.source()
        write_json(directory / 'source-manifest.json', before)
        receipt['source_manifest_sha256'] = digest(directory / 'source-manifest.json')
        started = dict(kind='profile_inspection_started', final_certified=False,
                       started_at=receipt['started_at'], source_manifest_sha256=receipt['source_manifest_sha256'],
                       worker_sha256=digest(Path(worker.__file__)), capture_sha256=digest(Path(__file__)))
        write_json(directory / 'started.json', started)
        receipt['started_sha256'] = digest(directory / 'started.json')
        stage = 'worker_process'
        command = [sys.executable, '-B', '-W', 'error::getpass.GetPassWarning', '-c',
                   "from release_support.profile_inspection import main; raise SystemExit(main(['--confirm-profile-test']))"]
        # Inherit stdin/console for getpass. No secret argument or environment mutation.
        # Raw output is memory-only; stderr is never saved or printed.
        process = subprocess.Popen(command, cwd=ROOT / 'backend', stdin=None,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            output, _ = process.communicate(timeout=600)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            receipt['interrupted'] = True
            process.kill()
            output, _ = process.communicate()
        receipt['native_exit_code'] = process.returncode
        stage = 'snapshot_validation'
        data = snapshot_shape(strict_json(output))
        write_json(directory / 'database-snapshot.json', data)
        receipt['snapshot_sha256'] = digest(directory / 'database-snapshot.json')
        stage = 'source_verification'
        receipt['source_unchanged'] = before == worker.source() == data.get('source')
        complete_snapshot(data, before)
        if (type(process.returncode) is not int or process.returncode != 0
                or receipt['interrupted'] or not receipt['source_unchanged']):
            raise ValueError('Process outcome incomplete')
        receipt['status'] = REVIEW_REQUIRED
    except (Exception, KeyboardInterrupt):
        # Fixed stage only: never serialize exception text or raw child diagnostics.
        receipt['failure_stage'] = stage
    receipt['completed_at'] = datetime.now(timezone.utc).isoformat()
    write_json(directory / 'process-receipt.json', receipt)
    try:
        validate_capture(directory, worker.source())
    except (Exception, KeyboardInterrupt):
        print(json.dumps(dict(status='blocked', evidence_directory=str(directory),
                              native_exit_code=receipt['native_exit_code'], final_certified=False)))
        return 1
    print(json.dumps(dict(status=REVIEW_REQUIRED, evidence_directory=str(directory),
                          native_exit_code=receipt['native_exit_code'], final_certified=False)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-profile-test', action='store_true', required=True)
    parser.parse_args(argv)
    try:
        return capture()
    except (Exception, KeyboardInterrupt):
        print('Capture incomplete; preserve evidence and stop. Details suppressed.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
