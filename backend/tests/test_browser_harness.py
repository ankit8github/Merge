"""PYTEST_DONT_REWRITE: offline harness failures; no HTTP listeners, real prompts or PostgreSQL."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import json
import warnings

from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import SecretBytes
import pytest
from sqlalchemy.engine import Engine

from app import auth, read_api
from app.services.sessions import IssuedSession, SessionPrincipal, ValidatedSession
from test_support import browser as b, database
from test_support.browser_state import RunScope, Snapshot, compare, snapshot

MARKER = 'synthetic-private-marker-never-print'
HEADERS = {'Origin': b.ORIGIN, 'X-Merge-Request': '1'}
BODY = {'username': 'offline_user', 'password': 'offline test passphrase'}


@pytest.fixture(autouse=True)
def forbid_live(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Live operation forbidden in offline tests')
    monkeypatch.setattr(database, 'create_engine', forbidden)
    monkeypatch.setattr(b, 'socket', SimpleNamespace(socket=forbidden))
    monkeypatch.setattr(b, 'getpass', forbidden)
    monkeypatch.setattr(b.uvicorn.Server, 'run', forbidden)
    import app.core.config
    import app.db.session
    monkeypatch.setattr(app.core.config, 'Settings', forbidden)
    monkeypatch.setattr(app.db.session, 'build_engine', forbidden)


@pytest.fixture
def scope():
    return RunScope.model_validate_json(json.dumps({'run_id': str(uuid4()), 'accounts': [
        {'user_id': str(uuid4()), 'username': 'offline_user', 'login_attempts': 3, 'logout_attempts': 2}]}))


class Connection:
    def __init__(self):
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.identity = ('merge_test', 'merge_app', '127.0.0.1', 5432)
        self.settings = ('read committed', 'read committed', 'on', '5s', '15s')
        self.revisions = ['0003_auth']
        self.isolation = 'READ COMMITTED'
        self.active = False
        self.options = {}
        self.queries = []
        self.invalid = False
        self.rollbacks = 0

    def in_transaction(self): return self.active
    def get_execution_options(self): return self.options
    def get_isolation_level(self): return self.isolation
    def rollback(self):
        self.active = False
        self.rollbacks += 1
    def invalidate(self): self.invalid = True
    def execute(self, statement):
        q = str(statement)
        self.queries.append(q)
        self.active = True
        value = self.identity if 'current_database' in q else self.settings
        return SimpleNamespace(one=lambda:value, scalars=lambda:SimpleNamespace(all=lambda:self.revisions))


@pytest.mark.parametrize('field,value', [
    ('identity', ('merge_dev', 'merge_app', '127.0.0.1', 5432)),
    ('identity', ('merge_test', 'postgres', '127.0.0.1', 5432)),
    ('identity', ('merge_test', 'merge_app', '192.0.2.1', 5432)),
    ('identity', ('merge_test', 'merge_app', '127.0.0.1', 5433)),
    ('isolation', 'REPEATABLE READ'), ('isolation', 'SERIALIZABLE'),
    ('revisions', []), ('revisions', ['0002_domain']), ('revisions', ['0003_auth', 'other']),
    ('settings', ('read committed', 'serializable', 'on', '5s', '15s')),
    ('settings', ('read committed', 'read committed', 'off', '5s', '15s')),
    ('settings', ('read committed', 'read committed', 'on', '0', '15s')),
    ('settings', ('read committed', 'read committed', 'on', '5s', '0')),
    ('active', True), ('options', {'isolation_level': 'AUTOCOMMIT'}),
])
def test_connection_guard_fails_and_latches(field, value):
    c, guard = Connection(), b.ConnectionGuard()
    setattr(c, field, value)
    with pytest.raises(database.DiagnosticFailure): guard(c)
    assert c.invalid and guard.failed.is_set()
    fresh = Connection()
    with pytest.raises(database.DiagnosticFailure): guard(fresh)
    assert fresh.queries == []


@pytest.mark.parametrize('mutation', ['autocommit', 'driver', 'async', 'backend'])
def test_driver_configuration_rejected_before_sql(mutation):
    c = Connection()
    if mutation == 'autocommit': c.connection.dbapi_connection.autocommit = True
    if mutation == 'driver': c.dialect.driver = 'psycopg2'
    if mutation == 'async': c.dialect.is_async = True
    if mutation == 'backend': c.dialect.name = 'sqlite'
    with pytest.raises(database.DiagnosticFailure): b.ConnectionGuard()(c)
    assert c.queries == [] and c.invalid


def test_every_logical_connection_rechecked_including_pool_reuse():
    c, guard = Connection(), b.ConnectionGuard()
    guard(c)
    guard(c)
    guard(Connection())
    assert c.rollbacks == 2 and not c.active
    assert sum('current_database' in q for q in c.queries) == 2
    c.connection.dbapi_connection.autocommit = True
    with pytest.raises(database.DiagnosticFailure): guard(c)


@pytest.mark.parametrize('overrides', [{'confirmed':False}, {'database':'merge_dev'}, {'user':'postgres'},
                                       {'host':'localhost'}, {'port':5433}, {'password':''}])
def test_settings_rejected_without_engine(overrides):
    values = dict(confirmed=True, password=MARKER)
    values.update(overrides)
    with pytest.raises(ValueError):
        with b.guarded_engine(database.TestDatabaseSettings(**values)):
            pytest.fail('Must not yield')


@pytest.fixture
def api(monkeypatch, scope):
    engine = MagicMock(spec=Engine)
    engine.hide_parameters, engine.echo = True, False
    sessions, reads, throttle = MagicMock(), MagicMock(), MagicMock()
    principal = SessionPrincipal(scope.accounts[0].user_id, 'offline_user', datetime.now(timezone.utc)+timedelta(hours=8))
    issued = IssuedSession(principal, datetime.now(timezone.utc), SecretBytes(b't'*32), SecretBytes(b'c'*32))
    sessions.login.return_value = issued
    sessions.validate.return_value = sessions.verify_csrf.return_value = principal
    sessions.validate_with_csrf.return_value = ValidatedSession(principal, issued.csrf_token)
    reads.hackathons.return_value = {'items': [], 'next_cursor': None}
    reads.my_team.return_value = {'team': None}
    monkeypatch.setattr(b, 'SessionService', lambda e:sessions)
    monkeypatch.setattr(b, 'TeamReadService', lambda e:reads)
    monkeypatch.setattr(b, 'ThrottleService', lambda *a, **kw:throttle)
    host, app, _ = b.browser_app(engine, b.ConnectionGuard(), scope, b.local_policy(), allow_writes=True)
    with TestClient(host, base_url=b.ORIGIN, client=(b.HOST, 40000)) as client:
        yield SimpleNamespace(client=client, app=app, sessions=sessions, reads=reads, throttle=throttle, issued=issued)
    assert app.state.auth_engine is None


def test_both_overrides_and_real_http_protections(api):
    assert set(api.app.dependency_overrides) == {auth.get_services, read_api.get_read_service}
    r = api.client.post('/auth/login', headers=HEADERS, json=BODY)
    assert r.status_code == 200
    cookie = r.headers['set-cookie']
    assert cookie.startswith('merge_session_dev=')
    assert all(flag in cookie for flag in ('HttpOnly', 'SameSite=lax', 'Path=/'))
    assert 'Secure' not in cookie and 'Domain=' not in cookie
    assert auth.encode_token(b't'*32) not in r.text
    assert api.client.get('/auth/session').status_code == 200
    assert api.client.get('/api/hackathons').json() == {'items': [], 'next_cursor': None}
    assert api.client.get('/api/hackathons/'+str(uuid4())+'/me/team').json() == {'team':None}
    assert api.client.post('/auth/logout', headers=HEADERS, json={}).status_code == 403
    api.sessions.revoke.assert_not_called()
    headers = {**HEADERS, 'X-CSRF-Token': auth.encode_token(b'c'*32)}
    assert api.client.post('/auth/logout', headers=headers, json={}).status_code == 204
    api.sessions.verify_csrf.assert_called_once_with(b't'*32, b'c'*32)
    api.sessions.revoke.assert_called_once_with(b't'*32)
    api.throttle.check.assert_called_once_with(operation='login', client_ip=b.HOST, username='offline_user')


@pytest.mark.parametrize('headers,code', [
    ({'Origin':'http://evil.example','X-Merge-Request':'1'}, 'origin_rejected'),
    ({'Origin':b.ORIGIN}, 'request_header_required'),
    ({**HEADERS,'X-Forwarded-For':'127.0.0.1'}, 'client_identity_rejected'),
    ({**HEADERS,'Forwarded':'for=127.0.0.1'}, 'client_identity_rejected'),
    ({**HEADERS,'Sec-Fetch-Site':'cross-site'}, 'origin_rejected'),
])
def test_policy_precedes_scope_body_and_throttle(api, headers, code):
    r = api.client.post('/auth/login', headers={**headers, 'Content-Type':'application/json'}, content=MARKER)
    assert r.status_code == 403 and r.json()['error']['code'] == code
    api.throttle.check.assert_not_called()
    api.sessions.login.assert_not_called()


def test_scope_budgets_registration_invalid_input_and_outside_account(api):
    assert api.client.post('/auth/register', headers=HEADERS, json=BODY).status_code == 403
    assert api.client.post('/auth/login', headers=HEADERS, json={**BODY,'username':'outside_user'}).status_code == 403
    assert api.client.post('/auth/login', headers=HEADERS, json={**BODY,'extra':MARKER}).status_code == 422
    api.throttle.check.assert_not_called()
    for _ in range(3):
        assert api.client.post('/auth/login', headers=HEADERS, json=BODY).status_code == 200
    assert api.client.post('/auth/login', headers=HEADERS, json=BODY).status_code == 403
    assert api.throttle.check.call_count == 3


def test_logout_revalidates_actual_principal_scope_before_revoke(api):
    api.client.cookies.set('merge_session_dev', auth.encode_token(b't'*32))
    api.sessions.validate.return_value = SessionPrincipal(uuid4(), 'outside_user', api.issued.principal.expires_at)
    r = api.client.post('/auth/logout', headers={**HEADERS,'X-CSRF-Token':auth.encode_token(b'c'*32)}, json={})
    assert r.status_code == 403
    api.sessions.revoke.assert_not_called()


@pytest.mark.parametrize('which', [auth.get_services, read_api.get_read_service])
def test_removed_override_fails_before_any_fallback(api, which):
    removed = api.app.dependency_overrides.pop(which)
    try:
        response = api.client.post('/auth/login', headers=HEADERS, json=BODY)
        assert response.status_code == 503
        assert response.headers['cache-control'] == 'no-store, private'
        assert response.headers['pragma'] == 'no-cache'
        assert response.headers['expires'] == '0'
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert api.client.get('/health').status_code == 503
        api.throttle.check.assert_not_called()
    finally:
        api.app.dependency_overrides[which] = removed


def test_unknown_database_dependency_fails_closed(api):
    def new_database_dependency(): raise AssertionError('Must never resolve')
    @api.app.get('/unsafe')
    def unsafe(value=Depends(new_database_dependency)): return {}
    try:
        assert api.client.get('/unsafe').status_code == 503
    finally:
        api.app.routes.pop()


@pytest.mark.parametrize('changes', [{'mode':'production','origin':'https://127.0.0.1:5173'},
    {'origin':'http://localhost:5173'}, {'trusted_proxies':('127.0.0.1/32',)}, {'login_ip_limit':31}])
def test_cookie_origin_proxy_and_throttle_modes_are_fixed(changes):
    policy = b.local_policy().model_copy(update=changes)
    with pytest.raises(database.DiagnosticFailure): b.validate_policy(policy, b.HOST)


@pytest.mark.parametrize('host', ['0.0.0.0','localhost','::1','192.0.2.1'])
def test_non_exact_loopback_bind_rejected_before_socket(host):
    with pytest.raises(database.DiagnosticFailure):
        with b.reserved_socket(host): pass
    with pytest.raises(database.DiagnosticFailure): b.validate_policy(b.local_policy(), host)


def test_policy_ignores_all_ordinary_environment(monkeypatch):
    for name in ('MODE','ORIGIN','THROTTLE_SECRET','TRUSTED_PROXIES','LOGIN_IP_LIMIT'):
        monkeypatch.setenv('MERGE_AUTH_'+name, MARKER)
    monkeypatch.setenv('MERGE_TEST_DB_PASSWORD', MARKER)
    b.validate_policy(b.local_policy(), b.HOST)


@pytest.mark.parametrize('argv', [[], ['serve'], ['serve','--confirm-merge-test','--revision','0003_auth','--manifest','scope.json'],
    ['inspect','--confirm-merge-test','--revision','0002_domain','--manifest','scope.json'],
    ['serve','--confirm-merge-test','--revision','0003_auth','--manifest','scope.json','--allow-scoped-auth-writes','--password',MARKER]])
def test_cli_refuses_before_prompt_or_connection(argv, capsys):
    with pytest.raises(SystemExit) as error: b.main(argv)
    assert error.value.code == 2
    assert MARKER not in str(capsys.readouterr())


def test_hidden_prompt_refuses_noninteractive_echo_fallback_and_empty(monkeypatch):
    monkeypatch.setattr(b.sys.stdin, 'isatty', lambda:False)
    with pytest.raises(database.DiagnosticFailure): b.hidden_password()
    monkeypatch.setattr(b.sys.stdin, 'isatty', lambda:True)
    def echo_warning(*args):
        warnings.warn(MARKER, b.GetPassWarning)
        pytest.fail('Must stop before fallback input')
    monkeypatch.setattr(b, 'getpass', echo_warning)
    with pytest.raises(b.GetPassWarning): b.hidden_password()
    monkeypatch.setattr(b, 'getpass', lambda *a:'')
    with pytest.raises(database.DiagnosticFailure): b.hidden_password()


def test_manifest_rejects_secrets_duplicate_keys_and_bad_budgets(tmp_path, scope):
    path = tmp_path/'scope.json'
    valid = scope.model_dump(mode='json')
    path.write_text(json.dumps(valid))
    assert b.read_scope(path) == scope
    for invalid in ({**valid,'password':MARKER}, {**valid,'accounts':[]},
                    {**valid,'accounts':[dict(valid['accounts'][0], login_attempts=True)]}):
        path.write_text(json.dumps(invalid))
        with pytest.raises(ValueError): b.read_scope(path)
    path.write_text('{"run_id":"one","run_id":"two"}')
    with pytest.raises(ValueError): b.read_scope(path)


def test_top_level_failure_suppresses_exception_and_log_secrets(monkeypatch, scope, capsys):
    monkeypatch.setattr(b, 'read_scope', lambda p:scope)
    def fail():
        import logging
        logging.critical(MARKER)
        raise RuntimeError(MARKER)
    monkeypatch.setattr(b, 'hidden_password', fail)
    assert b.main(['inspect','--confirm-merge-test','--revision','0003_auth','--manifest','scope.json']) == 1
    output = capsys.readouterr()
    assert MARKER not in output.out+output.err and 'exception text suppressed' in output.out


def test_compare_allows_only_bounded_scoped_effects(scope):
    user = scope.accounts[0].user_id
    throttle = SimpleNamespace(_key=lambda kind, name:(kind+name).encode())
    before = Snapshot(unchanged={'teams':(1,'fingerprint')})
    after = Snapshot(unchanged=dict(before.unchanged), sessions={b'session':(user,'private-fingerprint',None)},
                     buckets={('auth:v1:login_ip', throttle._key('login_ip',b.HOST), 1):(1,2,'private-fingerprint')})
    compare(before, after, scope, throttle)
    for bad in (Snapshot(unchanged={}), Snapshot(unchanged=dict(before.unchanged), sessions={b'x':(uuid4(),'x',None)}),
                Snapshot(unchanged=dict(before.unchanged), buckets={('outside',b'x',1):(1,2,'x')})):
        with pytest.raises(database.DiagnosticFailure): compare(before, bad, scope, throttle)


def test_verify_snapshot_is_read_only_with_bound_account_ids(scope):
    connection = MagicMock()
    queries = []
    def execute(statement, parameters=None):
        q = str(statement)
        queries.append((q,parameters))
        result = MagicMock()
        result.scalar_one_or_none.return_value = scope.accounts[0].user_id
        result.scalar_one.return_value = 0
        result.one.return_value = (0,'fingerprint')
        result.all.return_value = []
        return result
    connection.execute.side_effect = execute
    snapshot(connection, scope)
    assert queries[0][0] == 'SET TRANSACTION READ ONLY'
    assert all(q.startswith(('SET TRANSACTION READ ONLY','SELECT')) for q,p in queries)
    assert queries[1][1] == {'name':scope.accounts[0].username}
    assert all(scope.accounts[0].username not in q for q,p in queries)
    connection.rollback.assert_called_once()

@pytest.mark.parametrize('which', [auth.get_services, read_api.get_read_service])
def test_missing_override_rejects_asgi_startup(monkeypatch, scope, which):
    engine = MagicMock(spec=Engine)
    engine.hide_parameters, engine.echo = True, False
    host, app, _ = b.browser_app(engine, b.ConnectionGuard(), scope, b.local_policy(), allow_writes=True)
    app.dependency_overrides.pop(which)
    with pytest.raises(database.DiagnosticFailure):
        with TestClient(host): pytest.fail('Must not serve')
    engine.connect.assert_not_called()


def test_real_service_engine_wiring_and_no_implicit_write_optin(scope):
    engine = MagicMock(spec=Engine)
    engine.hide_parameters, engine.echo = True, False
    with pytest.raises(database.DiagnosticFailure): b.browser_app(engine, b.ConnectionGuard(), scope, b.local_policy())
    host, app, throttle = b.browser_app(engine, b.ConnectionGuard(), scope, b.local_policy(), allow_writes=True)
    import asyncio
    request = SimpleNamespace(method='GET')
    services = asyncio.run(app.dependency_overrides[auth.get_services](request))
    assert isinstance(services.credentials, b.CredentialService)
    assert isinstance(services.sessions.real, b.SessionService)
    assert services.credentials._engine is engine
    assert services.sessions.real._credentials._engine is engine
    assert throttle._owner._engine is engine
    assert app.dependency_overrides[read_api.get_read_service]()._engine is engine
    engine.connect.assert_not_called()


def test_guard_hook_installation_removal_and_connection_owner_disposal(monkeypatch):
    connection = Connection()
    connection.engine = MagicMock()
    phases, callbacks = [], []
    @contextmanager
    def owner(settings):
        phases.append('owner-enter')
        try: yield connection
        finally: phases.append('owner-disposed')
    def listen(engine, name, callback):
        assert name == 'engine_connect' and connection.rollbacks == 1
        callbacks.append(callback)
    monkeypatch.setattr(b, 'test_connection', owner)
    monkeypatch.setattr(b.event, 'listen', listen)
    monkeypatch.setattr(b.event, 'remove', lambda e,n,c:phases.append('hook-removed'))
    with pytest.raises(RuntimeError):
        with b.guarded_engine(database.TestDatabaseSettings(confirmed=True, password=MARKER)) as (engine, guard):
            callbacks[0](Connection())
            raise RuntimeError(MARKER)
    assert phases == ['owner-enter','hook-removed','owner-disposed']


@pytest.mark.parametrize('failure', ['none','startup','callback','shutdown','observer','compare','forced'])
def test_lifecycle_final_observer_disposal_and_safe_failure_labels(monkeypatch, scope, capsys, failure):
    phases = []
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = object()
    guard = b.ConnectionGuard()
    @contextmanager
    def owned(settings):
        phases.append('enter')
        try: yield engine, guard
        finally: phases.append('dispose')
    monkeypatch.setattr(b, 'guarded_engine', owned)
    def take(connection, manifest):
        phases.append('snapshot')
        if failure == 'observer' and phases.count('snapshot') == 2: raise RuntimeError(MARKER)
        return Snapshot()
    monkeypatch.setattr(b, 'snapshot', take)
    def check(*args):
        phases.append('compare')
        if failure == 'compare': raise RuntimeError(MARKER)
    monkeypatch.setattr(b, 'compare', check)
    app = SimpleNamespace(state=SimpleNamespace(auth_engine=None, browser_shutdown_complete=True))
    monkeypatch.setattr(b, 'browser_app', lambda *a, **kw:(object(), app, object()))
    configs = []
    monkeypatch.setattr(b.uvicorn, 'Config', lambda *a, **kw:configs.append(kw))
    class Server:
        def drained(self): return not self.force_exit
        def __init__(self, config):
            self.started = failure != 'startup'
            self.force_exit = failure == 'forced'
        def run(self, **kwargs):
            phases.append('run-drained')
            if failure == 'callback': guard.failed.set()
            if failure == 'shutdown': raise RuntimeError(MARKER)
    monkeypatch.setattr(b, 'BrowserServer', Server)
    @contextmanager
    def reserved(): yield object()
    monkeypatch.setattr(b, 'reserved_socket', reserved)
    monkeypatch.setattr(b, 'hidden_password', lambda:MARKER)
    monkeypatch.setattr(b, 'read_scope', lambda p:scope)
    result = b.main(['serve','--confirm-merge-test','--revision','0003_auth','--manifest','scope.json','--allow-scoped-auth-writes'])
    assert result == (0 if failure == 'none' else 1)
    assert phases.count('snapshot') == 2 and phases.count('dispose') == 2
    assert phases.index('run-drained') < len(phases)-1
    assert configs[0]['host'] == '127.0.0.1' and configs[0]['workers'] == 1
    assert configs[0]['proxy_headers'] is False and configs[0]['forwarded_allow_ips'] == ''
    assert configs[0]['access_log'] is False and configs[0]['reload'] is False
    output = capsys.readouterr()
    assert MARKER not in output.out+output.err
    assert ('final invariants verified' in output.out) == (failure == 'none')


def test_occupied_port_stops_before_prompt(monkeypatch, scope, capsys):
    monkeypatch.setattr(b, 'read_scope', lambda p:scope)
    @contextmanager
    def occupied():
        raise OSError(MARKER)
        yield
    monkeypatch.setattr(b, 'reserved_socket', occupied)
    assert b.main(['serve','--confirm-merge-test','--revision','0003_auth','--manifest','scope.json','--allow-scoped-auth-writes']) == 1
    output = capsys.readouterr()
    assert MARKER not in output.out+output.err


@pytest.mark.parametrize('effect', ['credential-change','session-delete','session-retarget','terminal-revoke',
                                    'unscoped-revoke','too-many-sessions','bucket-delete','unrelated-bucket'])
def test_final_comparison_rejects_unapproved_effects(scope, effect):
    user, outside = scope.accounts[0].user_id, uuid4()
    before = Snapshot(unchanged={'credentials':(1,'same')}, sessions={b'old':(user,'same',None)})
    after = Snapshot(unchanged=dict(before.unchanged), sessions=dict(before.sessions))
    if effect == 'credential-change': after.unchanged['credentials'] = (1,'different')
    if effect == 'session-delete': after.sessions.clear()
    if effect == 'session-retarget': after.sessions[b'old'] = (outside,'same',None)
    if effect == 'terminal-revoke':
        before.sessions[b'old'] = (user,'same',1)
        after.sessions[b'old'] = (user,'same',2)
    if effect == 'unscoped-revoke':
        before.sessions[b'old'] = (outside,'same',None)
        after.sessions[b'old'] = (outside,'same',2)
    if effect == 'too-many-sessions': after.sessions.update({bytes([i]):(user,'same',None) for i in range(4)})
    if effect == 'bucket-delete': before.buckets[('scope',b'key',1)] = (1,2,'same')
    if effect == 'unrelated-bucket': after.buckets[('scope',b'key',1)] = (1,2,'same')
    with pytest.raises(database.DiagnosticFailure): compare(before, after, scope, SimpleNamespace(_key=lambda *a:b'key'))

@pytest.mark.parametrize('kind', ['account','team','session'])
def test_readonly_preflight_refuses_missing_account_or_broken_invariants(scope, kind):
    connection = MagicMock()
    calls = []
    def execute(statement, parameters=None):
        query = str(statement)
        calls.append(query)
        result = MagicMock()
        result.scalar_one_or_none.return_value = None if kind == 'account' else scope.accounts[0].user_id
        result.scalar_one.return_value = 1 if ((kind == 'team' and 'broken' in query)
                                               or (kind == 'session' and 'LEFT JOIN public.users' in query)) else 0
        return result
    connection.execute.side_effect = execute
    with pytest.raises(database.DiagnosticFailure): snapshot(connection, scope)
    assert calls[0] == 'SET TRANSACTION READ ONLY'
    assert all(q.startswith(('SET TRANSACTION READ ONLY','SELECT')) for q in calls)


def test_real_throttle_and_credential_failures_still_consume_harness_budget(api):
    from app.services.throttling import ThrottleExceeded
    from app.services.session_errors import SessionCode, SessionError
    api.throttle.check.side_effect = ThrottleExceeded(12)
    response = api.client.post('/auth/login', headers=HEADERS, json=BODY)
    assert response.status_code == 429 and response.headers['Retry-After'] == '12'
    api.sessions.login.assert_not_called()
    api.throttle.check.side_effect = None
    api.sessions.login.side_effect = SessionError(SessionCode.AUTHENTICATION_CHANGED)
    assert api.client.post('/auth/login', headers=HEADERS, json=BODY).status_code == 401
    assert api.client.post('/auth/login', headers=HEADERS, json=BODY).status_code == 401
    assert api.client.post('/auth/login', headers=HEADERS, json=BODY).status_code == 403
    assert api.throttle.check.call_count == 3


def test_connection_callback_exception_is_private_and_latches(capsys):
    c, guard = Connection(), b.ConnectionGuard()
    def fail(statement): raise RuntimeError(MARKER)
    c.execute = fail
    with pytest.raises(database.DiagnosticFailure) as error: guard(c)
    assert str(error.value) == 'verification' and c.invalid and guard.failed.is_set()
    output = capsys.readouterr()
    assert not output.out and not output.err


def test_production_packaging_and_imports_exclude_test_host():
    import ast
    import tomllib
    backend = Path(__file__).resolve().parents[1]
    config = tomllib.loads((backend/'pyproject.toml').read_text())
    assert config['tool']['setuptools']['packages']['find']['include'] == ['app*']
    for path in (backend/'app').rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not item.name.startswith('test_support') for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or '').startswith('test_support')

# M-011A-R3: these assert required safety behavior. The drain-timeout regression
# remains an unchanged safety requirement, corrected by the R4 host-only fix.
def test_drain_timeout_without_request_task_must_exit_nonzero(monkeypatch, scope, capsys):
    import asyncio
    from unittest.mock import AsyncMock

    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = object()
    guard = b.ConnectionGuard()
    @contextmanager
    def owned(settings):
        yield engine, guard
    monkeypatch.setattr(b, 'guarded_engine', owned)
    monkeypatch.setattr(b, 'snapshot', lambda *args:Snapshot())
    throttle = SimpleNamespace(_key=lambda *args:b'unit-key')
    app = SimpleNamespace(state=SimpleNamespace(auth_engine=None, browser_shutdown_complete=False))
    monkeypatch.setattr(b, 'browser_app', lambda *args, **kwargs:(object(), app, throttle))
    @contextmanager
    def reserved(): yield object()
    monkeypatch.setattr(b, 'reserved_socket', reserved)
    monkeypatch.setattr(b, 'hidden_password', lambda:MARKER)
    monkeypatch.setattr(b, 'read_scope', lambda path:scope)

    class IdleConnection:
        def shutdown(self): pass

    observed = {}
    def run_shutdown_only(server, **kwargs):
        # Never run/start/serve a backend or bind a socket. Exercise the installed
        # Uvicorn shutdown implementation with a fake lingering transport.
        server.started = True
        server.servers = []
        server.server_state.connections.add(IdleConnection())
        server.config.timeout_graceful_shutdown = 0  # same timeout branch; no 25s wait
        async def lifespan_shutdown():
            app.state.browser_shutdown_complete = True
        server.lifespan = SimpleNamespace(shutdown=AsyncMock(side_effect=lifespan_shutdown))
        asyncio.run(server.shutdown())
        observed.update(remaining=len(server.server_state.connections),
                        force_exit=server.force_exit, latched=guard.failed.is_set(),
                        shutdown_complete=app.state.browser_shutdown_complete)
    monkeypatch.setattr(b.uvicorn.Server, 'run', run_shutdown_only)
    result = b.main(['serve','--confirm-merge-test','--revision','0003_auth',
                     '--manifest','unused-audit-path','--allow-scoped-auth-writes'])
    output = capsys.readouterr()
    assert observed == dict(remaining=1, force_exit=False, latched=False, shutdown_complete=True)
    assert MARKER not in output.out+output.err
    assert result == 1, 'Drain timeout must fail, even without a cancelled ASGI request'
    assert 'final invariants verified' not in output.out


@pytest.mark.parametrize('case', ['missing-field','missing-account-id','malformed-json','bad-uuid','bad-username',
    'negative-budget','over-budget','string-budget','boolean-budget','float-budget','too-many-accounts',
    'duplicate-user','duplicate-username','secret-field','duplicate-key','oversized'])
def test_r3_manifest_scope_rejections_before_prompt_or_engine(monkeypatch, scope, capsys, case):
    from copy import deepcopy
    value = deepcopy(scope.model_dump(mode='json'))
    account = value['accounts'][0]
    if case == 'missing-field': value.pop('run_id')
    if case == 'missing-account-id': account.pop('user_id')
    if case == 'bad-uuid': account['user_id'] = 'not-a-uuid'
    if case == 'bad-username': account['username'] = 'Out Of Scope'
    if case == 'negative-budget': account['login_attempts'] = -1
    if case == 'over-budget': account['logout_attempts'] = 31
    if case == 'string-budget': account['login_attempts'] = '1'
    if case == 'boolean-budget': account['login_attempts'] = True
    if case == 'float-budget': account['login_attempts'] = 1.0
    if case == 'too-many-accounts': value['accounts'] *= 4
    if case == 'duplicate-user': value['accounts'].append(dict(account,username='other_user'))
    if case == 'duplicate-username': value['accounts'].append(dict(account,user_id=str(uuid4())))
    if case == 'secret-field': account['password'] = MARKER
    raw = json.dumps(value).encode()
    if case == 'malformed-json': raw = b'{'
    if case == 'duplicate-key': raw = b'{"run_id":"one","run_id":"two"}'
    if case == 'oversized': raw = b' '*8193
    path = MagicMock()
    path.read_bytes.return_value = raw
    with pytest.raises(ValueError): b.read_scope(path)
    output = capsys.readouterr()
    assert MARKER not in output.out+output.err


@pytest.mark.parametrize('extra', [{'user_id':'client-actor'}, {'login_attempts':30}, {'logout_attempts':30},
                                  {'run_id':'client-run'}, {'identity':{'username':'outside_user'}}])
def test_r3_client_cannot_supply_scope_fields(api, extra):
    result = api.client.post('/auth/login', headers=HEADERS, json={**BODY, **extra})
    assert result.status_code == 422
    api.throttle.check.assert_not_called()
    api.sessions.login.assert_not_called()


@pytest.mark.parametrize('path', ['/auth/register','/auth/%72egister','/auth/register/'])
def test_r3_registration_aliases_cannot_charge_throttle(api, path):
    result = api.client.post(path, headers=HEADERS, json=BODY)
    assert result.status_code == 403
    api.throttle.check.assert_not_called()
    api.sessions.login.assert_not_called()


@pytest.mark.parametrize('path', ['/api/teams','/api/hackathons','/api/hackathons/'+str(uuid4())+'/teams',
                                  '/api/teams/'+str(uuid4())+'/join','/api/invites/redeem'])
def test_r3_no_domain_mutation_route(api, path):
    result = api.client.post(path, headers=HEADERS, json={})
    assert result.status_code in (404,405)
    api.throttle.check.assert_not_called()
    api.sessions.revoke.assert_not_called()


def test_m012a_create_router_is_excluded_and_reintroduction_latches_closed(api):
    from app import team_api
    path = '/api/hackathons/' + str(uuid4()) + '/teams'
    api.client.cookies.set('merge_session_dev', auth.encode_token(b't'*32))
    result = api.client.post(path, headers={**HEADERS, 'X-CSRF-Token': auth.encode_token(b'c'*32),
                             'Idempotency-Key': 'unapproved-create'}, json={'name': 'Forbidden'})
    assert result.status_code == 405
    api.sessions.verify_csrf.assert_not_called()
    # Even trusted code accidentally reinstalling the new router must be rejected
    # before its unoverridden database dependency can resolve ordinary Settings.
    api.app.include_router(team_api.router)
    try:
        assert api.client.post(path, headers=HEADERS, json={'name': 'Forbidden'}).status_code == 503
        assert api.client.get('/health').status_code == 503
        api.sessions.verify_csrf.assert_not_called()
    finally:
        api.app.routes.pop()


def test_r3_missing_manifest_refuses_without_prompt(monkeypatch, capsys):
    missing = MagicMock()
    missing.read_bytes.side_effect = FileNotFoundError(MARKER)
    monkeypatch.setattr(b, 'arguments', lambda argv:SimpleNamespace(manifest=missing, action='inspect'))
    assert b.main([]) == 1
    output = capsys.readouterr()
    assert MARKER not in output.out+output.err

@pytest.fixture
def r4_host(monkeypatch, scope):
    """Run only real Uvicorn shutdown, never startup/serve/listeners/PostgreSQL."""
    from unittest.mock import AsyncMock
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = object()
    guard = b.ConnectionGuard()
    app = SimpleNamespace(state=SimpleNamespace(auth_engine=None, browser_shutdown_complete=False))
    state = SimpleNamespace(phases=[], fail=None, snapshots=0, worker_active=False, server=None)
    @contextmanager
    def owned(settings):
        state.phases.append('engine-enter')
        try: yield engine, guard
        finally:
            state.phases.append('engine-dispose')
            if state.fail == 'engine-dispose': raise RuntimeError(MARKER)
    monkeypatch.setattr(b, 'guarded_engine', owned)
    def take(*args):
        state.snapshots += 1
        state.phases.append('snapshot')
        if state.snapshots == 2:
            if state.fail == 'observer': raise RuntimeError(MARKER)
            if state.fail == 'interrupt-observer': raise KeyboardInterrupt()
            if state.fail == 'residual-cleared-in-observer':
                state.server.server_state.tasks.clear()
            assert not state.worker_active, 'Normal final verification must follow worker completion'
        return Snapshot()
    monkeypatch.setattr(b, 'snapshot', take)
    def check(*args):
        state.phases.append('compare')
        if state.fail == 'compare': raise RuntimeError(MARKER)
        compare(*args)
    monkeypatch.setattr(b, 'compare', check)
    throttle = SimpleNamespace(_key=lambda *args:b'unit-key')
    monkeypatch.setattr(b, 'browser_app', lambda *args, **kwargs:(object(), app, throttle))
    class Socket:
        def close(self): state.phases.append('socket-close')
    @contextmanager
    def reserved():
        try: yield Socket()
        finally:
            state.phases.append('socket-context-exit')
            if state.fail == 'socket-exit': raise RuntimeError(MARKER)
    monkeypatch.setattr(b, 'reserved_socket', reserved)
    monkeypatch.setattr(b, 'hidden_password', lambda:MARKER)
    monkeypatch.setattr(b, 'read_scope', lambda path:scope)
    class Listener:
        def close(self): state.phases.append('listener-close')
        async def wait_closed(self):
            state.phases.append('listener-closed')
            if state.fail == 'listener-close': raise RuntimeError(MARKER)
    async def lifespan_shutdown():
        state.phases.append('lifespan-shutdown')
        if state.fail == 'lifespan': raise RuntimeError(MARKER)
        app.state.browser_shutdown_complete = True
    def prepare(server):
        state.server = server
        server.started = True
        server.servers = [Listener()]
        server.lifespan = SimpleNamespace(shutdown=AsyncMock(side_effect=lifespan_shutdown))
    state.prepare = prepare
    state.argv = ['serve','--confirm-merge-test','--revision','0003_auth',
                  '--manifest','unused-r4-unit-path','--allow-scoped-auth-writes']
    return state


@pytest.mark.parametrize('first_interrupt', [False,True])
def test_r4_clean_drain_waits_for_worker_then_verifies_and_closes(monkeypatch, r4_host, capsys, first_interrupt):
    import asyncio
    from threading import Event
    state = r4_host
    entered, release = Event(), Event()
    def worker():
        state.worker_active = True
        entered.set()
        try:
            assert release.wait(2), 'Offline worker release timed out'
        finally:
            state.worker_active = False
            state.phases.append('worker-finished')
    async def scenario(server, sockets):
        state.prepare(server)
        task = asyncio.create_task(asyncio.to_thread(worker))
        server.server_state.tasks.add(task)
        task.add_done_callback(server.server_state.tasks.discard)
        assert await asyncio.to_thread(entered.wait,2)
        original_close = server.servers[0].close
        def stop_accepting():
            original_close()
            release.set()
        server.servers[0].close = stop_accepting
        try: await server.shutdown(sockets=sockets)
        finally:
            release.set()
            await task
        assert server.drained() and not state.worker_active
    def run(server, sockets):
        asyncio.run(scenario(server,sockets))
        if first_interrupt: raise KeyboardInterrupt()
    monkeypatch.setattr(b.uvicorn.Server, 'run', run)
    assert b.main(state.argv) == 0
    assert state.snapshots == 2
    phases = state.phases
    assert phases.index('listener-close') < phases.index('worker-finished') < phases.index('lifespan-shutdown')
    assert phases.index('worker-finished') < len(phases)-1-phases[::-1].index('snapshot')
    assert phases[-1] == 'socket-context-exit'
    assert not state.worker_active and not state.server.server_state.tasks
    output = capsys.readouterr()
    assert 'final invariants verified' in output.out and MARKER not in output.out+output.err


def test_r4_timeout_with_request_does_not_confuse_cancel_with_worker_stop(monkeypatch, r4_host, capsys):
    import asyncio
    from threading import Event, Thread
    state = r4_host
    entered, release, finished = Event(), Event(), Event()
    def worker():
        state.worker_active = True
        entered.set()
        try: release.wait(2)
        finally:
            state.worker_active = False
            finished.set()
    thread = Thread(target=worker)
    thread.start()
    assert entered.wait(2)
    async def scenario(server,sockets):
        state.prepare(server)
        request = asyncio.create_task(asyncio.Event().wait())
        server.server_state.tasks.add(request)
        request.add_done_callback(server.server_state.tasks.discard)
        server.config.timeout_graceful_shutdown = 0
        try:
            await server.shutdown(sockets=sockets)
            assert state.worker_active, 'Cancelling an ASGI task must not imply a worker stopped'
            assert server.drain_failed and not server.drained()
            await asyncio.sleep(0)
            assert request.cancelled()
        finally:
            release.set()
    def run(server,sockets):
        asyncio.run(scenario(server,sockets))
        assert finished.wait(2)
        thread.join(2)
    monkeypatch.setattr(b.uvicorn.Server, 'run', run)
    try:
        assert b.main(state.argv) == 1
        assert state.snapshots == 2  # successful later snapshots cannot clear failure
        assert state.server.drain_failed
        assert state.phases[-1] == 'socket-context-exit'
        output = capsys.readouterr()
        assert 'final invariants verified' not in output.out and MARKER not in output.out+output.err
    finally:
        release.set()
        thread.join(2)


@pytest.mark.parametrize('failure', ['observer','compare','engine-dispose','socket-exit','listener-close','lifespan',
                                     'double-interrupt','interrupt-observer','residual-request','residual-cleared-in-observer'])
def test_r4_shutdown_and_cleanup_failures_never_report_success(monkeypatch, r4_host, capsys, failure):
    import asyncio
    import signal
    state = r4_host
    state.fail = failure
    async def scenario(server,sockets):
        state.prepare(server)
        if failure == 'double-interrupt':
            server.handle_exit(signal.SIGINT,None)
            server.handle_exit(signal.SIGINT,None)
        await server.shutdown(sockets=sockets)
        if failure in ('residual-request','residual-cleared-in-observer'):
            server.server_state.tasks.add(object())
    def run(server,sockets):
        asyncio.run(scenario(server,sockets))
        if failure == 'double-interrupt': raise KeyboardInterrupt()
    monkeypatch.setattr(b.uvicorn.Server, 'run', run)
    assert b.main(state.argv) == 1
    assert state.phases[-1] == 'socket-context-exit'
    output = capsys.readouterr()
    assert 'final invariants verified' not in output.out and MARKER not in output.out+output.err


def test_r4_drain_timeout_before_callback_entry_is_sticky(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    server = b.BrowserServer(b.uvicorn.Config(object(), log_config=None))
    server.started = True
    server.servers = []
    server.config.timeout_graceful_shutdown = 0
    server.lifespan = SimpleNamespace(shutdown=AsyncMock())
    asyncio.run(server.shutdown())
    assert server.drain_failed and not server.drained()
    server.drain_complete = True
    assert not server.drained(), 'Later completion cannot erase the failed acceptance run'
