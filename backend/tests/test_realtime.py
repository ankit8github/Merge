"""Offline SSE ownership/security checks. Not PostgreSQL commit-visibility proof."""
import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import SecretBytes
import pytest
from sqlalchemy.engine import Engine

from app import realtime_api as stream
from app.auth import encode_token
from app.services.realtime import RealtimeService, SNAPSHOT, fingerprint
from app.services.session_errors import SessionError, SessionCode
from app.services.team_reads import ReadError
from test_auth_http import api, assert_private


@pytest.fixture
def realtime(api, monkeypatch):
    service = MagicMock(spec=RealtimeService); h = uuid4()
    service.revision.return_value = 'a'*64
    api.app.dependency_overrides[stream.get_realtime_service] = lambda: service
    async def finite(*args):
        yield stream.frame('reset', h, api.issued.principal.user_id, 'a'*64)
    monkeypatch.setattr(stream, 'changes', finite)
    headers = {'Cookie':'__Host-merge_session='+encode_token(api.issued.session_token.get_secret_value())}
    return SimpleNamespace(api=api, h=h, service=service, headers=headers, path=f'/api/hackathons/{h}/events')


@pytest.mark.parametrize('kind,status', [('guest',401),('revoked',401),('origin',403),('fetch',403),('actor',422),('query',422),
    ('cursor',422),('duplicate',422),('long',422)])
def test_stream_policy_failures_never_sample(realtime,kind,status):
    r=realtime; headers=dict(r.headers); path=r.path
    if kind=='guest': headers={}
    elif kind=='revoked': r.api.services.sessions.validate_with_csrf.side_effect=SessionError(SessionCode.INVALID_SESSION)
    elif kind=='origin': headers['Origin']='https://other.example'
    elif kind=='fetch': headers['Sec-Fetch-Site']='cross-site'
    elif kind=='actor': headers['X-Actor-ID']=str(uuid4())
    elif kind=='query': path+='?actor_id=forged'
    elif kind=='cursor': headers['Last-Event-ID']='not-a-fingerprint'
    elif kind=='long': headers['Last-Event-ID']='a'*65
    elif kind=='duplicate': headers=[*headers.items(),('Last-Event-ID','a'*64),('Last-Event-ID','b'*64)]
    response=r.api.client.get(path,headers=headers)
    assert response.status_code==status; assert_private(response)
    r.service.revision.assert_not_called()


def test_stream_contract_is_private_bounded_and_has_no_domain_payload(realtime):
    r=realtime; response=r.api.client.get(r.path,headers={**r.headers,'Last-Event-ID':'a'*64})
    assert response.status_code==200 and response.headers['content-type'].startswith('text/event-stream')
    assert response.headers['x-accel-buffering']=='no'; assert_private(response)
    assert 'event: reset' in response.text and 'id: '+'a'*64 in response.text
    for private in ('csrf','token','request_id','team_id','invitation_id','member_count'):
        assert private not in response.text
    r.service.revision.assert_called_once_with(r.h,r.api.issued.principal.user_id)
    assert not r.api.app.state.realtime_subscribers.accounts


@pytest.mark.parametrize('code,status',[('hackathon_not_found',404),('service_unavailable',503)])
def test_initial_read_failure_releases_claim_before_headers(realtime,code,status):
    r=realtime; r.service.revision.side_effect=ReadError(code)
    assert r.api.client.get(r.path,headers=r.headers).status_code==status
    assert not r.api.app.state.realtime_subscribers.accounts


def test_subscriber_cap_denial_has_retry_after_and_never_samples(realtime):
    r=realtime; caps=r.api.app.state.realtime_subscribers; actor=r.api.issued.principal.user_id
    with caps.claim(actor),caps.claim(actor):
        response=r.api.client.get(r.path,headers=r.headers)
        assert response.status_code==429 and response.headers['retry-after']=='5'
        r.service.revision.assert_not_called()
    assert not caps.accounts


def test_total_cap_and_exception_cleanup():
    from contextlib import ExitStack
    caps=stream.Subscribers()
    with ExitStack() as stack:
        for _ in range(64): stack.enter_context(caps.claim(uuid4()))
        with pytest.raises(Exception): stack.enter_context(caps.claim(uuid4()))
    assert not caps.accounts


def test_send_headers_failure_releases_claim():
    async def exercise():
        caps=stream.Subscribers(); actor=uuid4(); claim=caps.claim(actor); claim.__enter__()
        async def body(): yield 'never sent'
        async def send(message): raise RuntimeError('synthetic-send-failure')
        async def receive(): return {'type':'http.disconnect'}
        response=stream.EventStream(body(),claim)
        with pytest.raises(RuntimeError):
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
        assert not caps.accounts
    asyncio.run(exercise())


def test_stream_cancellation_closes_body_and_releases_claim():
    async def exercise():
        caps=stream.Subscribers(); actor=uuid4(); claim=caps.claim(actor); claim.__enter__(); closed=[]
        async def body():
            try: yield 'first'
            finally: closed.append(True)
        async def send(message):
            if message['type']=='http.response.body': raise asyncio.CancelledError()
        async def receive(): return {'type':'http.disconnect'}
        response=stream.EventStream(body(),claim)
        with pytest.raises(asyncio.CancelledError):
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
        assert closed==[True] and not caps.accounts
    asyncio.run(exercise())


def test_lease_ends_without_further_queries(monkeypatch):
    clock=iter([0,61]); monkeypatch.setattr(stream,'monotonic',lambda:next(clock))
    services,reads=MagicMock(),MagicMock()
    async def exercise():
        values=stream.changes(MagicMock(),uuid4(),uuid4(),b'not-logged',services,reads,'a'*64)
        assert 'event: reset' in await anext(values)
        with pytest.raises(StopAsyncIteration): await anext(values)
        services.sessions.validate.assert_not_called(); reads.revision.assert_not_called()
    asyncio.run(exercise())


def test_stalled_network_send_has_deadline_and_releases_claim(monkeypatch):
    monkeypatch.setattr(stream,'SEND_TIMEOUT_SECONDS',0.001)
    async def exercise():
        caps=stream.Subscribers(); claim=caps.claim(uuid4()); claim.__enter__()
        async def body(): yield 'never sent'
        async def send(message): await asyncio.Event().wait()
        async def receive(): return {'type':'http.disconnect'}
        await stream.EventStream(body(),claim)({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
        assert not caps.accounts
    asyncio.run(exercise())


@pytest.mark.parametrize('failure',['revoked','identity','database','disconnect','duplicate','change'])
def test_stream_revalidates_each_poll_and_stops_safely(monkeypatch,failure):
    monkeypatch.setattr(stream,'POLL_SECONDS',0)
    actor,h=uuid4(),uuid4(); sessions=MagicMock(); sessions.validate.return_value=SimpleNamespace(user_id=actor)
    reads=MagicMock(); reads.revision.return_value='b'*64 if failure=='change' else 'a'*64
    if failure=='revoked': sessions.validate.side_effect=SessionError(SessionCode.INVALID_SESSION)
    elif failure=='identity': sessions.validate.return_value=SimpleNamespace(user_id=uuid4())
    elif failure=='database': reads.revision.side_effect=RuntimeError('private-driver-detail')
    request=MagicMock()
    async def disconnected(): return failure=='disconnect'
    request.is_disconnected=disconnected
    async def exercise():
        values=stream.changes(request,h,actor,b'not-logged',SimpleNamespace(sessions=sessions),reads,'a'*64)
        assert 'event: reset' in await anext(values)
        if failure=='disconnect':
            with pytest.raises(StopAsyncIteration): await anext(values)
            sessions.validate.assert_not_called()
        else:
            value=await anext(values)
            assert ('event: expired' if failure in ('revoked','identity') else 'event: unavailable' if failure=='database'
                else 'event: invalidate' if failure=='change' else ': keepalive') in value
            assert 'private-driver-detail' not in value
            sessions.validate.assert_called_once()
        await values.aclose()
    asyncio.run(exercise())


def test_fingerprint_scopes_and_late_commit_or_permission_changes():
    h,u=uuid4(),uuid4(); start=fingerprint(h,u,2,3)
    assert start==fingerprint(h,u,2,3)  # rollback/no committed change
    assert start!=fingerprint(h,u,3,3)  # late commit, independent of UUID/time
    assert start!=fingerprint(h,u,3,2)  # private visibility loss cannot offset public increment
    assert start!=fingerprint(uuid4(),u,2,3) and start!=fingerprint(h,uuid4(),2,3)


def test_sample_uses_owned_read_only_transaction_and_fixed_visibility_predicates():
    service=RealtimeService(MagicMock(spec=Engine)); h,u=uuid4(),uuid4(); c=MagicMock()
    c.execute.return_value.mappings.return_value.one_or_none.return_value=dict(public_count=2,private_count=1)
    calls=[]
    def read(operation): calls.append('owned-read'); return operation(c)
    service._read=read
    assert service.revision(h,u)==fingerprint(h,u,2,1) and calls==['owned-read']
    statement,params=c.execute.call_args.args
    assert params==dict(hackathon=h,actor=u)
    assert 'a.hackathon_id=:hackathon' in str(statement)
    for clause in ('r.requester_id=:actor','t.leader_user_id=:actor','t.deleted_at IS NULL','i.recipient_id=:actor'):
        assert clause in SNAPSHOT
    assert 'published_at' not in SNAPSHOT and not any(word in SNAPSHOT for word in ('UPDATE ','INSERT ','DELETE '))
    c.execute.return_value.mappings.return_value.one_or_none.return_value=None
    with pytest.raises(ReadError): service.revision(h,u)


def test_dependency_has_no_settings_or_engine_fallback(monkeypatch):
    from app.core import config
    from app.db import session
    def forbidden(*args): pytest.fail('Fallback reached')
    monkeypatch.setattr(config,'Settings',forbidden); monkeypatch.setattr(session,'build_engine',forbidden)
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(auth_engine=None)))
    with pytest.raises(ReadError): stream.get_realtime_service(request,MagicMock())


def test_real_read_owner_closes_transaction_before_return():
    from test_team_reads import Connection
    c=Connection(); c.rows=[dict(public_count=1,private_count=2)]
    engine=MagicMock(spec=Engine); engine.connect.return_value.__enter__.return_value=c
    service=RealtimeService(engine); h,u=uuid4(),uuid4()
    assert service.revision(h,u)==fingerprint(h,u,1,2)
    assert c.events==['begin','commit'] and not c.active
    assert [q for q,_ in c.queries[:3]]==['SET TRANSACTION READ ONLY',"SET LOCAL lock_timeout='5s'","SET LOCAL statement_timeout='15s'"]
    engine.connect.return_value.__exit__.assert_called_once()
    c.connection.dbapi_connection.autocommit=True
    with pytest.raises(ReadError): service.revision(h,u)


def test_realtime_runner_rejects_wrong_revision_before_credentials(monkeypatch):
    from test_support import concurrency
    monkeypatch.setattr('sys.argv',['concurrency','--confirm-merge-test','--suite','realtime','--revision','0003_auth'])
    monkeypatch.setattr(concurrency,'getpass',lambda *a:pytest.fail('Credential prompt reached'))
    monkeypatch.setattr(concurrency,'test_connection',lambda *a:pytest.fail('Connection reached'))
    with pytest.raises(SystemExit) as error: concurrency.main()
    assert error.value.code==2


def test_old_browser_scope_has_no_realtime_permission():
    # The pre-existing exact inventory/target guards stay unchanged.
    from test_support import browser, browser_full
    assert not any(path.endswith('/events') for path,_ in browser.ENDPOINTS)
    assert not any(path.endswith('/events') for path,_ in browser_full.ENDPOINTS)
