"""Independent exact0006 loopback host. No ASGI app or live I/O at import time."""
from contextlib import asynccontextmanager
import json
from starlette.concurrency import run_in_threadpool
from fastapi import Request
from fastapi.routing import APIRoute, iter_route_contexts
from pydantic import SecretBytes

from app import auth, read_api, team_api, admission_api, invitation_api, lifecycle_api, profile_api, realtime_api
from app.main import create_app
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.teams import TeamService
from app.services.admission import AdmissionService
from app.services.invitations import InvitationService
from app.services.lifecycle import LifecycleService
from app.services.team_reads import TeamReadService
from app.services.profiles import ProfileService
from app.services.matching import MatchingService
from app.services.realtime import RealtimeService
from app.services.throttling import ThrottleService, ThrottlePolicy
from release_support.integrated_ledger import Ledger, require
from release_support.integrated_diagnostics import HostDiagnostics
from release_support.targets import guarded_engine, Target, REVISION
from test_support.browser import HOST, PORT, ORIGIN, local_policy, validate_policy

# Independent closed inventory: do not import/modify the old host's allowlist.
H = '/api/hackathons/{hackathon_id}'
T = H+'/teams/{team_id}'
ENDPOINTS = {
    ('/auth/register','POST'):auth.register,('/auth/login','POST'):auth.login,
    ('/auth/session','GET'):auth.current_session,('/auth/logout','POST'):auth.logout,
    ('/api/hackathons','GET'):read_api.hackathons,(H+'/teams','GET'):read_api.teams,
    (T,'GET'):read_api.team,(H+'/me/team','GET'):read_api.my_team,
    (H+'/teams','POST'):team_api.create_team,
    (T+'/join-requests','POST'):admission_api.create_request,
    (T+'/join-requests/mine','GET'):admission_api.own_request,
    (T+'/join-requests','GET'):admission_api.pending_requests,
    (T+'/join-requests/{request_id}/decision','POST'):admission_api.decide_request,
    (T+'/invitations','POST'):invitation_api.issue_invitation,
    (T+'/invitations/{invitation_id}/redeem','POST'):invitation_api.redeem_invitation,
    (H+'/invitations/mine','GET'):invitation_api.own_invitations,
    (T+'/members','GET'):lifecycle_api.members,(T+'/leave','POST'):lifecycle_api.leave,
    (T+'/members/{user_id}/remove','POST'):lifecycle_api.remove,
    ('/api/me/profile','GET'):profile_api.profile,('/api/me/profile','POST'):profile_api.update_profile,
    ('/api/profile/timezones','GET'):profile_api.profile_timezones,
    (T+'/suggestions','GET'):profile_api.suggestions,(H+'/events','GET'):realtime_api.events,
}
SERVICES = {auth.get_services,read_api.get_read_service,team_api.get_team_service,
    admission_api.get_admission_service,invitation_api.get_invitation_service,
    lifecycle_api.get_lifecycle_service,profile_api.get_profile_service,
    profile_api.get_matching_service,realtime_api.get_realtime_service}
BASE = {auth.get_services,auth.authenticated_session,auth.session_cookie}
WRITE = {team_api.creation_session,team_api.idempotency_key}
DEPENDENCIES = SERVICES | BASE | WRITE | {read_api.read_request,admission_api.read_scope,
    invitation_api.mutation_session,invitation_api.inbox_scope,lifecycle_api.roster_scope,
    profile_api.scope,realtime_api.stream_request}


def expected_dependencies(path, method):
    if path in ('/auth/register','/auth/login'): return {auth.get_services}
    expected = BASE.copy()
    if path.startswith('/auth/'): return expected
    if path == '/api/profile/timezones': expected.add(profile_api.scope)
    elif path == '/api/me/profile' or path.endswith('/suggestions'):
        expected |= {profile_api.scope,profile_api.get_matching_service if path.endswith('/suggestions') else profile_api.get_profile_service}
        if method == 'POST': expected.add(team_api.creation_session)
    elif path.endswith('/events'): expected |= {realtime_api.get_realtime_service,realtime_api.stream_request}
    elif '/invitations' in path:
        expected.add(invitation_api.get_invitation_service)
        expected |= WRITE | {invitation_api.mutation_session} if method == 'POST' else {invitation_api.inbox_scope}
    elif '/join-requests' in path:
        expected.add(admission_api.get_admission_service)
        expected |= WRITE if method == 'POST' else {admission_api.read_scope}
    elif path.endswith('/members') or path.endswith('/leave') or path.endswith('/remove'):
        expected.add(lifecycle_api.get_lifecycle_service)
        expected |= WRITE if method == 'POST' else {lifecycle_api.roster_scope}
    elif method == 'POST': expected |= {team_api.get_team_service} | WRITE
    else: expected |= {read_api.get_read_service,read_api.read_request}
    return expected


def audit_wiring(app, overrides, health):
    require(dict(app.dependency_overrides) == overrides and set(overrides) == SERVICES)
    require(all(getattr(app.state,k,None) is None for k in ('auth_engine','auth_services','read_service')))
    def walk(d):
        result = set()
        for child in d.dependencies:
            require(child.call in DEPENDENCIES); result.add(child.call); result.update(walk(child))
        return result
    found = {}; count = 0
    for route in iter_route_contexts(app.routes):
        require(isinstance(route.original_route,APIRoute))
        calls = walk(route.dependant)
        if route.path == '/health':
            require(route.endpoint is health and route.methods == {'GET'} and not calls); count += 1; continue
        for method in route.methods:
            key = (route.path,method)
            require(key not in found and ENDPOINTS.get(key) is route.endpoint)
            require(route.original_route.endpoint is route.endpoint)
            require(calls == expected_dependencies(*key)); found[key] = route.endpoint
    require(found == ENDPOINTS and count == 1)


class Sessions:
    def __init__(self, real, ledger, diagnostics): self.real,self.ledger,self.diagnostics = real,ledger,diagnostics
    def _validate(self, method, *args):
        self.diagnostics.validation()
        value = getattr(self.real, method)(*args)
        self.ledger.principal(value.principal if method == 'validate_with_csrf' else value)
        self.diagnostics.validation(success=True)
        return value
    def validate(self, token):
        return self._validate('validate', token)
    def validate_with_csrf(self, token):
        return self._validate('validate_with_csrf', token)
    def verify_csrf(self, token, csrf):
        return self._validate('verify_csrf', token, csrf)
    def login(self, **v):
        active=self.ledger.active
        require(active and active['tag'].startswith('login_'))
        result=self.real.login(**v);self.ledger.principal(result.principal);return result
    def revoke(self, token):
        p=self.validate(token);require(self.ledger.active['tag']=='logout_'+self.ledger.principal(p))
        return self.real.revoke(token)


class Credentials:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def register(self, **v):
        value=self.real.register(**v);self.ledger.bind_account(value);return value


class Throttle:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def check(self, **v):
        active=self.ledger.active
        require(active and active['tag'].startswith(v['operation']+'_') and v['client_ip']==HOST)
        return self.real.check(**v)
    def check_invitation(self, *, actor_id, operation):
        self.ledger.invitation_charge(actor_id,operation)
        return self.real.check_invitation(actor_id=actor_id,operation=operation)


class Commands:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def create_team_idempotent(self, **v): return self.ledger.invoke(self.real,'create_team_idempotent',v)
    def create_request(self, **v): return self.ledger.invoke(self.real,'create_request',v)
    def decide_request(self, **v): return self.ledger.invoke(self.real,'decide_request',v)
    def issue(self, **v): return self.ledger.invoke(self.real,'issue',v)
    def redeem(self, **v): return self.ledger.invoke(self.real,'redeem',v)
    def leave(self, **v): return self.ledger.invoke(self.real,'leave',v)
    def remove(self, **v): return self.ledger.invoke(self.real,'remove',v)
    def own_request(self, **v):
        self.ledger.read(v['hackathon_id'],v['team_id'],v['actor_id']);return self.real.own_request(**v)
    def pending_requests(self, **v):
        self.ledger.read(v['hackathon_id'],v['team_id'],v['actor_id']);return self.real.pending_requests(**v)
    def mine(self, **v):
        self.ledger.read(v['hackathon_id'],actor=v['actor_id']);return self.real.mine(**v)
    def members(self, **v):
        self.ledger.read(v['hackathon_id'],v['team_id'],v['actor_id']);return self.real.members(**v)


class Reads:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def hackathons(self, **v): return self.real.hackathons(**v)
    def teams(self,h,**v): self.ledger.read(h);return self.real.teams(h,**v)
    def team(self,h,t): self.ledger.read(h,t);return self.real.team(h,t)
    def my_team(self,h,u): self.ledger.read(h,actor=u);return self.real.my_team(h,u)


class Profiles:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def get(self,u): self.ledger.actor(u);return self.real.get(u)
    def update(self,u,body):
        require(self.ledger.active and self.ledger.active['tag'].startswith('profile_'))
        self.ledger.actor(u);return self.real.update(u,body)


class Matching:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def suggestions(self,h,t,u,**v): self.ledger.read(h,t,u);return self.real.suggestions(h,t,u,**v)


class Realtime:
    def __init__(self, real, ledger): self.real,self.ledger=real,ledger
    def revision(self,h,u):
        self.ledger.read(h,actor=u)
        try:return self.real.revision(h,u)
        except BaseException:
            self.ledger.failed=True
            raise


def browser_app(engine, guard, plan, policy, *, allow_writes=False, diagnostics=None):
    validate_policy(policy,HOST);require(allow_writes is True)
    ledger=Ledger(plan);app=create_app(policy)
    diagnostics = diagnostics if diagnostics is not None else HostDiagnostics()
    app.state.integrated_diagnostics = diagnostics
    app.routes[:]=[r for r in app.routes if getattr(r,'path',None) not in ('/openapi.json','/docs','/docs/oauth2-redirect','/redoc')]
    app.openapi_url=app.docs_url=app.redoc_url=None
    raw_sessions=SessionService(engine)
    throttle=ThrottleService(engine,secret=SecretBytes(bytes.fromhex(policy.throttle_secret.get_secret_value())),policy=ThrottlePolicy())
    services=auth.AuthServices(Credentials(CredentialService(engine),ledger),Sessions(raw_sessions,ledger,diagnostics),Throttle(throttle,ledger))
    values={auth.get_services:services,read_api.get_read_service:Reads(TeamReadService(engine),ledger),
        team_api.get_team_service:Commands(TeamService(engine),ledger),
        admission_api.get_admission_service:Commands(AdmissionService(engine),ledger),
        invitation_api.get_invitation_service:Commands(InvitationService(engine),ledger),
        lifecycle_api.get_lifecycle_service:Commands(LifecycleService(engine),ledger),
        profile_api.get_profile_service:Profiles(ProfileService(engine),ledger),
        profile_api.get_matching_service:Matching(MatchingService(engine),ledger),
        realtime_api.get_realtime_service:Realtime(RealtimeService(engine),ledger)}
    def fixed(value):
        def provider(): return value
        return provider
    overrides={key:fixed(value) for key,value in values.items()};app.dependency_overrides.update(overrides)
    health=next(r.endpoint for r in iter_route_contexts(app.routes) if r.path=='/health')
    original=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with original(application):
            audit_wiring(app,overrides,health);require(not guard.failed.is_set())
            yield
            audit_wiring(app,overrides,health);app.state.integrated_shutdown_complete=True
    app.router.lifespan_context=lifespan

    class ClosedHost:
        async def __call__(self, scope, receive, send):
            if scope['type']!='http': return await app(scope,receive,send)
            diagnostics.request(scope)
            posted=False;status=None;complete=False
            try:
                audit_wiring(app,overrides,health)
                require(not ledger.failed and not guard.failed.is_set())
                scope['app']=app
                request=Request(scope)
                if request.method=='POST':
                    ledger.begin();posted=True
                    # Bound the request even when sent as chunked encoding.
                    raw=bytearray()
                    while True:
                        part=await receive();require(part['type']=='http.request')
                        raw.extend(part.get('body',b''));require(len(raw)<=8192)
                        if not part.get('more_body'):break
                    def unique(pairs):
                        out={}
                        for k,v in pairs:require(k not in out);out[k]=v
                        return out
                    body=json.loads(raw,object_pairs_hook=unique);require(type(body) is dict)
                    require(not request.url.query and not request.headers.getlist('x-user-id') and not request.headers.getlist('x-actor-id'))
                    probes=request.headers.getlist('x-merge-acceptance-probe');require(len(probes)<=1)
                    probe=probes[0] if probes else None
                    role=None
                    if request.url.path not in ('/auth/register','/auth/login'):
                        if probe=='missing_session':
                            require(not request.headers.getlist('cookie') and not request.headers.getlist('x-csrf-token'))
                        else:
                            token=auth.session_cookie(request)
                            p=await run_in_threadpool(services.sessions.validate,token)
                            role=ledger.principal(p)
                    if probe=='missing_csrf':require(not request.headers.getlist('x-csrf-token'))
                    if probe=='foreign_origin':
                        require(request.headers.getlist('origin')==['https://foreign.invalid'])
                        csrf_headers=request.headers.getlist('x-csrf-token');require(len(csrf_headers)==1)
                        csrf=auth.decode_token(csrf_headers[0]);require(csrf is not None)
                        await run_in_threadpool(services.sessions.verify_csrf,token,csrf)
                    if probe!='foreign_origin':require(request.headers.getlist('origin')==[ORIGIN])
                    keys=request.headers.getlist('idempotency-key');require(len(keys)<=1)
                    ledger.claim(request.url.path,body,role,keys[0] if keys else None,probe)
                    # Only transient body bytes are replayed to the REAL boundary.
                    supplied=False
                    async def replay():
                        nonlocal supplied
                        if not supplied:
                            supplied=True;return {'type':'http.request','body':bytes(raw),'more_body':False}
                        return await receive()
                    incoming=replay
                else:incoming=receive
                error_bytes=bytearray()
                async def observed(message):
                    nonlocal status,complete
                    if message['type']=='http.response.start':status=message['status']
                    if (posted and ledger.active and ledger.active['expected'] is not None and ledger.active['expected']>=400
                            and message['type']=='http.response.body'):
                        error_bytes.extend(message.get('body',b''));require(len(error_bytes)<=16384)
                    if message['type']=='http.response.body' and not message.get('more_body',False):complete=True
                    await send(message)
                await app(scope,incoming,observed)
                if posted:
                    error_code=json.loads(error_bytes).get('error',{}).get('code') if error_bytes else None
                    ledger.finish(status,complete,error_code)
                elif status is not None and status>=500:ledger.failed=True
            except BaseException:
                ledger.failed=True
                if posted:ledger.active=None
                if status is None:
                    response=auth.error_response(503,'service_unavailable','Integrated campaign closed; stop.')
                    response.headers.update({'Cache-Control':'no-store, private','X-Content-Type-Options':'nosniff'})
                    return await response(scope,receive,send)
                raise
    return ClosedHost(),app,ledger,throttle


def profile_engine(target):
    # Validate BEFORE the shared engine factory; never let benchmark be selected.
    require(isinstance(target,Target) and target.kind=='profiles')
    target.url()
    return guarded_engine(target,REVISION)
