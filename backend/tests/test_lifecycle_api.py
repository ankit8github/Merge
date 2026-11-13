"""Real HTTP policy and adapters over synthetic services; never opens a database."""
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from app.auth import encode_token
from app.lifecycle_api import get_lifecycle_service
from app.services.lifecycle import LifecycleService, LifecycleError
from app.services.errors import ErrorCode
from app.services.idempotency import _StoredReply
from test_auth_http import api, HEADERS


@pytest.fixture
def subject(api):
    service=MagicMock(spec=LifecycleService); h,t,u=uuid4(),uuid4(),uuid4()
    actor=api.issued.principal.user_id
    data=dict(hackathon_id=str(h),team_id=str(t),user_id=str(actor),member_count=0,
        team_version=2,leader_user_id=None,deleted=True)
    service.leave.return_value=_StoredReply._from_values(200,dict(schema_version=1,data=data),
        {'cache-control':'no-store','content-type':'application/json'})
    service.remove.return_value=service.leave.return_value
    api.app.dependency_overrides[get_lifecycle_service]=lambda:service
    headers={**HEADERS,'Cookie':'__Host-merge_session='+encode_token(api.issued.session_token.get_secret_value()),
        'X-CSRF-Token':encode_token(api.issued.csrf_token.get_secret_value()),'Idempotency-Key':'exact-lifecycle'}
    return service,f'/api/hackathons/{h}/teams/{t}',headers,h,t,u


def test_cookie_actor_csrf_and_exact_service_arguments(api,subject):
    s,path,headers,h,t,u=subject
    r=api.client.post(path+'/leave',headers=headers,json={})
    assert r.status_code==200 and r.json()==s.leave.return_value.body()
    assert r.headers['cache-control']=='no-store, private'
    s.leave.assert_called_once_with(hackathon_id=h,team_id=t,actor_id=api.issued.principal.user_id,key='exact-lifecycle')
    assert api.client.post(path+f'/members/{u}/remove',headers=headers,json={}).status_code==200
    s.remove.assert_called_once_with(hackathon_id=h,team_id=t,actor_id=api.issued.principal.user_id,user_id=u,key='exact-lifecycle')


@pytest.mark.parametrize('kind',['session','csrf','origin','identity','body','key','query','media','fetch'])
@pytest.mark.parametrize('remove',[False,True])
def test_rejected_security_and_schema_never_call_mutation(api,subject,kind,remove):
    s,path,headers,h,t,u=subject; body={}; expected=422
    if kind=='session': headers.pop('Cookie'); expected=401
    elif kind=='csrf': headers['X-CSRF-Token']='bad'; expected=403
    elif kind=='origin': headers['Origin']='https://other.example'; expected=403
    elif kind=='identity': headers['X-Actor-ID']=str(u)
    elif kind=='body': body={'actor_id':str(u)}
    elif kind=='key': headers.pop('Idempotency-Key')
    elif kind=='query': path+='?actor_id=forged'
    elif kind=='media': headers['Content-Type']='text/plain'; expected=415
    elif kind=='fetch': headers['Sec-Fetch-Site']='cross-site'; expected=403
    suffix=f'/members/{u}/remove' if remove else '/leave'
    url=path.partition('?')[0]+suffix+('?' + path.partition('?')[2] if '?' in path else '')
    r=api.client.post(url,headers=headers,json=body)
    assert r.status_code==expected
    s.leave.assert_not_called(); s.remove.assert_not_called()


@pytest.mark.parametrize('code,status',[(ErrorCode.FORBIDDEN,403),(ErrorCode.MEMBER_NOT_FOUND,409),
    (ErrorCode.USE_LEAVE,422),(ErrorCode.TEAM_NOT_FOUND,404),(ErrorCode.IDEMPOTENCY_MISMATCH,409),
    (ErrorCode.OUTCOME_UNCERTAIN,503),(ErrorCode.INTEGRITY_FAULT,503)])
def test_fixed_domain_errors(api,subject,code,status):
    s,path,headers,*_=subject; s.leave.side_effect=LifecycleError(code,retryable=code==ErrorCode.OUTCOME_UNCERTAIN)
    r=api.client.post(path+'/leave',headers=headers,json={})
    assert r.status_code==status and set(r.json())=={'error'}
    assert 'sql' not in r.text.lower()


def test_bounded_roster_is_authenticated_and_allowlisted(api,subject):
    s,path,headers,h,t,u=subject
    s.members.return_value=dict(items=[dict(user_id=u,display_name='Member',joined_at='2026-11-13T00:00:00Z',private='withheld')],next_cursor=None)
    r=api.client.get(path+'/members?limit=2',headers=headers)
    assert r.status_code==200 and set(r.json()['items'][0])=={'user_id','display_name','joined_at'}
    s.members.assert_called_once_with(hackathon_id=h,team_id=t,actor_id=api.issued.principal.user_id,limit=2,cursor=None)
    for query in ('limit=0','limit=101','actor_id=forged','cursor=invalid','limit=1&limit=2'):
        assert api.client.get(path+'/members?'+query,headers=headers).status_code==422
    assert s.members.call_count==1
