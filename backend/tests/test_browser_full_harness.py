"""Offline only. Every real connection, listener, prompt and ordinary Settings is forbidden."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4, UUID
import json

from fastapi.testclient import TestClient
from pydantic import SecretBytes, ValidationError
from sqlalchemy.engine import Engine
import pytest

from app import auth
from app.services.credentials import CredentialIdentity
from app.services.sessions import SessionPrincipal, ValidatedSession, IssuedSession
from app.services.idempotency import _StoredReply
from app.services.errors import DomainError, ErrorCode
from test_support import browser_full as b
from test_support.browser_full_scope import FullScope, Ledger, COMMANDS, ROLES, SUCCESS, read_scope
from test_support.browser_full_state import FullSnapshot, PK, preflight, certify, preserved
from test_support.database import DiagnosticFailure, TestDatabaseSettings
from test_browser_harness import Connection


@pytest.fixture(autouse=True)
def forbid_live(monkeypatch):
    def forbidden(*a,**kw): raise AssertionError('Live operation forbidden')
    monkeypatch.setattr(b,'create_engine',forbidden)
    monkeypatch.setattr(b,'hidden_password',forbidden)
    monkeypatch.setattr(b,'reserved_socket',forbidden)
    monkeypatch.setattr(b.BrowserServer,'run',forbidden)
    import app.core.config, app.db.session
    monkeypatch.setattr(app.core.config,'Settings',forbidden)
    monkeypatch.setattr(app.db.session,'build_engine',forbidden)


@pytest.fixture
def document():
    run=uuid4(); prefix='m015b_'+run.hex[:8]+'_'
    return dict(run_id=str(run),accounts=[dict(role=r,username=prefix+r,register_attempts=1,login_attempts=4,logout_attempts=4) for r in ROLES],
        hackathons=[dict(id=str(uuid4()),name=prefix+'challenge_'+n) for n in ('a','b')],team_a=prefix+'team_a',team_b=prefix+'team_b',
        commands=[dict(command=n,attempts=3) for n in COMMANDS])


@pytest.fixture
def scope(document): return FullScope.model_validate_json(json.dumps(document))


@pytest.mark.parametrize('change',[
    ('identity',('merge_dev','merge_app','127.0.0.1',5432)),('identity',('merge_test','postgres','127.0.0.1',5432)),
    ('identity',('merge_test','merge_app','192.0.2.1',5432)),('identity',('merge_test','merge_app','127.0.0.1',5433)),
    ('revisions',['0003_auth']),('revisions',['0004_admission']),('revisions',[]),('revisions',['0005_invitations','other']),
    ('active',True),('isolation','SERIALIZABLE'),('options',{'isolation_level':'AUTOCOMMIT'}),
    ('settings',('read committed','read committed','on','0','15s')),
    ('settings',('read committed','repeatable read','on','5s','15s'))])
def test_checkout_guard_refuses_and_latches(change):
    c=Connection(); c.in_nested_transaction=lambda:False; c.revisions=[b.REVISION]
    setattr(c,*change); guard=b.ConnectionGuard()
    with pytest.raises(DiagnosticFailure): guard(c)
    assert c.invalid and guard.failed.is_set()
    with pytest.raises(DiagnosticFailure): guard(Connection())


@pytest.mark.parametrize('autocommit',[True,None,'false'])
def test_real_driver_autocommit_required(autocommit):
    c=Connection(); c.in_nested_transaction=lambda:False; c.revisions=[b.REVISION]
    c.connection.dbapi_connection.autocommit=autocommit
    with pytest.raises(DiagnosticFailure): b.ConnectionGuard()(c)


def test_guard_repeats_on_pooled_checkout():
    c=Connection(); c.in_nested_transaction=lambda:False; c.revisions=[b.REVISION]
    g=b.ConnectionGuard(); g(c); g(c)
    assert sum('version_num' in q for q in c.queries)==2 and not g.failed.is_set()


@pytest.mark.parametrize('values',[{'database':'merge_dev'},{'user':'postgres'},{'host':'localhost'},{'confirmed':False},{'password':''}])
def test_bad_settings_refused_before_engine(values):
    data=dict(confirmed=True,password='synthetic'); data.update(values)
    with pytest.raises((ValueError,DiagnosticFailure)):
        with b.guarded_engine(TestDatabaseSettings(**data)): pytest.fail('No engine allowed')


@pytest.mark.parametrize('case',['extra','duplicate-role','username','zero-accounts','duplicate-hackathons','command','bool-budget','negative','too-large','password'])
def test_manifest_is_explicit_bounded_and_secret_free(document,case):
    if case=='extra': document['unknown']=1
    elif case=='duplicate-role': document['accounts'][1]=document['accounts'][0]
    elif case=='username': document['accounts'][0]['username']='unapproved'
    elif case=='zero-accounts': document['accounts']=[]
    elif case=='duplicate-hackathons': document['hackathons'][1]=document['hackathons'][0]
    elif case=='command': document['commands'][0]['command']='join_anywhere'
    elif case=='bool-budget': document['accounts'][0]['login_attempts']=True
    elif case=='negative': document['commands'][0]['attempts']=-1
    elif case=='too-large': document['commands'][0]['attempts']=4
    else: document['accounts'][0]['password']='synthetic-never-allowed'
    with pytest.raises(ValidationError): FullScope.model_validate_json(json.dumps(document))


def test_duplicate_json_and_oversized_manifest_refused(tmp_path):
    path=tmp_path/'scope.json'; path.write_text('{"run_id":1,"run_id":2}')
    with pytest.raises(DiagnosticFailure): read_scope(path)
    path.write_text(' '*16385)
    with pytest.raises(DiagnosticFailure): read_scope(path)


@pytest.fixture
def api(monkeypatch,scope):
    engine=MagicMock(spec=Engine); engine.hide_parameters=True; engine.echo=False
    real={n:MagicMock() for n in ('CredentialService','SessionService','TeamReadService','TeamService','AdmissionService','InvitationService','ThrottleService')}
    for name,value in real.items(): monkeypatch.setattr(b,name,lambda *a,_v=value,**kw:_v)
    host,app,ledger,throttle=b.browser_app(engine,b.ConnectionGuard(),scope,b.local_policy(),allow_writes=True)
    ids={r:uuid4() for r in ROLES}; ledger.ids.update(ids)
    principal=SessionPrincipal(ids['l'],ledger.accounts['l'].username,datetime.now(timezone.utc)+timedelta(hours=8))
    sessions=real['SessionService']; sessions.validate.return_value=sessions.verify_csrf.return_value=principal
    sessions.validate_with_csrf.return_value=ValidatedSession(principal,SecretBytes(b'c'*32))
    sessions.login.return_value=IssuedSession(principal,datetime.now(timezone.utc),SecretBytes(b't'*32),SecretBytes(b'c'*32))
    real['TeamReadService'].hackathons.return_value={'items':[],'next_cursor':None}
    headers={'Origin':b.ORIGIN,'X-CSRF-Token':auth.encode_token(b'c'*32),'Idempotency-Key':'exact-key'}
    with TestClient(host,base_url=b.ORIGIN,client=(b.HOST,40000)) as client:
        client.cookies.set('merge_session_dev',auth.encode_token(b't'*32))
        yield SimpleNamespace(client=client,app=app,ledger=ledger,real=real,scope=scope,ids=ids,headers=headers)
    assert app.state.auth_engine is None


@pytest.mark.parametrize('dependency',list(b.SERVICES))
def test_every_missing_override_closes_host_before_settings(api,dependency):
    saved=api.app.dependency_overrides.pop(dependency)
    try:
        assert api.client.get('/health').status_code==503
        api.real['SessionService'].validate_with_csrf.assert_not_called()
    finally:
        api.app.dependency_overrides[dependency]=saved
    # Fixing the override cannot clear the failure latch.
    assert api.client.get('/health').status_code==503


@pytest.mark.parametrize('headers,code',[
    ({'Origin':'http://evil.example'},'origin_rejected'),
    ({'Origin':b.ORIGIN,'Sec-Fetch-Site':'cross-site'},'origin_rejected'),
    ({'Origin':b.ORIGIN,'X-Forwarded-For':'127.0.0.1'},'client_identity_rejected'),
    ({'Origin':b.ORIGIN},'request_header_required')])
def test_real_browser_policy_precedes_throttle(api,headers,code):
    r=api.client.post('/auth/login',headers=headers,json={'username':api.ledger.accounts['l'].username,'password':'synthetic test password'})
    assert r.status_code==403 and r.json()['error']['code']==code
    api.real['ThrottleService'].check.assert_not_called()


def test_current_account_csrf_and_exact_create_command(api):
    h=api.scope.hackathons[0].id; t=uuid4()
    api.real['TeamService'].create_team_idempotent.return_value=_StoredReply._from_values(201,{'schema_version':1,'data':{
        'team_id':str(t),'hackathon_id':str(h),'user_id':str(api.ids['l']),'member_count':1,'team_version':1}}, {'content-type':'application/json','cache-control':'no-store'})
    url=f'/api/hackathons/{h}/teams'
    assert api.client.post(url,headers={'Origin':b.ORIGIN,'Idempotency-Key':'key'},json={'name':api.scope.team_a}).status_code==403
    api.real['TeamService'].create_team_idempotent.assert_not_called()
    r=api.client.post(url,headers=api.headers,json={'name':api.scope.team_a})
    assert r.status_code==201 and api.ledger.bindings['a']==t
    api.real['SessionService'].verify_csrf.assert_called_with(b't'*32,b'c'*32)
    assert api.client.post(url,headers={**api.headers,'Idempotency-Key':'changed'},json={'name':api.scope.team_a}).status_code==403
    assert api.real['TeamService'].create_team_idempotent.call_count==1


def test_registration_binds_server_uuid_only_with_budget(api):
    del api.ledger.ids['l']
    account=api.ledger.accounts['l']; api.real['CredentialService'].register.return_value=CredentialIdentity(api.ids['l'],account.username)
    headers={'Origin':b.ORIGIN,'X-Merge-Request':'1'}
    body={'username':account.username,'password':'synthetic test password'}
    assert api.client.post('/auth/register',headers=headers,json=body).status_code==201
    assert api.ledger.ids['l']==api.ids['l']
    assert api.client.post('/auth/register',headers=headers,json=body).status_code==403
    assert api.real['CredentialService'].register.call_count==1


def test_out_of_scope_invitation_rejected_before_durable_throttle(api):
    api.ledger.bindings['a']=uuid4()
    path=f'/api/hackathons/{api.scope.hackathons[1].id}/teams/{api.ledger.bindings["a"]}/invitations'
    assert api.client.post(path,headers=api.headers,json={'recipient_id':str(api.ids['r'])}).status_code==403
    api.real['ThrottleService'].check_invitation.assert_not_called()


@pytest.mark.parametrize('action,flag',[('prepare','--allow-fixture-writes'),('serve','--allow-browser-writes')])
def test_separate_opt_in_required_before_live_action(action,flag):
    argv=[action,'--confirm-merge-test','--revision',b.REVISION,'--manifest','unused.json']
    with pytest.raises(SystemExit): b.arguments(argv)
    assert b.arguments(argv+[flag]).action==action
    with pytest.raises(SystemExit): b.arguments(argv+['--allow-fixture-writes','--allow-browser-writes'])


def empty(): return FullSnapshot({t:{} for t in PK},{t:{} for t in PK})


def test_preflight_never_adopts_existing_accounts_or_domain_rows(scope):
    s=empty(); preflight(s,scope,prepared=False)
    s.rows['account_credentials']['existing']={}
    with pytest.raises(DiagnosticFailure): preflight(s,scope,prepared=False)
    s=empty(); s.rows['teams']['existing']={}
    with pytest.raises(DiagnosticFailure): preflight(s,scope,prepared=False)


def test_missing_journey_and_unrelated_changes_cannot_certify(scope):
    ledger=Ledger(scope)
    with pytest.raises(DiagnosticFailure): certify(empty(),empty(),ledger,MagicMock())
    before=empty(); after=empty(); before.hashes['users']['other']='unchanged'
    with pytest.raises(DiagnosticFailure): preserved(before,after)
    after.hashes['users']['other']='changed'
    with pytest.raises(DiagnosticFailure): preserved(before,after)


@pytest.mark.parametrize('drained,certifies',[(False,True),(True,False)])
def test_incomplete_shutdown_and_invariant_failure_cannot_succeed(monkeypatch,scope,drained,certifies):
    @contextmanager
    def guarded(settings):
        from threading import Event
        yield MagicMock(),SimpleNamespace(failed=Event())
    monkeypatch.setattr(b,'guarded_engine',guarded)
    monkeypatch.setattr(b,'snapshot',lambda *a:empty()); monkeypatch.setattr(b,'preflight',lambda *a,**kw:None)
    app=SimpleNamespace(state=SimpleNamespace(browser_shutdown_complete=True))
    ledger=SimpleNamespace(failed=False)
    monkeypatch.setattr(b,'browser_app',lambda *a,**kw:(object(),app,ledger,object()))
    server=SimpleNamespace(started=True,drained=lambda:drained,run=lambda **kw:None)
    monkeypatch.setattr(b,'BrowserServer',lambda config:server)
    def certify(*args):
        if not certifies: raise DiagnosticFailure('verification')
    monkeypatch.setattr(b,'certify',certify)
    with pytest.raises(DiagnosticFailure): b.serve(object(),scope,object())


def test_production_packaging_and_legacy_harness_unchanged():
    root=Path(__file__).resolve().parents[1]
    assert 'include = ["app*"]' in (root/'pyproject.toml').read_text()
    import test_support.browser as legacy
    assert legacy.REVISION=='0003_auth'
    assert not any('invitations' in path or 'join-requests' in path or method=='POST' and path.startswith('/api/') for path,method in legacy.ENDPOINTS)


def scene(scope):
    """Synthetic committed journey for certifier fault tests, never DB evidence."""
    from hashlib import sha256
    ledger=Ledger(scope); ledger.ids={r:uuid4() for r in ROLES}
    before=empty(); after=empty(); rows=after.rows
    now='2026-11-11T00:00:00+00:00'; later='2026-11-11T01:00:00+00:00'
    h=scope.hackathons[0].id
    for challenge in scope.hackathons:
        row=dict(id=str(challenge.id),name=challenge.name,min_team_size=2,max_team_size=3)
        before.rows['hackathons'][row['id']]=deepcopy(row); rows['hackathons'][row['id']]=row
        before.hashes['hackathons'][row['id']]='stable'
    for role,u in ledger.ids.items():
        rows['users'][str(u)]={'id':str(u)}
        rows['account_credentials'][str(u)]={'user_id':str(u),'username':ledger.accounts[role].username}
        ledger.used[(role,'register')]=1
    versions={}; counts={}
    def run(tag,method,values,data,subject,extra=None,previous_extra=None,admitted=False):
        fp_tag=ledger.reserve(method,values); assert fp_tag==tag
        reply=_StoredReply._from_values(201 if tag.startswith(('create_','request_','issue_')) else 200,
            {'schema_version':1,'data':data},{'content-type':'application/json','cache-control':'no-store'})
        real=SimpleNamespace(**{method:lambda **kw:reply})
        ledger.invoke(real,method,values,reserved=tag)
        t=data['team_id']; creating=tag.startswith('create_')
        versions[t]=versions.get(t,0)+1; counts[t]=counts.get(t,0)+int(creating or admitted)
        leader=str(ledger.ids['x' if tag=='create_b' else 'l'])
        rows['teams'][t]=dict(id=t,hackathon_id=str(h),name=scope.team_b if tag=='create_b' else scope.team_a,
            leader_user_id=leader,created_by=leader,version=versions[t],min_team_size=2,max_team_size=3,deleted_at=None)
        def state(version,count,member):
            result=dict(schema_version=1,team=dict(version=version,member_count=count,leader_user_id=leader,
                min_team_size=2,max_team_size=3,readiness='ready' if count>=2 else 'forming'),subject=dict(user_id=subject,member=member))
            return result
        old=None if creating else state(versions[t]-1,counts[t]-int(admitted),False)
        new=state(versions[t],counts[t],creating or admitted)
        if extra:
            new[extra[0]]=extra[1]; old[extra[0]]=previous_extra
        if creating or admitted: rows['memberships'][str(h)+'|'+subject]=dict(hackathon_id=str(h),team_id=t,user_id=subject)
        record,audit,event=[str(uuid4()) for _ in range(3)]; fp=ledger.calls[tag].fingerprint
        rows['idempotency_records'][record]=dict(id=record,actor_id=str(values['actor_id']),hackathon_id=str(h),operation=fp.operation,
            key=values['key'],request_hash=fp.fingerprint.digest.hex(),state='completed',completed_at=later,
            http_status=reply.http_status,response_body=reply.body(),response_headers=dict(reply.headers))
        rows['audit_events'][audit]=dict(id=audit,idempotency_record_id=record,actor_id=str(values['actor_id']),hackathon_id=str(h),
            team_id=t,action=fp.operation,team_version=versions[t],old_state=old,new_state=new)
        rows['outbox_events'][event]=dict(id=event,audit_event_id=audit,event_type='team.changed.v1',schema_version=1,
            payload=dict(hackathon_id=str(h),team_id=t,team_version=versions[t]),published_at=None,attempt_count=0)
    for suffix in ('a',):
        t=uuid4(); v=dict(hackathon_id=h,actor_id=ledger.ids['l'],name=scope.team_a,key='create_a')
        run('create_a','create_team_idempotent',v,dict(team_id=str(t),hackathon_id=str(h),user_id=str(ledger.ids['l']),member_count=1,team_version=1),str(ledger.ids['l']))
    a=ledger.bindings['a']
    for role in ('q','r'):
        target=uuid4(); data=dict(id=str(target),hackathon_id=str(h),team_id=str(a),requester_id=str(ledger.ids[role]),status='pending',created_at=now,resolved_at=None)
        rows['join_requests'][str(target)]=deepcopy(data)
        run('request_'+role,'create_request',dict(hackathon_id=h,team_id=a,actor_id=ledger.ids[role],key='request_'+role),data,str(ledger.ids[role]),('request',dict(id=str(target),status='pending')))
    for role,decision in (('q','approve'),('r','reject')):
        target=ledger.bindings['request_'+role]; data=rows['join_requests'][str(target)]
        data['status']='approved' if role=='q' else 'rejected'; data['resolved_at']=later
        run(decision+'_'+role,'decide_request',dict(hackathon_id=h,team_id=a,actor_id=ledger.ids['l'],request_id=target,decision=decision,key=decision+'_'+role),
            deepcopy(data),str(ledger.ids[role]),('request',dict(id=str(target),status=data['status'])),dict(id=str(target),status='pending'),role=='q')
    for role in ('r','x'):
        target=uuid4(); data=dict(id=str(target),hackathon_id=str(h),team_id=str(a),recipient_id=str(ledger.ids[role]),issued_by=str(ledger.ids['l']),
            status='pending',created_at=now,expires_at='2026-11-12T00:00:00+00:00',redeemed_at=None)
        rows['invitations'][str(target)]=deepcopy(data)
        run('issue_'+role,'issue',dict(hackathon_id=h,team_id=a,actor_id=ledger.ids['l'],recipient_id=ledger.ids[role],key='issue_'+role),data,
            str(ledger.ids[role]),('invitation',dict(id=str(target),status='pending')))
    target=ledger.bindings['issue_r']; data=rows['invitations'][str(target)]; data.update(status='redeemed',redeemed_at=later)
    run('redeem_r','redeem',dict(hackathon_id=h,team_id=a,actor_id=ledger.ids['r'],invitation_id=target,key='redeem_r'),deepcopy(data),
        str(ledger.ids['r']),('invitation',dict(id=str(target),status='redeemed')),dict(id=str(target),status='pending'),True)
    ledger.reserve('redeem',dict(hackathon_id=h,team_id=a,actor_id=ledger.ids['x'],invitation_id=ledger.bindings['issue_x'],key='redeem_x'))
    ledger.calls['redeem_x'].error=ErrorCode.TEAM_FULL
    t=uuid4(); v=dict(hackathon_id=h,actor_id=ledger.ids['x'],name=scope.team_b,key='create_b')
    run('create_b','create_team_idempotent',v,dict(team_id=str(t),hackathon_id=str(h),user_id=str(ledger.ids['x']),member_count=1,team_version=1),str(ledger.ids['x']))
    throttle=SimpleNamespace(_key=lambda op,value:sha256((op+value).encode()).digest())
    for op,value,count in [('register_ip','127.0.0.1',4),('invitation_issue',str(ledger.ids['l']),2),('invitation_redeem',str(ledger.ids['r']),1),('invitation_redeem',str(ledger.ids['x']),1)]:
        key=throttle._key(op,value).hex(); pk=op+'|'+key+'|window'
        rows['auth_throttle_buckets'][pk]=dict(scope='auth:v1:'+op,key=key,attempts=count)
        if op.startswith('invitation_'):
            ledger.used[(ledger.actor(UUID(value)),op)]=count
    for table in PK:
        after.hashes[table]={key:'stable' for key in rows[table]}
    return before,after,ledger,throttle


def test_exact_synthetic_journey_certifies(scope):
    certify(*scene(scope))


@pytest.mark.parametrize('fault',['capacity','duplicate-membership','consumed-loser','version','audit-link','audit-actor','audit-state','audit-chain','outbox','idempotency-body','hash','unrelated','throttle','missing-throttle','credential'])
def test_certifier_detects_committed_faults(scope,fault):
    before,after,ledger,throttle=scene(scope); rows=after.rows
    if fault=='capacity': next(iter(rows['teams'].values()))['max_team_size']=2
    elif fault=='duplicate-membership': rows['memberships']['duplicate']=next(iter(rows['memberships'].values()))
    elif fault=='consumed-loser': rows['invitations'][str(ledger.bindings['issue_x'])]['status']='redeemed'
    elif fault=='version': rows['teams'][str(ledger.bindings['a'])]['version']=9
    elif fault=='audit-link': next(iter(rows['audit_events'].values()))['idempotency_record_id']='wrong'
    elif fault=='audit-actor': next(iter(rows['audit_events'].values()))['actor_id']='wrong'
    elif fault=='audit-state': next(iter(rows['audit_events'].values()))['new_state']['team']['member_count']=3
    elif fault=='audit-chain':
        audit=next(x for x in rows['audit_events'].values() if x['team_version']==6)
        audit['old_state']['team']['member_count']=audit['new_state']['team']['member_count']=1
    elif fault=='outbox': next(iter(rows['outbox_events'].values()))['published_at']='unexpected'
    elif fault=='idempotency-body': next(iter(rows['idempotency_records'].values()))['response_body']={'bad':'reply'}
    elif fault=='hash': next(iter(rows['idempotency_records'].values()))['request_hash']='wrong'
    elif fault=='unrelated': after.hashes['users']['unscoped']='new'
    elif fault=='throttle': next(iter(rows['auth_throttle_buckets'].values()))['attempts']=99
    elif fault=='missing-throttle': rows['auth_throttle_buckets'].clear(); after.hashes['auth_throttle_buckets'].clear()
    else: next(iter(rows['account_credentials'].values()))['username']='other'
    with pytest.raises(DiagnosticFailure): certify(before,after,ledger,throttle)


@pytest.mark.parametrize('tamper',[False,True])
def test_prepare_is_exact_two_inserts_in_one_transaction_and_rolls_back_on_drift(monkeypatch,scope,tamper):
    before=empty(); before.hashes['users']['retained']='stable'
    current=deepcopy(before.hashes); phases=[]
    class C:
        @contextmanager
        def begin(self):
            phases.append('begin')
            try: yield
            except BaseException:
                phases.append('rollback'); raise
            else: phases.append('commit')
        def execute(self,statement,params=None):
            sql=str(statement)
            if sql.startswith('INSERT'):
                assert sql=='INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:h,:name,2,3)'
                phases.append('insert'); current['hackathons'][str(params['h'])]='new'
                if tamper: current['users']['retained']='drift'
                return None
            table=next(t for t in PK if 'FROM public.'+t+' t' in sql)
            return SimpleNamespace(all=lambda:list(current[table].items()))
    @contextmanager
    def connect(): yield C()
    monkeypatch.setattr(b,'snapshot',lambda *a:before)
    if tamper:
        with pytest.raises(DiagnosticFailure): b.prepare(SimpleNamespace(connect=connect),scope)
        assert phases==['begin','insert','insert','rollback']
    else:
        b.prepare(SimpleNamespace(connect=connect),scope)
        assert phases==['begin','insert','insert','commit']


def test_prepare_refuses_existing_scope_before_transaction(monkeypatch,scope):
    s=empty(); s.rows['hackathons'][str(scope.hackathons[0].id)]={}
    c=MagicMock(); c.__enter__.return_value=c
    monkeypatch.setattr(b,'snapshot',lambda *a:s)
    with pytest.raises(DiagnosticFailure): b.prepare(SimpleNamespace(connect=lambda:c),scope)
    c.begin.assert_not_called(); c.execute.assert_not_called()


@pytest.mark.parametrize('tamper',[False,True])
def test_prepare_requires_post_commit_global_preservation(monkeypatch,scope,tamper,capsys):
    before=empty(); before.hashes['users']['retained']='stable'
    after=deepcopy(before)
    for h in scope.hackathons:
        after.rows['hackathons'][str(h.id)]=dict(name=h.name,min_team_size=2,max_team_size=3)
        after.hashes['hackathons'][str(h.id)]='new'
    if tamper: after.hashes['users']['retained']='changed'
    @contextmanager
    def guarded(settings): yield MagicMock(),object()
    monkeypatch.setattr(b,'guarded_engine',guarded); monkeypatch.setattr(b,'read_scope',lambda p:scope)
    monkeypatch.setattr(b,'hidden_password',lambda:'synthetic'); monkeypatch.setattr(b,'prepare',lambda *a:before)
    monkeypatch.setattr(b,'snapshot',lambda *a:after)
    args=['prepare','--confirm-merge-test','--revision',b.REVISION,'--manifest','unused.json','--allow-fixture-writes']
    assert b.main(args)==int(tamper)
    assert ('fixtures prepared; retained' in capsys.readouterr().out)==(not tamper)


def test_snapshot_selects_only_fingerprints_and_no_raw_auth_secrets(scope):
    from test_support.browser_full_state import snapshot
    queries=[]
    class C:
        def execute(self,q,params=None):
            queries.append(str(q))
            return SimpleNamespace(all=lambda:[],mappings=lambda:SimpleNamespace(all=lambda:[]))
        def rollback(self): queries.append('ROLLBACK')
    snapshot(C(),scope)
    assert queries[0]=='SET TRANSACTION READ ONLY' and queries[-1]=='ROLLBACK'
    assert all(q.startswith(('SELECT','SET TRANSACTION READ ONLY','ROLLBACK')) for q in queries)
    credential=next(q for q in queries if 'WHERE username=ANY' in q)
    assert 'password_hash' not in credential
    sessions=next(q for q in queries if "to_jsonb(s)-'token_hash'" in q)
    assert "-'csrf_token'" in sessions


def test_guard_attached_before_first_checkout_and_on_reuse_then_disposed(monkeypatch):
    order=[]; guard_callback=[]
    c=Connection(); c.in_nested_transaction=lambda:False; c.revisions=[b.REVISION]
    @contextmanager
    def connect():
        order.append('connect'); guard_callback[0](c); yield c
    engine=SimpleNamespace(connect=connect,dispose=lambda:order.append('dispose'))
    def create(url,**kw):
        assert url.database=='merge_test' and url.host=='127.0.0.1' and url.username=='merge_app'
        assert kw['hide_parameters'] is True and kw['isolation_level']=='READ COMMITTED'
        assert kw['connect_args']['options']=='-c statement_timeout=15000 -c lock_timeout=5000'
        order.append('engine'); return engine
    def listen(e,name,callback):
        assert e is engine and name=='engine_connect'; order.append('listen'); guard_callback.append(callback)
    monkeypatch.setattr(b,'create_engine',create); monkeypatch.setattr(b.event,'listen',listen)
    with b.guarded_engine(TestDatabaseSettings(confirmed=True,password='synthetic')) as (e,g):
        with e.connect(): pass
        with e.connect(): pass
    assert order==['engine','listen','connect','connect','connect','dispose']
    assert sum('version_num' in q for q in c.queries)==3


def test_uncertain_result_recovers_same_command_and_unclassified_failure_latches(scope):
    ledger=Ledger(scope); ledger.ids['l']=uuid4()
    values=dict(hackathon_id=scope.hackathons[0].id,actor_id=ledger.ids['l'],name=scope.team_a,key='original')
    real=SimpleNamespace(create_team_idempotent=MagicMock(side_effect=DomainError(ErrorCode.OUTCOME_UNCERTAIN)))
    with pytest.raises(DomainError): ledger.invoke(real,'create_team_idempotent',values)
    assert not ledger.failed
    with pytest.raises(auth.AuthFailure): ledger.invoke(real,'create_team_idempotent',{**values,'key':'changed'})
    real.create_team_idempotent.side_effect=DomainError(ErrorCode.INTEGRITY_FAULT)
    with pytest.raises(DomainError): ledger.invoke(real,'create_team_idempotent',values)
    assert ledger.failed


def test_registration_unknown_to_ledger_cannot_login_or_be_adopted(scope):
    ledger=Ledger(scope)
    with pytest.raises(auth.AuthFailure): ledger.auth_charge(ledger.accounts['l'].username,'login')


@pytest.mark.parametrize('tag',['redeem_x','create_b'])
def test_outsider_cannot_redeem_early_or_create_before_full_conflict(scope,tag):
    ledger=Ledger(scope); ledger.ids={r:uuid4() for r in ROLES}; ledger.bindings.update(a=uuid4(),issue_x=uuid4())
    values=dict(hackathon_id=scope.hackathons[0].id,actor_id=ledger.ids['x'],key='original')
    if tag=='redeem_x': values.update(team_id=ledger.bindings['a'],invitation_id=ledger.bindings['issue_x']); method='redeem'
    else: values['name']=scope.team_b; method='create_team_idempotent'
    real=MagicMock()
    with pytest.raises(auth.AuthFailure): ledger.invoke(real,method,values)
    assert not real.mock_calls


def test_full_http_journey_binds_real_returned_ids_and_each_actor_session(api):
    from app.services.invitations import InvitationError
    api.ledger.ids.clear(); api.client.cookies.clear()  # Start guest; do not duplicate the fixture's synthetic cookie.
    h=api.scope.hackathons[0].id; a,bteam=uuid4(),uuid4()
    request_ids={r:uuid4() for r in ('q','r')}; grants={r:uuid4() for r in ('r','x')}
    now='2026-11-11T00:00:00+00:00'; later='2026-11-11T01:00:00+00:00'
    roles={a.username:a.role for a in api.scope.accounts}
    def principal(role): return SessionPrincipal(api.ids[role],api.ledger.accounts[role].username,datetime.now(timezone.utc)+timedelta(hours=8))
    sessions=api.real['SessionService']
    sessions.login.side_effect=lambda **v:IssuedSession(principal(roles[v['username']]),datetime.now(timezone.utc),SecretBytes(roles[v['username']].encode()*32),SecretBytes(b'c'*32))
    sessions.validate_with_csrf.side_effect=lambda token:ValidatedSession(principal(token[:1].decode()),SecretBytes(b'c'*32))
    sessions.verify_csrf.side_effect=lambda token,csrf:principal(token[:1].decode())
    api.real['CredentialService'].register.side_effect=lambda **v:CredentialIdentity(api.ids[roles[v['username']]],v['username'])
    def reply(data,status=200): return _StoredReply._from_values(status,{'schema_version':1,'data':data},{'content-type':'application/json','cache-control':'no-store'})
    api.real['TeamService'].create_team_idempotent.side_effect=lambda **v:reply(dict(hackathon_id=str(h),team_id=str(a if v['actor_id']==api.ids['l'] else bteam),user_id=str(v['actor_id']),member_count=1,team_version=1),201)
    def request(role,status='pending'):
        return dict(id=str(request_ids[role]),hackathon_id=str(h),team_id=str(a),requester_id=str(api.ids[role]),status=status,created_at=now,resolved_at=None if status=='pending' else later)
    api.real['AdmissionService'].create_request.side_effect=lambda **v:reply(request(api.ledger.actor(v['actor_id'])),201)
    api.real['AdmissionService'].decide_request.side_effect=lambda **v:reply(request('q' if v['decision']=='approve' else 'r','approved' if v['decision']=='approve' else 'rejected'))
    def grant(role,redeemed=False):
        return dict(id=str(grants[role]),hackathon_id=str(h),team_id=str(a),recipient_id=str(api.ids[role]),issued_by=str(api.ids['l']),status='redeemed' if redeemed else 'pending',created_at=now,expires_at='2026-11-12T00:00:00+00:00',redeemed_at=later if redeemed else None)
    api.real['InvitationService'].issue.side_effect=lambda **v:reply(grant(api.ledger.actor(v['recipient_id'])),201)
    def redeem(**v):
        if v['actor_id']==api.ids['x']: raise InvitationError(ErrorCode.TEAM_FULL)
        return reply(grant('r',True))
    api.real['InvitationService'].redeem.side_effect=redeem
    auth_headers={'Origin':b.ORIGIN,'X-Merge-Request':'1'}
    for account in api.scope.accounts:
        assert api.client.post('/auth/register',headers=auth_headers,json={'username':account.username,'password':'synthetic test password'}).status_code==201
    def sign_in(role):
        assert api.client.post('/auth/login',headers=auth_headers,json={'username':api.ledger.accounts[role].username,'password':'synthetic test password'}).status_code==200
    base=f'/api/hackathons/{h}/teams'; key=0
    def post(path,body,status):
        nonlocal key
        key+=1
        r=api.client.post(path,headers={**api.headers,'Idempotency-Key':'key_'+str(key)},json=body)
        assert r.status_code==status,r.text
    sign_in('l'); post(base,{'name':api.scope.team_a},201)
    for role in ('q','r'):
        sign_in(role); post(base+f'/{a}/join-requests',{},201)
    sign_in('l')
    for role,decision in (('q','approve'),('r','reject')):
        post(base+f'/{a}/join-requests/{request_ids[role]}/decision',{'decision':decision},200)
    for role in ('r','x'): post(base+f'/{a}/invitations',{'recipient_id':str(api.ids[role])},201)
    sign_in('r'); post(base+f'/{a}/invitations/{grants["r"]}/redeem',{},200)
    sign_in('x'); post(base+f'/{a}/invitations/{grants["x"]}/redeem',{},409)
    post(base,{'name':api.scope.team_b},201)
    assert api.ledger.bindings==dict(a=a,b=bteam,request_q=request_ids['q'],request_r=request_ids['r'],issue_r=grants['r'],issue_x=grants['x'])
    assert all(api.ledger.calls[n].reply is not None for n in SUCCESS)
    assert api.real['ThrottleService'].check_invitation.call_count==4
    assert api.ledger.calls['redeem_x'].error==ErrorCode.TEAM_FULL


@pytest.mark.parametrize('failure',['observe','certify','dispose','listener','system-exit','none'])
def test_main_never_prints_final_success_on_failed_shutdown_checks(monkeypatch,scope,failure,capsys):
    args=['serve','--confirm-merge-test','--revision',b.REVISION,'--manifest','unused.json','--allow-browser-writes']
    monkeypatch.setattr(b,'read_scope',lambda p:scope); monkeypatch.setattr(b,'hidden_password',lambda:'synthetic')
    @contextmanager
    def socket():
        yield object()
        if failure=='listener': raise RuntimeError('synthetic-private-connection-string')
    monkeypatch.setattr(b,'reserved_socket',socket)
    phases=[]; opened=0
    from threading import Event
    @contextmanager
    def guarded(settings):
        nonlocal opened
        opened+=1; index=opened
        yield MagicMock(),SimpleNamespace(failed=Event())
        phases.append('dispose_'+str(index))
        if failure=='dispose' and index==1: raise RuntimeError('synthetic-private-connection-string')
    monkeypatch.setattr(b,'guarded_engine',guarded)
    def snapshot(*a):
        phases.append('snapshot_'+str(opened))
        if failure=='observe' and opened==2: raise RuntimeError('synthetic-private-connection-string')
        return empty()
    monkeypatch.setattr(b,'snapshot',snapshot); monkeypatch.setattr(b,'preflight',lambda *a,**kw:None)
    app=SimpleNamespace(state=SimpleNamespace(browser_shutdown_complete=True))
    monkeypatch.setattr(b,'browser_app',lambda *a,**kw:(object(),app,SimpleNamespace(failed=False),object()))
    def run(**kw):
        if failure=='system-exit': raise SystemExit(0)
    monkeypatch.setattr(b,'BrowserServer',lambda config:SimpleNamespace(started=True,drained=lambda:True,run=run))
    def certify(*a):
        phases.append('certify')
        if failure=='certify': raise RuntimeError('synthetic-private-connection-string')
    monkeypatch.setattr(b,'certify',certify)
    assert b.main(args)==(0 if failure=='none' else 1)
    output=capsys.readouterr().out
    assert ('final journey invariants verified' in output)==(failure=='none')
    assert 'synthetic-private' not in output
    if failure=='none': assert phases==['snapshot_1','snapshot_2','dispose_2','certify','dispose_1']
