"""Railway adapter tests use synthetic env/connections/processes only."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr, SecretBytes
import psycopg
import pytest
from sqlalchemy.engine import Engine
from app.railway import config, database, application, check, operations, api, serve
from app.auth import AuthServices, get_services, encode_token
from app.services.sessions import SessionPrincipal, IssuedSession, ValidatedSession

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'https://merge-synthetic.up.railway.app'  # Synthetic, never a deployed URL.
ADDRESS = 'fd12::1234'


def environment():
    return {'RAILWAY_ENVIRONMENT_NAME': 'production', 'RAILWAY_PROJECT_ID': str(uuid4()),
            'RAILWAY_ENVIRONMENT_ID': str(uuid4()), 'RAILWAY_PUBLIC_DOMAIN': 'merge-synthetic.up.railway.app',
            'PORT': '8080', 'MERGE_RAILWAY_DB_HOST': config.DB_HOST,
            'MERGE_RAILWAY_RUNTIME_PASSWORD': 'r' * 48, 'MERGE_RAILWAY_THROTTLE_KEY': 'a' * 64}


def target(role='runtime'):
    return config.RailwayConfig(role, SecretStr(('r' if role == 'runtime' else 'm') * 48), ORIGIN,
                                SecretStr('a' * 64) if role == 'runtime' else None)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*a, **k): pytest.fail('Real database or DNS reached from offline test')
    monkeypatch.setattr(psycopg, 'connect', blocked)
    monkeypatch.setattr(database.socket, 'getaddrinfo', blocked)


@pytest.mark.parametrize('change', [
    {'RAILWAY_ENVIRONMENT_NAME': 'staging'}, {'RAILWAY_ENVIRONMENT_NAME': ''},
    {'RAILWAY_PROJECT_ID': 'bad'}, {'RAILWAY_ENVIRONMENT_ID': ''},
    {'MERGE_RAILWAY_DB_HOST': 'localhost'}, {'MERGE_RAILWAY_DB_HOST': 'public.example.org'},
    {'MERGE_RAILWAY_DB_HOST': 'merge_test'}, {'PORT': '8000'}, {'PORT': ''}, {'PORT': '80'},
    {'PORT': '65536'}, {'PORT': '8080\n'}, {'PORT': '0x2000'},
    {'RAILWAY_PUBLIC_DOMAIN': ''}, {'RAILWAY_PUBLIC_DOMAIN': 'https://merge-synthetic.up.railway.app'},
    {'RAILWAY_PUBLIC_DOMAIN': 'other.org'}, {'RAILWAY_PUBLIC_DOMAIN': 'a.up.railway.app.evil.org'},
    {'RAILWAY_PUBLIC_DOMAIN': 'a.up.railway.app/'}, {'RAILWAY_PUBLIC_DOMAIN': 'A.up.railway.app'},
    {'MERGE_RAILWAY_RUNTIME_PASSWORD': 'short'}, {'MERGE_RAILWAY_THROTTLE_KEY': 'A' * 64},
    {'MERGE_AUTH_MODE': 'development'}, {'MERGE_DB_NAME': 'merge_dev'},
    {'DATABASE_URL': 'synthetic-forbidden'}, {'DATABASE_PUBLIC_URL': 'synthetic-forbidden'},
    {'PGHOST': 'localhost'}, {'VITE_SECRET': 'synthetic-forbidden'},
    {'MERGE_RAILWAY_ADMIN_PASSWORD': 's' * 48}, {'MERGE_RAILWAY_MIGRATOR_PASSWORD': 's' * 48},
    {'RAILWAY_TCP_PROXY_DOMAIN': 'synthetic-tcp.example.org'}])
def test_runtime_rejects_unsafe_or_missing_inputs_before_dns(change):
    with pytest.raises(ValueError): config.load(environ=environment() | change)


def test_runtime_config_fixes_production_auth_and_private_target_without_secrets_in_repr():
    selected = config.load(environ=environment())
    url = selected.url()
    assert (url.host, url.port, url.database, url.username) == (config.DB_HOST, 5432, 'merge_prod', 'merge_runtime')
    policy = selected.auth()
    assert policy.secure and policy.cookie_name == '__Host-merge_session'
    assert policy.trusted_proxies == ('127.0.0.1/32',) and policy.origin == ORIGIN
    assert selected.password.get_secret_value() not in repr(selected)
    assert selected.throttle_key.get_secret_value() not in repr(selected)
    assert config.port({'PORT': '43210'}) == 43210


def test_operations_have_explicit_action_and_separate_secrets():
    env = environment()
    for key in ('RAILWAY_PUBLIC_DOMAIN', 'PORT', 'MERGE_RAILWAY_RUNTIME_PASSWORD', 'MERGE_RAILWAY_THROTTLE_KEY'): env.pop(key)
    env |= {'MERGE_RAILWAY_ACTION': 'prepare', 'MERGE_RAILWAY_MIGRATOR_PASSWORD': 'm' * 48}
    action, selected = config.operation_environment(env)
    assert action == 'prepare' and selected.url().username == 'merge_migrator'
    for change in ({'MERGE_RAILWAY_ACTION': ''}, {'MERGE_RAILWAY_ACTION': 'downgrade'},
                   {'MERGE_RAILWAY_ADMIN_PASSWORD': 's' * 48}, {'RAILWAY_PUBLIC_DOMAIN': 'a.up.railway.app'},
                   {'MERGE_RAILWAY_RUNTIME_PASSWORD': 'r' * 48}, {'RAILWAY_TCP_PROXY_DOMAIN': 'tcp.example.org'}):
        with pytest.raises(ValueError): config.operation_environment(env | change)
    with pytest.raises(ValueError): selected.auth()


@pytest.mark.parametrize('addresses', [[], ['127.0.0.1'], ['::1'], ['8.8.8.8'], ['fd12::1234', '8.8.8.8']])
def test_private_dns_rejects_empty_public_or_loopback(monkeypatch, addresses):
    monkeypatch.setattr(database.socket, 'getaddrinfo', lambda *a, **k: [(None, None, None, None, (ip, 5432)) for ip in addresses])
    with pytest.raises(ValueError): database.private_addresses()


def test_private_dns_accepts_only_resolved_private_addresses_and_pins_connect(monkeypatch):
    monkeypatch.setattr(database.socket, 'getaddrinfo', lambda *a, **k: [(None, None, None, None, (ADDRESS, 5432))] * 2)
    assert database.private_addresses() == (ADDRESS,)
    created = []
    monkeypatch.setattr(database, 'create_engine', lambda *a, **k: created.append((a, k)) or MagicMock())
    monkeypatch.setattr(database.event, 'listen', lambda *a: None)
    database.engine(target())
    kwargs = created[0][1]
    assert kwargs['connect_args']['hostaddr'] == ADDRESS
    assert kwargs['connect_args']['sslmode'] == 'require'
    assert kwargs['isolation_level'] == 'READ COMMITTED' and kwargs['hide_parameters'] is True
    assert kwargs['pool_size'] == 5 and kwargs['max_overflow'] == 5


class Connection:
    def __init__(self):
        self.active = False
        self.invalid = False
        self.calls = []
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.who = ('merge_prod', 'merge_runtime', ADDRESS, 5432)
        self.version = 170004
        self.ssl = True
        self.flags = (False,) * 5
        self.member = False
        self.permissions = (True, True, False, False, False)
        self.revision = ['0006_profiles']
        self.settings = ('read committed', 'read committed', 'on', '5s', '15s', 'off', False)
    def in_transaction(self): return self.active
    def in_nested_transaction(self): return False
    def get_execution_options(self): return {}
    def execute(self, q, *a):
        q = str(q)
        self.calls.append(q)
        self.active = True
        one = self.who if 'current_database(),current_user' in q else self.flags if 'SELECT rolsuper' in q else self.permissions if 'has_database_privilege' in q else self.settings
        scalar = self.version if 'server_version_num' in q else self.ssl if 'pg_stat_ssl' in q else self.member if 'pg_auth_members' in q else True
        return SimpleNamespace(one=lambda: one, scalar_one=lambda: scalar,
                               scalars=lambda: SimpleNamespace(all=lambda: self.revision))
    def rollback(self): self.active = False
    def invalidate(self): self.invalid = True


@pytest.mark.parametrize('change', ['database', 'role', 'address', 'port', 'version16', 'version18', 'tls',
    'flags', 'member', 'schema', 'revision', 'duplicate_revision', 'autocommit', 'transaction',
    'driver', 'read_only', 'standby', 'timeouts'])
def test_railway_guard_fails_closed_and_poisoned(change):
    c = Connection()
    guard = database.Guard(target(), (ADDRESS,))
    if change == 'database': c.who = ('merge_test', *c.who[1:])
    elif change == 'role': c.who = (c.who[0], 'postgres', *c.who[2:])
    elif change == 'address': c.who = (*c.who[:2], 'fd12::9999', 5432)
    elif change == 'port': c.who = (*c.who[:3], 5433)
    elif change == 'version16': c.version = 160008
    elif change == 'version18': c.version = 180000
    elif change == 'tls': c.ssl = False
    elif change == 'flags': c.flags = (True, False, False, False, False)
    elif change == 'member': c.member = True
    elif change == 'schema': c.permissions = (True, True, True, False, False)
    elif change == 'revision': c.revision = ['0005_invitations']
    elif change == 'duplicate_revision': c.revision *= 2
    elif change == 'autocommit': c.connection.dbapi_connection.autocommit = True
    elif change == 'transaction': c.active = True
    elif change == 'driver': c.dialect.driver = 'other'
    elif change == 'read_only': c.settings = (*c.settings[:5], 'on', False)
    elif change == 'standby': c.settings = (*c.settings[:6], True)
    else: c.settings = (*c.settings[:3], '0', '0', *c.settings[5:])
    with pytest.raises(ValueError): guard(c)
    assert c.invalid and guard.failed.is_set()
    with pytest.raises(ValueError): guard(Connection())


def test_guard_closes_each_preflight_and_cannot_relax_runtime_revision():
    guard = database.Guard(target(), (ADDRESS,))
    for _ in range(2):
        c = Connection()
        guard(c)
        assert c.calls[0] == 'SET TRANSACTION READ ONLY' and not c.active
    for revision in (None, '0005_invitations', 'head'):
        with pytest.raises(ValueError): database.Guard(target(), (ADDRESS,), revision)


def package():
    return json.loads((ROOT / 'deploy/railway/caddy.template.json').read_text())


@pytest.mark.parametrize('unsafe', ['listener', 'admin', 'tls', 'host', 'proto', 'client_ip', 'public_ready',
                                   'upstream', 'flush', 'lease', 'forwarded', 'identity_capture', 'assets'])
def test_caddy_template_rejects_security_and_sse_drift(unsafe):
    template = package()
    server = template['apps']['http']['servers']['railway']
    public = server['routes'][1]
    routes = public['handle'][0]['routes']
    proxy = routes[2]['handle'][0]
    if unsafe == 'listener': server['listen'] = [':8000']
    elif unsafe == 'admin': template['admin']['disabled'] = False
    elif unsafe == 'tls': server['automatic_https']['disable'] = False
    elif unsafe == 'host': public['match'][0]['host'] = ['*']
    elif unsafe == 'proto': public['match'][0]['header']['X-Forwarded-Proto'] = ['*']
    elif unsafe == 'client_ip': del public['match'][0]['header']['X-Real-IP']
    elif unsafe == 'public_ready': routes[1]['match'][0]['path'].remove('/ready')
    elif unsafe == 'upstream': proxy['upstreams'] = [{'dial': '0.0.0.0:8000'}]
    elif unsafe == 'flush': proxy['flush_interval'] = 1000000000
    elif unsafe == 'lease': proxy['stream_timeout'] = '5s'
    elif unsafe == 'forwarded': proxy['headers']['request']['set']['X-Forwarded-For'] = ['{http.request.header.X-Forwarded-For}']
    elif unsafe == 'identity_capture': routes[0]['handle'][0]['railway_client_ip'] = '{http.request.header.X-Forwarded-For}'
    else: routes[3]['handle'][1]['root'] = '/tmp'
    with pytest.raises(ValueError): check.validate_template(template)


def test_packaging_generates_exact_hostname_dynamic_port_and_no_build_secret_inputs():
    template = package()
    generated = check.caddy(target(), 54321, template)
    server = generated['apps']['http']['servers']['railway']
    assert server['listen'] == [':54321']
    assert server['routes'][1]['match'][0]['host'] == ['merge-synthetic.up.railway.app']
    assert template['apps']['http']['servers']['railway']['listen'] == [':8080']
    assert check.validate_settings(json.loads((ROOT / 'deploy/railway/settings.json').read_text())) == config.REVISION
    docker = (ROOT / 'deploy/Dockerfile.railway').read_text()
    assert 'COPY --from=frontend /build/dist /srv/merge/web' in docker and 'USER 10001:10001' in docker
    assert not any(line.startswith(('ARG ', 'EXPOSE ')) for line in docker.splitlines())
    assert 'test_support' not in docker and 'alembic upgrade' not in docker


@pytest.mark.parametrize('unsafe', ['predeploy', 'replicas', 'sleep', 'health', 'db_port', 'ops_restart'])
def test_dashboard_contract_rejects_unsafe_settings(unsafe):
    settings = json.loads((ROOT / 'deploy/railway/settings.json').read_text())
    if unsafe == 'predeploy': settings['application']['preDeployCommand'] = 'alembic upgrade head'
    elif unsafe == 'replicas': settings['application']['numReplicas'] = 2
    elif unsafe == 'sleep': settings['application']['sleepApplication'] = True
    elif unsafe == 'health': settings['application']['healthcheckPath'] = '/health'
    elif unsafe == 'db_port': settings['database']['tcpProxy'] = True
    else: settings['operations']['restartPolicyType'] = 'ON_FAILURE'
    with pytest.raises(ValueError): check.validate_settings(settings)


@pytest.fixture
def railway_app(monkeypatch):
    resource = MagicMock(spec=Engine)
    resource.hide_parameters = True
    resource.echo = False
    monkeypatch.setattr(config, 'load', lambda: target())
    monkeypatch.setattr(database, 'engine', lambda *a, **k: resource)
    monkeypatch.setattr(database, 'ready', lambda *a: None)
    return application.create_railway_app(), resource


def test_runtime_lifecycle_preserves_auth_csrf_secure_cookie_and_client_throttle(railway_app, monkeypatch):
    app, resource = railway_app
    monkeypatch.setattr(operations.command, 'upgrade', lambda *a: pytest.fail('Startup DDL reached'))
    now = datetime.now(timezone.utc)
    principal = SessionPrincipal(uuid4(), 'railway_user', now + timedelta(hours=8))
    issued = IssuedSession(principal, now, SecretBytes(b't' * 32), SecretBytes(b'c' * 32))
    sessions = MagicMock()
    sessions.login.return_value = issued
    sessions.validate_with_csrf.return_value = ValidatedSession(principal, issued.csrf_token)
    services = AuthServices(MagicMock(), sessions, MagicMock())
    app.dependency_overrides[get_services] = lambda: services
    headers = {'Origin': ORIGIN, 'X-Forwarded-For': '192.0.2.8', 'X-Forwarded-Proto': 'https', 'X-Merge-Request': '1'}
    with TestClient(app, base_url=ORIGIN, client=('127.0.0.1', 12345)) as client:
        assert client.get('/ready').status_code == 200
        assert client.get('/docs').status_code == 404
        assert client.post('/auth/login', headers=headers | {'Origin': 'https://evil.org'}, json={}).status_code == 403
        assert client.get('/auth/session', headers=headers | {'X-Forwarded-Proto': 'http'}).status_code == 403
        assert client.get('/auth/session', headers=headers | {'Forwarded': 'for=192.0.2.8'}).status_code == 403
        assert client.get('/api/hackathons/' + str(uuid4()) + '/events', headers=headers).status_code == 401
        response = client.post('/auth/login', headers=headers, json={'username': 'railway_user', 'password': 'synthetic private passphrase'})
        assert response.status_code == 200
        cookie = response.headers['set-cookie']
        assert cookie.startswith('__Host-merge_session=') and 'Domain=' not in cookie
        assert all(s in cookie for s in ('Secure', 'HttpOnly', 'SameSite=lax', 'Path=/'))
        assert 'no-store' in response.headers['cache-control'] and 'access-control-allow-origin' not in response.headers
        services.throttle.check.assert_called_once_with(operation='login', client_ip='192.0.2.8', username='railway_user')
        assert client.post('/auth/logout', headers=headers, json={}).status_code == 403
        sessions.revoke.assert_not_called()
        assert client.post('/auth/logout', headers=headers | {'X-CSRF-Token': encode_token(b'c' * 32)}, json={}).status_code == 204
    resource.connect.assert_not_called()
    resource.dispose.assert_called_once()


def test_runtime_readiness_and_startup_fail_closed_without_private_error(railway_app, monkeypatch):
    app, resource = railway_app
    with TestClient(app, base_url=ORIGIN) as client:
        monkeypatch.setattr(database, 'ready', lambda *a: (_ for _ in ()).throw(ValueError('synthetic-private-error')))
        assert client.get('/ready').json() == {'status': 'unavailable'}
        assert client.get('/ready').status_code == 503
    with pytest.raises(RuntimeError, match='private details suppressed') as error:
        with TestClient(app): pass
    assert 'synthetic-private-error' not in str(error.value)
    assert resource.dispose.call_count == 2


def test_migration_failure_rolls_back_ddl_grants_and_preservation(monkeypatch):
    events = []
    class Migrating:
        def in_transaction(self): return False
        @contextmanager
        def begin(self):
            events.append('begin')
            try: yield; events.append('commit')
            except Exception: events.append('rollback'); raise
        def execute(self, *a): return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [config.PREVIOUS]))
    monkeypatch.setattr(database, 'identity', lambda *a: None)
    snapshots = iter([{'users': (2, 'a')}, {'users': (2, 'b')}])
    monkeypatch.setattr(operations, 'snapshot', lambda *a: next(snapshots))
    monkeypatch.setattr(operations.command, 'upgrade', lambda *a: events.append('ddl'))
    monkeypatch.setattr(operations.grants, 'apply', lambda *a: events.append('grants'))
    with pytest.raises(ValueError): operations.migration(Migrating(), target('migrator'), (ADDRESS,), 'migrate')
    assert events == ['begin', 'ddl', 'grants', 'rollback']


def test_bootstrap_refuses_existing_production_namespace_before_any_ddl(monkeypatch):
    statements = []
    class Admin:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, q):
            statements.append(str(q))
            result = ('postgres', 'postgres', ADDRESS, 5432) if 'current_database()' in q else (170004,) if 'server_version_num' in q else (True,)
            return SimpleNamespace(fetchone=lambda: result)
        def transaction(self): pytest.fail('DDL transaction reached for existing namespace')
    monkeypatch.setattr(psycopg, 'connect', lambda **k: Admin())
    env = {'MERGE_RAILWAY_ADMIN_PASSWORD': 'a' * 48, 'MERGE_RAILWAY_RUNTIME_PASSWORD': 'r' * 48}
    with pytest.raises(ValueError): operations.bootstrap(env, target('migrator'), (ADDRESS,))
    assert len(statements) == 4
    assert all(not q.startswith(('CREATE ', 'ALTER ', 'DROP ', 'DELETE ')) for q in statements)


def test_bootstrap_requires_distinct_secrets_before_connect():
    with pytest.raises(ValueError): operations.bootstrap({'MERGE_RAILWAY_ADMIN_PASSWORD': 'r' * 48, 'MERGE_RAILWAY_RUNTIME_PASSWORD': 'r' * 48}, target('migrator'), (ADDRESS,))


class Process:
    def __init__(self, name, events, status=None, stall=False):
        self.name, self.events, self.status, self.stall = name, events, status, stall
    def poll(self): return self.status
    def terminate(self): self.events.append(self.name + ':term')
    def wait(self, timeout):
        if self.stall:
            self.stall = False
            raise subprocess.TimeoutExpired(self.name, timeout)
        self.events.append(self.name + ':wait')
        return 0
    def kill(self): self.events.append(self.name + ':kill')


def test_supervisor_exits_on_edge_failure_and_stops_both_children(monkeypatch):
    events = []
    children = iter([Process('api', events), Process('edge', events, status=0)])
    monkeypatch.setattr(serve.subprocess, 'Popen', lambda *a, **k: next(children))
    monkeypatch.setattr(serve, 'wait_for_api', lambda *a: True)
    stopped = SimpleNamespace(is_set=lambda: False, wait=lambda *a: False)
    assert serve.supervise('synthetic.json', stopped, {}) == 1
    assert 'api:term' in events and 'edge:wait' in events and 'api:wait' in events


def test_supervisor_graceful_shutdown_drains_edge_first_and_bounds_hung_child():
    events = []
    children = [Process('api', events), Process('edge', events, stall=True)]
    serve.stop_children(children, timeout=0)
    assert events[:2] == ['edge:term', 'api:term']
    assert 'edge:kill' in events and events[-1] == 'api:wait'


def test_supervisor_cleans_up_api_when_caddy_launch_fails(monkeypatch):
    events = []
    def launch(args, **kwargs):
        if args[0] == 'caddy': raise OSError('synthetic launch failure')
        return Process('api', events)
    monkeypatch.setattr(serve.subprocess, 'Popen', launch)
    monkeypatch.setattr(serve, 'wait_for_api', lambda *a: True)
    stopped = SimpleNamespace(is_set=lambda: False, wait=lambda *a: True)
    with pytest.raises(OSError): serve.supervise('synthetic.json', stopped, {})
    assert events == ['api:term', 'api:wait']


def test_private_worker_uses_one_loopback_worker_and_no_proxy_middleware(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['api'])
    monkeypatch.setattr(api, 'load', lambda: target())
    calls = []
    monkeypatch.setattr(api.uvicorn, 'run', lambda *a, **k: calls.append((a, k)))
    api.main()
    kwargs = calls[0][1]
    assert kwargs['host'] == '127.0.0.1' and kwargs['port'] == 8000 and kwargs['workers'] == 1
    assert kwargs['proxy_headers'] is False and kwargs['access_log'] is False and kwargs['forwarded_allow_ips'] == ''


def test_supervisor_supplies_no_runtime_secrets_to_caddy(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'argv', ['serve'])
    monkeypatch.setenv('PORT', '8080')
    monkeypatch.setattr(config, 'load', lambda: target())
    monkeypatch.setattr(serve, 'TEMPLATE', ROOT / 'deploy/railway/caddy.template.json')
    monkeypatch.setattr(serve.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0))
    captured = []
    monkeypatch.setattr(serve, 'supervise', lambda filename, stopped, env: captured.append((Path(filename), dict(env))) or 0)
    with pytest.raises(SystemExit) as result: serve.main()
    assert result.value.code == 0
    assert set(captured[0][1]) == {'PATH', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME'}
    assert not captured[0][0].exists()


def test_explicit_operations_invalid_config_is_sanitized_before_dns(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['operations', '--confirm-merge-prod'])
    monkeypatch.setattr(config, 'operation_environment', lambda *a: (_ for _ in ()).throw(ValueError('synthetic-private-error')))
    with pytest.raises(SystemExit) as result: operations.main()
    output = capsys.readouterr().out
    assert result.value.code == 1 and 'synthetic-private-error' not in output
    assert json.loads(output)['action'] == 'configuration'


@pytest.mark.parametrize('action', ['prepare', 'migrate'])
def test_explicit_migration_success_owns_transaction_and_uses_exact_versions(monkeypatch, action):
    events = []
    class Migrating:
        revision = config.PREVIOUS
        def in_transaction(self): return False
        @contextmanager
        def begin(self):
            events.append('begin')
            try: yield; events.append('commit')
            except Exception: events.append('rollback'); raise
        def execute(self, q):
            return SimpleNamespace(scalar_one=lambda: 0,
                scalars=lambda: SimpleNamespace(all=lambda: [self.revision]))
    c = Migrating()
    monkeypatch.setattr(database, 'identity', lambda *a: events.append('identity'))
    monkeypatch.setattr(operations, 'snapshot', lambda *a: {'users': (0, 'synthetic-digest')})
    def upgrade(cfg, final):
        assert cfg.attributes['railway_connection'] is c
        assert cfg.attributes['railway_addresses'] == (ADDRESS,)
        assert cfg.get_main_option('script_location').endswith('railway_alembic')
        c.revision = final
        events.append('ddl:' + final)
    monkeypatch.setattr(operations.command, 'upgrade', upgrade)
    monkeypatch.setattr(operations.grants, 'apply', lambda c, rev: events.append('grants:' + rev))
    result = operations.migration(c, target('migrator'), (ADDRESS,), action)
    final = config.PREVIOUS if action == 'prepare' else config.REVISION
    assert result == {'revision': final, 'old_tables_preserved': action == 'migrate'}
    assert events == ['begin', 'identity', 'ddl:' + final, 'grants:' + final, 'commit']


def test_bootstrap_success_creates_only_new_namespace_and_restricts_grants(monkeypatch):
    statements, kwargs_seen = [], []
    class Admin:
        def __init__(self, db): self.db = db
        def __enter__(self): return self
        def __exit__(self, *a): pass
        @contextmanager
        def transaction(self): yield
        def execute(self, q):
            rendered = q.as_string() if hasattr(q, 'as_string') else q
            statements.append(rendered)
            result = (self.db, 'postgres', ADDRESS, 5432) if 'current_database()' in rendered else (170004,) if 'server_version_num' in rendered else (True,) if 'pg_stat_ssl' in rendered else (False,)
            return SimpleNamespace(fetchone=lambda: result)
    def connect(**kwargs):
        kwargs_seen.append(kwargs)
        return Admin(kwargs['dbname'])
    monkeypatch.setattr(psycopg, 'connect', connect)
    env = {'MERGE_RAILWAY_ADMIN_PASSWORD': 'a' * 48, 'MERGE_RAILWAY_RUNTIME_PASSWORD': 'r' * 48}
    operations.bootstrap(env, target('migrator'), (ADDRESS,))
    assert [k['dbname'] for k in kwargs_seen] == ['postgres', 'merge_prod']
    assert all(k['host'] == config.DB_HOST and k['hostaddr'] == ADDRESS and k['sslmode'] == 'require' for k in kwargs_seen)
    assert all('log_min_error_statement=panic' in k['options'] for k in kwargs_seen)
    assert 'CREATE DATABASE merge_prod TEMPLATE template0' in statements
    assert sum(q.startswith('CREATE ROLE ') for q in statements) == 2
    assert 'REVOKE ALL ON DATABASE merge_prod FROM PUBLIC' in statements
    assert not any(q.startswith(('DROP ', 'DELETE ', 'TRUNCATE ', 'ALTER ROLE ', 'ALTER DATABASE ')) for q in statements)


def test_wait_for_api_rejects_dead_child_without_probe(monkeypatch):
    monkeypatch.setattr(serve, 'api_ready', lambda: pytest.fail('Probe after child death'))
    stopped = SimpleNamespace(is_set=lambda: False)
    assert serve.wait_for_api(SimpleNamespace(poll=lambda: 1), stopped) is False


def test_wait_for_api_success_uses_bounded_local_readiness(monkeypatch):
    monkeypatch.setattr(serve, 'api_ready', lambda: True)
    stopped = SimpleNamespace(is_set=lambda: False)
    assert serve.wait_for_api(SimpleNamespace(poll=lambda: None), stopped) is True


def test_supervisor_clean_stop_terminates_and_reaps_both_children(monkeypatch):
    events = []
    children = iter([Process('api', events), Process('edge', events)])
    monkeypatch.setattr(serve.subprocess, 'Popen', lambda *a, **k: next(children))
    monkeypatch.setattr(serve, 'wait_for_api', lambda *a: True)
    stopped = SimpleNamespace(is_set=lambda: False, wait=lambda *a: True)
    assert serve.supervise('synthetic.json', stopped, {}) == 0
    assert events == ['edge:term', 'api:term', 'edge:wait', 'api:wait']


def test_worker_factory_rejects_config_before_creating_app(monkeypatch):
    monkeypatch.setattr(config, 'load', lambda: (_ for _ in ()).throw(ValueError('synthetic-private-error')))
    monkeypatch.setattr(application, 'create_app', lambda *a: pytest.fail('Factory reached invalid config'))
    with pytest.raises(RuntimeError, match='private details suppressed') as error:
        application.create_railway_app()
    assert 'synthetic-private-error' not in str(error.value)
