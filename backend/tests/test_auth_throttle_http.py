"""PYTEST_DONT_REWRITE: adapter failure/privacy checks; PostgreSQL proofs are separate."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from test_auth_http import api, HEADERS, BODY, login
from app.main import create_app
from app.security.auth_policy import AuthSettings
from app.services.credential_errors import CredentialCode, CredentialError
from app.services.throttling import ThrottleExceeded
from app import serve


@pytest.mark.parametrize('path', ['/auth/register', '/auth/login'])
def test_429_before_authentication_with_bounded_retry(api, path, caplog):
    api.services.throttle.check.side_effect = ThrottleExceeded(299)
    r = api.client.post(path, headers=HEADERS, json=BODY)
    assert r.status_code == 429 and r.headers['retry-after'] == '299'
    assert r.json() == {'error': {'code': 'rate_limited', 'message': 'Too many authentication attempts.', 'retryable': True}}
    assert r.headers['cache-control'] == 'no-store, private'
    api.services.sessions.login.assert_not_called()
    api.services.credentials.register.assert_not_called()
    assert BODY['password'] not in r.text+caplog.text
    assert '192.0.2.1' not in r.text+caplog.text


@pytest.mark.parametrize('code', [CredentialCode.DATABASE_FAILURE, CredentialCode.INTEGRITY_FAULT,
                                 CredentialCode.LOCK_TIMEOUT, CredentialCode.TRANSACTION_CONFIGURATION])
@pytest.mark.parametrize('path', ['/auth/register', '/auth/login'])
def test_storage_fault_never_bypasses_throttle(api, path, code):
    api.services.throttle.check.side_effect = CredentialError(code)
    r = api.client.post(path, headers=HEADERS, json=BODY)
    assert r.status_code == 503 and r.json()['error']['code'] == 'service_unavailable'
    assert 'retry-after' not in r.headers
    api.services.sessions.login.assert_not_called()
    api.services.credentials.register.assert_not_called()


def test_throttle_called_with_only_server_ip_and_canonical_account(api):
    assert login(api).status_code == 200
    api.services.throttle.check.assert_called_once_with(operation='login', client_ip='192.0.2.1', username=BODY['username'])


@pytest.mark.parametrize('header', ['X-Forwarded-For', 'X-Forwarded-Proto', 'Forwarded', 'X-Real-IP'])
def test_untrusted_forwarding_rejected_before_kdf_or_counters(api, header):
    r = api.client.post('/auth/login', headers={**HEADERS, header: '198.51.100.1'}, json=BODY)
    assert r.status_code == 403 and r.json()['error']['code'] == 'client_identity_rejected'
    api.services.throttle.check.assert_not_called()
    api.services.sessions.login.assert_not_called()


@pytest.mark.parametrize('change', [{'throttle_secret': ''}, {'throttle_secret': 'a'*63},
                                   {'throttle_secret': 'z'*64}, {'login_ip_limit': 0},
                                   {'login_ip_limit': 501}, {'login_account_limit': 101},
                                   {'register_ip_limit': 51}, {'throttle_window_seconds': 59},
                                   {'throttle_window_seconds': 3601}, {'trusted_proxies': ('0.0.0.0/0',)},
                                   {'trusted_proxies': ('*',)}, {'trusted_proxies': ('127.0.0.1%zone',)},
                                   {'trusted_proxies': ('::ffff:0.0.0.0/96',)}])
def test_unsafe_throttle_settings_rejected(change):
    values = {'origin': 'https://merge.example', 'throttle_secret': 'a'*64, **change}
    with pytest.raises(ValidationError): AuthSettings(**values)


def test_missing_shared_secret_fails_startup(monkeypatch):
    monkeypatch.setenv('MERGE_AUTH_ORIGIN', 'https://merge.example')
    monkeypatch.delenv('MERGE_AUTH_THROTTLE_SECRET', raising=False)
    with pytest.raises(RuntimeError, match='Invalid authentication configuration'):
        with TestClient(create_app()): pass


def test_shared_secret_not_in_policy_repr():
    settings = AuthSettings(origin='https://merge.example', throttle_secret='a'*64)
    assert 'a'*64 not in repr(settings) and 'a'*64 not in str(settings)


def test_controlled_server_preserves_actual_peer(monkeypatch):
    run = MagicMock()
    monkeypatch.setattr('sys.argv', ['serve', '--workers', '2'])
    monkeypatch.setattr(serve.uvicorn, 'run', run)
    monkeypatch.setenv('FORWARDED_ALLOW_IPS', '*')
    monkeypatch.setenv('UVICORN_PROXY_HEADERS', 'true')
    serve.main()
    assert run.call_args.kwargs['proxy_headers'] is False
    assert run.call_args.kwargs['forwarded_allow_ips'] == ''
    assert run.call_args.kwargs['access_log'] is False
