"""Offline production packaging/config tests. No database, host, Docker or TLS."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient
from pydantic import SecretStr,SecretBytes
import pytest
from sqlalchemy.engine import Engine
from app.production import config,database,application,grants,check,migrate,bootstrap,serve,prepare

ORIGIN='https://merge.contestant.org'  # Synthetic fixture, not a deployed URL.


def settings(role='runtime'):
    return config.ProductionConfig(ORIGIN,role,SecretStr('s'*48),SecretStr('a'*64) if role=='runtime' else None)


@pytest.mark.parametrize('origin',[None,'','http://merge.contestant.org','https://localhost','https://127.0.0.1','https://[::1]',
    'https://merge_dev','https://example.com','https://merge.example.org','https://deployment.invalid','https://x.local',
    'https://Upper.example','https://merge.contestant.org/','https://merge.contestant.org:443','https://a@merge.contestant.org',
    'https://merge.contestant.org?x=1','https://-bad.org','https://bad-.org','https://a..org','https://x.org\n'])
def test_production_rejects_unsafe_or_placeholder_origin(origin):
    with pytest.raises(ValueError):config.public_origin(origin)


def test_production_fixed_target_and_auth_never_reuse_local_settings(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setattr(Settings,'database_url',lambda *a:pytest.fail('Local target reached'))
    target=settings();url=target.url();policy=target.auth()
    assert (url.host,url.port,url.database,url.username)==('postgres',5432,'merge_prod','merge_runtime')
    assert policy.mode=='production' and policy.secure and policy.cookie_name=='__Host-merge_session'
    assert policy.trusted_proxies==('172.30.240.2/32',) and policy.register_ip_limit==5
    assert 's'*48 not in repr(target) and 'a'*64 not in repr(target)


@pytest.mark.parametrize('role',['merge_dev','merge_test','profiles','benchmark','admin','postgres','merge_runtime'])
def test_production_unknown_role_rejected_before_engine(role,monkeypatch):
    monkeypatch.setattr(database,'create_engine',lambda *a,**k:pytest.fail('Engine reached'))
    with pytest.raises(ValueError):database.engine(config.ProductionConfig(ORIGIN,role,SecretStr('s'*48)))


@pytest.mark.parametrize('key',['MERGE_DB_NAME','MERGE_AUTH_MODE','MERGE_TEST_DB_PASSWORD','MERGE_RELEASE_DB_PASSWORD','MERGE_PROD_DB_HOST',
    'DATABASE_URL','PGHOST','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE'])
def test_conflicting_environments_fail_before_reading_secrets(key,monkeypatch):
    monkeypatch.setattr(config,'secret_file',lambda *a,**k:pytest.fail('Secret read reached'))
    with pytest.raises(ValueError):config.load(environ={'MERGE_PROD_ORIGIN':ORIGIN,key:'synthetic'})


@pytest.mark.parametrize('value',['','short','x'*257,'s'*32+'\r\n','s'*32+'\n\n','private value with spaces'*2])
def test_secret_file_invalid_content_is_withheld(tmp_path,value):
    (tmp_path/'runtime_db_password').write_text(value)
    with pytest.raises(ValueError) as e:config.secret_file('runtime_db_password',directory=tmp_path)
    assert str(e.value)=='Missing or invalid production secret file'


def test_secret_files_explicit_and_bounded(tmp_path):
    for name,value in [('runtime_db_password','s'*48),('throttle_key','a'*64)]:
        (tmp_path/name).write_bytes((value+'\n').encode('ascii'))
    selected=config.load(environ={'MERGE_PROD_ORIGIN':ORIGIN},directory=tmp_path)
    assert selected.password.get_secret_value()=='s'*48 and selected.auth().origin==ORIGIN
    with pytest.raises(ValueError):config.secret_file('../other',directory=tmp_path)
    with pytest.raises(ValueError):config.secret_file('migrator_db_password',directory=tmp_path)


class Connection:
    def __init__(self):
        self.active=False;self.invalid=False;self.calls=[];self.dialect=SimpleNamespace(name='postgresql',driver='psycopg',is_async=False)
        self.connection=SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.who=('merge_prod','merge_runtime',config.DB_ADDRESS,5432);self.flags=(False,)*5;self.member=False
        self.permissions=(True,True,False,False,False);self.revision=[config.REVISION]
        self.settings=('read committed','read committed','on','5s','15s','off',False)
    def in_transaction(self):return self.active
    def in_nested_transaction(self):return False
    def get_execution_options(self):return {}
    def execute(self,q,*args):
        q=str(q);self.active=True;self.calls.append(q)
        one=self.who if 'current_database(),current_user' in q else self.flags if 'SELECT rolsuper' in q else self.permissions if 'has_database_privilege' in q else self.settings
        scalar=self.member if 'pg_auth_members' in q else True
        return SimpleNamespace(one=lambda:one,scalar_one=lambda:scalar,scalars=lambda:SimpleNamespace(all=lambda:self.revision))
    def rollback(self):self.active=False
    def invalidate(self):self.invalid=True


@pytest.mark.parametrize('kind',['database','role','host','port','flags','member','schema','revision','autocommit','transaction','isolation','driver','timeouts','read_only','standby'])
def test_production_connection_guard_poisoned_on_any_mismatch(kind):
    c=Connection();guard=database.Guard(settings())
    if kind=='database':c.who=('merge_test',*c.who[1:])
    elif kind=='role':c.who=(c.who[0],'postgres',*c.who[2:])
    elif kind=='host':c.who=(*c.who[:2],'127.0.0.1',5432)
    elif kind=='port':c.who=(*c.who[:3],5433)
    elif kind=='flags':c.flags=(True,False,False,False,False)
    elif kind=='member':c.member=True
    elif kind=='schema':c.permissions=(True,True,True,False,False)
    elif kind=='revision':c.revision=['0005_invitations']
    elif kind=='autocommit':c.connection.dbapi_connection.autocommit=True
    elif kind=='transaction':c.active=True
    elif kind=='driver':c.dialect.driver='other'
    elif kind=='isolation':c.settings=('serializable',*c.settings[1:])
    elif kind=='read_only':c.settings=(*c.settings[:5],'on',False)
    elif kind=='standby':c.settings=(*c.settings[:6],True)
    else:c.settings=(*c.settings[:3],'0','0',*c.settings[5:])
    with pytest.raises(ValueError):guard(c)
    assert c.invalid and guard.failed.is_set()
    with pytest.raises(ValueError):guard(Connection())


def test_production_connection_guard_every_new_handle_closes_preflight():
    guard=database.Guard(settings())
    for _ in range(2):
        c=Connection();guard(c);assert c.calls[0]=='SET TRANSACTION READ ONLY' and not c.active
    with pytest.raises(ValueError):database.Guard(settings(),config.PREVIOUS)


def package():
    return [json.loads((check.ROOT/path).read_text()) for path in ('deploy/compose.json','deploy/caddy.template.json')]


@pytest.mark.parametrize('unsafe',['api_port','db_port','network','proxy','secrets','env','profile','storage','sse','headers','tls','ready'])
def test_deployment_contract_rejects_unsafe_changes(unsafe):
    c,t=package();s=c['services'];routes=t['apps']['http']['servers']['https']['routes'][0]['handle'][0]['routes']
    if unsafe=='api_port':s['api']['ports']=['8000:8000']
    elif unsafe=='db_port':s['postgres']['ports']=['5432:5432']
    elif unsafe=='network':c['networks']['database']['internal']=False
    elif unsafe=='proxy':s['web']['networks']['edge']['ipv4_address']='172.30.240.6'
    elif unsafe=='secrets':s['api']['secrets'].append('admin_db_password')
    elif unsafe=='env':s['api']['environment']['MERGE_AUTH_MODE']='development'
    elif unsafe=='profile':s['migrate']['profiles']=[]
    elif unsafe=='storage':s['postgres']['volumes']=[]
    elif unsafe=='sse':routes[2]['handle'][0]['flush_interval']=1_000_000_000
    elif unsafe=='headers':routes[2]['handle'][0]['headers']['request']['set']['X-Forwarded-For']=['{http.request.header.X-Forwarded-For}']
    elif unsafe=='tls':t['admin']['disabled']=False
    else:routes[1]['match'][0]['path'].remove('/ready')
    with pytest.raises(ValueError):check.validate(c,t)


def test_packaging_json_schema_revision_and_dockerfile_contracts():
    c,t=package();assert check.validate(c,t)==config.REVISION
    generated=check.caddy(ORIGIN,t)
    assert generated['apps']['http']['servers']['https']['routes'][0]['match'][0]['host']==['merge.contestant.org']
    assert t['apps']['http']['servers']['https']['routes'][0]['match'][0]['host']==['deployment.invalid']
    api=(check.ROOT/'deploy/Dockerfile.api').read_text();web=(check.ROOT/'deploy/Dockerfile.web').read_text()
    assert 'USER 10001:10001' in api and 'app.production.serve' in api and 'alembic upgrade' not in api
    assert 'npm ci' in web and 'npm run build' in web and '/build/dist /srv/merge/web' in web
    ignore=(check.ROOT/'.dockerignore').read_text();assert all(p in ignore for p in ('deploy/private','**/.env','**/test-results','.git','**/.venv'))
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    cfg=Config();cfg.set_main_option('script_location',str(check.ROOT/'backend/alembic'))
    assert ScriptDirectory.from_config(cfg).get_heads()==[config.REVISION]
    workflow=json.loads((check.ROOT/'.github/workflows/ci.yml').read_text())
    assert config.REVISION in workflow['jobs']['postgres']['strategy']['matrix']['revision']


def test_runtime_grants_preserve_lock_rights_and_append_only_history():
    assert set(grants.TABLE_RIGHTS)=={'users','hackathons','teams','memberships','idempotency_records','audit_events','outbox_events','account_credentials','auth_sessions','auth_throttle_buckets','join_requests','invitations','participant_profiles','alembic_version'}
    assert grants.LOCK_COLUMNS=={'users':'id','hackathons':'id','account_credentials':'user_id'}
    assert grants.TABLE_RIGHTS['audit_events']==grants.TABLE_RIGHTS['outbox_events']==('SELECT','INSERT')
    c=MagicMock();grants.apply(c,config.PREVIOUS)
    statements=[str(call.args[0]) for call in c.execute.call_args_list]
    assert not any('participant_profiles' in q for q in statements)
    assert any('UPDATE(user_id)' in q for q in statements) and not any('GRANT ALL' in q for q in statements)


def test_production_migration_reuses_preservation_and_rolls_back_mismatch(monkeypatch):
    events=[]
    class MigrationConnection:
        def in_transaction(self):return False
        @contextmanager
        def begin(self):
            events.append('begin')
            try:yield;events.append('commit')
            except Exception:events.append('rollback');raise
        def execute(self,q,*a):return SimpleNamespace(scalars=lambda:SimpleNamespace(all=lambda:[config.PREVIOUS]))
    monkeypatch.setattr(database,'identity',lambda *a:None)
    snapshots=iter([{'users':(2,'a')},{'users':(2,'b')}]);monkeypatch.setattr(migrate,'snapshot',lambda c:next(snapshots))
    monkeypatch.setattr(migrate.command,'upgrade',lambda *a:events.append('ddl'))
    monkeypatch.setattr(grants,'apply',lambda *a:events.append('grants'))
    with pytest.raises(ValueError):migrate.migrate(MigrationConnection(),settings('migrator'),'migrate')
    assert events==['begin','ddl','grants','rollback']


def test_bootstrap_rejects_existing_namespace_before_writes():
    c=MagicMock();c.execute.side_effect=[SimpleNamespace(fetchone=lambda:('merge_prod','postgres',config.DB_ADDRESS,5432)),SimpleNamespace(fetchone=lambda:(True,))]
    with pytest.raises(ValueError):bootstrap.initialize(c,SecretStr('r'*48),SecretStr('m'*48))
    assert c.execute.call_count==2


def test_private_log_formatter_and_parser_never_echo_submitted_values(capsys):
    message='synthetic-private-password-and-cookie'
    record=logging.LogRecord('uvicorn.error',logging.ERROR,__file__,1,message,(message,),None)
    assert message not in serve.SafeFormatter().format(record)
    with pytest.raises(SystemExit):config.SafeParser().parse_args(['--password',message])
    assert message not in capsys.readouterr().err


def test_secret_preparation_refuses_windows_nonroot_and_existing_directory(tmp_path,monkeypatch):
    monkeypatch.setattr(prepare.os,'name','nt')
    with pytest.raises(ValueError):prepare.prepare(ORIGIN,tmp_path/'private')
    assert not (tmp_path/'private').exists()


@pytest.fixture
def production_app(monkeypatch):
    monkeypatch.setattr(config,'load',lambda:settings())
    resource=MagicMock(spec=Engine);resource.hide_parameters=True;resource.echo=False
    monkeypatch.setattr(database,'engine',lambda *a:resource);monkeypatch.setattr(database,'ready',lambda *a:None)
    app=application.create_production_app()
    return app,resource


def test_production_lifespan_reuses_security_and_disposes_without_migration(production_app,monkeypatch):
    app,resource=production_app
    monkeypatch.setattr(migrate.command,'upgrade',lambda *a:pytest.fail('Startup migration reached'))
    with TestClient(app,base_url=ORIGIN,client=('172.30.240.2',50000)) as client:
        assert client.get('/health').status_code==200
        assert client.get('/ready').status_code==200
        assert client.get('/auth/session').status_code==403  # Trusted peer must supply both headers.
        headers={'X-Forwarded-For':'192.0.2.8','X-Forwarded-Proto':'https','Origin':ORIGIN}
        assert client.get('/auth/session',headers=headers).status_code==401
        assert client.get('/auth/session',headers=headers|{'X-Forwarded-Proto':'http'}).status_code==403
        assert client.get('/auth/session',headers=headers|{'Forwarded':'for=192.0.2.8'}).status_code==403
        assert client.post('/auth/login',headers=headers|{'Origin':'https://evil.org','X-Merge-Request':'1'},json={}).status_code==403
        assert client.get('/docs').status_code==404
    resource.connect.assert_not_called();resource.dispose.assert_called_once()


def test_production_startup_and_readiness_fail_closed_and_suppress_errors(production_app,monkeypatch):
    app,resource=production_app
    with TestClient(app,base_url=ORIGIN) as client:
        monkeypatch.setattr(database,'ready',lambda *a:(_ for _ in ()).throw(ValueError('synthetic-private-password')))
        response=client.get('/ready');assert response.status_code==503 and response.json()=={'status':'unavailable'}
    with pytest.raises(RuntimeError,match='private details suppressed') as error:
        with TestClient(app):pass
    assert 'synthetic-private-password' not in str(error.value)
    assert resource.dispose.call_count==2


def test_production_factory_config_failure_prints_no_private_input(monkeypatch):
    monkeypatch.setattr(config,'load',lambda:(_ for _ in ()).throw(ValueError('synthetic-private-password')))
    with pytest.raises(RuntimeError) as error:application.create_production_app()
    assert str(error.value)=='Invalid production configuration; private details suppressed'


def test_production_cookie_csrf_and_client_ip_throttling_survive_proxy(production_app):
    from app.auth import AuthServices,get_services,encode_token
    from app.services.sessions import SessionPrincipal,IssuedSession,ValidatedSession
    app,resource=production_app;now=datetime.now(timezone.utc)
    principal=SessionPrincipal(uuid4(),'unit_user',now+timedelta(hours=8))
    issued=IssuedSession(principal,now,SecretBytes(b't'*32),SecretBytes(b'c'*32))
    sessions=MagicMock();sessions.login.return_value=issued;sessions.validate_with_csrf.return_value=ValidatedSession(principal,issued.csrf_token)
    services=AuthServices(MagicMock(),sessions,MagicMock());app.dependency_overrides[get_services]=lambda:services
    headers={'Origin':ORIGIN,'X-Forwarded-For':'192.0.2.8','X-Forwarded-Proto':'https','X-Merge-Request':'1'}
    with TestClient(app,base_url=ORIGIN,client=('172.30.240.2',50000)) as client:
        response=client.post('/auth/login',headers=headers,json={'username':'unit_user','password':'synthetic private passphrase'})
        assert response.status_code==200
        cookie=response.headers['set-cookie']
        assert cookie.startswith('__Host-merge_session=') and 'Domain=' not in cookie
        assert all(s in cookie for s in ('Secure','HttpOnly','SameSite=lax','Path=/'))
        services.throttle.check.assert_called_once_with(operation='login',client_ip='192.0.2.8',username='unit_user')
        assert client.post('/auth/logout',headers=headers,json={}).status_code==403
        sessions.revoke.assert_not_called()
        assert client.post('/auth/logout',headers=headers|{'X-CSRF-Token':encode_token(issued.csrf_token.get_secret_value())},json={}).status_code==204
        sessions.verify_csrf.assert_called_once_with(b't'*32,b'c'*32)
        assert 'no-store' in response.headers['cache-control'] and 'access-control-allow-origin' not in response.headers
    resource.connect.assert_not_called()


@pytest.mark.parametrize('corrupt',['none','audit_update','missing_lock'])
def test_readiness_grant_checks_are_bounded_and_reject_drift(corrupt):
    c=MagicMock();rights=('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')
    tables=[dict(name=t,privilege=r,allowed=r in allowed) for t,allowed in grants.TABLE_RIGHTS.items() for r in rights]
    locks=[dict(name=t,col=col,allowed=True) for t,col in grants.LOCK_COLUMNS.items()]
    if corrupt=='audit_update':next(row for row in tables if row['name']=='audit_events' and row['privilege']=='UPDATE')['allowed']=True
    if corrupt=='missing_lock':locks[0]['allowed']=False
    c.execute.return_value.mappings.return_value.all.side_effect=[tables,locks]
    if corrupt=='none':grants.verify(c);assert c.execute.call_count==2
    else:
        with pytest.raises(ValueError):grants.verify(c)
