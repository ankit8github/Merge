"""Offline release contracts, synthetic metrics/fixtures only. No DB/HTTP/k6 host."""
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
from unittest.mock import MagicMock
from uuid import uuid4
from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy.engine import Engine
from release_support import targets,migrations,evidence,ci,seed,load,acceptance,verify


@pytest.mark.parametrize('overrides',[{'kind':'merge_dev'},{'kind':'merge_test'},{'kind':'production'},
    {'confirmed':False},{'confirmed':1},{'host':'localhost'},{'host':'example.com'},{'port':5433},{'password':''}])
def test_new_targets_reject_before_connect(overrides,monkeypatch):
    monkeypatch.setattr(targets,'create_engine',lambda *a,**k:pytest.fail('Connection factory reached'))
    values=dict(kind='profiles',confirmed=True,password='synthetic-only')|overrides
    with pytest.raises(ValueError):
        with targets.guarded_engine(targets.Target(**values)):pass


def test_new_targets_cannot_address_retained_or_development():
    assert targets.Target('profiles',True,'synthetic-only').url().database=='merge_profile_test'
    assert targets.Target('benchmark',True,'synthetic-only').url().database=='merge_bench'
    assert targets.Target('benchmark',True,'synthetic-only').url().username=='merge_bench_app'
    from test_support.revisions import TARGET_REVISIONS,validate_migration_start
    assert TARGET_REVISIONS==('0002_domain','0003_auth','0004_admission','0005_invitations')
    with pytest.raises(ValueError):validate_migration_start(['0005_invitations'],'0006_profiles')


class GuardConnection:
    def __init__(self):
        self.dialect=SimpleNamespace(name='postgresql',driver='psycopg',is_async=False)
        self.connection=SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False));self.active=False
        self.revision=['0006_profiles'];self.who=('merge_profile_test','merge_app','127.0.0.1',5432)
        self.flags=(False,)*5;self.membership=False;self.settings=('read committed','read committed','on','5s','15s');self.invalid=False;self.calls=[]
    def in_transaction(self):return self.active
    def in_nested_transaction(self):return False
    def get_execution_options(self):return {}
    def execute(self,q,p=None):
        q=str(q);self.calls.append(q);self.active=True
        one=self.who if 'current_database()' in q else self.flags if 'SELECT rolsuper' in q else self.settings
        scalar=self.membership if 'pg_auth_members' in q else True
        return SimpleNamespace(one=lambda:one,scalar_one=lambda:scalar,scalars=lambda:SimpleNamespace(all=lambda:self.revision))
    def rollback(self):self.active=False
    def invalidate(self):self.invalid=True


def test_guard_covers_new_and_pooled_handles_and_closes_preflight():
    guard=targets.Guard(targets.Target('profiles',True,'synthetic-only'),targets.REVISION)
    for _ in range(2):
        c=GuardConnection();guard(c);assert not c.active and not c.invalid
        assert c.calls[0]=='SET TRANSACTION READ ONLY'


@pytest.mark.parametrize('kind',['database','role','host','port','revision','autocommit','transaction','driver','timeouts','privileged','membership'])
def test_guard_fails_closed_and_poisoned(kind):
    guard=targets.Guard(targets.Target('profiles',True,'synthetic-only'),targets.REVISION);c=GuardConnection()
    if kind=='database':c.who=('merge_dev',*c.who[1:])
    elif kind=='role':c.who=(c.who[0],'postgres',*c.who[2:])
    elif kind=='host':c.who=(*c.who[:2],'10.0.0.1',5432)
    elif kind=='port':c.who=(*c.who[:3],5433)
    elif kind=='revision':c.revision=['0005_invitations']
    elif kind=='autocommit':c.connection.dbapi_connection.autocommit=True
    elif kind=='transaction':c.active=True
    elif kind=='driver':c.dialect.driver='asyncpg'
    elif kind=='timeouts':c.settings=(*c.settings[:3],'0','0')
    elif kind=='privileged':c.flags=(True,False,False,False,False)
    else:c.membership=True
    with pytest.raises(ValueError):guard(c)
    assert c.invalid and guard.failed.is_set()
    with pytest.raises(ValueError):guard(GuardConnection())


def test_migration_preserves_all_old_tables_and_rolls_back_on_mismatch(monkeypatch):
    assert len(migrations.TABLES)==12 and 'invitations' in migrations.TABLES
    events=[]
    class Connection:
        def in_transaction(self):return False
        @contextmanager
        def begin(self):
            events.append('begin')
            try:yield;events.append('commit')
            except Exception:events.append('rollback');raise
        def execute(self,q,*args):return SimpleNamespace(scalars=lambda:SimpleNamespace(all=lambda:['0005_invitations'] if len(events)==1 else ['0006_profiles']))
    c=Connection();calls=iter([{'users':(1,'a')},{'users':(1,'b')}])
    monkeypatch.setattr(migrations,'snapshot',lambda c:next(calls))
    monkeypatch.setattr(migrations.command,'upgrade',lambda *args:events.append('ddl'))
    with pytest.raises(ValueError,match='Old rows changed'):migrations.migrate(c,targets.Target('profiles',True,'synthetic-only'),'migrate')
    assert events==['begin','ddl','rollback']


def test_migration_graph_and_sql_are_offline_additive():
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('batchb_profile_ddl',root/'alembic/versions/0006_profiles.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    output=io.StringIO();context=MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':output})
    with Operations.context(context):module.upgrade()
    sql=output.getvalue();assert 'PRIMARY KEY(user_id)' in sql and 'REFERENCES public.users(id)' in sql
    assert all(n in sql for n in ('ck_profiles_skills','ck_profiles_timezone','ck_profiles_discovery','ck_profiles_version'))
    assert not any(word in sql for word in ('DROP ','DELETE ','UPDATE public.','GRANT '))


def test_deterministic_full_scale_dataset_without_database():
    a=seed.dataset();b=seed.dataset()
    assert len(a['users'])==10000 and len(a['teams'])==2000 and len(a['memberships'])==5000
    assert seed.digest(a)==seed.digest(b) and seed.digest(a)!=seed.digest(seed.dataset(2027))
    assert len({u['timezone'] for u in a['users']})==9 and len({tuple(u['skills']) for u in a['users']})==9
    assert sum(u['discoverable'] for u in a['users'])==8000


@pytest.mark.parametrize('kind',['duplicate','leader','membership','zone','username','scope'])
def test_synthetic_dataset_corruption_detected(kind):
    d=seed.dataset(users=8,teams=2)
    if kind=='duplicate':d['users'][1]['id']=d['users'][0]['id']
    elif kind=='leader':d['teams'][0]['leader']=uuid4()
    elif kind=='membership':d['memberships'].append(d['memberships'][0])
    elif kind=='username':d['users'][1]['username']=d['users'][0]['username']
    elif kind=='scope':d['teams'][0]['hackathon_id']=uuid4()
    else:d['users'][0]['timezone']='Mars/Base'
    with pytest.raises(ValueError):seed.validate_dataset(d)


def test_seed_rejects_existing_rows_before_any_insert():
    c=MagicMock();c.execute.return_value.scalar_one.return_value=1
    with pytest.raises(ValueError,match='empty'):seed.insert(c,seed.dataset(users=4,teams=1),'synthetic-hash-not-used')
    assert all(not str(call.args[0]).startswith('INSERT') for call in c.execute.call_args_list)


def summary(p95=150,error=0):
    return dict(schema_version=1,vus=100,duration_seconds=60,warmup_seconds=20,measured_elapsed_seconds=60,metrics={
        'board_latency':{'values':{'med':50,'p(95)':p95,'p(99)':max(190,p95)}},
        'board_errors':{'values':{'rate':error}},'board_requests':{'values':{'count':6000,'rate':100}}})


def test_synthetic_load_summary_and_threshold_failure_are_not_measurements():
    assert load.validate_summary(summary(),0)['passed'] is True
    assert load.validate_summary(summary(201),99)['passed'] is False
    assert load.validate_summary(summary(error=.01),99)['passed'] is False


@pytest.mark.parametrize('kind',['missing','vus','duration','nan','negative','count','order','exit','threshold'])
def test_load_report_refuses_incomplete_or_contradictory_results(kind):
    s=summary();code=0
    if kind=='missing':del s['metrics']['board_latency']
    elif kind=='vus':s['vus']=99
    elif kind=='duration':s['duration_seconds']=1
    elif kind=='nan':s['metrics']['board_latency']['values']['p(95)']=float('nan')
    elif kind=='negative':s['metrics']['board_errors']['values']['rate']=-1
    elif kind=='count':s['metrics']['board_requests']['values']['count']=1
    elif kind=='order':s['metrics']['board_latency']['values']['p(99)']=10
    elif kind=='exit':code=1
    else:code=99
    with pytest.raises((ValueError,KeyError)):load.validate_summary(s,code)


def accepted():
    return dict(schema_version=1,suite='profiles',revision=targets.REVISION,repetitions=1,status='passed',stage='pytest',collected=29,
        teardowns_completed=29,skipped=0,failures=[],active_node=None,exit_code=0,invariant_verification='suite_and_fixture_checks_completed')


@pytest.mark.parametrize('field,value',[('collected',0),('collected',28),('skipped',1),('teardowns_completed',28),
    ('active_node','unfinished'),('status','incomplete'),('failures',[{}]),('exit_code',1),('invariant_verification','not_certified'),('revision','0005_invitations')])
def test_test_evidence_missing_skipped_or_incomplete_fails(field,value):
    data=accepted();data[field]=value
    with pytest.raises(ValueError):evidence.validate_test_report(data,'profiles',targets.REVISION,29,0)


def test_ci_rejects_local_environment_before_bootstrap():
    with pytest.raises(ValueError):ci.require_ci({})
    assert ci.require_ci(dict(GITHUB_ACTIONS='true',CI='true',RUNNER_ENVIRONMENT='github-hosted',CI_ADMIN_PASSWORD='synthetic-only')) is None


def test_workflow_yaml_json_subset_syntax_and_required_jobs():
    path=Path(__file__).resolve().parents[2]/'.github/workflows/ci.yml'
    workflow=json.loads(path.read_text())  # JSON is a strict YAML 1.2 subset.
    assert set(workflow['jobs']['postgres']['strategy']['matrix']['revision'])==set(ci.PLANS)
    assert workflow['permissions']=={'contents':'read'}
    assert workflow['jobs']['postgres']['services']['postgres']['ports']==['127.0.0.1:5432:5432']
    assert any('--maxWorkers=1' in step.get('run','') for step in workflow['jobs']['offline']['steps'])
    assert sum(n for suite,n in ci.PLANS['0003_auth'])==53 and ci.PLANS['0005_invitations'][0]==('invitations',13)
    assert acceptance.EXPECTED==30


def test_benchmark_host_has_no_write_routes_or_settings_fallback():
    from release_support.benchmark_host import benchmark_app
    from fastapi.testclient import TestClient
    engine=MagicMock(spec=Engine);engine.hide_parameters=True;engine.echo=False
    h=uuid4();app=benchmark_app(engine,h,'a'*64)
    paths={r.path for r in app.routes};assert paths=={'/health','/auth/session','/api/hackathons/{hackathon_id}/teams','/api/hackathons/{hackathon_id}/events','/api/benchmark/preflight'}
    assert all(r.methods=={'GET'} for r in app.routes)
    with TestClient(app,base_url='http://127.0.0.1:8766',client=('127.0.0.1',50000)) as client:
        assert client.get('/health').status_code==200
        assert client.get('/auth/session').status_code==401
        assert client.get('/api/benchmark/preflight').status_code==401
        assert client.post('/auth/register',json={}).status_code in (403,404)
        assert client.get(f'/api/hackathons/{uuid4()}/teams').status_code==403
    engine.connect.assert_not_called()


def test_load_host_mismatch_refused_before_workload():
    client=MagicMock();client.get.return_value.status_code=404
    with pytest.raises(ValueError):load.check_host(client,'synthetic-cookie',seed.dataset(users=4,teams=1))
    client.get.return_value.status_code=200;client.get.return_value.json.return_value={'database':'merge_dev'}
    with pytest.raises(ValueError):load.check_host(client,'synthetic-cookie',seed.dataset(users=4,teams=1))


@pytest.mark.parametrize('field,value',[('native_exit_code',1),('native_exit_code',False),('source_unchanged',False),('source',{'files':{}}),('kind','unknown')])
def test_receipt_verifier_rejects_stale_failed_or_unknown(field,value):
    current={'head':'synthetic','files':{'a':'digest'}}
    data=dict(schema_version=1,kind='migration',source=current,source_unchanged=True,native_exit_code=0,target='profiles',action='verify')
    assert verify.validate(data,current)=='migration'
    with pytest.raises(ValueError):verify.validate(data|{field:value},current)


def test_receipt_verifier_requires_complete_ci_matrix_job_evidence():
    current={'head':'synthetic','files':{}}
    data=dict(schema_version=1,kind='ci',source=current,source_unchanged=True,native_exit_code=0,revision='0006_profiles',isolated_postgres=True,
        steps=[dict(action=a,native_exit_code=0) for a in ('prepare','migrate','verify')])
    with pytest.raises(ValueError):verify.validate(data,current)
    report=accepted()|dict(collected=30,teardowns_completed=30)
    data['steps'].append(dict(suite='profiles',native_exit_code=0,report=report))
    assert verify.validate(data,current)=='ci'
    data['steps'][0]['native_exit_code']=1
    with pytest.raises(ValueError):verify.validate(data,current)


def test_report_rejects_missing_completion_marker_and_boolean_counts():
    data=accepted();del data['active_node']
    with pytest.raises(ValueError):evidence.validate_test_report(data,'profiles',targets.REVISION,29,0)
    data=accepted()|dict(skipped=False)
    with pytest.raises(ValueError):evidence.validate_test_report(data,'profiles',targets.REVISION,29,0)


def test_environment_template_cannot_be_used_as_measured_hardware():
    template=Path(__file__).resolve().parents[2]/'load/environment.example.json'
    with pytest.raises(ValueError):load.disclosures(json.loads(template.read_text()))


def test_synthetic_performance_receipt_verification_requires_finite_complete_metrics():
    current={'head':'synthetic','files':{}}
    hardware={k:'synthetic offline fixture' for k in ('client_cpu','client_ram','server_cpu','server_ram','postgres_topology','storage','cache_conditions')}
    hardware['server_workers']='1'
    data=dict(schema_version=1,kind='load',source=current,source_unchanged=True,native_exit_code=0,hardware=hardware,
        users=10000,teams=2000,vus=100,duration_seconds=60,warmup_seconds=20,sse_clients=32,measured=True,
        metrics=load.validate_summary(summary(),0),postgres_version='synthetic',k6_version='synthetic',outbox_rows=0)
    assert verify.validate(data,current)=='load'
    data['metrics']['p99_ms']=float('nan')
    with pytest.raises(ValueError):verify.validate(data,current)


def test_provisioning_proposals_are_fixed_create_only_and_never_adopt_existing():
    root=Path(__file__).resolve().parents[2]
    for name,db in [('profile_test','merge_profile_test'),('bench','merge_bench')]:
        source=(root/f'scripts/provision_merge_{name}.sql').read_text()
        assert f'CREATE DATABASE {db} ' in source and '\\set ON_ERROR_STOP on' in source
        assert '127.0.0.1' in source and "current_user<>'postgres'" in source and 'RAISE EXCEPTION' in source
        assert not any(word in source.upper() for word in ('DROP ','TRUNCATE ','DELETE ','ALTER ROLE','ALTER DATABASE'))


def test_profile_collection_has_thirty_unique_safe_receipt_node_ids():
    from test_support.diagnostics import Diagnostics
    root=Path(__file__).resolve().parents[1]
    env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='')
    result=subprocess.run([sys.executable,'-m','pytest','profile_tests','--collect-only','-q','--confirm-profile-test'],
        cwd=root,env=env,capture_output=True,text=True,timeout=30)
    nodes=[Diagnostics.node_id(line) for line in result.stdout.splitlines() if line.startswith('profile_tests/test_profiles.py::')]
    assert result.returncode==0 and len(nodes)==30 and len(set(nodes))==30 and all('withheld' not in n for n in nodes)
    plugin=acceptance.Plugin(None)
    with pytest.raises(ValueError):plugin.pytest_collection_finish(SimpleNamespace(items=[]))
    plugin.pytest_collection_finish(SimpleNamespace(items=[SimpleNamespace(nodeid=n) for n in nodes]))
