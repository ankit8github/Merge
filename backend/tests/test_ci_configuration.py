"""Offline workflow regression checks: no Docker, database or network access."""
import ast
import json
from pathlib import Path
import shlex

from release_support import ci

ROOT = Path(__file__).resolve().parents[2]


def workflow():
    # JSON is also YAML 1.2; keep the existing dependency-free parser contract.
    return json.loads((ROOT / '.github/workflows/ci.yml').read_text())


def test_postgres_service_health_options_are_individual_docker_arguments():
    service = workflow()['jobs']['postgres']['services']['postgres']
    assert service['image'] == 'postgres:17'
    expected = ['--health-cmd=pg_isready', '--health-interval=5s',
                '--health-timeout=5s', '--health-retries=10']
    # Actions does not preserve shell-style quotes in docker create arguments.
    assert service['options'].split() == expected
    assert shlex.split(service['options']) == expected
    assert service['ports'] == ['127.0.0.1:5432:5432']
    assert service['env'] == {
        'POSTGRES_PASSWORD': '${{ github.run_id }}-${{ github.run_attempt }}'}


def test_four_isolated_revisions_keep_authenticated_suites_and_race():
    job = workflow()['jobs']['postgres']
    assert job['runs-on'] == 'ubuntu-24.04'
    assert job['strategy']['fail-fast'] is False
    assert job['strategy']['matrix']['revision'] == [
        '0003_auth', '0004_admission', '0005_invitations', '0006_profiles']
    assert ci.PLANS == {
        '0003_auth': (('auth-api', 18), ('team-api', 35)),
        '0004_admission': (('admission', 35),),
        '0005_invitations': (('invitations', 13), ('lifecycle', 10), ('realtime', 4)),
        '0006_profiles': (('profiles', 30),),
    }
    steps = job['steps']
    execute = next(s for s in steps if 'release_support.ci' in s.get('run', ''))
    assert execute['working-directory'] == 'backend'
    assert execute['env']['CI_ADMIN_PASSWORD'] == job['services']['postgres']['env']['POSTGRES_PASSWORD']
    command = execute['run']
    assert command.startswith('set -euo pipefail\n')
    for required in ('docker inspect', '${{ job.services.postgres.id }}',
                     "PYTHON=$(command -v python)", 'nsenter --target "$PG_PID" --net "$PYTHON"',
                     '--preserve-env=CI,GITHUB_ACTIONS,RUNNER_ENVIRONMENT,CI_ADMIN_PASSWORD',
                     '--confirm-ephemeral-postgres', "--revision '${{ matrix.revision }}'"):
        assert required in command
    assert 'continue-on-error' not in execute and '|| true' not in command
    upload = next(s for s in steps if s.get('uses') == 'actions/upload-artifact@v4')
    assert upload['if'] == 'always()'
    assert upload['with']['if-no-files-found'] == 'error'
    race = ast.parse((ROOT / 'backend/invitation_tests/test_invitations.py').read_text())
    assert any(isinstance(n, ast.FunctionDef) and
               n.name == 'test_distinct_authenticated_50_caller_last_seat'
               for n in ast.walk(race))


def test_ci_checks_each_native_exit_and_complete_receipt_before_success():
    # Existing synthetic tests exercise rejection of bad reports; pin the real
    # orchestration call so a future workflow edit cannot bypass that validator.
    tree = ast.parse((ROOT / 'backend/release_support/ci.py').read_text())
    checks = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Name) and n.func.id == 'validate_test_report']
    assert len(checks) == 1
    assert [ast.unparse(a) for a in checks[0].args] == [
        'data', 'suite', 'args.revision', 'count', 'rc']
    assert workflow()['permissions'] == {'contents': 'read'}
    offline = workflow()['jobs']['offline']['steps']
    for required in ("-m 'not database'", '--maxWorkers=1', 'npm run build', 'git diff --check'):
        assert any(required in s.get('run', '') for s in offline)
