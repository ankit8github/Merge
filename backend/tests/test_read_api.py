"""HTTP security/contract tests with explicit doubles, never database evidence."""
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.auth import encode_token
from app.read_api import get_read_service
from app.read_models import HackathonPage, MyTeam, TeamPage
from app.services.session_errors import SessionCode, SessionError
from app.services.team_reads import ReadError, TeamReadService, _team
from test_auth_http import api, assert_private, ORIGIN, HEADERS


@pytest.fixture
def discovery(api):
    h, t = uuid4(), uuid4()
    row = dict(scope_id=h, team_id=t, name='Visible team', min_team_size=2, max_team_size=3,
               member_count=1, leader_user_id=api.issued.principal.user_id,
               leader_name='Display only', created_at=api.issued.created_at)
    view = _team(row)
    service = MagicMock(spec=TeamReadService)
    service.hackathons.return_value = HackathonPage(items=[], next_cursor=None)
    service.teams.return_value = TeamPage(items=[view], next_cursor=None)
    service.team.return_value = view
    service.my_team.return_value = MyTeam(team=view)
    api.app.dependency_overrides[get_read_service] = lambda: service
    return SimpleNamespace(api=api, service=service, h=h, t=t, view=view,
        paths=['/api/hackathons', f'/api/hackathons/{h}/teams',
               f'/api/hackathons/{h}/teams/{t}', f'/api/hackathons/{h}/me/team'])


def authenticate(d):
    d.api.client.cookies.set('__Host-merge_session', encode_token(d.api.issued.session_token.get_secret_value()))


@pytest.mark.parametrize('index', range(4))
def test_missing_cookie_and_forged_identity_cannot_authorize(discovery, index):
    d = discovery
    result = d.api.client.get(d.paths[index], headers={'X-User-ID':str(uuid4())})
    assert result.status_code == 401 and result.json()['error']['code'] == 'invalid_session'
    assert_private(result)
    d.api.services.sessions.validate_with_csrf.assert_not_called()
    assert d.service.mock_calls == [] and d.api.app.state.auth_engine is None


@pytest.mark.parametrize('index', range(4))
@pytest.mark.parametrize('kind', ['malformed', 'duplicate', 'invalid'])
def test_invalid_sessions_fail_before_read_service(discovery, index, kind):
    d = discovery
    token = encode_token(d.api.issued.session_token.get_secret_value())
    cookie = '__Host-merge_session=bad' if kind=='malformed' else '__Host-merge_session='+token
    if kind=='duplicate': cookie += '; __Host-merge_session='+token
    if kind=='invalid':
        d.api.services.sessions.validate_with_csrf.side_effect = SessionError(SessionCode.INVALID_SESSION)
    result = d.api.client.get(d.paths[index], headers={'Cookie':cookie})
    assert result.status_code == 401 and result.json()['error']['code'] == 'invalid_session'
    assert_private(result)
    assert d.service.mock_calls == []


@pytest.mark.parametrize('index', range(4))
def test_valid_session_has_allowlisted_response_and_one_validation(discovery, index):
    d = discovery
    authenticate(d)
    result = d.api.client.get(d.paths[index])
    assert result.status_code == 200
    assert_private(result)
    assert 'set-cookie' not in result.headers
    d.api.services.sessions.validate_with_csrf.assert_called_once_with(d.api.issued.session_token.get_secret_value())
    for private in ('csrf_token','username','password','session_token','created_by','audit','request_hash'):
        assert private not in result.text
    if index==0: d.service.hackathons.assert_called_once_with(limit=20, cursor=None)
    elif index==1: d.service.teams.assert_called_once_with(d.h, limit=20, cursor=None)
    elif index==2: d.service.team.assert_called_once_with(d.h, d.t)
    else: d.service.my_team.assert_called_once_with(d.h, d.api.issued.principal.user_id)


@pytest.mark.parametrize('query', ['limit=0','limit=101','limit=bad','cursor=private-invalid-uuid',
    'limit=1&limit=2','cursor=&cursor=bad','actor_id=private-actor','unexpected=private-value'])
@pytest.mark.parametrize('index', [0,1])
def test_invalid_pagination_and_extra_fields_are_sanitized(discovery, index, query):
    d = discovery
    authenticate(d)
    result = d.api.client.get(d.paths[index]+'?'+query)
    assert result.status_code == 422 and result.json()['error']['code'] == 'invalid_request'
    assert 'private-' not in result.text and d.service.mock_calls == []
    assert_private(result)


@pytest.mark.parametrize('index', [2,3])
def test_details_do_not_accept_actor_query(discovery, index):
    authenticate(discovery)
    result = discovery.api.client.get(discovery.paths[index]+'?actor_id='+str(uuid4()))
    assert result.status_code == 422 and discovery.service.mock_calls == []


@pytest.mark.parametrize('header', ['X-User-ID','X-Actor-ID'])
def test_identity_headers_rejected_even_with_session(discovery, header):
    authenticate(discovery)
    result = discovery.api.client.get(discovery.paths[3], headers={header:str(uuid4())})
    assert result.status_code == 422 and discovery.service.mock_calls == []


@pytest.mark.parametrize('path', ['/api/hackathons/private-uuid/teams',
    '/api/hackathons/private-uuid/me/team', '/api/hackathons/{h}/teams/private-team'])
def test_invalid_path_uuids_do_not_echo_input(discovery, path):
    authenticate(discovery)
    result = discovery.api.client.get(path.format(h=discovery.h))
    assert result.status_code == 422 and 'private-' not in result.text
    assert discovery.service.mock_calls == []


@pytest.mark.parametrize('code,status', [('hackathon_not_found',404),('team_not_found',404),
    ('invalid_request',422),('service_unavailable',503)])
def test_expected_read_errors_have_fixed_contract(discovery, code, status):
    authenticate(discovery)
    discovery.service.team.side_effect = ReadError(code)
    result = discovery.api.client.get(discovery.paths[2])
    assert result.status_code == status and result.json()['error']['code'] == code
    assert result.json()['error']['retryable'] is False
    assert_private(result)


def test_fault_and_invalid_response_never_leak_or_log_private_data(discovery, caplog):
    d = discovery
    authenticate(d)
    for failure in (RuntimeError('private-driver-detail'), None):
        d.service.team.side_effect = failure
        d.service.team.return_value = {'password_hash':'private-credential-detail'}
        result = d.api.client.get(d.paths[2])
        assert result.status_code == 503
        assert 'private-' not in result.text+caplog.text
        assert encode_token(d.api.issued.session_token.get_secret_value()) not in result.text+caplog.text
        assert_private(result)


@pytest.mark.parametrize('headers', [{'Origin':'https://evil.example'},
    {'Sec-Fetch-Site':'same-site'}, {'Sec-Fetch-Site':'cross-site'},
    {'X-Forwarded-Proto':'https'}])
def test_read_browser_and_proxy_policy_rejects_hostile_requests(discovery, headers):
    authenticate(discovery)
    result = discovery.api.client.get(discovery.paths[0], headers=headers)
    assert result.status_code == 403 and discovery.service.mock_calls == []
    assert_private(result)


def test_read_production_http_and_cors_preflight_rejected(discovery):
    authenticate(discovery)
    result = discovery.api.client.get('http://merge.example'+discovery.paths[0])
    assert result.status_code == 403 and result.json()['error']['code'] == 'https_required'
    preflight = discovery.api.client.options(discovery.paths[0], headers={
        'Origin':ORIGIN, 'Access-Control-Request-Method':'GET'})
    assert preflight.status_code == 405 and 'access-control-allow-origin' not in preflight.headers


@pytest.mark.parametrize('method,index', [(method,index) for method in ('POST','PUT','PATCH','DELETE')
                                        for index in range(4) if (method,index) != ('POST',1)])
def test_no_other_mutation_routes(discovery, method, index):
    authenticate(discovery)
    result = discovery.api.client.request(method, discovery.paths[index], headers=HEADERS, json={})
    assert result.status_code == 405 and discovery.service.mock_calls == []
    assert_private(result)


def test_read_openapi_types_preserved_alongside_create(discovery):
    schema = discovery.api.client.get('/openapi.json').json()
    paths = {k:v for k,v in schema['paths'].items() if k.startswith('/api/')}
    base='/api/hackathons'
    expected={base:{'get'},base+'/{hackathon_id}/teams':{'get','post'},
        base+'/{hackathon_id}/teams/{team_id}':{'get'},base+'/{hackathon_id}/me/team':{'get'},
        base+'/{hackathon_id}/teams/{team_id}/join-requests':{'get','post'},
        base+'/{hackathon_id}/teams/{team_id}/join-requests/mine':{'get'},
        base+'/{hackathon_id}/teams/{team_id}/join-requests/{request_id}/decision':{'post'},
        base+'/{hackathon_id}/invitations/mine':{'get'},
        base+'/{hackathon_id}/teams/{team_id}/invitations':{'post'},
        base+'/{hackathon_id}/teams/{team_id}/invitations/{invitation_id}/redeem':{'post'},
        base+'/{hackathon_id}/teams/{team_id}/leave':{'post'},
        base+'/{hackathon_id}/teams/{team_id}/members':{'get'},
        base+'/{hackathon_id}/teams/{team_id}/members/{user_id}/remove':{'post'},
        base+'/{hackathon_id}/events':{'get'},
        '/api/me/profile':{'get','post'},
        base+'/{hackathon_id}/teams/{team_id}/suggestions':{'get'}}
    assert {path:set(operations) for path,operations in paths.items()} == expected
    for path,operations in paths.items():
        if 'get' not in operations: continue
        assert {'401','403','404','422','503'} <= set(operations['get']['responses'])


def test_explicit_pagination_is_parsed_to_typed_bounded_arguments(discovery):
    authenticate(discovery)
    cursor=uuid4()
    result=discovery.api.client.get(discovery.paths[1],params={'limit':100,'cursor':str(cursor)})
    assert result.status_code==200
    discovery.service.teams.assert_called_once_with(discovery.h,limit=100,cursor=cursor)


def test_bearer_header_alone_is_not_session_authentication(discovery):
    raw=encode_token(discovery.api.issued.session_token.get_secret_value())
    r=discovery.api.client.get(discovery.paths[0],headers={'Authorization':'Bearer '+raw})
    assert r.status_code==401 and discovery.service.mock_calls==[]


def test_lazy_read_service_reuses_owned_engine_without_opening_it():
    from threading import Lock
    from sqlalchemy.engine import Engine
    engine=MagicMock(spec=Engine)
    state=SimpleNamespace(auth_lock=Lock(),read_service=None,auth_engine=engine)
    request=SimpleNamespace(app=SimpleNamespace(state=state))
    service=get_read_service(request,auth=None)
    assert service is get_read_service(request,auth=None) and service._engine is engine
    engine.connect.assert_not_called()
    state.read_service=None
    state.auth_engine=None
    with pytest.raises(ReadError): get_read_service(request,auth=None)


def test_guarded_client_fixture_constructs_offline_without_database():
    from sqlalchemy.engine import Engine
    from read_api_tests.conftest import client as guarded_client
    from app.services.credentials import CredentialService
    from app.services.sessions import SessionService
    env=SimpleNamespace(engine=MagicMock(spec=Engine),service=MagicMock(spec=CredentialService),
        sessions=MagicMock(spec=SessionService),reads=MagicMock(spec=TeamReadService))
    env.engine.hide_parameters=True
    env.engine.echo=False
    fixture=guarded_client.__wrapped__(env)
    client=next(fixture)
    try:
        assert client.get('/api/hackathons').status_code==401
        env.engine.connect.assert_not_called()
    finally:
        with pytest.raises(StopIteration): next(fixture)
