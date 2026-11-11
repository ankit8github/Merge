"""Owner-run, fixed-target concurrency entry point; never loads development settings."""
import argparse
from dataclasses import dataclass, field
from getpass import getpass
import os
from pathlib import Path
import sys

import pytest
from test_support.database import TestDatabaseSettings, safe_failure_message, test_connection
from test_support.revisions import AUTH_REVISION, DOMAIN_REVISION, ADMISSION_REVISION, TARGET_REVISIONS
from test_support.diagnostics import Diagnostics


@dataclass(repr=False)
class PrivateTestPlugin:
    settings: TestDatabaseSettings = field(repr=False)

    def pytest_configure(self, config):
        config._merge_concurrency_settings = self.settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-merge-test', action='store_true', required=True)
    parser.add_argument('--repetitions', type=int, choices=range(1, 11), default=3)
    parser.add_argument('--suite', choices=('schema', 'services', 'auth', 'credentials', 'sessions', 'auth-api', 'throttles', 'idempotency', 'mutations', 'retries', 'reads', 'team-api', 'admission'), default='schema')
    parser.add_argument('--revision', choices=TARGET_REVISIONS, default=DOMAIN_REVISION)
    args = parser.parse_args()
    if args.suite == 'admission' and args.revision != ADMISSION_REVISION:
        parser.error('Admission suite requires explicit --revision 0004_admission')
    if args.suite in ('auth', 'credentials', 'sessions', 'auth-api', 'throttles', 'idempotency', 'mutations', 'retries', 'reads', 'team-api') and args.revision != AUTH_REVISION:
        parser.error('Selected suite requires explicit --revision 0003_auth')
    if not __debug__:
        parser.error('Python optimization must be disabled so invariant assertions execute')
    try:
        diagnostics = Diagnostics(Path(__file__).resolve().parents[1], args.suite,
                                  args.revision, args.repetitions)
    except (OSError, ValueError):
        print('Cannot create safe diagnostic report; no database opened.')
        raise SystemExit(1) from None
    print(f'Diagnostic report: test-results/guarded/{diagnostics.path.name}', flush=True)
    code = 1
    try:
        result = run(args, diagnostics, parser)
        if not isinstance(result, int) or isinstance(result, bool) or result not in range(6):
            raise ValueError('Unexpected pytest exit code')
        code = result
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else 1
    except KeyboardInterrupt:
        code = 2
        diagnostics.data['status'] = 'interrupted'
    except Exception:
        diagnostics.data['status'] = 'internal_error'
    finally:
        try:
            diagnostics.finish(code)
        except (Exception, KeyboardInterrupt):
            print('Diagnostic finalization incomplete; invariants NOT CERTIFIED.')
            if code == 0:
                code = 1
            diagnostics.data['status'] = 'diagnostics_incomplete'
            diagnostics.data['invariant_verification'] = 'not_certified'
            diagnostics.data['exit_code'] = code
            try:
                diagnostics.save()
            except (Exception, KeyboardInterrupt):
                pass  # Exit remains unsuccessful even when the filesystem is unavailable.
    for failure in diagnostics.data['failures']:
        print(f"FAILED {failure['node_id']} phase={failure['phase']} category={failure['category']}")
    print(f"Run status: {diagnostics.data['status']}; exit={code}; "
          f"invariants={diagnostics.data['invariant_verification']}")
    raise SystemExit(code)


def run(args, diagnostics, parser):
    password = os.environ.get('MERGE_TEST_DB_PASSWORD')
    if password is None:
        if not sys.stdin.isatty():
            parser.error('Interactive hidden password input or private test-only secret environment required')
        password = getpass('Existing merge_app password (hidden): ')
    if not password:
        parser.error('A nonempty explicit test credential is required')
    settings = TestDatabaseSettings(confirmed=args.confirm_merge_test, password=password)
    diagnostics.data['stage'] = 'preflight'
    diagnostics.save()
    try:
        with test_connection(settings) as connection:
            from sqlalchemy import text
            connection.execute(text('SET TRANSACTION READ ONLY'))
            if connection.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() != [args.revision]:
                parser.error('Unexpected revision for explicit test target; no migrations will run')
    except Exception as error:
        print(safe_failure_message(error, 'connection'))
        raise SystemExit(1) from None
    root = Path(__file__).resolve().parents[1]
    directories = {'schema': [root / 'concurrency_tests'],
                   'services': [root / 'service_tests'],
                   'auth': [root / 'auth_schema_tests'],
                   'credentials': [root / 'credential_tests'],
                   'sessions': [root / 'session_tests'],
                   'auth-api': [root / 'auth_api_tests'],
                   'throttles': [root / 'throttle_tests'],
                   'idempotency': [root / 'idempotency_tests'],
                   'mutations': [root / 'team_mutation_tests'],
                   'retries': [root / 'retry_tests'],
                   'reads': [root / 'read_api_tests'],
                   'team-api': [root / 'team_api_tests'],
                   'admission': [root / 'admission_tests']}[args.suite]
    # Fixed suite, fail fast, no exception/local-variable dumps or third-party autoload.
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    os.environ.pop('PYTEST_ADDOPTS', None)
    os.environ.pop('PYTEST_PLUGINS', None)
    result = diagnostics.run_pytest([*(str(directory) for directory in directories), '-q', '-s', '-x', '--tb=no',
                          '--show-capture=no', '-rN', '--disable-warnings',
                          '-o', 'log_cli=false', '-o', 'log_file=' + os.devnull,
                          '--assert=plain', '-o', 'addopts=', '-p', 'no:cacheprovider',
                          '--confirm-merge-test', f'--race-repetitions={args.repetitions}'],
                         plugins=[PrivateTestPlugin(settings), diagnostics])
    return result


if __name__ == '__main__':
    main()
