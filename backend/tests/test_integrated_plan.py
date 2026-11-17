"""Offline campaign adversaries. No engine, PostgreSQL, listener or browser."""
from copy import deepcopy
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from release_support import integrated_plan as p, targets, migrations, acceptance
from test_support import browser_full as legacy


@pytest.fixture(autouse=True)
def no_live(monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail('Live operation reached in offline acceptance preparation')
    monkeypatch.setattr(targets, 'create_engine', forbidden)
    monkeypatch.setattr(legacy, 'create_engine', forbidden)
    monkeypatch.setattr(legacy, 'hidden_password', forbidden)
    monkeypatch.setattr(legacy, 'reserved_socket', forbidden)
    monkeypatch.setattr(legacy.BrowserServer, 'run', forbidden)
    import psycopg
    monkeypatch.setattr(psycopg, 'connect', forbidden)


@pytest.fixture
def plan():
    return deepcopy(p.load_plan())


def test_fresh_public_scope_is_closed_and_has_exact_effect_and_transport_counts(plan):
    assert p.validate_plan(plan) is plan
    assert len(p.digest(plan)) == 64
    assert all(len(a['username']) <= 32 for a in plan['accounts'])
    assert sum(c['attempts'] for c in plan['commands']) == 18
    assert sum(c['effects'] for c in plan['commands']) == 14
    assert sum(a[k] for a in plan['accounts'] for k in ('register_attempts','login_attempts','logout_attempts')) == 10
    assert len(plan['profiles']) == 7 and sum(c['status'] == 200 for c in plan['profiles']) == 5
    assert 10 + 18 + 7 + len(plan['security']) == plan['counts']['total_posts'] == 38
    newer = p.definition(uuid4(), [uuid4(), uuid4()])
    assert not ({a['username'] for a in newer['accounts']} & {a['username'] for a in plan['accounts']})


@pytest.mark.parametrize('change', ['database','role','host','port','revision','budget','bool','new_command',
    'missing_case','duplicate_role','secret','duplicate_event','unknown_field','origin','profile_payload','viewport'])
def test_modified_scope_cannot_expand_permissions(plan, change):
    if change in ('database','role','host','port','revision'):
        plan['target'][change] = {'database':'merge_dev','role':'postgres','host':'localhost','port':5433,'revision':'head'}[change]
    elif change == 'budget': plan['commands'][0]['attempts'] = 3
    elif change == 'bool': plan['commands'][0]['effects'] = True
    elif change == 'new_command': plan['commands'].append(plan['commands'][0])
    elif change == 'missing_case': plan['coverage'].pop()
    elif change == 'duplicate_role': plan['accounts'][1] = plan['accounts'][0]
    elif change == 'secret': plan['accounts'][0]['password'] = 'synthetic-not-a-real-credential'
    elif change == 'duplicate_event': plan['hackathons'][1] = plan['hackathons'][0]
    elif change == 'origin': plan['origin'] = 'http://localhost:5173'
    elif change == 'profile_payload': plan['profile_values']['l']['discoverable'] = True
    elif change == 'viewport': plan['viewports'].pop()
    else: plan['target_url'] = 'unapproved'
    with pytest.raises((ValueError, KeyError)):
        p.validate_plan(plan)


def test_read_rejects_duplicate_keys_and_oversize(tmp_path):
    path = tmp_path / 'plan.json'
    path.write_text('{"run_id":1,"run_id":2}')
    with pytest.raises(ValueError, match='Duplicate'): p.load_plan(path)
    path.write_text(' ' * 32769)
    with pytest.raises(ValueError, match='large'): p.load_plan(path)


def test_preflight_honestly_blocks_execution_without_prompt_or_connection(plan, capsys):
    result = p.readiness(plan)
    assert result['status'] == 'CONDITIONAL' and result['live_operations_performed'] is False
    assert result['routes'] == 25 and result['service_overrides'] == 9
    assert len(result['missing_legacy_routes']) == 8
    assert p.main(['validate']) == 0
    assert p.main(['readiness']) == 2
    assert 'CONDITIONAL' in capsys.readouterr().out
    with pytest.raises(SystemExit): p.main(['serve'])


def test_legacy_host_still_rejects_profiles_lifecycle_and_sse(plan):
    from app import profile_api, lifecycle_api, realtime_api
    from fastapi.routing import iter_route_contexts
    engine = MagicMock(spec=Engine)
    engine.hide_parameters, engine.echo = True, False
    # A separate synthetic old scope; never read/write any historical manifest.
    from test_support.browser_full_scope import FullScope, COMMANDS, ROLES
    run = uuid4(); prefix = 'm015b_' + run.hex[:8] + '_'
    scope = FullScope.model_validate_json(json.dumps(dict(run_id=str(run),
        accounts=[dict(role=r,username=prefix+r,register_attempts=1,login_attempts=1,logout_attempts=1) for r in ROLES],
        hackathons=[dict(id=str(uuid4()),name=prefix+str(n)) for n in range(2)],
        team_a=prefix+'a',team_b=prefix+'b',commands=[dict(command=c,attempts=1) for c in COMMANDS])))
    host, app, ledger, throttle = legacy.browser_app(engine, legacy.ConnectionGuard(), scope, legacy.local_policy(), allow_writes=True)
    # Only the three inert startup sentinels are needed by the static wiring
    # audit. Do not enter the lifespan or run a TestClient/server here.
    app.state.auth_engine = app.state.auth_services = app.state.read_service = None
    health = next(r.endpoint for r in iter_route_contexts(app.routes) if r.path == '/health')
    overrides = dict(app.dependency_overrides)
    legacy.audit_wiring(app, overrides, health)
    assert len(legacy.ENDPOINTS) == 16
    for router in (profile_api.router,lifecycle_api.router,realtime_api.router):
        old = list(app.routes)
        app.include_router(router)
        from test_support.database import DiagnosticFailure
        with pytest.raises(DiagnosticFailure): legacy.audit_wiring(app, overrides, health)
        app.routes[:] = old
    engine.connect.assert_not_called()


@pytest.mark.parametrize('kind', ['merge_dev','merge_test','merge_prod','merge_bench'])
def test_profile_runner_cannot_select_other_database_before_engine(kind):
    with pytest.raises(ValueError):
        with targets.guarded_engine(targets.Target(kind, True, 'synthetic')): pass
    assert targets.Target('profiles', True, 'synthetic').url().database == 'merge_profile_test'
    assert acceptance.EXPECTED == 30


def test_profile_case_roster_rejects_duplicates_before_execution():
    plugin = acceptance.Plugin(None)
    nodes = [SimpleNamespace(nodeid='profile_tests/test_profiles.py::test_case') for _ in range(30)]
    with pytest.raises(ValueError): plugin.pytest_collection_finish(SimpleNamespace(items=nodes))


def test_owner_warning_flag_prevents_getpass_echo_fallback():
    script = '''import getpass
try:
    getpass.fallback_getpass('Synthetic prompt: ')
except getpass.GetPassWarning:
    print('fatal_hidden_input_warning_verified')
else:
    raise AssertionError('Hidden input fallback must never run')
'''
    result = subprocess.run([sys.executable, '-W', 'error::getpass.GetPassWarning', '-c', script],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and result.stdout.strip() == 'fatal_hidden_input_warning_verified'
    assert result.stderr == ''


def test_migration_prepare_rejects_existing_relations_before_upgrade(monkeypatch):
    from contextlib import contextmanager
    events = []
    class Connection:
        def in_transaction(self): return False
        @contextmanager
        def begin(self):
            try: yield
            except BaseException: events.append('rollback'); raise
        def execute(self, q):
            return SimpleNamespace(scalar_one=lambda:1)
    monkeypatch.setattr(migrations.command, 'upgrade', lambda *a:pytest.fail('DDL reached'))
    with pytest.raises(ValueError, match='empty'):
        migrations.migrate(Connection(), targets.Target('profiles', True, 'synthetic'), 'prepare')
    assert events == ['rollback']


def accepted(plan):
    source = dict(head='a'*40, files={'synthetic.py':'b'*64})
    observations = ('two_isolated_clients','sse_without_manual_refresh','lease_reconnect_refetch',
        'no_private_content_leak','old_account_callbacks_fenced','old_workspace_callbacks_fenced',
        'keyboard_only_actions','mobile_390_no_overflow','cancel_no_posts_focus_restored',
        'navigation_no_automatic_posts')
    data = dict(schema_version=1,kind='integrated-browser',run_id=plan['run_id'],plan_sha256=p.digest(plan),
        target=p.TARGET.copy(),source=source,source_unchanged=True,status='passed',failures=[],skipped=[],active_checkpoint=None,
        native_exits=dict(host=0,browser=0,observer=0),
        checkpoints=[dict(id=c,status='passed',evidence_sha256='c'*64) for c in p.COVERAGE],
        commands={t:dict(attempts=n,effects=e,statuses=[s]*n,same_key_payload_actor_scope=True) for t,r,n,e,s in p.COMMANDS},
        totals=dict(auth_posts=10,profile_posts=7,security_posts=3,total_posts=38,users=4,credentials=4,sessions=5,
            revoked_sessions=1,profiles=4,hackathons=2,teams=2,memberships=1,requests=2,invitations=2,tombstones=1,
            idempotency=14,audit=14,outbox=14,team_a_version=13,team_b_version=1),
        invariants='fresh_scope_and_prior_rows_verified',host_drained=True,budget_enforced_by_host=True,actual_bindings_verified=True,
        profile_statuses={t:s for t,r,s in p.PROFILE_POSTS},security_statuses=dict(missing_session=401,missing_csrf=403,foreign_origin=403),
        observations={k:True for k in observations})
    return data, source


def test_synthetic_receipt_consistency_is_explicitly_not_certification(plan):
    data, source = accepted(plan)
    assert p.validate_receipt(data, plan, source) == 'metadata_consistent_requires_evidence_review'


def test_campaign_recipient_denial_matches_real_http_privacy_mapping():
    import asyncio
    from app.invitation_api import invitation_error_handler
    from app.services.invitations import InvitationError
    from app.services.errors import ErrorCode
    response = asyncio.run(invitation_error_handler(None, InvitationError(ErrorCode.INVITATION_NOT_FOUND)))
    expected = next(c for c in p.COMMANDS if c[0] == 'deny_redeem')
    assert response.status_code == expected[4] == 404
    assert json.loads(response.body)['error']['code'] == 'invitation_not_found'


@pytest.mark.parametrize('change', ['stale','native','bool_exit','missing_exit','skip','active','missing_case','duplicate_case',
    'budget','effect','replay','status','db','revision','prior_rows','drain','enforcement','bindings','totals','profile',
    'security','observation','missing_hash','bad_hash','plan_hash','incomplete'])
def test_failed_partial_or_fabricated_shape_cannot_pass_consistency_contract(plan, change):
    data, source = accepted(plan)
    if change == 'stale': data['source_unchanged'] = False
    elif change == 'native': data['native_exits']['browser'] = 1
    elif change == 'bool_exit': data['native_exits']['host'] = False
    elif change == 'missing_exit': del data['native_exits']['observer']
    elif change == 'skip': data['skipped'] = ['profiles']
    elif change == 'active': data['active_checkpoint'] = 'soft_delete'
    elif change == 'missing_case': data['checkpoints'].pop()
    elif change == 'duplicate_case': data['checkpoints'][1] = data['checkpoints'][0]
    elif change == 'budget': data['commands']['create_a']['attempts'] = 3
    elif change == 'effect': data['commands']['create_a']['effects'] = 2
    elif change == 'replay': data['commands']['create_a']['same_key_payload_actor_scope'] = False
    elif change == 'status': data['commands']['deny_redeem']['statuses'] = [200]
    elif change == 'db': data['target']['database'] = 'merge_dev'
    elif change == 'revision': data['target']['revision'] = '0005_invitations'
    elif change == 'prior_rows': data['invariants'] = 'scope_only'
    elif change == 'drain': data['host_drained'] = False
    elif change == 'enforcement': data['budget_enforced_by_host'] = False
    elif change == 'bindings': data['actual_bindings_verified'] = False
    elif change == 'totals': data['totals']['total_posts'] = 39
    elif change == 'profile': data['profile_statuses']['profile_stale'] = 200
    elif change == 'security': data['security_statuses']['foreign_origin'] = 200
    elif change == 'observation': data['observations']['keyboard_only_actions'] = False
    elif change == 'missing_hash': del data['checkpoints'][0]['evidence_sha256']
    elif change == 'bad_hash': data['source'] = dict(head='a'*40,files={'synthetic.py':'unhashed'})
    elif change == 'plan_hash': data['plan_sha256'] = 'd'*64
    else: data['status'] = 'incomplete'
    with pytest.raises(ValueError): p.validate_receipt(data, plan, source)
