"""Owner-gated integrated host supervisor. No module-level live operations."""
from hashlib import sha256
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from release_support.evidence import ROOT, sources
from release_support.integrated_plan import load_plan, digest, TARGET, COMMANDS, PROFILE_POSTS
from release_support.integrated_ledger import require
from release_support.integrated_diagnostics import HostDiagnostics, IntegratedServer

DIRECTORY=ROOT/'backend/test-results/integrated'


class CampaignFailure(ValueError):
    def __init__(self,diagnostics):
        self.diagnostics=diagnostics
        super().__init__('Integrated campaign incomplete; retain state')


class ObserverFailure(ValueError):
    def __init__(self,path,native):
        self.path,self.native=path,native
        super().__init__('Independent observer incomplete')


def new_path(prefix):
    require(prefix in ('host','prepare','inspect','process','observer','certification'))
    for p in (DIRECTORY.parent,DIRECTORY):
        require(not p.is_symlink() and p.resolve()==p.parent.resolve()/p.name)
        p.mkdir(exist_ok=True)
    return DIRECTORY/f'{prefix}-{uuid4().hex}.json'


def write_new(path,data):
    require(path.parent==DIRECTORY and not path.is_symlink() and DIRECTORY.resolve()==DIRECTORY)
    with path.open('x',encoding='utf8') as out:json.dump(data,out,indent=2,allow_nan=False)


def claim_campaign(plan,source):
    """One start per public run ID, including failures before the first POST.

    This local evidence fence supplements DB freshness checks. Never delete it
    to reset budgets; an interrupted scope needs a new reviewed campaign.
    """
    path=DIRECTORY/f"campaign-{plan['run_id']}.json"
    write_new(path,dict(schema_version=1,kind='integrated-start-marker',run_id=plan['run_id'],
        plan_sha256=digest(plan),target=TARGET,source=source,status='started_not_certified'))
    return path


def read_report(path):
    path=Path(path).absolute()
    require(path.parent==DIRECTORY and DIRECTORY.resolve()==DIRECTORY and not path.is_symlink() and path.stat().st_size<=4_000_000)
    return json.loads(path.read_text(encoding='utf8'))


def charges(throttle,ledger):
    entries=[('register_ip','127.0.0.1',4),('login_ip','127.0.0.1',5)]
    entries += [('login_account',a['username'],2 if a['role']=='l' else 1) for a in ledger.plan['accounts']]
    entries += [('invitation_issue',str(ledger.ids['l']),2)]
    entries += [('invitation_redeem',str(ledger.ids[r]),1) for r in ('q','r','x')]
    return [dict(scope='auth:v1:'+op,key=throttle._key(op,identifier).hex(),count=count) for op,identifier,count in entries]


def observer_process(before,plan,ledger,throttle,password):
    payload=dict(before=before,plan=plan,ledger=ledger.observer_input(),charges=charges(throttle,ledger))
    raw=json.dumps(payload,allow_nan=False).encode();require(len(raw)<=8_000_000)
    env=dict(os.environ,MERGE_INTEGRATED_CHILD_PASSWORD=password)
    native=None;data=dict(status='failed',invariants='not_certified');path=new_path('observer')
    try:
        result=subprocess.run([sys.executable,'-m','release_support.integrated_observer','--private-worker'],
            cwd=ROOT/'backend',input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,timeout=60)
        native=result.returncode;require(len(result.stdout)<=16384)
        parsed=json.loads(result.stdout)
        require(set(parsed)<= {'status','invariants','totals'})
        data=parsed
    except BaseException:pass
    write_new(path,dict(native_exit_code=native,**data))
    if not (type(native) is int and native==0 and data.get('status')=='passed'
        and data.get('invariants')=='fresh_scope_and_prior_rows_verified'):
        raise ObserverFailure(path,native)
    return data,native,path


def serve_worker(target,plan,password):
    import uvicorn
    from release_support.integrated_host import profile_engine,browser_app
    from release_support.integrated_observer import snapshot,preflight
    from test_support.browser import reserved_socket,local_policy,HOST,PORT
    stage='preflight';ledger=None;diagnostic=HostDiagnostics()
    try:
        with reserved_socket() as sock, profile_engine(target) as (engine,guard):
            with engine.connect() as c:before=snapshot(c,plan);preflight(before,plan,True)
            host,app,ledger,throttle=browser_app(engine,guard,plan,local_policy(),allow_writes=True,diagnostics=diagnostic)
            config=uvicorn.Config(host,host=HOST,port=PORT,workers=1,reload=False,proxy_headers=False,
                forwarded_allow_ips='',access_log=False,log_config=None,log_level='critical',timeout_graceful_shutdown=25)
            server=IntegratedServer(config,diagnostic)
            stage='browser'
            try:
                print('Integrated exact0006 host starting; approved loopback campaign only.',flush=True)
                try:
                    server.run(sockets=[sock]);diagnostic.run_returned=True
                except KeyboardInterrupt:
                    diagnostic.interrupted=True;diagnostic.shutdown_requested=True
            finally:
                if not server.drained():
                    diagnostic.drain_failure_latched_guard=True;guard.failed.set()
            stage='drain'
            diagnostic.check_drain(server,guard,ledger,app)
            stage='ledger_complete'
            try:ledger.complete()
            except BaseException:
                diagnostic.failed_predicates=['ledger_complete']
                raise
            stage='observer'
            observed,exit_code,path=observer_process(before,plan,ledger,throttle,password)
            summary=ledger.observer_input()
            return dict(status='passed',host_drained=True,budget_enforced_by_host=True,actual_bindings_verified=True,
                diagnostics=dict(lifecycle=diagnostic.snapshot()),
                observer_native_exit=exit_code,observer_report=path.name,observer_sha256=sha256(path.read_bytes()).hexdigest(),
                totals=observed['totals'],invariants=observed['invariants'],
                commands={t:dict(attempts=n,effects=e,statuses=ledger.statuses[t],
                    same_key_payload_actor_scope=True) for t,r,n,e,s in COMMANDS},
                profile_statuses={t:ledger.statuses[t][0] for t,r,s in PROFILE_POSTS},
                security_statuses={t:ledger.statuses[t][0] for t in ('missing_session','missing_csrf','foreign_origin')},
                denial_codes=ledger.denials,
                bindings=dict(summary['bindings'],**summary['ids']))
    except BaseException as error:
        diagnostics=dict(stage=stage,ledger=None if ledger is None else ledger.diagnostics(),lifecycle=diagnostic.snapshot())
        if isinstance(error,ObserverFailure):
            diagnostics.update(observer_report=error.path.name,observer_native_exit=error.native,
                observer_sha256=sha256(error.path.read_bytes()).hexdigest())
        raise CampaignFailure(diagnostics) from None


def worker(action,path):
    from release_support.integrated_host import profile_engine
    from release_support.integrated_observer import snapshot,preflight,prepare,preparation_delta
    from release_support.targets import Target
    from test_support.browser import quiet_logs
    require(action in ('inspect','prepare','serve') and path.parent==DIRECTORY and DIRECTORY.resolve()==DIRECTORY
        and not path.exists() and not path.is_symlink()
        and re.fullmatch(r'(?:host|prepare|inspect)-[0-9a-f]{32}\.json',path.name) is not None)
    before_source=sources();plan=load_plan();code=1;started=datetime.now(timezone.utc).isoformat()
    data=dict(status='failed',invariants='not_certified');marker=None;marker_hash=None
    try:
        password=os.environ.pop('MERGE_INTEGRATED_CHILD_PASSWORD','');require(bool(password))
        target=Target('profiles',True,password)
        with quiet_logs():
            if action=='serve':
                marker=claim_campaign(plan,before_source);marker_hash=sha256(marker.read_bytes()).hexdigest()
                data=serve_worker(target,plan,password)
                require(sha256(marker.read_bytes()).hexdigest()==marker_hash)
            else:
                with profile_engine(target) as (engine,_):
                    if action=='prepare':before=prepare(engine,plan)
                    else:
                        with engine.connect() as c:preflight(snapshot(c,plan),plan,False)
                if action=='prepare':
                    with profile_engine(target) as (observer,_):
                        with observer.connect() as c:after=snapshot(c,plan)
                    preparation_delta(before,after,plan)
                data=dict(status='passed',invariants='two_new_hackathons_only' if action=='prepare' else 'unprepared_scope_fresh')
        code=0
    except CampaignFailure as error:
        data=dict(status='failed',invariants='not_certified',diagnostics=error.diagnostics)
    except FileExistsError:
        data=dict(status='failed',invariants='not_certified',diagnostics={'stage':'start_marker','reason':'scope_already_started'})
    except BaseException:pass
    after_source=sources()
    if before_source!=after_source:code=1;data['status']='failed'
    write_new(path,dict(schema_version=1,kind='integrated-host-step',action=action,
        run_id=plan['run_id'],plan_sha256=digest(plan),target=TARGET,source=before_source,
        start_marker=None if marker is None else marker.name,start_marker_sha256=marker_hash,
        source_unchanged=before_source==after_source,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),**data))
    return code


def static_readiness():
    """Construct/audit route objects only: no service, lifespan, engine or socket."""
    from app.main import create_app
    from fastapi.routing import iter_route_contexts
    from release_support.integrated_host import SERVICES,audit_wiring,ENDPOINTS
    from test_support.browser import local_policy
    app=create_app(local_policy())
    app.routes[:]=[r for r in app.routes if getattr(r,'path',None) not in ('/openapi.json','/docs','/docs/oauth2-redirect','/redoc')]
    def forbidden():raise ValueError('Static audit has no live service')
    overrides={key:forbidden for key in SERVICES};app.dependency_overrides.update(overrides)
    health=next(r.endpoint for r in iter_route_contexts(app.routes) if r.path=='/health')
    audit_wiring(app,overrides,health)
    return dict(status='CONDITIONAL',infrastructure='offline_route_audit_passed',routes=len(ENDPOINTS)+1,
        service_overrides=len(SERVICES),target=TARGET,live_operations_performed=False,
        blockers=['Owner-approved provisioning/exact0006 and source-bound profile30 evidence are still required.',
                  'No live host/browser/observer, keyboard/mobile or transport acceptance has executed.'])


def arguments(argv):
    from test_support.browser import SafeParser
    parser=SafeParser(description=__doc__)
    parser.add_argument('action',choices=('readiness','inspect','prepare','serve'))
    parser.add_argument('--confirm-profile-test',action='store_true')
    parser.add_argument('--revision',choices=('0006_profiles',))
    parser.add_argument('--profile-receipt',type=Path)
    parser.add_argument('--allow-fixture-writes',action='store_true')
    parser.add_argument('--allow-browser-writes',action='store_true')
    args=parser.parse_args(argv)
    live=args.action!='readiness'
    if (not __debug__ or args.confirm_profile_test!=live or bool(args.revision)!=live or bool(args.profile_receipt)!=live
            or args.allow_fixture_writes!=(args.action=='prepare') or args.allow_browser_writes!=(args.action=='serve')):
        parser.error('Exact target/revision, profile evidence and separate write opt-in required')
    return args


def approved_profile(path,current):
    from release_support.verify import validate
    path=path.absolute();directory=ROOT/'backend/test-results/release'
    require(path.parent==directory and directory.resolve()==directory and not path.is_symlink() and path.stat().st_size<=2_000_000)
    require(validate(json.loads(path.read_text(encoding='utf8')),current)=='profiles')


def main(argv=None):
    args=arguments(argv)
    if args.action=='readiness':print(json.dumps(static_readiness(),indent=2));return 0
    from test_support.browser import hidden_password
    before=sources();report_path=new_path('host' if args.action=='serve' else args.action)
    start_path=new_path('process')
    write_new(start_path,dict(schema_version=1,kind='integrated-process',action=args.action,status='incomplete',
        run_id=load_plan()['run_id'],source=before,source_unchanged=True,native_exit_code=None,
        worker_report=report_path.name,worker_sha256=None))
    print(f'Integrated start receipt: {start_path.name}; incomplete until final receipt.',flush=True)
    code=1;host_native=None;report=None
    try:
        require(not any(name in os.environ for name in ('MERGE_RELEASE_DB_PASSWORD','MERGE_TEST_DB_PASSWORD','MERGE_INTEGRATED_CHILD_PASSWORD')))
        approved_profile(args.profile_receipt,before)
        password=hidden_password()
        env=dict(os.environ,MERGE_INTEGRATED_CHILD_PASSWORD=password)
        # No shell, arbitrary executable, URL, DB name or user-selected test path.
        process=subprocess.Popen([sys.executable,'-m','release_support.integrated_run','_private_worker',args.action,str(report_path)],
            cwd=ROOT/'backend',env=env)
        try:
            try:host_native=process.wait()
            # Includes 25s drain + the independent observer's 60s ceiling and
            # bounded teardown/hash overhead. A second interrupt still fails.
            except KeyboardInterrupt:host_native=process.wait(timeout=100)
        except BaseException:
            process.terminate();process.wait(timeout=10);raise
        report=read_report(report_path)
        require(type(host_native) is int and host_native==0 and report.get('status')=='passed'
            and report.get('schema_version')==1 and report.get('kind')=='integrated-host-step'
            and report.get('action')==args.action and report.get('run_id')==load_plan()['run_id']
            and report.get('plan_sha256')==digest(load_plan()) and report.get('target')==TARGET
            and report.get('source')==before and report.get('source_unchanged') is True)
        code=0
    except BaseException:pass
    after=sources()
    if before!=after:code=1
    path=new_path('process')
    write_new(path,dict(schema_version=1,kind='integrated-process',action=args.action,status='passed' if code==0 else 'failed',
        run_id=load_plan()['run_id'],source=before,source_unchanged=before==after,native_exit_code=host_native,
        worker_report=report_path.name if report_path.exists() else None,
        worker_sha256=sha256(report_path.read_bytes()).hexdigest() if report_path.exists() else None))
    print(f'Integrated process receipt: {path.name}; exit={code}; fixtures retained.')
    return code


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='_private_worker':
        require(sys.argv[2] in ('inspect','prepare','serve'))
        raise SystemExit(worker(sys.argv[2],Path(sys.argv[3]).absolute()))
    raise SystemExit(main())
