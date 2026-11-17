"""Synthetic control-flow/HTTP/observer tests only; never PostgreSQL evidence."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4,UUID

from fastapi.testclient import TestClient
from pydantic import SecretBytes
from sqlalchemy.engine import Engine
import pytest
from app import auth
from app.services.credentials import CredentialIdentity
from app.services.sessions import SessionPrincipal,ValidatedSession,IssuedSession
from app.services.idempotency import _StoredReply
from app.services.errors import DomainError,ErrorCode
from release_support import integrated_host as h,integrated_observer as o,integrated_run as run,targets
from release_support.integrated_ledger import Ledger,ORDER,command_spec,DENIALS
from release_support.integrated_plan import load_plan,COMMANDS


@pytest.fixture(autouse=True)
def forbid_live(monkeypatch):
    def forbidden(*a,**kw):pytest.fail('Live operation reached in offline harness tests')
    import psycopg,app.core.config,app.db.session,test_support.browser
    monkeypatch.setattr(targets,'create_engine',forbidden)
    monkeypatch.setattr(psycopg,'connect',forbidden)
    monkeypatch.setattr(app.core.config,'Settings',forbidden)
    monkeypatch.setattr(app.db.session,'build_engine',forbidden)
    monkeypatch.setattr(test_support.browser,'reserved_socket',forbidden)
    monkeypatch.setattr(test_support.browser,'hidden_password',forbidden)
    monkeypatch.setattr(test_support.browser.BrowserServer,'run',forbidden)
    monkeypatch.setattr(run.subprocess,'Popen',forbidden)


def empty():return dict(hashes={t:{} for t in o.PK},rows={t:{} for t in o.PK})


def scene():
    """Simulate every planned attempt and all persisted effects, with no SQL."""
    plan=deepcopy(load_plan());ledger=Ledger(plan);before,after=empty(),empty();rows=after['rows']
    now='2026-11-14T00:00:00+00:00';later='2026-11-14T01:00:00+00:00'
    for challenge in plan['hackathons']:
        row=dict(challenge,min_team_size=2,max_team_size=3)
        before['rows']['hackathons'][row['id']]=deepcopy(row);rows['hackathons'][row['id']]=deepcopy(row)
        before['hashes']['hackathons'][row['id']]='stable'
    before['hashes']['users']['prior-user']='preserved'
    for account in plan['accounts']:
        role=account['role'];ledger.begin();ledger.claim('/auth/register',{'username':account['username']})
        u=uuid4();ledger.bind_account(CredentialIdentity(u,account['username']));ledger.finish(201)
        ledger.begin();ledger.claim('/auth/login',{'username':account['username']});ledger.finish(200)
        rows['users'][str(u)]=dict(id=str(u));rows['account_credentials'][str(u)]=dict(user_id=str(u),username=account['username'])
    for role in ('l','q','r','x'):
        ledger.begin();ledger.claim('/api/me/profile',plan['profile_values'][role],role);ledger.finish(200)
        u=str(ledger.ids[role]);rows['participant_profiles'][u]=dict(plan['profile_values'][role],version=2 if role=='l' else 1,user_id=u)
    for tag,status in (('profile_invalid',422),('profile_edit',200),('profile_stale',409)):
        body=dict(plan['profile_values']['l'],version=1)
        if tag=='profile_invalid':body['timezone']='Mars/Base'
        ledger.begin();assert ledger.claim('/api/me/profile',body,'l')==tag;ledger.finish(status,error_code=DENIALS.get(tag))
    for tag,status in (('missing_session',401),('missing_csrf',403),('foreign_origin',403)):
        ledger.begin();ledger.claim('/api/me/profile',dict(plan['profile_values']['l'],version=2),'l',probe=tag);ledger.finish(status,error_code=DENIALS[tag])
    versions={};counts={};teams={};denied={'deny_decision':ErrorCode.FORBIDDEN,'deny_remove':ErrorCode.FORBIDDEN,'deny_redeem':ErrorCode.INVITATION_NOT_FOUND}
    for tag in ORDER:
        role=next(c['actor'] for c in plan['commands'] if c['tag']==tag)
        path,body,method,v=command_spec(plan,tag,ledger.ids,ledger.bindings,tag)
        ledger.begin();assert ledger.claim(path,body,role,tag)==tag
        if tag in denied:
            def reject(**kw):raise DomainError(denied[tag])
            with pytest.raises(DomainError):ledger.invoke(SimpleNamespace(**{method:reject}),method,v)
            ledger.finish(404 if tag=='deny_redeem' else 403,error_code=DENIALS[tag]);continue
        if ledger.calls[tag]['reply']:
            ledger.invoke(SimpleNamespace(**{method:lambda **kw:ledger.calls[tag]['reply']}),method,v);ledger.finish(201);continue
        create=tag.startswith('create_');team=str(uuid4()) if create else str(ledger.bindings['a'])
        previous_version=versions.get(team,0);previous_count=counts.get(team,0)
        delta=1 if create or tag in ('approve_q','redeem_r','redeem_q') else -1 if tag in ('remove_r','leave_q','leave_l','final_q') else 0
        version=previous_version+1;count=previous_count+delta;versions[team]=version;counts[team]=count
        h_id=str(v['hackathon_id']);old_leader=teams.get(team,{}).get('leader_user_id')
        leader=str(ledger.ids['q']) if tag in ('create_b','leave_l') else None if tag=='final_q' else str(ledger.ids['l'])
        row=dict(id=team,hackathon_id=h_id,name=plan['teams']['b' if tag=='create_b' else 'a'],
            created_by=str(ledger.ids['q' if tag=='create_b' else 'l']),leader_user_id=leader,deleted_at=later if count==0 else None,
            min_team_size=2,max_team_size=3,version=version)
        teams[team]=row;rows['teams'][team]=deepcopy(row)
        subject=str(v['actor_id']) if create or tag in ('leave_q','leave_l','final_q') else str(ledger.ids['q' if tag in ('request_q','approve_q','issue_q','redeem_q') else 'r'])
        if delta==1:rows['memberships'][h_id+'|'+subject]=dict(hackathon_id=h_id,team_id=team,user_id=subject)
        if delta==-1:del rows['memberships'][h_id+'|'+subject]
        extra=None;previous_extra=None
        if create:data=dict(hackathon_id=h_id,team_id=team,user_id=subject,member_count=1,team_version=1)
        elif method in ('create_request','decide_request'):
            target=str(uuid4()) if method=='create_request' else str(v['request_id'])
            status='pending' if method=='create_request' else 'rejected' if tag=='reject_r' else 'approved'
            data=dict(id=target,hackathon_id=h_id,team_id=team,requester_id=subject,status=status,created_at=now,resolved_at=None if status=='pending' else later)
            rows['join_requests'][target]=deepcopy(data);extra=('request',dict(id=target,status=status))
            previous_extra=None if method=='create_request' else dict(id=target,status='pending')
        elif method in ('issue','redeem'):
            target=str(uuid4()) if method=='issue' else str(v['invitation_id']);status='pending' if method=='issue' else 'redeemed'
            data=dict(id=target,hackathon_id=h_id,team_id=team,recipient_id=subject,issued_by=str(ledger.ids['l']),status=status,
                created_at=now,expires_at='2026-11-15T00:00:00+00:00',redeemed_at=None if method=='issue' else later)
            rows['invitations'][target]=deepcopy(data);extra=('invitation',dict(id=target,status=status))
            previous_extra=None if method=='issue' else dict(id=target,status='pending')
        else:data=dict(hackathon_id=h_id,team_id=team,user_id=subject,member_count=count,team_version=version,leader_user_id=leader,deleted=count==0)
        status=next(c['status'] for c in plan['commands'] if c['tag']==tag)
        reply=_StoredReply._from_values(status,dict(schema_version=1,data=data),{'content-type':'application/json','cache-control':'no-store'})
        ledger.invoke(SimpleNamespace(**{method:lambda **kw:reply}),method,v);ledger.finish(status)
        record,audit,event=[str(uuid4()) for _ in range(3)];fp=ledger.calls[tag]['fp']
        rows['idempotency_records'][record]=dict(id=record,actor_id=str(fp.actor_id),hackathon_id=h_id,operation=fp.operation,key=fp.key,
            request_hash=fp.fingerprint.digest.hex(),state='completed',completed_at=later,http_status=status,response_body=reply.body(),response_headers=dict(reply.headers))
        def state(n,c,lead,member):return dict(schema_version=1,team=dict(version=n,member_count=c,leader_user_id=lead,
            min_team_size=2,max_team_size=3,deleted=c==0,readiness='deleted' if c==0 else 'ready' if c>=2 else 'forming'),subject=dict(user_id=subject,member=member))
        old=None if create else state(previous_version,previous_count,old_leader,delta==-1)
        new=state(version,count,leader,delta==1)
        if extra:old[extra[0]]=previous_extra;new[extra[0]]=extra[1]
        rows['audit_events'][audit]=dict(id=audit,idempotency_record_id=record,actor_id=str(fp.actor_id),hackathon_id=h_id,team_id=team,
            action=fp.operation,team_version=version,old_state=old,new_state=new)
        rows['outbox_events'][event]=dict(id=event,audit_event_id=audit,event_type='team.changed.v1',schema_version=1,
            payload=dict(hackathon_id=h_id,team_id=team,team_version=version),published_at=None,attempt_count=0)
    ledger.begin();ledger.claim('/auth/logout',{},'x');ledger.finish(204)
    ledger.begin();ledger.claim('/auth/login',{'username':plan['accounts'][0]['username']});ledger.finish(200)
    for role in ('l','l','q','r','x'):
        rows['auth_sessions'][str(uuid4())]=dict(user_id=str(ledger.ids[role]),created_at=now,expires_at='2026-11-14T08:00:00+00:00',revoked_at=later if role=='x' else None)
    throttle=SimpleNamespace(_key=lambda op,identifier:sha256((op+'|'+identifier).encode()).digest())
    charge=run.charges(throttle,ledger)
    for bucket in charge:
        pk=bucket['scope']+'|'+bucket['key']+'|window'
        rows['auth_throttle_buckets'][pk]=dict(scope=bucket['scope'],key=bucket['key'],attempts=bucket['count'])
    for table in o.PK:
        after['hashes'][table]=dict(before['hashes'][table],**{k:'stable' for k in rows[table]})
    return plan,before,after,ledger,charge


def test_complete_synthetic_campaign_and_independent_observer():
    plan,before,after,ledger,charge=scene();ledger.complete()
    result=o.verify_final(before,after,plan,ledger.observer_input(),charge)
    assert result['total_posts']==38 and result['audit']==14 and result['memberships']==1


@pytest.mark.parametrize('fault',['prior','unrelated','profile','profile-version','membership','leader','delete','version',
    'team-scope','creator','request','invite','invite-expiry','session','revocation','audit-link','audit-actor','audit-state',
    'audit-chain','audit-subject','audit-request','outbox','idempotency','fingerprint','pending','extra-receipt','throttle','missing-throttle','ledger-status','partial','denial'])
def test_independent_observer_rejects_corrupt_committed_state(fault):
    plan,before,after,ledger,charge=scene();r=after['rows'];export=ledger.observer_input()
    first=lambda table:next(iter(r[table].values()))
    if fault=='prior':after['hashes']['users']['prior-user']='changed'
    elif fault=='unrelated':after['hashes']['users']['outside']='new'
    elif fault=='profile':first('participant_profiles')['skills']=['unapproved']
    elif fault=='profile-version':first('participant_profiles')['version']=9
    elif fault=='membership':r['memberships'].clear()
    elif fault=='leader':r['teams'][str(ledger.bindings['b'])]['leader_user_id']=str(ledger.ids['l'])
    elif fault=='delete':r['teams'][str(ledger.bindings['a'])]['deleted_at']=None
    elif fault=='version':first('teams')['version']=7
    elif fault=='team-scope':first('teams')['hackathon_id']=str(uuid4())
    elif fault=='creator':first('teams')['created_by']=str(uuid4())
    elif fault=='request':first('join_requests')['status']='pending'
    elif fault=='invite':first('invitations')['status']='pending'
    elif fault=='invite-expiry':first('invitations')['expires_at']='2026-11-13T00:00:00+00:00'
    elif fault=='session':r['auth_sessions'].pop(next(iter(r['auth_sessions'])))
    elif fault=='revocation':first('auth_sessions')['revoked_at']='2026-11-14T01:00:00+00:00'
    elif fault=='audit-link':first('audit_events')['idempotency_record_id']=str(uuid4())
    elif fault=='audit-actor':first('audit_events')['actor_id']=str(uuid4())
    elif fault=='audit-state':first('audit_events')['new_state']['team']['member_count']=3
    elif fault=='audit-chain':list(r['audit_events'].values())[2]['old_state']['team']['leader_user_id']=str(uuid4())
    elif fault=='audit-subject':first('audit_events')['new_state']['subject']['user_id']=str(uuid4())
    elif fault=='audit-request':next(v for v in r['audit_events'].values() if 'request' in v['new_state'])['new_state']['request']['status']='approved'
    elif fault=='outbox':first('outbox_events')['payload']['team_version']=99
    elif fault=='idempotency':first('idempotency_records')['response_body']={}
    elif fault=='fingerprint':first('idempotency_records')['request_hash']='0'*64
    elif fault=='pending':first('idempotency_records')['state']='pending'
    elif fault=='extra-receipt':r['idempotency_records'][str(uuid4())]=deepcopy(first('idempotency_records'))
    elif fault=='throttle':first('auth_throttle_buckets')['attempts']+=1
    elif fault=='missing-throttle':r['auth_throttle_buckets'].clear()
    elif fault=='ledger-status':export['statuses']['deny_redeem']=[200]
    elif fault=='denial':export['denials']['foreign_origin']='invalid_csrf'
    else:export['total']=37
    with pytest.raises((ValueError,KeyError,StopIteration)):o.verify_final(before,after,plan,export,charge)


@pytest.mark.parametrize('target',['benchmark','merge_dev','merge_test','merge_prod'])
def test_integrated_target_rejected_before_engine(target):
    with pytest.raises(ValueError):
        with h.profile_engine(targets.Target(target,True,'synthetic')):pytest.fail('Engine reached')


def test_static_readiness_no_live_io():
    result=run.static_readiness()
    assert result['status']=='CONDITIONAL' and result['routes']==25 and result['service_overrides']==9
    assert result['live_operations_performed'] is False


@pytest.mark.parametrize('argv',[
    ['serve'],['serve','--confirm-profile-test','--revision','0005_invitations'],
    ['serve','--confirm-profile-test','--revision','head'],['readiness','--allow-browser-writes'],
    ['prepare','--confirm-profile-test','--revision','0006_profiles','--allow-browser-writes']])
def test_cli_cannot_prompt_or_connect_without_exact_separate_opt_ins(argv):
    with pytest.raises(SystemExit):run.arguments(argv)


@pytest.mark.parametrize('fault',['overrun','overlap','unbound','changed-key','changed-body','changed-workspace','unknown-outcome','late-failure'])
def test_ledger_failure_latches_and_does_not_retry(fault):
    plan,before,after,completed,charge=scene();ledger=Ledger(plan);ledger.ids=completed.ids.copy()
    if fault=='overrun':ledger.total=38
    if fault=='overlap':ledger.active={}
    if fault in ('overrun','overlap'):
        with pytest.raises(auth.AuthFailure):ledger.begin()
    elif fault=='unbound':
        with pytest.raises(auth.AuthFailure):ledger.actor(uuid4())
    else:
        ledger.statuses['profile_stale']=[409]
        # First creation in H2, then the one allowed A replay sequence.
        for tag in ('create_b','create_a'):
            path,body,method,v=command_spec(plan,tag,ledger.ids,ledger.bindings,tag)
            ledger.begin();ledger.claim(path,body,'q' if tag=='create_b' else 'l',tag)
            if tag=='create_a' and fault=='unknown-outcome':
                def uncertain(**kw):raise DomainError(ErrorCode.OUTCOME_UNCERTAIN)
                with pytest.raises(DomainError):ledger.invoke(SimpleNamespace(**{method:uncertain}),method,v)
                break
            ledger.invoke(SimpleNamespace(**{method:lambda **kw:completed.calls[tag]['reply']}),method,v)
            if tag=='create_a' and fault=='late-failure':
                with pytest.raises(ValueError):ledger.finish(201,False)
                break
            ledger.finish(201)
        if fault not in ('unknown-outcome','late-failure'):
            path,body,method,v=command_spec(plan,'create_a',ledger.ids,ledger.bindings,'create_a')
            if fault=='changed-key':v['key']='different'
            if fault=='changed-body':body={'name':'different'}
            if fault=='changed-workspace':path=path.replace(plan['hackathons'][0]['id'],plan['hackathons'][1]['id'])
            ledger.begin()
            with pytest.raises(auth.AuthFailure):ledger.claim(path,body,'l',v['key'])
    assert ledger.failed
    with pytest.raises(auth.AuthFailure):ledger.begin()


@pytest.fixture
def api(monkeypatch):
    plan,before,after,reference,charge=scene()
    engine=MagicMock(spec=Engine);engine.hide_parameters=True;engine.echo=False
    names=('CredentialService','SessionService','TeamService','AdmissionService','InvitationService','LifecycleService',
           'TeamReadService','ProfileService','MatchingService','RealtimeService','ThrottleService')
    real={n:MagicMock() for n in names}
    for name,value in real.items():monkeypatch.setattr(h,name,lambda *a,_v=value,**kw:_v)
    host,app,ledger,throttle=h.browser_app(engine,SimpleNamespace(failed=__import__('threading').Event()),plan,h.local_policy(),allow_writes=True)
    now=datetime.now(timezone.utc);principals={r:SessionPrincipal(u,next(a['username'] for a in plan['accounts'] if a['role']==r),now+timedelta(hours=8)) for r,u in reference.ids.items()}
    tokens={r:(r.encode()*32) for r in principals};csrf=b'c'*32
    def principal(token):return principals[next(r for r,v in tokens.items() if v==token)]
    sessions=real['SessionService'];sessions.validate.side_effect=principal
    sessions.validate_with_csrf.side_effect=lambda t:ValidatedSession(principal(t),SecretBytes(csrf))
    sessions.verify_csrf.side_effect=lambda t,c:principal(t) if c==csrf else (_ for _ in ()).throw(ValueError('bad csrf'))
    def login(**v):
        role=next(r for r,p in principals.items() if p.username==v['username']);return IssuedSession(principals[role],now,SecretBytes(tokens[role]),SecretBytes(csrf))
    sessions.login.side_effect=login
    real['CredentialService'].register.side_effect=lambda **v:CredentialIdentity(next(p.user_id for p in principals.values() if p.username==v['username']),v['username'])
    def domain(method,**v):
        tag=ledger.active['tag']
        if tag.startswith('deny_'):
            from app.services.admission import AdmissionError
            from app.services.invitations import InvitationError
            from app.services.lifecycle import LifecycleError
            error=InvitationError if tag=='deny_redeem' else LifecycleError if tag=='deny_remove' else AdmissionError
            raise error(ErrorCode.INVITATION_NOT_FOUND if tag=='deny_redeem' else ErrorCode.FORBIDDEN)
        return reference.calls[tag]['reply']
    for name,methods in [('TeamService',['create_team_idempotent']),('AdmissionService',['create_request','decide_request']),
        ('InvitationService',['issue','redeem']),('LifecycleService',['leave','remove'])]:
        for method in methods:getattr(real[name],method).side_effect=lambda _m=method,**v:domain(_m,**v)
    def save(u,body):
        from app.services.profiles import ProfileError
        if ledger.active['tag']=='profile_stale':raise ProfileError('profile_changed')
        return dict(user_id=u,username=principals[ledger.actor(u)].username,display_name='Synthetic',**body.model_dump(exclude={'version'}),version=body.version+1)
    real['ProfileService'].update.side_effect=save
    def post(client,path,body,role=None,extra=None,key=None):
        client.cookies.clear();headers={'Origin':h.ORIGIN,'X-Merge-Request':'1'}
        if role:headers.update(Cookie='merge_session_dev='+auth.encode_token(tokens[role]),**{'X-CSRF-Token':auth.encode_token(csrf)})
        if key:headers['Idempotency-Key']=key
        if extra:
            for k,v in extra.items():
                if v is None:headers.pop(k,None)
                else:headers[k]=v
        return client.post(path,json=body,headers=headers)
    with TestClient(host,base_url=h.ORIGIN,client=('127.0.0.1',40000),raise_server_exceptions=False) as client:
        yield SimpleNamespace(client=client,app=app,ledger=ledger,plan=plan,real=real,reference=reference,
            post=lambda path,body,role=None,extra=None,key=None:post(client,path,body,role,extra,key),engine=engine)
    engine.connect.assert_not_called()


def test_full_38_http_attempts_use_real_boundary_csrf_dtos_and_service_adapters(api):
    a=api;p=a.plan
    for account in p['accounts']:
        body=dict(username=account['username'],password='synthetic long test password')
        assert a.post('/auth/register',body).status_code==201
        assert a.post('/auth/login',body).status_code==200
    for role in ('l','q','r','x'):assert a.post('/api/me/profile',p['profile_values'][role],role).status_code==200
    for tag,status in (('profile_invalid',422),('profile_edit',200),('profile_stale',409)):
        body=dict(p['profile_values']['l'],version=1)
        if tag=='profile_invalid':body['timezone']='Mars/Base'
        result=a.post('/api/me/profile',body,'l');assert result.status_code==status,result.text
    for probe,status in (('missing_session',401),('missing_csrf',403),('foreign_origin',403)):
        extra={'X-Merge-Acceptance-Probe':probe}
        if probe=='missing_csrf':extra['X-CSRF-Token']=None
        if probe=='foreign_origin':extra['Origin']='https://foreign.invalid'
        result=a.post('/api/me/profile',dict(p['profile_values']['l'],version=2),None if probe=='missing_session' else 'l',extra)
        assert result.status_code==status,result.text
    for tag in ORDER:
        role=next(c['actor'] for c in p['commands'] if c['tag']==tag)
        path,body,method,values=command_spec(p,tag,a.ledger.ids,a.ledger.bindings,tag)
        result=a.post(path,body,role,key=tag)
        assert result.status_code==next(c['status'] for c in p['commands'] if c['tag']==tag),result.text
    assert a.post('/auth/logout',{},'x').status_code==204
    assert a.post('/auth/login',dict(username=p['accounts'][0]['username'],password='synthetic long test password')).status_code==200
    a.ledger.complete();assert a.ledger.total==38
    assert a.real['ThrottleService'].check_invitation.call_count==5
    assert a.real['ProfileService'].update.call_count==6 # invalid IANA fails before service
    assert a.real['TeamService'].create_team_idempotent.call_count==3
    assert a.real['LifecycleService'].leave.call_count==3


@pytest.mark.parametrize('dependency',list(h.SERVICES))
def test_every_missing_override_closes_host_before_fallback(api,dependency):
    saved=api.app.dependency_overrides.pop(dependency)
    assert api.client.get('/health').status_code==503
    api.app.dependency_overrides[dependency]=saved
    assert api.client.get('/health').status_code==503
    api.real['SessionService'].validate.assert_not_called()


@pytest.mark.parametrize('fault',['origin','actor','username','unknown','duplicate','content','metadata','proxy','budget'])
def test_unapproved_posts_cannot_reach_durable_throttle(api,fault):
    body=dict(username=api.plan['accounts'][0]['username'],password='synthetic long test password');extra={};path='/auth/register'
    if fault=='origin':extra['Origin']='https://foreign.invalid'
    elif fault=='actor':extra['X-Actor-ID']=str(uuid4())
    elif fault=='username':body['username']='outside_scope'
    elif fault=='unknown':path='/api/unknown'
    elif fault=='duplicate':
        assert api.post(path,body).status_code==201
        api.real['ThrottleService'].check.reset_mock()
    elif fault=='content':extra['Content-Type']='text/plain'
    elif fault=='metadata':extra['Sec-Fetch-Site']='cross-site'
    elif fault=='proxy':extra['X-Forwarded-For']='127.0.0.1'
    else:api.ledger.total=38
    assert api.post(path,body,extra=extra).status_code>=400
    assert api.ledger.failed
    api.real['ThrottleService'].check.assert_not_called()
    assert api.client.get('/health').status_code==503


def test_sse_endpoint_uses_scoped_realtime_and_sessions_without_starting_a_server(api,monkeypatch):
    from app import realtime_api
    # Only truncate the lease generator; exercise the real endpoint, slot claim,
    # service override, identity guard and StreamingResponse resource release.
    async def finite(request,hackathon,actor,raw,services,service,initial):
        services.sessions.validate(raw)
        yield realtime_api.frame('reset',hackathon,actor,initial)
    monkeypatch.setattr(realtime_api,'changes',finite)
    api.ledger.ids=api.reference.ids.copy();api.real['RealtimeService'].revision.return_value='a'*64
    token=auth.encode_token(b'q'*32)
    result=api.client.get(f"/api/hackathons/{api.plan['hackathons'][0]['id']}/events",headers={'Cookie':'merge_session_dev='+token})
    assert result.status_code==200 and 'event: reset' in result.text
    assert str(api.reference.ids['q']) in result.text and str(api.reference.ids['l']) not in result.text
    api.real['SessionService'].validate.assert_called()
    assert not api.app.state.realtime_subscribers.accounts


def test_origin_probe_requires_valid_current_csrf_even_when_origin_is_foreign(api):
    api.ledger.ids=api.reference.ids.copy()
    result=api.post('/api/me/profile',dict(api.plan['profile_values']['l'],version=2),'l',
        {'X-Merge-Acceptance-Probe':'foreign_origin','Origin':'https://foreign.invalid','X-CSRF-Token':None})
    assert result.status_code==503 and api.ledger.failed
    api.real['ProfileService'].update.assert_not_called()


def test_status_403_from_wrong_boundary_does_not_certify_origin_restriction(api,monkeypatch):
    original=auth.AuthBoundary.__call__
    async def masked(self,scope,receive,send):
        if scope.get('path')=='/api/me/profile':
            return await auth.error_response(403,'invalid_csrf','Synthetic unrelated denial.')(scope,receive,send)
        return await original(self,scope,receive,send)
    monkeypatch.setattr(auth.AuthBoundary,'__call__',masked);api.ledger.ids=api.reference.ids.copy()
    result=api.post('/api/me/profile',dict(api.plan['profile_values']['l'],version=2),'l',
        {'X-Merge-Acceptance-Probe':'foreign_origin','Origin':'https://foreign.invalid'})
    assert result.status_code==403 and api.ledger.failed and 'foreign_origin' not in api.ledger.denials


@pytest.mark.parametrize('fault',['extra-route','changed-endpoint','missing-dependency','extra-dependency'])
def test_closed_route_and_dependency_graph_audit_rejects_drift(api,fault):
    from fastapi.routing import iter_route_contexts
    health=next(r.endpoint for r in iter_route_contexts(api.app.routes) if r.path=='/health')
    overrides=dict(api.app.dependency_overrides)
    route=next(r for r in iter_route_contexts(api.app.routes) if r.path=='/api/me/profile' and r.methods=={'POST'})
    saved_routes=list(api.app.routes);saved_endpoint=route.original_route.endpoint;saved_dependencies=list(route.dependant.dependencies)
    try:
        if fault=='extra-route':
            @api.app.get('/unexpected')
            def extra():return {}
        elif fault=='changed-endpoint':route.original_route.endpoint=lambda:None
        elif fault=='missing-dependency':route.dependant.dependencies.clear()
        else:route.dependant.dependencies.append(SimpleNamespace(call=lambda:None,dependencies=[]))
        with pytest.raises(ValueError):h.audit_wiring(api.app,overrides,health)
    finally:
        # FastAPI retains shared original router objects; restore before the
        # lifespan's shutdown audit AND before another test constructs an app.
        api.app.routes[:]=saved_routes;route.original_route.endpoint=saved_endpoint
        route.dependant.dependencies[:]=saved_dependencies


@pytest.mark.parametrize('exit_code,body',[(1,{'status':'passed'}),(0,{'status':'failed'}),(0,None)])
def test_observer_failure_preserves_actual_exit_and_never_certifies(monkeypatch,tmp_path,exit_code,body):
    plan,before,after,ledger,charge=scene();folder=tmp_path/'reports';folder.mkdir();monkeypatch.setattr(run,'DIRECTORY',folder)
    monkeypatch.setattr(run.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=exit_code,stdout=b'invalid' if body is None else json.dumps(body).encode()))
    throttle=SimpleNamespace(_key=lambda op,v:sha256((op+v).encode()).digest())
    with pytest.raises(ValueError):run.observer_process(before,plan,ledger,throttle,'synthetic-not-real')
    report=json.loads(next(folder.glob('observer-*.json')).read_text())
    assert report['native_exit_code']==exit_code
    assert 'synthetic-not-real' not in json.dumps(report)


@pytest.mark.parametrize('fault',['drain','shutdown','guard','ledger','interrupted'])
def test_failed_host_shutdown_cannot_run_observer_or_pass(monkeypatch,fault):
    from contextlib import contextmanager
    from threading import Event
    import test_support.browser as browser
    plan,before,after,ledger,charge=scene();guard=SimpleNamespace(failed=Event());engine=MagicMock()
    @contextmanager
    def context(*a,**kw):yield engine,guard
    @contextmanager
    def socket(*a,**kw):yield object()
    monkeypatch.setattr(h,'profile_engine',context);monkeypatch.setattr(browser,'reserved_socket',socket)
    monkeypatch.setattr(o,'snapshot',lambda *a:before)
    monkeypatch.setattr(h,'browser_app',lambda *a,**kw:(object(),SimpleNamespace(state=SimpleNamespace(integrated_shutdown_complete=fault!='shutdown')),ledger,object()))
    class Server:
        started=True
        def __init__(self,*a):pass
        def run(self,**kw):
            if fault=='guard':guard.failed.set()
            if fault=='ledger':ledger.failed=True
            if fault=='interrupted':raise RuntimeError('Synthetic interruption')
        def drained(self):return fault not in ('drain','interrupted')
    monkeypatch.setattr(run,'IntegratedServer',Server)
    monkeypatch.setattr(run,'observer_process',lambda *a:pytest.fail('Observer reached after failed drain/guard'))
    with pytest.raises(run.CampaignFailure) as error:run.serve_worker(targets.Target('profiles',True,'synthetic'),plan,'synthetic')
    diagnostic=error.value.diagnostics
    assert diagnostic['stage'] in ('browser','drain') and diagnostic['ledger']['attempted_posts']==38
    assert 'synthetic' not in json.dumps(diagnostic) and 'calls' not in diagnostic['ledger']


@pytest.mark.parametrize('native',[0,1,None])
def test_supervisor_records_native_exit_not_report_success(monkeypatch,tmp_path,native):
    import test_support.browser as browser
    folder=tmp_path/'reports';folder.mkdir();monkeypatch.setattr(run,'DIRECTORY',folder)
    current=dict(head='a'*40,files={'synthetic':'b'*64})
    monkeypatch.setattr(run,'sources',lambda:current)
    monkeypatch.setattr(run,'approved_profile',lambda *a:None)
    monkeypatch.setattr(browser,'hidden_password',lambda:'synthetic-only')
    class Process:
        def __init__(self,argv,**kw):
            if native is None:raise RuntimeError('Synthetic launch failure')
            plan=load_plan()
            run.write_new(__import__('pathlib').Path(argv[-1]),dict(schema_version=1,kind='integrated-host-step',action='serve',
                run_id=plan['run_id'],plan_sha256=run.digest(plan),target=plan['target'],status='passed',source=current,source_unchanged=True))
        def wait(self,*a,**kw):return native
    monkeypatch.setattr(run.subprocess,'Popen',Process)
    result=run.main(['serve','--confirm-profile-test','--revision','0006_profiles','--profile-receipt','synthetic.json','--allow-browser-writes'])
    reports=[json.loads(path.read_text()) for path in folder.glob('process-*.json')]
    assert any(r['status']=='incomplete' and r['native_exit_code'] is None for r in reports)
    report=next(r for r in reports if r['status']!='incomplete')
    assert report['native_exit_code']==native and (result==0)==(native==0)
    assert report['status']==('passed' if native==0 else 'failed')


def test_get_and_auth_counters_do_not_spend_mutation_budget(api):
    assert api.client.get('/health').status_code == 200
    assert api.client.get('/auth/session').status_code == 401
    counts = api.app.state.integrated_diagnostics.snapshot()['requests']
    assert counts == dict(http_requests=2, get_requests=2, authentication_requests=1,
                         session_validation_attempts=0, session_validation_successes=0)
    assert api.ledger.total == 0 and not api.ledger.failed
    for service in api.real.values():
        service.register.assert_not_called()
        service.login.assert_not_called()


def test_successful_authenticated_get_counts_only_aggregate_validations(api):
    account = api.plan['accounts'][0]
    assert api.post('/auth/register',dict(username=account['username'],password='synthetic long test password')).status_code == 201
    token = auth.encode_token(b'l'*32)
    result = api.client.get('/auth/session', headers={'Cookie':'merge_session_dev='+token})
    assert result.status_code == 200
    counts = api.app.state.integrated_diagnostics.snapshot()['requests']
    assert counts == dict(http_requests=2, get_requests=1, authentication_requests=2,
                         session_validation_attempts=1, session_validation_successes=1)
    assert api.ledger.total == 1
    assert token not in json.dumps(api.app.state.integrated_diagnostics.snapshot())


def test_ready_drained_host_with_zero_posts_fails_at_ledger_not_startup(monkeypatch):
    from contextlib import contextmanager
    from threading import Event
    import test_support.browser as browser
    plan,before,*_ = scene(); ledger = Ledger(plan)
    guard=SimpleNamespace(failed=Event()); engine=MagicMock()
    @contextmanager
    def context(*args, **kwargs): yield engine,guard
    @contextmanager
    def socket(*args, **kwargs): yield object()
    monkeypatch.setattr(h,'profile_engine',context)
    monkeypatch.setattr(browser,'reserved_socket',socket)
    monkeypatch.setattr(o,'snapshot',lambda *args:before)
    monkeypatch.setattr(h,'browser_app',lambda *args,**kwargs:(object(),
        SimpleNamespace(state=SimpleNamespace(integrated_shutdown_complete=True)),ledger,object()))
    class Server:
        started=True
        def __init__(self,config,diagnostics): self.diagnostics=diagnostics
        def run(self,**kwargs):
            for name in ('startup_reached','readiness_achieved','shutdown_requested','shutdown_completed'):
                setattr(self.diagnostics,name,True)
        def drained(self): return True
    monkeypatch.setattr(run,'IntegratedServer',Server)
    monkeypatch.setattr(run,'observer_process',lambda *args:pytest.fail('Incomplete ledger reached observer'))
    with pytest.raises(run.CampaignFailure) as failure:
        run.serve_worker(targets.Target('profiles',True,'synthetic'),plan,'synthetic')
    diagnostic=failure.value.diagnostics
    assert diagnostic['stage']=='ledger_complete'
    assert diagnostic['lifecycle']['readiness_achieved']
    assert diagnostic['lifecycle']['shutdown_completed']
    assert diagnostic['lifecycle']['failed_predicates']==['ledger_complete']
    assert diagnostic['ledger']['attempted_posts']==0
