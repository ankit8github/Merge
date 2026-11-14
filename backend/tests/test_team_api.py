"""Create-only HTTP contract/security tests; doubles are not PostgreSQL evidence."""
from threading import Lock
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine

from app.auth import encode_token
from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import _StoredReply
from app.services.session_errors import SessionCode, SessionError
from app.services.teams import TeamService
from app.team_api import get_team_service
from test_auth_http import api, assert_private, ORIGIN


@pytest.fixture
def creation(api):
    h, t = uuid4(), uuid4()
    body = {'schema_version': 1, 'data': {'team_id': str(t), 'hackathon_id': str(h),
        'user_id': str(api.issued.principal.user_id), 'member_count': 1, 'team_version': 1}}
    service = MagicMock(spec=TeamService)
    service.create_team_idempotent.return_value = _StoredReply._from_values(201, body,
        {'content-type': 'application/json', 'cache-control': 'no-store'})
    api.app.dependency_overrides[get_team_service] = lambda: service
    api.client.cookies.set('__Host-merge_session', encode_token(api.issued.session_token.get_secret_value()))
    return SimpleNamespace(api=api, service=service, h=h, body=body,
        path=f'/api/hackathons/{h}/teams', headers={'Origin': ORIGIN, 'Idempotency-Key': 'offline-key',
        'X-CSRF-Token': encode_token(api.issued.csrf_token.get_secret_value())})


def post(d, **kwargs):
    return d.api.client.post(d.path, headers=kwargs.pop('headers', d.headers), **(kwargs or {'json': {'name': ' Team '}}))


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'duplicate', 'unknown', 'expired', 'revoked'])
def test_session_required_before_mutation(creation, kind):
    d = creation
    d.api.client.cookies.clear()
    headers = dict(d.headers)
    token = encode_token(d.api.issued.session_token.get_secret_value())
    if kind != 'missing':
        headers['Cookie'] = '__Host-merge_session=' + ('bad' if kind == 'malformed' else token)
    if kind == 'duplicate': headers['Cookie'] += '; __Host-merge_session=' + token
    if kind in ('unknown', 'expired', 'revoked'):
        d.api.services.sessions.validate_with_csrf.side_effect = SessionError(SessionCode.INVALID_SESSION)
    r = post(d, headers=headers)
    assert r.status_code == 401 and r.json()['error']['code'] == 'invalid_session'
    assert_private(r)
    assert not d.service.mock_calls and d.api.app.state.auth_engine is None


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'duplicate', 'other-session', 'revoked-between-checks'])
def test_csrf_required_even_when_mutation_dependency_overridden(creation, kind):
    d = creation
    headers = list(d.headers.items())
    if kind == 'missing': headers = [(k,v) for k,v in headers if k != 'X-CSRF-Token']
    if kind == 'malformed': headers = [(k,'bad' if k == 'X-CSRF-Token' else v) for k,v in headers]
    if kind == 'duplicate': headers.append(('X-CSRF-Token', d.headers['X-CSRF-Token']))
    if kind in ('other-session', 'revoked-between-checks'):
        code = SessionCode.INVALID_CSRF if kind == 'other-session' else SessionCode.INVALID_SESSION
        d.api.services.sessions.verify_csrf.side_effect = SessionError(code)
    r = post(d, headers=headers)
    assert r.status_code == (401 if kind == 'revoked-between-checks' else 403)
    assert not d.service.mock_calls
    assert_private(r)


@pytest.mark.parametrize('header,value', [('Origin', None), ('Origin', 'null'),
    ('Origin', 'https://evil.example'), ('Origin', ORIGIN+'/'), ('Sec-Fetch-Site', 'same-site'),
    ('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Site', 'invalid'), ('X-Forwarded-Proto', 'https'),
    ('Forwarded', 'for=192.0.2.2;proto=https')])
def test_browser_and_actual_peer_policy(creation, header, value):
    headers = {k:v for k,v in creation.headers.items() if k != header}
    if value is not None: headers[header] = value
    r = post(creation, headers=headers)
    assert r.status_code == 403 and not creation.service.mock_calls
    assert_private(r)


@pytest.mark.parametrize('header', ['Origin', 'Sec-Fetch-Site', 'Content-Type'])
def test_duplicate_browser_headers_rejected(creation, header):
    headers = list(creation.headers.items()) + [('Content-Type', 'application/json')]
    value = {'Origin': ORIGIN, 'Sec-Fetch-Site': 'same-origin', 'Content-Type': 'application/json'}[header]
    if header == 'Sec-Fetch-Site': headers.append((header, value))
    headers.append((header, value))
    r = post(creation, headers=headers)
    assert r.status_code == (415 if header == 'Content-Type' else 403)
    assert not creation.service.mock_calls


@pytest.mark.parametrize('key', [None, '', 'x'*129, 'private\tkey', 'non-ascii-\xe9'])
def test_invalid_idempotency_header_before_service(creation, key):
    headers = {k:v for k,v in creation.headers.items() if k != 'Idempotency-Key'}
    if key is not None:
        # Raw HTTP bytes allow the non-ASCII rejection case through HTTPX.
        headers = [(k.encode(),v.encode()) for k,v in headers.items()]
        headers.append((b'Idempotency-Key', key.encode('latin-1')))
    r = post(creation, headers=headers)
    assert r.status_code == 422 and r.json()['error']['code'] == 'invalid_request'
    assert not creation.service.mock_calls and 'private' not in r.json()['error']['message']


def test_duplicate_idempotency_header_rejected(creation):
    r = post(creation, headers=list(creation.headers.items())+[('Idempotency-Key','other')])
    assert r.status_code == 422 and not creation.service.mock_calls


@pytest.mark.parametrize('key', [' ', ' Key With Spaces ', '~'*128])
def test_exact_key_and_name_passed_without_normalization(creation, key):
    d = creation
    r = post(d, headers={**d.headers, 'Idempotency-Key': key})
    assert r.status_code == 201 and r.json() == d.body
    d.service.create_team_idempotent.assert_called_once_with(hackathon_id=d.h,
        actor_id=d.api.issued.principal.user_id, name=' Team ', key=key)
    d.api.services.sessions.verify_csrf.assert_called_once_with(
        d.api.issued.session_token.get_secret_value(), d.api.issued.csrf_token.get_secret_value())
    assert 'set-cookie' not in r.headers and r.headers['content-type'] == 'application/json'
    assert_private(r)


@pytest.mark.parametrize('body', [{}, {'name': ''}, {'name': ' '*3}, {'name': 'x'*121},
    {'name': None}, {'name': 1}, {'name': ['Team']}, {'name': 'bad\x00name'},
    {'name': '\ud800'}, {'name': 'Team', 'actor_id': 'private-actor'},
    {'name': 'Team', 'user_id': 'private-actor'}, {'name': 'Team', 'team_id': str(uuid4())},
    {'name': 'Team', 'max_team_size': 9}, {'name': 'Team', 'key': 'private-key'}, []])
def test_strict_body_rejects_invalid_fields_without_echo(creation, body):
    import json
    r = post(creation, content=json.dumps(body), headers={**creation.headers, 'Content-Type': 'application/json'})
    assert r.status_code == 422 and r.json()['error']['code'] == 'invalid_request'
    assert 'private-' not in r.text and not creation.service.mock_calls
    assert_private(r)


@pytest.mark.parametrize('body', ['{', 'null', '{"name":NaN}', '"private-input"'])
def test_malformed_json_is_sanitized(creation, body):
    r = post(creation, content=body, headers={**creation.headers, 'Content-Type': 'application/json'})
    assert r.status_code == 422 and 'private-input' not in r.text and not creation.service.mock_calls


@pytest.mark.parametrize('media', [None, 'text/plain', 'application/problem+json', 'application/x-www-form-urlencoded'])
def test_json_required(creation, media):
    headers = dict(creation.headers)
    if media: headers['Content-Type'] = media
    r = post(creation, content='{}', headers=headers)
    assert r.status_code == 415 and not creation.service.mock_calls


@pytest.mark.parametrize('kind', ['uuid', 'query', 'actor-header', 'user-header'])
def test_no_scope_or_identity_overrides(creation, kind):
    d = creation
    headers = dict(d.headers)
    if kind == 'uuid': d.path = '/api/hackathons/private-uuid/teams'
    if kind == 'query': d.path += '?actor_id=private-actor'
    if kind.endswith('header'): headers['X-Actor-ID' if kind == 'actor-header' else 'X-User-ID'] = str(uuid4())
    r = post(d, headers=headers)
    assert r.status_code == 422 and 'private-' not in r.text and not d.service.mock_calls


@pytest.mark.parametrize('code', list(ErrorCode))
def test_domain_errors_stable_sanitized_and_uncertainty_explicit(creation, code, caplog):
    creation.service.create_team_idempotent.side_effect = DomainError(code, retryable=True)
    r = post(creation)
    expected = {ErrorCode.INVALID_INPUT: (422,'invalid_request'),
        ErrorCode.HACKATHON_NOT_FOUND: (404,'hackathon_not_found'),
        ErrorCode.ALREADY_ASSIGNED: (409,'already_assigned'),
        ErrorCode.IDEMPOTENCY_MISMATCH: (409,'idempotency_mismatch'),
        ErrorCode.OUTCOME_UNCERTAIN: (503,'outcome_uncertain')}.get(code,(503,'service_unavailable'))
    assert (r.status_code,r.json()['error']['code']) == expected
    assert r.json()['error']['retryable'] == (code in (ErrorCode.OUTCOME_UNCERTAIN,
        ErrorCode.TRANSACTION_CONFLICT, ErrorCode.TRANSACTION_DEADLINE, ErrorCode.LOCK_TIMEOUT))
    if code == ErrorCode.OUTCOME_UNCERTAIN:
        assert 'SAME Idempotency-Key' in r.json()['error']['message']
    assert 'offline-key' not in r.text+caplog.text
    assert_private(r)


def test_unexpected_failure_or_bad_reply_is_sanitized(creation, caplog):
    for failure, result in [(RuntimeError('private-driver-detail'), None), (None, {'password': 'private-value'})]:
        creation.service.create_team_idempotent.side_effect = failure
        creation.service.create_team_idempotent.return_value = result
        r = post(creation)
        assert r.status_code == 503 and 'private-' not in r.text+caplog.text
        assert encode_token(creation.api.issued.session_token.get_secret_value()) not in r.text+caplog.text


def test_replay_returns_stored_snapshot_without_read_service(creation):
    first, second = post(creation), post(creation)
    assert first.status_code == second.status_code == 201
    assert first.content == second.content and first.json() == creation.body
    assert dict(first.headers) == dict(second.headers)
    assert creation.api.app.state.read_service is None and creation.api.app.state.auth_engine is None
    creation.api.services.throttle.check.assert_not_called()
    creation.service.create_team.assert_not_called()
    creation.service.join_team_idempotent.assert_not_called()


def test_production_https_and_no_cors_preflight(creation):
    r = creation.api.client.post('http://merge.example'+creation.path, headers=creation.headers, json={'name': 'Team'})
    assert r.status_code == 403 and r.json()['error']['code'] == 'https_required'
    r = creation.api.client.options(creation.path, headers={'Origin': ORIGIN, 'Access-Control-Request-Method': 'POST'})
    assert r.status_code == 405 and 'access-control-allow-origin' not in r.headers
    assert not creation.service.mock_calls


def test_authorization_header_is_never_actor_proof(creation):
    d = creation
    forged = {'Authorization': 'Bearer private-untrusted-token'}
    r = post(d, headers={**d.headers, **forged})
    assert r.status_code == 201
    assert d.service.create_team_idempotent.call_args.kwargs['actor_id'] == d.api.issued.principal.user_id
    d.service.reset_mock()
    d.api.client.cookies.clear()
    r = post(d, headers={**d.headers, **forged})
    assert r.status_code == 401 and not d.service.mock_calls


def test_lazy_mutation_dependency_reuses_engine_without_connecting():
    engine = MagicMock(spec=Engine)
    state = SimpleNamespace(auth_lock=Lock(), auth_engine=engine)
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    service = get_team_service(request, auth=None)
    assert service._engine is engine
    engine.connect.assert_not_called()
    state.auth_engine = None
    with pytest.raises(DomainError) as caught: get_team_service(request, auth=None)
    assert caught.value.code == ErrorCode.TRANSACTION_CONFIGURATION


def test_openapi_has_only_scoped_domain_mutations_with_required_keys(creation):
    schema = creation.api.client.get('/openapi.json').json()
    paths = schema['paths']
    mutations = [(path,method) for path,operations in paths.items() if path.startswith('/api/')
                 for method in operations if method != 'get']
    base='/api/hackathons/{hackathon_id}/teams'
    assert mutations == [(base,'post'),(base+'/{team_id}/join-requests','post'),
        (base+'/{team_id}/join-requests/{request_id}/decision','post'),
        (base+'/{team_id}/invitations','post'),
        (base+'/{team_id}/invitations/{invitation_id}/redeem','post'),
        (base+'/{team_id}/leave','post'),
        (base+'/{team_id}/members/{user_id}/remove','post'),
        ('/api/me/profile','post')]
    for path,method in mutations:
        if path == '/api/me/profile':
            # Own-profile replacement is versioned, not a team command.
            assert not any(p['name']=='Idempotency-Key' for p in paths[path][method].get('parameters',[]))
            assert {'skills','timezone','discoverable','version'} <= set(schema['components']['schemas']['ProfileBody']['required'])
            continue
        assert next(p for p in paths[path][method]['parameters'] if p['name']=='Idempotency-Key')['required']
    operation = paths[mutations[0][0]]['post']
    assert next(p for p in operation['parameters'] if p['name'] == 'Idempotency-Key')['required']
    assert {'201','401','403','404','409','415','422','503'} <= set(operation['responses'])


def test_guarded_http_fixture_wires_real_facades_offline_without_settings(monkeypatch):
    from team_api_tests.conftest import client as guarded_client
    from app.services.credentials import CredentialService
    from app.services.sessions import SessionService
    from app.services.team_reads import TeamReadService
    import app.core.config
    import app.db.session
    def forbidden(*args, **kwargs):
        pytest.fail('Ordinary Settings or database connection attempted')
    monkeypatch.setattr(app.core.config, 'Settings', forbidden)
    monkeypatch.setattr(app.db.session, 'build_engine', forbidden)
    engine = MagicMock(spec=Engine)
    engine.connect.side_effect = forbidden
    engine.hide_parameters = True
    engine.echo = False
    env = SimpleNamespace(engine=engine, service=MagicMock(spec=CredentialService),
        sessions=MagicMock(spec=SessionService), reads=MagicMock(spec=TeamReadService),
        teams=MagicMock(spec=TeamService))
    fixture = guarded_client.__wrapped__(env)
    client = next(fixture)
    try:
        r = client.post(f'/api/hackathons/{uuid4()}/teams', headers={
            'Origin': ORIGIN, 'Idempotency-Key': 'key'}, json={'name': 'Team'})
        assert r.status_code == 401
        env.teams.create_team_idempotent.assert_not_called()
        engine.connect.assert_not_called()
    finally:
        with pytest.raises(StopIteration): next(fixture)


def test_guarded_suite_refuses_direct_execution_before_connections(monkeypatch):
    from team_api_tests.conftest import environment
    import team_api_tests.conftest as guarded
    monkeypatch.setattr(guarded.TeamApiEnvironment, 'connection',
                        lambda *args: pytest.fail('Connection attempted'))
    config = SimpleNamespace(getoption=lambda name: True)
    generator = environment.__wrapped__(SimpleNamespace(config=config), repetition=0)
    with pytest.raises(pytest.fail.Exception, match='Use guarded --suite team-api'):
        next(generator)


def test_real_guarded_account_fixture_satisfies_credential_and_http_rules(monkeypatch):
    from uuid import UUID
    from app.auth import LoginBody, RegisterBody
    from app.services import credentials
    from session_tests import conftest as session_fixtures
    from team_api_tests import conftest as team_fixtures
    from test_credentials import Connection, service

    # Pin public fixture entropy, never use a retained account or private secret.
    monkeypatch.setattr(team_fixtures, 'uuid4', lambda: UUID('01234567-89ab-cdef-0123-456789abcdef'))
    phrase = 'synthetic fixture regression passphrase'
    def fixture_password(size):
        assert size == 32
        return phrase
    monkeypatch.setattr(session_fixtures.secrets, 'token_urlsafe', fixture_password)
    connection = Connection()  # Existing in-memory SQL/transaction double only.
    credential_service = service(connection)
    hasher = MagicMock(return_value='synthetic-hash')
    verifier = MagicMock(return_value=True)
    monkeypatch.setattr(credentials._PASSWORDS, 'hash', hasher)
    monkeypatch.setattr(credentials._PASSWORDS, 'verify', verifier)
    environment = SimpleNamespace(service=credential_service,
                                  username=team_fixtures.TeamApiEnvironment.username)

    # Execute the exact imported account fixture, with real registration validation.
    identity, password = session_fixtures.account.__wrapped__(environment)
    assert credentials.valid_username(identity.username) and 3 <= len(identity.username) <= 32
    assert password == phrase and connection.closed and connection.committed
    hasher.assert_called_once_with(phrase)
    assert any('INSERT INTO public.account_credentials' in q for q in connection.statements)
    registration = RegisterBody(username=identity.username, password=password)
    login = LoginBody(username=identity.username, password=password)
    assert registration.username == login.username == identity.username

    # Public verification and session login's private verification path both
    # receive this same username/password; no validation function is replaced.
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    connection.record = SimpleNamespace(user_id=identity.user_id, username=identity.username,
        password_hash='synthetic-hash', created_at=now, updated_at=now)
    assert credential_service.verify_credentials(username=identity.username, password=password) == identity
    assert credential_service._verify_for_session(username=identity.username, password=password).identity == identity
    assert verifier.call_count == 2
    verifier.assert_called_with('synthetic-hash', phrase)


def test_previous_33_character_fixture_name_still_fails_before_hash_or_sql(monkeypatch):
    from app.services import credentials
    from app.services.credential_errors import CredentialCode, CredentialError
    from test_credentials import Connection, service

    connection = Connection()
    credential_service = service(connection)
    bad_name = 'team_api_' + '0123456789abcdef01234567'
    assert len(bad_name) == 33 and not credentials.valid_username(bad_name)
    hasher = MagicMock(side_effect=AssertionError('Hashing must not run'))
    monkeypatch.setattr(credentials._PASSWORDS, 'hash', hasher)
    with pytest.raises(CredentialError) as caught:
        credential_service.register(username=bad_name, password='synthetic fixture regression passphrase')
    assert caught.value.code == CredentialCode.INVALID_INPUT
    hasher.assert_not_called()
    credential_service._engine.connect.assert_not_called()
    assert connection.statements == []
