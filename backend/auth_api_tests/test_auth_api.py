"""PYTEST_DONT_REWRITE: real guarded PostgreSQL HTTP authentication, retained fixtures."""
from datetime import timedelta
import secrets

import pytest
from sqlalchemy import event

from app.auth import encode_token
from app.services.credential_errors import CredentialCode, CredentialError
from app.services.sessions import SessionService
from app.services.throttling import ThrottlePolicy, ThrottleService
from pydantic import SecretBytes
from session_tests.test_sessions import seeded_session
from test_support.races import sql

ORIGIN = 'https://merge.example'
HEADERS = {'Origin': ORIGIN, 'X-Merge-Request': '1'}


def login(client, account):
    identity, password = account
    result = client.post('/auth/login', headers=HEADERS, json={'username': identity.username, 'password': password})
    assert result.status_code == 200
    return result


def test_register_login_session_logout_real_dependencies(client, environment):
    env = environment
    username, password = env.username(), secrets.token_urlsafe(32)
    body = {'username': username, 'password': password, 'display_name': 'API fixture'}
    registered = client.post('/auth/register', headers=HEADERS, json=body)
    assert registered.status_code == 201 and not client.cookies and 'set-cookie' not in registered.headers
    assert env.counts() == (1, 1) and env.session_count() == 0
    body.pop('display_name')
    logged = client.post('/auth/login', headers=HEADERS, json=body)
    assert logged.status_code == 200 and logged.json()['identity'] == registered.json()
    raw_cookie = client.cookies.get('__Host-merge_session')
    assert raw_cookie not in logged.text
    current = client.get('/auth/session')
    assert current.status_code == 200 and current.json() == logged.json()
    csrf = current.json()['csrf_token']
    assert client.post('/auth/logout', headers={**HEADERS, 'X-CSRF-Token': csrf}, json={}).status_code == 204
    assert not client.cookies and client.get('/auth/session').status_code == 401
    assert client.get('/auth/session', headers={'Cookie': '__Host-merge_session='+raw_cookie}).status_code == 401
    assert env.session_count() == 1
    with env.connection() as c:
        assert sql(c, 'SELECT count(*) FROM public.auth_sessions WHERE user_id=ANY(:ids) AND revoked_at IS NOT NULL', ids=list(env.ids)).scalar_one() == 1


def test_wrong_password_and_unknown_account_equivalent(client, environment, account):
    first = client.post('/auth/login', headers=HEADERS, json={'username': account[0].username, 'password': secrets.token_urlsafe(32)})
    second = client.post('/auth/login', headers=HEADERS, json={'username': environment.username(), 'password': secrets.token_urlsafe(32)})
    assert first.status_code == second.status_code == 401 and first.json() == second.json()
    assert first.json()['error']['code'] == 'invalid_credentials' and environment.session_count() == 0


def test_duplicate_username_is_conflict_without_extra_user(client, environment, account):
    response = client.post('/auth/register', headers=HEADERS,
                           json={'username': account[0].username, 'password': secrets.token_urlsafe(32)})
    assert response.status_code == 409 and response.json()['error']['code'] == 'username_unavailable'
    assert environment.counts() == (1, 1) and environment.session_count() == 0


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'forged', 'expired', 'revoked'])
def test_invalid_cookie_rejected_by_real_service(client, environment, account, kind):
    if kind == 'expired':
        raw, _, _ = seeded_session(environment, account, timedelta(hours=9))
        cookie = encode_token(raw)
    elif kind == 'revoked':
        material = environment.sessions.login(username=account[0].username, password=account[1])
        raw = material.session_token.get_secret_value()
        environment.sessions.revoke(raw)
        cookie = encode_token(raw)
    else:
        cookie = None if kind == 'missing' else 'invalid' if kind == 'malformed' else encode_token(secrets.token_bytes(32))
    headers = {} if cookie is None else {'Cookie': '__Host-merge_session='+cookie}
    result = client.get('/auth/session', headers=headers)
    assert result.status_code == 401 and result.json()['error']['code'] == 'invalid_session'


@pytest.mark.parametrize('csrf', ['missing', 'malformed', 'wrong_session'])
def test_logout_csrf_rejection_preserves_active_session(client, environment, account, csrf):
    first, second = login(client, account), login(client, account)
    headers = dict(HEADERS)
    if csrf != 'missing': headers['X-CSRF-Token'] = 'invalid' if csrf == 'malformed' else first.json()['csrf_token']
    result = client.post('/auth/logout', headers=headers, json={})
    assert result.status_code == 403 and result.json()['error']['code'] == 'invalid_csrf'
    current = client.get('/auth/session')
    assert current.status_code == 200 and current.json() == second.json()


@pytest.mark.parametrize('failure', ['origin', 'fetch_site', 'content_type', 'extra_field', 'custom_header'])
def test_request_policy_rejects_before_registration(client, environment, failure):
    headers = dict(HEADERS)
    body = {'username': environment.username(), 'password': secrets.token_urlsafe(32)}
    if failure == 'origin': headers['Origin'] = 'https://evil.example'
    elif failure == 'fetch_site': headers['Sec-Fetch-Site'] = 'cross-site'
    elif failure == 'content_type': headers['Content-Type'] = 'text/plain'
    elif failure == 'extra_field': body['actor_id'] = str(secrets.token_hex(16))
    else: headers.pop('X-Merge-Request')
    result = client.post('/auth/register', headers=headers, json=body)
    assert result.status_code == {'content_type': 415, 'extra_field': 422}.get(failure, 403)
    assert environment.counts() == (0, 0) and environment.session_count() == 0


def test_auth_responses_and_logs_exclude_credentials(client, environment, account, caplog):
    result = login(client, account)
    cookie = client.cookies.get('__Host-merge_session')
    with environment.connection() as c:
        encoded = sql(c, 'SELECT password_hash FROM public.account_credentials WHERE user_id=:u', u=account[0].user_id).scalar_one()
    response = client.post('/auth/login', headers=HEADERS,
                           json={'username': account[0].username, 'password': account[1], 'actor_id': account[0].user_id.hex})
    assert response.status_code == 422
    combined = result.text+response.text+caplog.text
    assert all(secret not in combined for secret in (account[1], encoded, cookie))
    assert result.json()['csrf_token'] not in caplog.text+response.text
    assert result.headers['cache-control'] == response.headers['cache-control'] == 'no-store, private'


def test_real_autocommit_rejected_at_http_boundary(client, environment, account, monkeypatch):
    from app.auth import AuthServices, get_services
    from app.services.credentials import CredentialService
    env = environment
    unsafe = env.engine.execution_options(isolation_level='AUTOCOMMIT')
    services = AuthServices(CredentialService(unsafe), SessionService(unsafe),
                           ThrottleService(unsafe, secret=SecretBytes(secrets.token_bytes(32)), policy=ThrottlePolicy()))
    client.app.dependency_overrides[get_services] = lambda: services
    statements, actual, failures = [], [], []
    original_check = services.throttle.check

    def capture_failure(**values):
        try:
            return original_check(**values)
        except CredentialError as error:
            failures.append(error.code)
            raise

    monkeypatch.setattr(services.throttle, 'check', capture_failure)

    def state(c):
        actual.append(c.connection.dbapi_connection.autocommit)

    def observe(c, cursor, statement, parameters, context, many):
        if ('public.account_credentials' in statement or 'public.auth_sessions' in statement
                or 'public.auth_throttle_buckets' in statement or statement.startswith('SET LOCAL')):
            statements.append('unexpected-service-sql')

    event.listen(unsafe, 'before_cursor_execute', observe)
    event.listen(unsafe, 'engine_connect', state)
    try:
        result = client.post('/auth/login', headers=HEADERS,
                             json={'username': account[0].username, 'password': account[1]})
        assert result.status_code == 503 and result.json()['error']['retryable'] is False
    finally:
        event.remove(unsafe, 'engine_connect', state)
        event.remove(unsafe, 'before_cursor_execute', observe)
    assert actual == [True] and failures == [CredentialCode.TRANSACTION_CONFIGURATION]
    assert statements == [] and env.session_count() == 0
