"""Explicit exact-0005 full-stack browser CLI. No module-level ASGI app or live I/O."""
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from threading import Event
from uuid import UUID

from fastapi import Request
from fastapi.routing import APIRoute, iter_route_contexts
from pydantic import SecretBytes, ValidationError
from sqlalchemy import create_engine, event, text
import uvicorn

from app import auth, read_api, team_api, admission_api, invitation_api, lifecycle_api, realtime_api, profile_api
from app.main import create_app
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.teams import TeamService
from app.services.admission import AdmissionService
from app.services.invitations import InvitationService
from app.services.team_reads import TeamReadService
from app.services.throttling import ThrottleService, ThrottlePolicy
from test_support.browser import (HOST, PORT, ORIGIN, BrowserServer, SafeParser,
    hidden_password, quiet_logs, reserved_socket, local_policy, validate_policy)
from test_support.database import TestDatabaseSettings, DiagnosticFailure, assert_test_identity, safe_failure_message
from test_support.browser_full_scope import read_scope, Ledger, rejected
from test_support.browser_full_state import PK, snapshot, preflight, certify, preserved, require

REVISION = '0005_invitations'


class ConnectionGuard:
    def __init__(self):
        self.failed = Event()

    def __call__(self, c):
        try:
            if self.failed.is_set():
                raise DiagnosticFailure('identity')
            if (c.dialect.name!='postgresql' or c.dialect.driver!='psycopg' or c.dialect.is_async is not False
                    or c.in_transaction() or c.in_nested_transaction()
                    or c.connection.dbapi_connection.autocommit is not False
                    or c.get_execution_options().get('isolation_level')=='AUTOCOMMIT'):
                raise DiagnosticFailure('driver-configuration')
            c.execute(text('SET TRANSACTION READ ONLY'))
            assert_test_identity(c)
            settings = tuple(c.execute(text('''SELECT current_setting('transaction_isolation'),
                current_setting('default_transaction_isolation'),current_setting('transaction_read_only'),
                current_setting('lock_timeout'),current_setting('statement_timeout')''')).one())
            if settings!=('read committed','read committed','on','5s','15s'):
                raise DiagnosticFailure('identity')
            if c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()!=[REVISION]:
                raise DiagnosticFailure('migration-state')
            c.rollback()
        except BaseException as error:
            self.failed.set()
            try: c.invalidate()
            except Exception: pass
            raise DiagnosticFailure(error.category if isinstance(error,DiagnosticFailure) else 'verification') from None


@contextmanager
def guarded_engine(settings):
    url = settings.url()
    if not settings.password:
        raise DiagnosticFailure('authentication')
    engine = create_engine(url, hide_parameters=True, isolation_level='READ COMMITTED',
        execution_options={'schema_translate_map':{None:'public'}},
        connect_args={'connect_timeout':5,'options':'-c statement_timeout=15000 -c lock_timeout=5000'})
    guard = ConnectionGuard()
    event.listen(engine,'engine_connect',guard)
    try:
        with engine.connect(): pass  # Initial guard before any snapshot/service.
        yield engine,guard
    finally:
        engine.dispose()


class Credentials:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def register(self, **v):
        identity = self.real.register(**v)
        self.ledger.bind_account(identity)
        return identity


class Sessions:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def login(self, **v):
        result=self.real.login(**v); self.ledger.principal(result.principal); return result
    def validate_with_csrf(self, token):
        result=self.real.validate_with_csrf(token); self.ledger.principal(result.principal); return result
    def verify_csrf(self, token, csrf):
        result=self.real.verify_csrf(token,csrf); self.ledger.principal(result); return result
    def revoke(self, token):
        principal=self.real.validate(token); role=self.ledger.principal(principal)
        self.ledger.auth_charge(self.ledger.accounts[role].username,'logout')
        return self.real.revoke(token)


class Throttle:
    def __init__(self, real, ledger, request, body):
        self.real,self.ledger,self.request,self.body=real,ledger,request,body
    def check(self, **v): return self.real.check(**v)
    def check_invitation(self, *, actor_id, operation):
        # Charge the exact domain attempt BEFORE the separately committing real
        # invitation throttle. An out-of-scope call cannot consume a DB bucket.
        p=self.request.path_params
        values={'hackathon_id':UUID(str(p['hackathon_id'])), 'team_id':UUID(str(p['team_id'])),
                'actor_id':actor_id, 'key':single_key(self.request)}
        method='issue' if operation=='issue' else 'redeem'
        values['recipient_id' if method=='issue' else 'invitation_id'] = UUID(self.body.recipient_id) if method=='issue' else UUID(str(p['invitation_id']))
        tag=self.ledger.reserve(method,values)
        self.request.state.browser_reserved=(tag,method,values)
        role=self.ledger.actor(actor_id)
        with self.ledger.lock:
            key=(role,'invitation_'+operation)
            self.ledger.used[key]=self.ledger.used.get(key,0)+1
        return self.real.check_invitation(actor_id=actor_id,operation=operation)


def single_key(request):
    from app.services.idempotency import _key
    values=request.headers.getlist('idempotency-key')
    if len(values)!=1: rejected()
    _key(values[0]); return values[0]


class Teams:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def create_team_idempotent(self, **v): return self.ledger.invoke(self.real,'create_team_idempotent',v)


class Admission:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def create_request(self, **v): return self.ledger.invoke(self.real,'create_request',v)
    def decide_request(self, **v): return self.ledger.invoke(self.real,'decide_request',v)
    def own_request(self, **v):
        self.ledger.read(v['hackathon_id'],v['team_id'],v['actor_id']); return self.real.own_request(**v)
    def pending_requests(self, **v):
        self.ledger.read(v['hackathon_id'],v['team_id'],v['actor_id']); return self.real.pending_requests(**v)


class Invitations:
    def __init__(self, real, ledger, request): self.real,self.ledger,self.request=real,ledger,request
    def mutate(self, method, v):
        reserved=getattr(self.request.state,'browser_reserved',None)
        if reserved is None or reserved[1:]!=(method,v): rejected()
        return self.ledger.invoke(self.real,method,v,reserved=reserved[0])
    def issue(self, **v): return self.mutate('issue',v)
    def redeem(self, **v): return self.mutate('redeem',v)
    def mine(self, **v):
        self.ledger.read(v['hackathon_id'],actor=v['actor_id']); return self.real.mine(**v)


class Reads:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def hackathons(self, **v): return self.real.hackathons(**v)  # Canonical public catalog; no fabricated filtering.
    def teams(self, h, **v): self.ledger.read(h); return self.real.teams(h,**v)
    def team(self, h, t): self.ledger.read(h,t); return self.real.team(h,t)
    def my_team(self, h, u): self.ledger.read(h,actor=u); return self.real.my_team(h,u)


ENDPOINTS = {
 ('/auth/register','POST'):auth.register, ('/auth/login','POST'):auth.login,
 ('/auth/session','GET'):auth.current_session, ('/auth/logout','POST'):auth.logout,
 ('/api/hackathons','GET'):read_api.hackathons,
 ('/api/hackathons/{hackathon_id}/teams','GET'):read_api.teams,
 ('/api/hackathons/{hackathon_id}/teams/{team_id}','GET'):read_api.team,
 ('/api/hackathons/{hackathon_id}/me/team','GET'):read_api.my_team,
 ('/api/hackathons/{hackathon_id}/teams','POST'):team_api.create_team,
 **{('/api/hackathons/{hackathon_id}/teams/{team_id}'+path,method):endpoint for path,method,endpoint in (
   ('/join-requests','POST',admission_api.create_request),('/join-requests/mine','GET',admission_api.own_request),
   ('/join-requests','GET',admission_api.pending_requests),('/join-requests/{request_id}/decision','POST',admission_api.decide_request))},
 ('/api/hackathons/{hackathon_id}/teams/{team_id}/invitations','POST'):invitation_api.issue_invitation,
 ('/api/hackathons/{hackathon_id}/teams/{team_id}/invitations/{invitation_id}/redeem','POST'):invitation_api.redeem_invitation,
 ('/api/hackathons/{hackathon_id}/invitations/mine','GET'):invitation_api.own_invitations}
SERVICES={auth.get_services,read_api.get_read_service,team_api.get_team_service,
          admission_api.get_admission_service,invitation_api.get_invitation_service}
DEPENDENCIES=SERVICES|{auth.authenticated_session,auth.session_cookie,read_api.read_request,
    team_api.creation_session,team_api.idempotency_key,admission_api.read_scope,
    invitation_api.mutation_session,invitation_api.inbox_scope}


def audit_wiring(app, overrides, health):
    if (dict(app.dependency_overrides)!=overrides or set(overrides)!=SERVICES
            or any(getattr(app.state,k) is not None for k in ('auth_engine','auth_services','read_service'))):
        raise DiagnosticFailure('verification')
    def walk(d):
        result=set()
        for child in d.dependencies:
            if child.call not in DEPENDENCIES: raise DiagnosticFailure('verification')
            result.add(child.call); result.update(walk(child))
        return result
    found={}; count=0
    for r in iter_route_contexts(app.routes):
        if not isinstance(r.original_route,APIRoute): raise DiagnosticFailure('verification')
        calls=walk(r.dependant)
        if r.path=='/health':
            require(r.endpoint is health and r.methods=={'GET'} and not calls); count+=1; continue
        expected={auth.get_services}
        if r.path not in ('/auth/register','/auth/login'):
            expected|={auth.authenticated_session,auth.session_cookie}
        if r.path.startswith('/api/'):
            if '/invitations' in r.path:
                expected|={invitation_api.get_invitation_service}
                expected|={invitation_api.mutation_session,team_api.creation_session,team_api.idempotency_key} if r.methods=={'POST'} else {invitation_api.inbox_scope}
            elif '/join-requests' in r.path:
                expected|={admission_api.get_admission_service}
                expected|={team_api.creation_session,team_api.idempotency_key} if r.methods=={'POST'} else {admission_api.read_scope}
            elif r.methods=={'POST'}:
                expected|={team_api.get_team_service,team_api.creation_session,team_api.idempotency_key}
            else:
                expected|={read_api.get_read_service,read_api.read_request}
        require(calls==expected)
        for m in r.methods:
            require((r.path,m) not in found); found[(r.path,m)]=r.endpoint
    require(found==ENDPOINTS and count==1)


def browser_app(engine, guard, scope, policy, *, allow_writes=False, host=HOST):
    validate_policy(policy,host)
    require(allow_writes is True)
    app=create_app(policy)
    app.routes[:]=[r for r in app.routes if getattr(r,'path',None) not in ('/openapi.json','/docs','/docs/oauth2-redirect','/redoc')
                  and getattr(r,'original_router',None) not in (lifecycle_api.router,realtime_api.router,profile_api.router)]
    app.openapi_url=app.docs_url=app.redoc_url=None
    ledger=Ledger(scope)
    throttle=ThrottleService(engine,secret=SecretBytes(bytes.fromhex(policy.throttle_secret.get_secret_value())),policy=ThrottlePolicy())
    credentials=Credentials(CredentialService(engine),ledger); sessions=Sessions(SessionService(engine),ledger)
    reads=Reads(TeamReadService(engine),ledger); teams=Teams(TeamService(engine),ledger)
    admission=Admission(AdmissionService(engine),ledger); invitations=InvitationService(engine)

    async def scoped_auth(request: Request):
        body=None
        if request.method=='POST':
            model=auth.RegisterBody if request.url.path=='/auth/register' else auth.LoginBody if request.url.path=='/auth/login' else invitation_api.IssueBody if request.scope['route'].name=='issue_invitation' else None
            if model:
                try: body=model.model_validate(await request.json())
                except (ValueError,ValidationError):
                    raise auth.AuthFailure(422,'invalid_request','Request body is invalid.') from None
            if request.url.path in ('/auth/register','/auth/login'):
                if request.state.auth_client_ip!=HOST: rejected()
                ledger.auth_charge(body.username,'register' if request.url.path=='/auth/register' else 'login')
        return auth.AuthServices(credentials,sessions,Throttle(throttle,ledger,request,body))

    def scoped_reads(): return reads
    def scoped_teams(): return teams
    def scoped_admission(): return admission
    def scoped_invitations(request: Request): return Invitations(invitations,ledger,request)
    overrides={auth.get_services:scoped_auth,read_api.get_read_service:scoped_reads,
        team_api.get_team_service:scoped_teams,admission_api.get_admission_service:scoped_admission,
        invitation_api.get_invitation_service:scoped_invitations}
    app.dependency_overrides.update(overrides)
    health=next(r.endpoint for r in iter_route_contexts(app.routes) if r.path=='/health')
    original=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with original(application):
            audit_wiring(app,overrides,health); require(not guard.failed.is_set())
            print('Full browser host ready; exact-0005 guarded loopback only.',flush=True)
            yield
            audit_wiring(app,overrides,health)
            app.state.browser_shutdown_complete=True
    app.router.lifespan_context=lifespan
    class ClosedHost:
        async def __call__(self, scope, receive, send):
            if scope['type']=='http':
                try:
                    audit_wiring(app,overrides,health); require(not guard.failed.is_set() and not ledger.failed)
                except Exception:
                    guard.failed.set()
                    response=auth.error_response(503,'service_unavailable','Browser host guard failed.')
                    response.headers.update({'Cache-Control':'no-store, private','Pragma':'no-cache','Expires':'0','X-Content-Type-Options':'nosniff'})
                    return await response(scope,receive,send)
            try: return await app(scope,receive,send)
            except BaseException:
                guard.failed.set(); raise
    return ClosedHost(),app,ledger,throttle


def prepare(engine, scope):
    with engine.connect() as c:
        before=snapshot(c,scope); preflight(before,scope,prepared=False)
        with c.begin():
            for h in scope.hackathons:
                c.execute(text('INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:h,:name,2,3)'),{'h':h.id,'name':h.name})
            # Inspect our uncommitted writes on this same transaction, then return
            # to writable mode only by committing the one owned transaction.
            for table,key in PK.items():
                current=dict(c.execute(text(f'SELECT {key},md5(to_jsonb(t)::text) FROM public.{table} t')).all())
                require(all(current.get(k)==v for k,v in before.hashes[table].items()))
                require(set(current)-set(before.hashes[table])==({str(h.id) for h in scope.hackathons} if table=='hackathons' else set()))
    return before


def serve(settings, scope, sock):
    with guarded_engine(settings) as (engine,guard):
        with engine.connect() as c:
            before=snapshot(c,scope); preflight(before,scope,prepared=True)
        host,app,ledger,throttle=browser_app(engine,guard,scope,local_policy(),allow_writes=True)
        config=uvicorn.Config(host,host=HOST,port=PORT,workers=1,reload=False,proxy_headers=False,
            forwarded_allow_ips='',access_log=False,log_config=None,log_level='critical',timeout_graceful_shutdown=25)
        server=BrowserServer(config)
        try:
            try: server.run(sockets=[sock])
            except KeyboardInterrupt: pass
        finally:
            if not server.drained():
                server.drain_failed=True
                guard.failed.set()
            with guarded_engine(settings) as (observer,_):
                with observer.connect() as c: after=snapshot(c,scope)
            certify(before,after,ledger,throttle)
        require(server.started and server.drained() and not guard.failed.is_set() and not ledger.failed
                and getattr(app.state,'browser_shutdown_complete',False))


def arguments(argv):
    parser=SafeParser(description=__doc__)
    parser.add_argument('action',choices=('inspect','prepare','serve','verify'))
    parser.add_argument('--confirm-merge-test',action='store_true',required=True)
    parser.add_argument('--revision',choices=(REVISION,),required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--allow-fixture-writes',action='store_true')
    parser.add_argument('--allow-browser-writes',action='store_true')
    args=parser.parse_args(argv)
    if (not __debug__ or args.allow_fixture_writes!=(args.action=='prepare')
            or args.allow_browser_writes!=(args.action=='serve')):
        parser.error('Separate explicit write approval required')
    return args


def main(argv=None):
    args=arguments(argv)
    try:
        with quiet_logs():
            scope=read_scope(args.manifest)
            if args.action=='serve':
                with reserved_socket() as sock:
                    settings=TestDatabaseSettings(confirmed=True,password=hidden_password())
                    serve(settings,scope,sock)
                print('Full browser host final journey invariants verified; fixtures retained.')
            else:
                settings=TestDatabaseSettings(confirmed=True,password=hidden_password())
                with guarded_engine(settings) as (engine,_):
                    if args.action=='prepare':
                        before=prepare(engine,scope)
                        with guarded_engine(settings) as (observer,_):
                            with observer.connect() as c: after=snapshot(c,scope)
                        preflight(after,scope,prepared=True)
                        preserved(before,after)
                        for table in PK:
                            require(set(after.hashes[table])-set(before.hashes[table])==
                                    ({str(h.id) for h in scope.hackathons} if table=='hackathons' else set()))
                    else:
                        with engine.connect() as c:
                            current=snapshot(c,scope)
                            if args.action=='inspect': preflight(current,scope,prepared=bool(current.rows['hackathons']))
                print('Full browser fixtures prepared; retained.' if args.action=='prepare' else 'Full browser current-state checks verified; no server started; no run certification.')
    except BaseException as error:
        # Parser exits are outside this block. Even a library SystemExit(0)
        # during an operational phase is failure, never successful certification.
        print(safe_failure_message(error,'verification')); return 1
    return 0


if __name__=='__main__': raise SystemExit(main())
