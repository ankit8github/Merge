"""Render deployment regression tests: synthetic SQL, DNS, HTTP and processes only."""
from contextlib import contextmanager
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import sys
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from pydantic import SecretBytes, SecretStr
from sqlalchemy.engine import Engine
from app.auth import AuthServices, get_services, encode_token
from app.services.sessions import SessionPrincipal, IssuedSession, ValidatedSession
import psycopg
import pytest
from app.render import config, database, check, initialization as init, setup, api, serve, application

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'https://merge-synthetic.onrender.com'
ADDRESS = '10.1.2.3'


def environment():
    return dict(RENDER='true', RENDER_SERVICE_TYPE='web', RENDER_SERVICE_ID='srv-abcdefgh1234',
        RENDER_EXTERNAL_HOSTNAME='merge-synthetic.onrender.com', PORT='10000',
        MERGE_RENDER_ENVIRONMENT='production', MERGE_RENDER_DB_HOST='dpg-abcdefgh1234-a',
        MERGE_RENDER_RUNTIME_PASSWORD='r'*48, MERGE_RENDER_THROTTLE_KEY='a'*64)


def target(): return config.RenderConfig('dpg-abcdefgh1234-a', 'runtime', SecretStr('r'*48), ORIGIN, SecretStr('a'*64))


def setup_env():
    env = environment(); env.pop('MERGE_RENDER_THROTTLE_KEY')
    return env | dict(MERGE_RENDER_MIGRATOR_PASSWORD='m'*48, MERGE_RENDER_SETUP_ATTEMPT=str(uuid4()),
        MERGE_RENDER_SETUP_COMMIT='b'*40, RENDER_GIT_COMMIT='b'*40, MERGE_RENDER_CATALOG_ID=str(uuid4()),
        MERGE_RENDER_CATALOG_NAME='Synthetic event', MERGE_RENDER_CATALOG_MIN='2', MERGE_RENDER_CATALOG_MAX='4')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*a, **k): pytest.fail('Real database/DNS reached from offline Render test')
    monkeypatch.setattr(psycopg, 'connect', blocked)
    monkeypatch.setattr(database.socket, 'getaddrinfo', blocked)


@pytest.mark.parametrize('change', [
    {'RENDER':'false'}, {'RENDER_SERVICE_TYPE':'worker'}, {'RENDER_SERVICE_ID':''}, {'IS_PULL_REQUEST':'true'},
    {'MERGE_RENDER_ENVIRONMENT':'development'}, {'MERGE_AUTH_MODE':'production'}, {'PGHOST':'localhost'},
    {'DATABASE_URL':'forbidden'}, {'DATABASE_PUBLIC_URL':'forbidden'}, {'RAILWAY_PROJECT_ID':'forbidden'},
    {'VITE_SECRET':'forbidden'}, {'MERGE_RENDER_MIGRATOR_PASSWORD':'m'*48}, {'MERGE_RENDER_SETUP_ATTEMPT':str(uuid4())},
    {'MERGE_RENDER_DB_HOST':'localhost'}, {'MERGE_RENDER_DB_HOST':'127.0.0.1'}, {'MERGE_RENDER_DB_HOST':'dpg-abcdefgh1234-a.singapore-postgres.render.com'},
    {'RENDER_EXTERNAL_HOSTNAME':'https://merge.onrender.com'}, {'RENDER_EXTERNAL_HOSTNAME':'merge.example.org'},
    {'RENDER_EXTERNAL_HOSTNAME':'merge.onrender.com.evil.org'}, {'RENDER_EXTERNAL_HOSTNAME':'MERGE.onrender.com'},
    {'RENDER_EXTERNAL_URL':'http://merge-synthetic.onrender.com'}, {'MERGE_RENDER_RUNTIME_PASSWORD':'short'},
    {'MERGE_RENDER_THROTTLE_KEY':'Z'*64}, *[{'PORT':p} for p in ('8000','18012','18013','19099','','80','65536','10000\n')]])
def test_runtime_rejects_unsafe_inputs(change):
    with pytest.raises(ValueError): config.load(environ=environment() | change)


def test_fixed_target_auth_and_secrets():
    selected=target(); url=selected.url(); policy=selected.auth()
    assert (url.database,url.username,url.host,url.port)==('merge_prod','merge_runtime','dpg-abcdefgh1234-a',5432)
    assert policy.secure and policy.cookie_name=='__Host-merge_session'
    assert policy.origin==ORIGIN and policy.trusted_proxies==('127.0.0.1/32',)
    assert 'r'*48 not in repr(selected) and 'a'*64 not in repr(selected)


@pytest.mark.parametrize('change', [{'MERGE_RENDER_SETUP_COMMIT':'c'*40}, {'RENDER_GIT_COMMIT':''},
    {'MERGE_RENDER_SETUP_ATTEMPT':'bad'}, {'MERGE_RENDER_CATALOG_ID':'bad'}, {'MERGE_RENDER_CATALOG_NAME':''},
    {'MERGE_RENDER_CATALOG_MIN':'0'}, {'MERGE_RENDER_CATALOG_MAX':'101'}, {'MERGE_RENDER_CATALOG_MIN':'5'},
    {'MERGE_RENDER_MIGRATOR_PASSWORD':'r'*48}, {'MERGE_RENDER_THROTTLE_KEY':'a'*64}])
def test_setup_requires_explicit_reviewed_inputs_and_separate_secrets(change):
    with pytest.raises(ValueError): config.load_setup(environ=setup_env() | change)


@pytest.mark.parametrize('addresses',[[],['127.0.0.1'],['::1'],['8.8.8.8'],[ADDRESS,'8.8.8.8']])
def test_private_dns_fails_closed(monkeypatch, addresses):
    monkeypatch.setattr(database.socket,'getaddrinfo',lambda *a,**k:[(None,None,None,None,(ip,5432)) for ip in addresses])
    with pytest.raises(ValueError): database.private_addresses(target())


def test_small_tls_pinned_pool(monkeypatch):
    monkeypatch.setattr(database.socket,'getaddrinfo',lambda *a,**k:[(None,None,None,None,(ADDRESS,5432))])
    created=[]; listeners=[]
    monkeypatch.setattr(database,'create_engine',lambda *a,**k:created.append(k) or MagicMock())
    monkeypatch.setattr(database.event,'listen',lambda *a:listeners.append(a))
    database.engine(target()); kw=created[0]
    assert (kw['pool_size'],kw['max_overflow'],kw['pool_timeout'])==(2,0,5)
    assert kw['hide_parameters'] and kw['isolation_level']=='READ COMMITTED'
    assert kw['connect_args']['hostaddr']==ADDRESS and kw['connect_args']['sslmode']=='require'
    assert listeners[0][2].revision=='0006_profiles'


def package(): return json.loads((ROOT/'deploy/render/caddy.template.json').read_text())


def test_checked_packaging_dynamic_hostname_port_and_fresh_blueprint(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['check'])
    check.main()
    generated=check.caddy(target(),54321,package())
    server=generated['apps']['http']['servers']['render']
    assert server['listen']==[':54321']
    assert all(r['match'][0]['host']==['merge-synthetic.onrender.com'] for r in server['routes'][:2])
    assert package()['apps']['http']['servers']['render']['listen']==[':10000']
    assert 'alembic upgrade' not in (ROOT/'deploy/Dockerfile.render').read_text()


@pytest.mark.parametrize('unsafe',['admin','host','scheme','client_ip','capture','forwarding','flush','upstream','public_ready','assets'])
def test_proxy_contract_rejects_broken_security_or_streaming(unsafe):
    t=package(); server=t['apps']['http']['servers']['render']; public=server['routes'][1]; routes=public['handle'][0]['routes']; proxy=routes[2]['handle'][0]
    if unsafe=='admin': t['admin']['disabled']=False
    elif unsafe=='host': public['match'][0]['host']=['*']
    elif unsafe=='scheme': public['match'][0]['header']['X-Forwarded-Proto']=['*']
    elif unsafe=='client_ip': del public['match'][0]['header']['CF-Connecting-IP']
    elif unsafe=='capture': routes[0]['handle'][0]['render_client_ip']='{http.request.header.X-Forwarded-For}'
    elif unsafe=='forwarding': proxy['headers']['request']['set']['X-Forwarded-For']=['{http.request.header.X-Forwarded-For}']
    elif unsafe=='flush': proxy['flush_interval']=1000000000
    elif unsafe=='upstream': proxy['upstreams']=[{'dial':'0.0.0.0:8000'}]
    elif unsafe=='public_ready': routes[1]['match'][0]['path'].remove('/ready')
    else: routes[3]['handle'][1]['root']='/tmp'
    with pytest.raises(ValueError): check.validate_template(t)


@pytest.mark.parametrize('unsafe',['paid_hook','autostart','instances','health','external_db','version','region','secret'])
def test_blueprint_refuses_unsafe_deployment(unsafe):
    bp=json.loads((ROOT/'render.yaml').read_text()); web=bp['services'][0]; db=bp['databases'][0]
    if unsafe=='paid_hook': web['preDeployCommand']='forbidden'
    elif unsafe=='autostart': web['initialDeployHook']='forbidden'
    elif unsafe=='instances': web['numInstances']=2
    elif unsafe=='health': web['healthCheckPath']='/health'
    elif unsafe=='external_db': db['ipAllowList']=[{'source':'0.0.0.0/0'}]
    elif unsafe=='version': db['postgresMajorVersion']='18'
    elif unsafe=='region': db['region']='oregon'
    else: web['envVars'][-1]['value']='forbidden'
    with pytest.raises(ValueError): check.validate_blueprint(bp)


class SetupConnection:
    def __init__(self):
        self.metadata=False; self.rows=[]; self.objects=0; self.role=False; self.calls=[]; self.events=[]
        self.flags=(False,True,True,False,'off'); self.changed=1; self.revision=['0006_profiles']
        self.connection=SimpleNamespace(dbapi_connection=SimpleNamespace(pgconn=SimpleNamespace(encrypt_password=lambda *a:b'SCRAM-SHA-256$synthetic-verifier')))
    @contextmanager
    def begin(self):
        snapshot=(self.metadata,list(self.rows)); self.events.append('begin')
        try: yield; self.events.append('commit')
        except BaseException:
            self.metadata,self.rows=snapshot; self.events.append('rollback'); raise
    def execute(self,q,params=None):
        q=str(q); self.calls.append((q,params))
        scalar=self.metadata if 'SELECT EXISTS(SELECT 1 FROM pg_namespace' in q else self.role if "WHERE rolname='merge_runtime'" in q else self.objects
        if q.startswith('CREATE SCHEMA'): self.metadata=True
        if q.startswith('INSERT INTO merge_deployment'): self.rows=[(params['attempt'],params['commit'],'claimed')]
        if q.startswith('UPDATE merge_deployment'): self.rows=[(params['attempt'],params['commit'],'complete')]
        return SimpleNamespace(scalar_one=lambda:scalar,all=lambda:list(self.rows),one=lambda:self.flags,
            scalars=lambda:SimpleNamespace(all=lambda:self.revision),rowcount=self.changed)
    def exec_driver_sql(self,q): self.calls.append((q,None))


def test_claim_commits_before_ddl_failure_and_refuses_any_retry(monkeypatch):
    selected=config.load_setup(environ=setup_env()); c=SetupConnection()
    assert init.claim(c,selected) is True and c.events==['begin','commit']
    monkeypatch.setattr(init,'owner',lambda *a:None)
    monkeypatch.setattr(init,'upgrade',lambda *a:(_ for _ in ()).throw(ValueError('synthetic migration failure')))
    with pytest.raises(ValueError): init.apply(c,selected,(ADDRESS,))
    assert c.rows==[(selected.attempt,selected.commit,'claimed')]
    assert c.events[-1]=='rollback'
    with pytest.raises(ValueError): init.claim(c,selected)
    assert not any(q.startswith(('DROP ','DELETE ','TRUNCATE ')) for q,p in c.calls)
    assert selected.runtime_password.get_secret_value() not in str(c.calls)


@pytest.mark.parametrize('existing',['objects','role'])
def test_fresh_setup_refuses_existing_application_before_any_ddl(existing):
    c=SetupConnection(); setattr(c,existing,1 if existing=='objects' else True)
    with pytest.raises(ValueError): init.claim(c,config.load_setup(environ=setup_env()))
    assert all(q.startswith('SELECT') for q,p in c.calls)


def test_completed_matching_claim_only_reads_and_mismatched_attempt_refuses():
    selected=config.load_setup(environ=setup_env()); c=SetupConnection(); c.metadata=True
    c.rows=[(selected.attempt,selected.commit,'complete')]
    assert init.claim(c,selected) is False
    assert all(q.startswith('SELECT') for q,p in c.calls)
    with pytest.raises(ValueError): init.claim(c,config.load_setup(environ=setup_env()))


def test_success_commits_revision_grants_catalog_and_claim_together(monkeypatch):
    selected=config.load_setup(environ=setup_env()); c=SetupConnection(); init.claim(c,selected)
    monkeypatch.setattr(init,'owner',lambda *a:None)
    monkeypatch.setattr(init,'upgrade',lambda *a:None)
    grant_calls=[]; monkeypatch.setattr(init.grants,'apply',lambda *a:grant_calls.append(a))
    init.apply(c,selected,(ADDRESS,))
    assert c.rows==[(selected.attempt,selected.commit,'complete')]
    assert c.events==['begin','commit','begin','commit'] and grant_calls==[(c,'0006_profiles')]
    catalog=[p for q,p in c.calls if q.startswith('INSERT INTO public.hackathons')]
    assert catalog==[dict(id=selected.catalog_id,name=selected.catalog_name,minimum=2,maximum=4)]


@pytest.mark.parametrize('flags',[(True,True,True,False,'off'),(False,False,True,False,'off'),(False,True,False,False,'off'),(False,True,True,True,'off'),(False,True,True,False,'on')])
def test_owner_preflight_requires_exact_restricted_database_owner(monkeypatch,flags):
    monkeypatch.setattr(database,'server',lambda *a,**k:None)
    c=SetupConnection(); c.flags=flags
    with pytest.raises(ValueError): init.owner(c,config.load_setup(environ=setup_env()).target,(ADDRESS,))
    assert all(q.startswith('SELECT') for q,p in c.calls)


def test_setup_status_http_is_read_only_and_sanitized_without_listener():
    status=setup.Status(); cls=setup.handler(status)
    h=object.__new__(cls); h.path='/ready'; h.command='GET'; h.wfile=io.BytesIO()
    codes=[]; h.send_response=lambda code:codes.append(code); h.send_header=lambda *a:None; h.end_headers=lambda:None
    h.do_GET(); assert codes==[200] and json.loads(h.wfile.getvalue())==dict(initialized=False,state='initializing')
    h.send_error=lambda code:codes.append(code)
    h.do_POST(); h.path='/run-migrations'; h.do_GET()
    assert codes==[200,405,404]
    status.set(dict(initialized=False,state='failed')); assert b'failed' in status.body()


def test_private_worker_bounds_one_loopback_worker_and_disables_proxy_middleware(monkeypatch):
    monkeypatch.setattr(sys,'argv',['api']); monkeypatch.setattr(api,'load',target)
    calls=[]; monkeypatch.setattr(api.uvicorn,'run',lambda *a,**k:calls.append(k))
    api.main(); kw=calls[0]
    assert (kw['host'],kw['port'],kw['workers'],kw['limit_concurrency'])==('127.0.0.1',8000,1,64)
    assert kw['proxy_headers'] is False and kw['forwarded_allow_ips']=='' and kw['access_log'] is False


def test_runtime_supervisor_has_no_setup_path_and_strips_caddy_secrets(monkeypatch):
    monkeypatch.setattr(sys,'argv',['serve']); monkeypatch.setenv('PORT','10000')
    monkeypatch.setattr(config,'load',target); monkeypatch.setattr(serve,'TEMPLATE',ROOT/'deploy/render/caddy.template.json')
    monkeypatch.setattr(serve.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0))
    captured=[]; monkeypatch.setattr(serve,'supervise',lambda filename,stopped,env:captured.append((filename,env)) or 0)
    with pytest.raises(SystemExit) as result: serve.main()
    assert result.value.code==0 and not Path(captured[0][0]).exists()
    assert set(captured[0][1])=={'PATH','XDG_CONFIG_HOME','XDG_DATA_HOME','GOMEMLIMIT','GOMAXPROCS'}
    assert captured[0][1]['GOMEMLIMIT']=='64MiB'
    for name in ('serve.py','api.py','application.py'):
        source=(ROOT/'backend/app/render'/name).read_text()
        assert 'initialization' not in source and 'app.render.setup' not in source and 'command.upgrade' not in source


@pytest.fixture
def render_app(monkeypatch):
    resource = MagicMock(spec=Engine)
    resource.hide_parameters = True
    resource.echo = False
    monkeypatch.setattr(config, 'load', lambda: target())
    monkeypatch.setattr(database, 'engine', lambda *a, **k: resource)
    monkeypatch.setattr(database, 'ready', lambda *a: None)
    return application.create_render_app(), resource


def test_runtime_lifecycle_preserves_auth_csrf_secure_cookie_and_client_throttle(render_app, monkeypatch):
    app, resource = render_app
    monkeypatch.setattr(init.command, 'upgrade', lambda *a: pytest.fail('Startup DDL reached'))
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


def test_runtime_readiness_and_startup_fail_closed_without_private_error(render_app, monkeypatch):
    app, resource = render_app
    with TestClient(app, base_url=ORIGIN) as client:
        monkeypatch.setattr(database, 'ready', lambda *a: (_ for _ in ()).throw(ValueError('synthetic-private-error')))
        assert client.get('/ready').json() == {'status': 'unavailable'}
        assert client.get('/ready').status_code == 503
    with pytest.raises(RuntimeError, match='private details suppressed') as error:
        with TestClient(app): pass
    assert 'synthetic-private-error' not in str(error.value)
    assert resource.dispose.call_count == 2



@pytest.mark.parametrize('failure',['revision','claim_update','catalog','grants'])
def test_any_finalization_failure_rolls_back_but_preserves_durable_claim(monkeypatch,failure):
    selected=config.load_setup(environ=setup_env()); c=SetupConnection(); init.claim(c,selected)
    monkeypatch.setattr(init,'owner',lambda *a:None); monkeypatch.setattr(init,'upgrade',lambda *a:None)
    def fail(*a): raise ValueError('synthetic failure')
    monkeypatch.setattr(init.grants,'apply',fail if failure=='grants' else lambda *a:None)
    if failure=='revision': c.revision=['0005_invitations']
    if failure=='claim_update': c.changed=0
    if failure=='catalog':
        execute=c.execute
        def rejected(q,*a):
            if str(q).startswith('INSERT INTO public.hackathons'): fail()
            return execute(q,*a)
        c.execute=rejected
    with pytest.raises(ValueError): init.apply(c,selected,(ADDRESS,))
    assert c.rows==[(selected.attempt,selected.commit,'claimed')] and c.events[-1]=='rollback'


@pytest.mark.parametrize('new_claim,locked,fail_apply',[(True,True,False),(False,True,False),(True,False,False),(True,True,True)])
def test_initializer_serializes_disposes_and_verifies_runtime_only_after_success(monkeypatch,new_claim,locked,fail_apply):
    selected=config.load_setup(environ=setup_env()); events=[]
    connection=MagicMock()
    connection.execute.return_value.scalar_one.return_value=locked
    resource=MagicMock(); resource.connect.return_value.__enter__.return_value=connection
    runtime=MagicMock()
    monkeypatch.setattr(database,'private_addresses',lambda *a:(ADDRESS,))
    monkeypatch.setattr(database,'setup_engine',lambda *a:resource)
    monkeypatch.setattr(init,'owner',lambda *a:events.append('owner'))
    monkeypatch.setattr(init,'claim',lambda *a:events.append('claim') or new_claim)
    def apply(*a):
        events.append('apply')
        if fail_apply: raise ValueError('synthetic private failure')
    monkeypatch.setattr(init,'apply',apply)
    def engine(selected):
        assert selected.role=='runtime' and selected.password.get_secret_value()=='r'*48
        events.append('runtime_engine'); return runtime
    monkeypatch.setattr(database,'engine',engine)
    monkeypatch.setattr(database,'ready',lambda resource:events.append('ready'))
    if not locked or fail_apply:
        with pytest.raises(ValueError): init.initialize(selected)
        assert 'runtime_engine' not in events
    else:
        result=init.initialize(selected)
        assert result['initialized'] and result['source_commit']==selected.commit
        assert ('apply' in events)==new_claim and events[-2:]==['runtime_engine','ready']
        runtime.dispose.assert_called_once()
    resource.dispose.assert_called_once()
    statements=[str(call.args[0]) for call in connection.execute.call_args_list]
    assert statements[0]=='SELECT pg_try_advisory_lock(:key)'
    assert ('SELECT pg_advisory_unlock(:key)' in statements)==locked


def test_render_migration_entry_requires_explicit_owned_transaction(monkeypatch):
    import runpy
    from alembic import context
    monkeypatch.setattr(context,'is_offline_mode',lambda:False)
    monkeypatch.setattr(context,'config',SimpleNamespace(attributes={}),raising=False)
    with pytest.raises(RuntimeError,match='transaction required'):
        runpy.run_path(str(ROOT/'backend/render_alembic/env.py'))


def test_runtime_guard_rejects_stale_schema_for_render_target():
    # The shared guard is deliberately exercised with a Render target, without DNS.
    from test_railway import Connection
    c=Connection(); c.who=('merge_prod','merge_runtime',ADDRESS,5432)
    guard=database.Guard(target(),(ADDRESS,))
    guard(c); assert not c.invalid
    c.revision=['0005_invitations']
    with pytest.raises(ValueError): guard(c)
    assert c.invalid and guard.failed.is_set()


def test_render_supervisor_stops_both_children_on_edge_exit(monkeypatch):
    from test_railway import Process
    events=[]; children=iter([Process('api',events),Process('edge',events,status=0)])
    monkeypatch.setattr(serve.subprocess,'Popen',lambda *a,**k:next(children))
    monkeypatch.setattr(serve,'wait_for_api',lambda *a,**k:True)
    stopped=SimpleNamespace(is_set=lambda:False,wait=lambda *a:False)
    assert serve.supervise('synthetic.json',stopped,{})==1
    assert 'api:term' in events and 'edge:wait' in events and 'api:wait' in events
