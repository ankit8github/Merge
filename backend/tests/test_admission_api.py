"""Offline auth/browser/strict-contract boundary tests; no database access."""
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.auth import encode_token
from app.admission_api import get_admission_service
from app.services.admission import AdmissionService, AdmissionError
from app.services.errors import ErrorCode
from app.services.idempotency import _StoredReply
from app.services.session_errors import SessionCode, SessionError
from test_auth_http import api, ORIGIN, assert_private


@pytest.fixture
def admission(api):
    h,t,r=uuid4(),uuid4(),uuid4()
    service=MagicMock(spec=AdmissionService)
    dto=dict(id=str(r),hackathon_id=str(h),team_id=str(t),requester_id=str(api.issued.principal.user_id),
        status='pending',created_at='2026-11-10T00:00:00+00:00',resolved_at=None)
    reply=_StoredReply._from_values(201,dict(schema_version=1,data=dto),{'content-type':'application/json','cache-control':'no-store'})
    service.create_request.return_value=reply
    service.decide_request.return_value=_StoredReply._from_values(200,dict(schema_version=1,data=dto),dict(reply.headers))
    service.own_request.return_value={'request':dto}
    service.pending_requests.return_value={'items':[dto],'next_cursor':None}
    api.app.dependency_overrides[get_admission_service]=lambda:service
    api.client.cookies.set('__Host-merge_session',encode_token(api.issued.session_token.get_secret_value()))
    return SimpleNamespace(api=api,service=service,h=h,t=t,r=r,dto=dto,path=f'/api/hackathons/{h}/teams/{t}/join-requests',
        headers={'Origin':ORIGIN,'X-CSRF-Token':encode_token(api.issued.csrf_token.get_secret_value()),'Idempotency-Key':'original key'})


def call(d,kind,headers=None,body=None):
    path=d.path+('/'+str(d.r)+'/decision' if kind=='decision' else '/mine' if kind=='mine' else '')
    if kind in ('mine','list'): return d.api.client.get(path,headers=headers)
    return d.api.client.post(path,headers=d.headers if headers is None else headers,
        json=({'decision':'approve'} if kind=='decision' else {}) if body is None else body)


@pytest.mark.parametrize('kind',['create','decision','mine','list'])
def test_all_endpoints_require_validated_cookie(admission,kind):
    d=admission
    d.api.client.cookies.clear()
    response=call(d,kind)
    assert response.status_code==401 and not d.service.mock_calls
    assert_private(response)


@pytest.mark.parametrize('kind',['create','decision'])
@pytest.mark.parametrize('change',['csrf-missing','csrf-wrong','origin','fetch','forwarded','key-missing','key-invalid','actor','query'])
def test_mutation_guards_run_even_with_service_override(admission,kind,change):
    d=admission; headers=dict(d.headers); expected=403
    if change=='csrf-missing': headers.pop('X-CSRF-Token')
    if change=='csrf-wrong': d.api.services.sessions.verify_csrf.side_effect=SessionError(SessionCode.INVALID_CSRF)
    if change=='origin': headers['Origin']='https://evil.example'
    if change=='fetch': headers['Sec-Fetch-Site']='same-site'
    if change=='forwarded': headers['Forwarded']='for=192.0.2.2'
    if change=='key-missing': headers.pop('Idempotency-Key'); expected=422
    if change=='key-invalid': headers['Idempotency-Key']='bad\tkey'; expected=422
    if change=='actor': headers['X-Actor-ID']=str(uuid4()); expected=422
    if change=='query': d.path+='?actor_id=private'; expected=422
    response=call(d,kind,headers=headers)
    assert response.status_code==expected and not d.service.mock_calls
    assert_private(response)


@pytest.mark.parametrize(('kind','body'), [('create',{'requester_id':'private'}),('create',{'team_id':'private'}),
    ('decision',{}),('decision',{'decision':'join'}),('decision',{'decision':'approve','actor_id':'private'}),
    ('decision',{'decision':1})])
def test_strict_inputs_never_echo_private_fields(admission,kind,body):
    r=call(admission,kind,body=body)
    assert r.status_code==422 and 'private' not in r.text and not admission.service.mock_calls


@pytest.mark.parametrize('kind',['create','decision'])
def test_media_and_duplicate_key_guards(admission,kind):
    d=admission
    path=d.path+('/'+str(d.r)+'/decision' if kind=='decision' else '')
    r=d.api.client.post(path,content='{}',headers={**d.headers,'Content-Type':'text/plain'})
    assert r.status_code==415 and not d.service.mock_calls
    r=call(d,kind,headers=list(d.headers.items())+[('Idempotency-Key','another')])
    assert r.status_code==422 and not d.service.mock_calls


def test_exact_session_actor_csrf_stored_reply_and_scoped_read(admission):
    d=admission
    r=call(d,'create')
    assert r.status_code==201 and r.json()==dict(schema_version=1,data=d.dto)
    d.service.create_request.assert_called_once_with(hackathon_id=d.h,team_id=d.t,
        actor_id=d.api.issued.principal.user_id,key='original key')
    d.api.services.sessions.verify_csrf.assert_called_once_with(
        d.api.issued.session_token.get_secret_value(),d.api.issued.csrf_token.get_secret_value())
    assert_private(r)
    assert call(d,'decision').status_code==200
    d.service.decide_request.assert_called_once_with(hackathon_id=d.h,team_id=d.t,
        actor_id=d.api.issued.principal.user_id,request_id=d.r,decision='approve',key='original key')
    own=call(d,'mine')
    assert own.status_code==200, own.text
    assert own.json()['request']['id']==str(d.r)
    assert call(d,'list').status_code==200
    assert d.api.app.state.auth_engine is None


@pytest.mark.parametrize(('code','status'),[(ErrorCode.FORBIDDEN,403),(ErrorCode.REQUEST_NOT_FOUND,404),
    (ErrorCode.TEAM_NOT_FOUND,404),(ErrorCode.TEAM_FULL,409),(ErrorCode.REQUEST_RESOLVED,409),
    (ErrorCode.ALREADY_ASSIGNED,409),(ErrorCode.IDEMPOTENCY_MISMATCH,409),(ErrorCode.OUTCOME_UNCERTAIN,503)])
def test_error_mapping_and_same_key_uncertainty(admission,code,status):
    admission.service.decide_request.side_effect=AdmissionError(code)
    r=call(admission,'decision')
    assert r.status_code==status and r.json()['error']['code']==code.value
    if code==ErrorCode.OUTCOME_UNCERTAIN: assert 'SAME Idempotency-Key' in r.json()['error']['message']
    assert_private(r)


@pytest.mark.parametrize('suffix',['/mine?requester_id=private','?limit=101','?limit=1&limit=2','?cursor=invalid'])
def test_private_and_bounded_read_inputs(admission,suffix):
    r=admission.api.client.get(admission.path+suffix)
    assert r.status_code==422 and not admission.service.mock_calls


def test_new_service_dependency_never_loads_settings_or_builds_fallback(monkeypatch):
    from threading import Lock
    from sqlalchemy.engine import Engine
    import app.core.config
    import app.db.session
    def forbidden(*a,**k): pytest.fail('Ordinary Settings/engine fallback reached')
    monkeypatch.setattr(app.core.config,'Settings',forbidden)
    monkeypatch.setattr(app.db.session,'build_engine',forbidden)
    engine=MagicMock(spec=Engine)
    engine.connect.side_effect=forbidden
    state=SimpleNamespace(auth_lock=Lock(),auth_engine=engine)
    req=SimpleNamespace(app=SimpleNamespace(state=state))
    assert get_admission_service(req,MagicMock())._engine is engine
    engine.connect.assert_not_called()
    state.auth_engine=None
    with pytest.raises(AdmissionError) as error: get_admission_service(req,MagicMock())
    assert error.value.code==ErrorCode.TRANSACTION_CONFIGURATION


def test_pending_http_page_serializes_real_string_cursor_and_preserves_private_projection(admission):
    d=admission
    d.service.pending_requests.return_value={'items':[d.dto],'next_cursor':str(d.r)}
    response=d.api.client.get(d.path+'?limit=1')
    assert response.status_code==200
    assert response.json()['next_cursor']==str(d.r)
    assert response.json()['items'][0]['id']==str(d.r)
    assert 'resolved_by' not in response.json()['items'][0]
    d.service.pending_requests.assert_called_once_with(hackathon_id=d.h,team_id=d.t,
        actor_id=d.api.issued.principal.user_id,limit=1,cursor=None)
    assert_private(response)


def test_cursor_output_fix_still_rejects_invalid_uuid_without_echo(admission):
    d=admission
    d.service.pending_requests.return_value={'items':[d.dto],'next_cursor':'private-invalid-cursor'}
    response=d.api.client.get(d.path+'?limit=1')
    assert response.status_code==503 and 'private-invalid-cursor' not in response.text
    assert_private(response)
