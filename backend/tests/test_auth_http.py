"""PYTEST_DONT_REWRITE: HTTP adapter/policy tests; no PostgreSQL evidence."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import secrets

from fastapi.testclient import TestClient
from pydantic import SecretBytes, ValidationError
import pytest

from app.auth import AuthServices, decode_token, encode_token, get_services
from app.main import create_app
from app.security.auth_policy import AuthSettings
from app.services.credentials import CredentialIdentity, CredentialService
from app.services.credential_errors import CredentialCode, CredentialError
from app.services.sessions import IssuedSession, SessionPrincipal, SessionService, ValidatedSession
from app.services.session_errors import SessionCode, SessionError

ORIGIN = 'https://merge.example'
HEADERS = {'Origin': ORIGIN, 'X-Merge-Request': '1'}
BODY = {'username': 'unit_user', 'password': 'synthetic HTTP passphrase'}


@pytest.fixture
def api():
    now = datetime.now(timezone.utc)
    principal = SessionPrincipal(uuid4(), 'unit_user', now+timedelta(hours=8))
    issued = IssuedSession(principal, now, SecretBytes(secrets.token_bytes(32)), SecretBytes(secrets.token_bytes(32)))
    credentials, sessions = MagicMock(spec=CredentialService), MagicMock(spec=SessionService)
    credentials.register.return_value = CredentialIdentity(principal.user_id, principal.username)
    sessions.login.return_value = issued
    sessions.validate_with_csrf.return_value = ValidatedSession(principal, issued.csrf_token)
    services = AuthServices(credentials, sessions)
    app = create_app(AuthSettings(origin=ORIGIN))
    app.dependency_overrides[get_services] = lambda: services
    with TestClient(app, base_url=ORIGIN) as client:
        yield SimpleNamespace(app=app, client=client, services=services, issued=issued)


def login(api):
    return api.client.post('/auth/login', headers=HEADERS, json=BODY)


def assert_private(response):
    assert response.headers['cache-control'] == 'no-store, private'
    assert response.headers['pragma'] == 'no-cache'
    assert response.headers['expires'] == '0'
    assert 'access-control-allow-origin' not in response.headers


def test_register_login_session_logout_contract_and_production_cookie(api):
    r = api.client.post('/auth/register', headers=HEADERS, json=BODY)
    assert r.status_code == 201 and set(r.json()) == {'user_id', 'username'}
    assert not r.headers.get('set-cookie') and not api.client.cookies
    api.services.sessions.login.assert_not_called()
    r = login(api)
    assert r.status_code == 200
    csrf = r.json()['csrf_token']
    cookie = r.headers['set-cookie']
    assert cookie.startswith('__Host-merge_session=')
    assert all(flag in cookie for flag in ('Secure', 'HttpOnly', 'SameSite=lax', 'Path=/', 'Max-Age=28800'))
    assert 'Domain=' not in cookie
    assert set(r.json()) == {'identity', 'expires_at', 'csrf_token'}
    assert encode_token(api.issued.session_token.get_secret_value()) not in r.text
    assert_private(r)
    current = api.client.get('/auth/session')
    assert current.status_code == 200 and current.json() == r.json()
    assert 'set-cookie' not in current.headers
    result = api.client.post('/auth/logout', headers={**HEADERS, 'X-CSRF-Token': csrf}, json={})
    assert result.status_code == 204 and result.content == b''
    cleared = result.headers['set-cookie']
    assert all(flag in cleared for flag in ('__Host-merge_session=', 'Max-Age=0', 'Secure', 'HttpOnly', 'SameSite=lax', 'Path=/'))
    assert 'Domain=' not in cleared and not api.client.cookies
    api.services.sessions.verify_csrf.assert_called_once_with(api.issued.session_token.get_secret_value(), api.issued.csrf_token.get_secret_value())
    api.services.sessions.revoke.assert_called_once()
    assert_private(result)


@pytest.mark.parametrize('path', ['/auth/register', '/auth/login', '/auth/logout'])
@pytest.mark.parametrize('content', ['text/plain', 'application/x-www-form-urlencoded', 'multipart/form-data', 'application/problem+json', None])
def test_only_json_mutations(api, path, content):
    headers = dict(HEADERS)
    if content: headers['Content-Type'] = content
    response = api.client.post(path, headers=headers, content='{}')
    assert response.status_code == 415
    assert_private(response)
    api.services.credentials.register.assert_not_called()
    api.services.sessions.login.assert_not_called()


@pytest.mark.parametrize('origin', [None, 'null', 'https://evil.example', 'https://merge.example.evil', ORIGIN+'/', 'http://merge.example'])
@pytest.mark.parametrize('path', ['/auth/register', '/auth/login', '/auth/logout'])
def test_mutations_require_exact_origin(api, origin, path):
    headers = {'X-Merge-Request': '1'}
    if origin is not None: headers['Origin'] = origin
    r = api.client.post(path, headers=headers, json=BODY)
    assert r.status_code == 403 and r.json()['error']['code'] == 'origin_rejected'


@pytest.mark.parametrize('site', ['cross-site', 'same-site', 'invalid'])
@pytest.mark.parametrize('path', ['/auth/register', '/auth/login', '/auth/logout', '/auth/session'])
def test_fetch_metadata_rejects_non_same_origin(api, site, path):
    if path == '/auth/session':
        response = api.client.get(path, headers={'Sec-Fetch-Site': site})
    else:
        response = api.client.post(path, headers={**HEADERS, 'Sec-Fetch-Site': site}, json={})
    assert response.status_code == 403
    api.services.sessions.login.assert_not_called()
    api.services.sessions.validate_with_csrf.assert_not_called()


@pytest.mark.parametrize('header', [None, '0', 'true'])
@pytest.mark.parametrize('path', ['/auth/register', '/auth/login'])
def test_unauthenticated_custom_header_required(api, header, path):
    headers = {'Origin': ORIGIN}
    if header: headers['X-Merge-Request'] = header
    assert api.client.post(path, headers=headers, json=BODY).status_code == 403


@pytest.mark.parametrize('extra', ['actor_id', 'user_id', 'is_leader', 'identity'])
@pytest.mark.parametrize('path', ['/auth/register', '/auth/login'])
def test_no_client_identity_fields(api, path, extra):
    r = api.client.post(path, headers=HEADERS, json={**BODY, extra: 'synthetic-input'})
    assert r.status_code == 422 and 'synthetic-input' not in r.text
    api.services.credentials.register.assert_not_called()
    api.services.sessions.login.assert_not_called()


@pytest.mark.parametrize('body', [None, [], {'username': 42, 'password': BODY['password']},
                                {**BODY, 'password': 42}, {**BODY, 'username': 'Upper'},
                                {**BODY, 'password': 'short'}, {**BODY, 'password': '\ud800'*20}])
def test_strict_invalid_body_has_fixed_errors(api, body):
    import json
    r = api.client.post('/auth/login', headers={**HEADERS, 'Content-Type': 'application/json'},
                        content=json.dumps(body))
    assert r.status_code == 422
    assert r.json() == {'error': {'code': 'invalid_request', 'message': 'Request body is invalid.', 'retryable': False}}


def test_malformed_json_and_duplicate_security_headers(api):
    assert api.client.post('/auth/login', headers={**HEADERS, 'Content-Type': 'application/json'}, content='{').status_code == 422
    headers = [('Origin', ORIGIN), ('Origin', ORIGIN), ('X-Merge-Request', '1')]
    assert api.client.post('/auth/login', headers=headers, json=BODY).status_code == 403
    assert api.client.options('/auth/login', headers={'Origin': 'https://evil.example', 'Access-Control-Request-Method': 'POST'}).status_code == 403


@pytest.mark.parametrize('cookie', [None, 'forged', 'A'*42, 'A'*44, '!'*43, 'A'*42+'B'])
def test_missing_malformed_or_noncanonical_cookie(api, cookie):
    headers = {} if cookie is None else {'Cookie': '__Host-merge_session='+cookie}
    r = api.client.get('/auth/session', headers=headers)
    assert r.status_code == 401
    api.services.sessions.validate_with_csrf.assert_not_called()


def test_missing_cookie_does_not_initialize_runtime_database(api):
    def unexpected_services():
        pytest.fail('Missing-cookie request reached database dependency')
    api.app.dependency_overrides[get_services] = unexpected_services
    assert api.client.get('/auth/session').status_code == 401
    assert api.client.post('/auth/logout', headers=HEADERS, json={}).status_code == 401


def test_equivalent_invalid_credentials_and_safe_validation_logs(api, caplog):
    api.services.sessions.login.side_effect = CredentialError(CredentialCode.INVALID_CREDENTIALS)
    first = login(api)
    second = api.client.post('/auth/login', headers=HEADERS, json={**BODY, 'username': 'unknown_user'})
    assert first.status_code == second.status_code == 401 and first.json() == second.json()
    invalid = api.client.post('/auth/login', headers=HEADERS, json={**BODY, 'user_id': 'synthetic-private-input'})
    assert invalid.status_code == 422
    assert BODY['password'] not in invalid.text+caplog.text
    assert 'synthetic-private-input' not in invalid.text+caplog.text


def test_auth_openapi_documents_structured_errors(api):
    schema = api.client.get('/openapi.json').json()
    response = schema['paths']['/auth/login']['post']['responses']['422']
    assert response['content']['application/json']['schema']['$ref'].endswith('/ErrorResponse')


def test_duplicate_cookie_rejected(api):
    value = encode_token(secrets.token_bytes(32))
    r = api.client.get('/auth/session', headers={'Cookie': f'__Host-merge_session={value}; __Host-merge_session={value}'})
    assert r.status_code == 401


@pytest.mark.parametrize('token', [None, 'invalid', encode_token(secrets.token_bytes(32))])
def test_logout_csrf_failure_does_not_revoke(api, token):
    login(api)
    if token and len(token) == 43:
        api.services.sessions.verify_csrf.side_effect = SessionError(SessionCode.INVALID_CSRF)
    headers = dict(HEADERS)
    if token: headers['X-CSRF-Token'] = token
    r = api.client.post('/auth/logout', headers=headers, json={})
    assert r.status_code == 403 and r.json()['error']['code'] == 'invalid_csrf'
    api.services.sessions.revoke.assert_not_called()


@pytest.mark.parametrize('code', list(CredentialCode))
def test_all_credential_errors_are_fixed_and_sanitized(api, code, caplog):
    api.services.sessions.login.side_effect = CredentialError(code, retryable=True)
    r = login(api)
    expected = {CredentialCode.INVALID_CREDENTIALS: 401, CredentialCode.USERNAME_UNAVAILABLE: 409,
                CredentialCode.INVALID_INPUT: 422}.get(code, 503)
    assert r.status_code == expected
    assert set(r.json()['error']) == {'code', 'message', 'retryable'}
    assert r.json()['error']['retryable'] is (code in (
        CredentialCode.HASHING_BUSY, CredentialCode.TRANSACTION_CONFLICT, CredentialCode.LOCK_TIMEOUT))
    assert BODY['password'] not in r.text+caplog.text
    assert_private(r)


@pytest.mark.parametrize('code', list(SessionCode))
def test_all_session_errors_are_fixed(api, code):
    login(api)
    api.services.sessions.validate_with_csrf.side_effect = SessionError(code)
    r = api.client.get('/auth/session')
    assert r.status_code == {SessionCode.INVALID_SESSION: 401, SessionCode.INVALID_CSRF: 403,
                             SessionCode.AUTHENTICATION_CHANGED: 401}.get(code, 503)


def test_unexpected_error_never_logs_or_exposes_details(api, caplog):
    api.services.sessions.login.side_effect = RuntimeError('synthetic-sensitive-driver-detail')
    r = login(api)
    assert r.status_code == 503
    combined = r.text+caplog.text
    assert 'synthetic-sensitive-driver-detail' not in combined and BODY['password'] not in combined
    assert encode_token(api.issued.session_token.get_secret_value()) not in combined


@pytest.mark.parametrize('change', [{'origin': 'http://merge.example'}, {'origin': '*'}, {'origin': ORIGIN+'/'},
                                   {'origin': ORIGIN+'/path'}, {'origin': 'https://user:pass@merge.example'},
                                   {'origin': ORIGIN+':70000'}, {'mode': 'development', 'origin': ORIGIN}])
def test_insecure_configuration_rejected(change):
    with pytest.raises(ValidationError): AuthSettings(**change)


def test_startup_rejects_missing_production_origin(monkeypatch):
    monkeypatch.delenv('MERGE_AUTH_ORIGIN', raising=False)
    monkeypatch.setenv('MERGE_AUTH_MODE', 'production')
    with pytest.raises(RuntimeError, match='Invalid authentication configuration'):
        with TestClient(create_app()): pass


def test_explicit_loopback_development_cookie_policy(api):
    app = create_app(AuthSettings(mode='development', origin='http://127.0.0.1:5173'))
    app.dependency_overrides[get_services] = lambda: api.services
    with TestClient(app, base_url='http://127.0.0.1:5173') as client:
        r = client.post('/auth/login', headers={'Origin': 'http://127.0.0.1:5173', 'X-Merge-Request': '1'}, json=BODY)
        assert r.status_code == 200
        cookie = r.headers['set-cookie']
        assert cookie.startswith('merge_session_dev=') and 'Secure' not in cookie and 'Domain=' not in cookie
        assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie
        assert client.get('/auth/session').status_code == 200


def test_production_http_and_hostile_read_origin_rejected(api):
    assert api.client.get('/auth/session', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert api.client.get('http://merge.example/auth/session').status_code == 403


def test_no_team_endpoints_or_permissive_cors(api):
    assert api.client.post('/teams', json={'actor_id': str(uuid4())}).status_code == 404
    r = api.client.options('/auth/login', headers={'Origin': ORIGIN, 'Access-Control-Request-Method': 'POST'})
    assert r.status_code == 405 and 'access-control-allow-origin' not in r.headers
    assert api.client.get('/health').json() == {'status': 'ok'}
