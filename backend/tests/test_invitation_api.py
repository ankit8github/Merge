"""Real HTTP/auth boundaries over test services, without PostgreSQL."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from app.auth import encode_token
from app.invitation_api import get_invitation_service
from app.services.invitations import InvitationService, InvitationError
from app.services.idempotency import _StoredReply
from app.services.errors import ErrorCode
from test_auth_http import api, ORIGIN, assert_private


@pytest.fixture
def invitation(api):
    h,t,i,recipient=uuid4(),uuid4(),uuid4(),uuid4(); now=datetime.now(timezone.utc)
    row=dict(id=str(i),hackathon_id=str(h),team_id=str(t),recipient_id=str(recipient),
        issued_by=str(api.issued.principal.user_id),status='pending',created_at=now.isoformat(),
        expires_at=(now+timedelta(hours=24)).isoformat(),redeemed_at=None)
    service=MagicMock(spec=InvitationService)
    service.issue.return_value=_StoredReply._from_values(201,dict(schema_version=1,data=row),{'content-type':'application/json','cache-control':'no-store'})
    service.redeem.return_value=_StoredReply._from_values(200,dict(schema_version=1,data=row),{'content-type':'application/json','cache-control':'no-store'})
    service.mine.return_value=dict(items=[dict(row,available=True)],next_cursor=str(i))
    api.app.dependency_overrides[get_invitation_service]=lambda:service
    api.client.cookies.set('__Host-merge_session',encode_token(api.issued.session_token.get_secret_value()))
    return SimpleNamespace(api=api,service=service,h=h,t=t,i=i,recipient=recipient,
        base=f'/api/hackathons/{h}/teams/{t}/invitations',
        headers={'Origin':ORIGIN,'X-CSRF-Token':encode_token(api.issued.csrf_token.get_secret_value()),'Idempotency-Key':'same-key'})


def call(d,kind,headers=None,body=None):
    if kind=='mine': return d.api.client.get(f'/api/hackathons/{d.h}/invitations/mine',headers=headers)
    return d.api.client.post(d.base+('/'+str(d.i)+'/redeem' if kind=='redeem' else ''),
        headers=d.headers if headers is None else headers,
        json=({'recipient_id':str(d.recipient)} if kind=='issue' else {}) if body is None else body)


@pytest.mark.parametrize('kind',['issue','redeem','mine'])
def test_cookie_is_required_even_with_service_override(invitation,kind):
    d=invitation; d.api.client.cookies.clear()
    response=call(d,kind)
    assert response.status_code==401 and not d.service.mock_calls
    assert_private(response)


@pytest.mark.parametrize('kind',['issue','redeem'])
@pytest.mark.parametrize('bad',['csrf','origin','metadata','key','actor','body','media'])
def test_browser_csrf_json_identity_and_key_protections(invitation,kind,bad):
    d=invitation; headers=dict(d.headers); body=None
    if bad=='csrf': headers.pop('X-CSRF-Token')
    if bad=='origin': headers['Origin']='https://other.example'
    if bad=='metadata': headers['Sec-Fetch-Site']='cross-site'
    if bad=='key': headers.pop('Idempotency-Key')
    if bad=='actor': headers['X-Actor-ID']=str(uuid4())
    if bad=='body': body={'actor_id':'private'}
    if bad=='media':
        response=d.api.client.post(d.base,content='{}',headers={**headers,'Content-Type':'text/plain'})
    else: response=call(d,kind,headers,body)
    assert response.status_code in (403,415,422) and not d.service.mock_calls
    assert 'private' not in response.text
    assert_private(response)


def test_exact_session_actor_subject_and_throttle_scopes(invitation):
    d=invitation; actor=d.api.issued.principal.user_id
    assert call(d,'issue').status_code==201
    d.service.issue.assert_called_once_with(hackathon_id=d.h,team_id=d.t,actor_id=actor,recipient_id=d.recipient,key='same-key')
    assert call(d,'redeem').status_code==200
    d.service.redeem.assert_called_once_with(hackathon_id=d.h,team_id=d.t,actor_id=actor,invitation_id=d.i,key='same-key')
    assert d.api.services.throttle.check_invitation.call_args_list==[
        (( ),dict(actor_id=actor,operation='issue')),(( ),dict(actor_id=actor,operation='redeem'))]
    inbox=call(d,'mine')
    assert inbox.status_code==200
    assert inbox.json()['next_cursor']==str(d.i)
    assert d.api.app.state.auth_engine is None


@pytest.mark.parametrize('suffix',['?recipient_id=private','?limit=101','?limit=1&limit=2','?cursor=bad'])
def test_inbox_has_no_recipient_selector_or_unbounded_page(invitation,suffix):
    d=invitation
    response=d.api.client.get(f'/api/hackathons/{d.h}/invitations/mine'+suffix)
    assert response.status_code==422 and not d.service.mock_calls


@pytest.mark.parametrize(('code','status'),[(ErrorCode.INVITATION_NOT_FOUND,404),
    (ErrorCode.INVITATION_EXPIRED,409),(ErrorCode.INVITATION_STALE,409),(ErrorCode.INVITATION_REDEEMED,409),
    (ErrorCode.TEAM_FULL,409),(ErrorCode.FORBIDDEN,403),(ErrorCode.OUTCOME_UNCERTAIN,503)])
def test_fixed_errors_and_same_key_uncertainty(invitation,code,status):
    d=invitation; d.service.redeem.side_effect=InvitationError(code)
    response=call(d,'redeem')
    assert response.status_code==status and response.json()['error']['code']==code.value
    assert_private(response)


def test_throttle_failure_precedes_domain_work(invitation):
    from app.services.throttling import ThrottleExceeded
    d=invitation; d.api.services.throttle.check_invitation.side_effect=ThrottleExceeded(30)
    response=call(d,'redeem')
    assert response.status_code==429 and response.headers['Retry-After']=='30' and not d.service.mock_calls


def test_fifty_http_arrivals_use_independent_cookie_csrf_and_test_host_capacity(api):
    """Framework/control-flow evidence with synthetic sessions, not a DB race."""
    from datetime import datetime,timedelta,timezone
    from threading import Thread
    from pydantic import SecretBytes
    from app.services.sessions import SessionPrincipal,ValidatedSession
    from test_support.invitation_race import ArrivalGate
    from test_support.races import workers,Outcome
    actors=[uuid4() for _ in range(50)]; gate=ArrivalGate(actors)
    tokens=[n.to_bytes(32,'big') for n in range(1,51)]
    csrf=[n.to_bytes(32,'big') for n in range(101,151)]
    def validate(raw):
        n=tokens.index(raw)
        return ValidatedSession(SessionPrincipal(actors[n],'synthetic_user',datetime.now(timezone.utc)+timedelta(hours=1)),SecretBytes(csrf[n]))
    def verify(raw,supplied): assert supplied==csrf[tokens.index(raw)]
    api.services.sessions.validate_with_csrf.side_effect=validate
    api.services.sessions.verify_csrf.side_effect=verify
    service=MagicMock(spec=InvitationService)
    def redeem(**kwargs):
        gate.enter(kwargs['actor_id'])
        raise InvitationError(ErrorCode.TEAM_FULL)
    service.redeem.side_effect=redeem
    api.app.dependency_overrides[get_invitation_service]=lambda:service
    async def configure():
        import anyio.to_thread
        limiter=anyio.to_thread.current_default_thread_limiter()
        old=limiter.total_tokens; limiter.total_tokens=64
        return limiter,old
    limiter,old=api.client.portal.call(configure)
    released=[]
    def release():
        released.append(gate.arrived.wait(10)); gate.release.set()
    observer=Thread(target=release,daemon=True); observer.start()
    try:
        h,t=uuid4(),uuid4()
        def action(n):
            response=api.client.post(f'/api/hackathons/{h}/teams/{t}/invitations/{uuid4()}/redeem',json={},headers={
                'Origin':ORIGIN,'Cookie':'__Host-merge_session='+encode_token(tokens[n]),
                'X-CSRF-Token':encode_token(csrf[n]),'Idempotency-Key':'synthetic-'+str(n)})
            return Outcome(str(response.status_code),response.json().get('error',{}).get('code',''))
        outcomes=workers([lambda n=n:action(n) for n in range(50)])
    finally:
        gate.release.set(); observer.join(2)
        async def restore(): limiter.total_tokens=old
        api.client.portal.call(restore)
    assert released==[True] and not observer.is_alive()
    gate.verify()
    assert all(o==Outcome('409','team_full') for o in outcomes)
    assert api.services.sessions.verify_csrf.call_count==50
    assert {call.kwargs['actor_id'] for call in service.redeem.call_args_list}==set(actors)
