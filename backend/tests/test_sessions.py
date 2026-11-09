"""PYTEST_DONT_REWRITE: no token/hash values in assertion introspection."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.services import credentials, sessions
from app.services.credential_errors import CredentialCode, CredentialError
from app.services.session_errors import SessionCode, SessionError

PHRASE = 'synthetic session unit passphrase'


@pytest.fixture(scope='module')
def encoded():
    return credentials._PASSWORDS.hash(PHRASE)


class Connection:
    def __init__(self, encoded):
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.clock = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
        self.account = SimpleNamespace(user_id=uuid4(), username='unit_user', password_hash=encoded,
                                       created_at=self.clock, updated_at=self.clock)
        self.current = self.account
        self.user_exists = True
        self.active = self.closed = self.committed = self.rolled_back = False
        self.statements, self.parameters, self.store = [], [], {}
        self.fail_insert = self.fail_commit = False

    def get_isolation_level(self):
        return 'READ COMMITTED'

    def in_transaction(self):
        return self.active

    @contextmanager
    def begin(self):
        before = deepcopy(self.store)
        self.active = True
        try:
            yield
            if self.fail_commit:
                self.failure()
            self.committed = True
        except Exception:
            self.store = before
            self.rolled_back = True
            raise
        finally:
            self.active = False

    @staticmethod
    def failure():
        original = RuntimeError('synthetic-driver-detail')
        original.sqlstate = '23514'
        original.diag = SimpleNamespace(constraint_name='unexpected_test_check')
        raise IntegrityError('synthetic SQL', {}, original)

    def execute(self, statement, values):
        q = str(statement)
        self.statements.append(q)
        self.parameters.append(values)
        row = None
        if 'FROM public.account_credentials' in q:
            row = self.current if 'FOR SHARE' in q else self.account
        elif 'FROM public.users' in q:
            row = SimpleNamespace(id=self.account.user_id) if self.user_exists else None
        elif 'SELECT clock_timestamp()' in q:
            return SimpleNamespace(scalar_one=lambda: self.clock)
        elif 'INSERT INTO public.auth_sessions' in q:
            self.store[values['digest']] = SimpleNamespace(user_id=values['u'],
                username=self.account.username, password_hash=self.account.password_hash,
                csrf_token=values['csrf'], created_at=values['created'], expires_at=values['expires'], revoked_at=None)
            if self.fail_insert:
                self.failure()
        elif 'FROM public.auth_sessions s' in q:
            row = deepcopy(self.store.get(values['digest']))
            if row is not None:
                row.checked_at = self.clock
                if not self.user_exists or self.current is None:
                    row = None
                else:
                    row.password_hash = self.current.password_hash
        elif 'UPDATE public.auth_sessions' in q:
            stored = self.store.get(values['digest'])
            if stored is not None and stored.revoked_at is None:
                stored.revoked_at = max(self.clock, stored.created_at)
        return SimpleNamespace(one_or_none=lambda: row)


@pytest.fixture
def setup(encoded, monkeypatch):
    c = Connection(encoded)
    engine = MagicMock(spec=Engine)
    engine.hide_parameters, engine.echo = True, False

    @contextmanager
    def connect():
        c.closed = False
        try:
            yield c
        finally:
            c.closed = True

    engine.connect.side_effect = connect
    original = credentials._PASSWORDS.verify

    def verify(value, password):
        assert c.closed and not c.active, 'Database transaction during Argon2'
        return original(value, password)

    monkeypatch.setattr(credentials._PASSWORDS, 'verify', verify)
    return sessions.SessionService(engine), c, engine


def login(service):
    return service.login(username='unit_user', password=PHRASE)


def raw(material):
    return material.session_token.get_secret_value()


def test_login_commits_exactly_one_digest_and_independent_secrets(setup, monkeypatch):
    s, c, engine = setup
    original = sessions.secrets.token_bytes
    calls = []

    def random_bytes(length):
        assert not c.active and c.closed
        calls.append(length)
        return original(length)

    monkeypatch.setattr(sessions.secrets, 'token_bytes', random_bytes)
    material = login(s)
    token, csrf = raw(material), material.csrf_token.get_secret_value()
    digest = sessions.sha256(token).digest()
    assert c.closed and c.committed and len(c.store) == 1
    assert calls == [32, 32] and len(token) == len(csrf) == 32
    assert token != csrf and digest in c.store
    assert all(token != value for params in c.parameters for value in params.values()), 'Raw token reached SQL'
    assert material.principal.expires_at - material.created_at == timedelta(hours=8)
    assert material.created_at.tzinfo is timezone.utc
    assert s.validate(token).user_id == c.account.user_id
    assert s.verify_csrf(token, csrf) == material.principal
    sql = '\n'.join(c.statements)
    assert sql.index('FROM public.users') < sql.index('FOR SHARE') < sql.index('INSERT INTO public.auth_sessions')


def test_sensitive_result_and_errors_do_not_represent_tokens(setup):
    s, c, engine = setup
    m = login(s)
    rendered = (repr(m) + str(m) + repr(m.session_token) + str(m.csrf_token)).encode()
    assert raw(m) not in rendered and m.csrf_token.get_secret_value() not in rendered
    with pytest.raises(SessionError) as error:
        s.validate(b'synthetic-invalid')
    assert error.value.args == ('invalid_session',)


def test_no_uuid_or_constructible_credential_identity_issuance_input(setup):
    s, c, engine = setup
    fake = credentials.CredentialIdentity(uuid4(), 'unit_user')
    for supplied in (uuid4(), fake):
        with pytest.raises(TypeError):
            s.login(identity=supplied)
    assert not hasattr(s, 'issue')
    engine.connect.assert_not_called()


def test_unknown_uncredentialed_user_and_wrong_password_cannot_issue(setup):
    s, c, engine = setup
    with pytest.raises(CredentialError) as wrong:
        s.login(username='unit_user', password=PHRASE + '!')
    c.account = None
    with pytest.raises(CredentialError) as unknown:
        login(s)
    assert wrong.value.code == unknown.value.code == CredentialCode.INVALID_CREDENTIALS
    assert not c.store


@pytest.mark.parametrize('change', ['user_missing', 'credential_missing', 'hash', 'username', 'created', 'updated', 'identity'])
def test_issuance_rechecks_verified_snapshot_under_credential_share_lock(setup, change):
    s, c, engine = setup
    current = deepcopy(c.account)
    if change == 'user_missing': c.user_exists = False
    elif change == 'credential_missing': current = None
    elif change == 'hash': current.password_hash = '$argon2id$synthetic-changed'
    elif change == 'username': current.username = 'other_name'
    elif change == 'created': current.created_at += timedelta(seconds=1)
    elif change == 'updated': current.updated_at += timedelta(seconds=1)
    else: current.user_id = uuid4()
    c.current = current
    with pytest.raises(SessionError) as error:
        login(s)
    assert error.value.code == SessionCode.AUTHENTICATION_CHANGED
    assert c.rolled_back and not c.store
    assert not any('INSERT INTO public.auth_sessions' in q for q in c.statements)
    assert any('FOR SHARE' in q for q in c.statements)


@pytest.mark.parametrize('kind', ['expired', 'revoked', 'unknown', 'future', 'missing_user', 'missing_credential', 'invalid_credential'])
def test_invalid_stored_sessions_fail_closed_without_renewal(setup, kind):
    s, c, engine = setup
    material = login(s)
    token = raw(material)
    stored = c.store[sessions.sha256(token).digest()]
    expiry = stored.expires_at
    if kind == 'expired': c.clock = expiry
    elif kind == 'revoked': stored.revoked_at = c.clock
    elif kind == 'unknown': c.store.clear()
    elif kind == 'future': c.clock -= timedelta(seconds=1)
    elif kind == 'missing_user': c.user_exists = False
    elif kind == 'missing_credential': c.current = None
    else: c.current.password_hash = '$argon2id$synthetic-invalid'
    with pytest.raises(SessionError) as error:
        s.validate(token)
    assert error.value.code == SessionCode.INVALID_SESSION
    assert stored.expires_at == expiry
    if kind == 'expired':
        c.clock += timedelta(hours=1)
        with pytest.raises(SessionError): s.validate(token)
        assert stored.expires_at == expiry


@pytest.mark.parametrize('kind', ['none', 'text', 'short', 'long', 'mutable'])
@pytest.mark.parametrize('operation', ['validate', 'revoke'])
def test_malformed_token_rejected_before_database(setup, kind, operation):
    s, c, engine = setup
    supplied = {'none': None, 'text': 'x'*32, 'short': b'x'*31,
                'long': b'x'*33, 'mutable': bytearray(32)}[kind]
    with pytest.raises(SessionError): getattr(s, operation)(supplied)
    engine.connect.assert_not_called()


def test_cross_session_csrf_rejection_and_constant_time_primitive(setup, monkeypatch):
    s, c, engine = setup
    first, second = login(s), login(s)
    assert raw(first) != raw(second), 'Issuance reused bearer token'
    original = sessions.secrets.compare_digest
    calls = []

    def compare(a, b):
        calls.append((len(a), len(b)))
        return original(a, b)

    monkeypatch.setattr(sessions.secrets, 'compare_digest', compare)
    with pytest.raises(SessionError) as error:
        s.verify_csrf(raw(first), second.csrf_token.get_secret_value())
    assert error.value.code == SessionCode.INVALID_CSRF and calls == [(32, 32)]
    assert s.verify_csrf(raw(first), first.csrf_token.get_secret_value()) == first.principal


def test_revoke_is_terminal_repeat_safe_and_unknown_is_noop(setup):
    s, c, engine = setup
    m = login(s)
    s.revoke(raw(m))
    stored = c.store[sessions.sha256(raw(m)).digest()]
    stamp = stored.revoked_at
    c.clock += timedelta(seconds=1)
    s.revoke(raw(m))
    s.revoke(b'x'*32)
    assert stored.revoked_at == stamp and len(c.store) == 1
    with pytest.raises(SessionError): s.validate(raw(m))
    assert all('revoked_at IS NULL' in q for q in c.statements if 'UPDATE' in q)


@pytest.mark.parametrize('phase', ['insert', 'commit'])
def test_failure_after_issuance_mutation_rolls_back_and_detaches_driver_error(setup, phase):
    s, c, engine = setup
    c.fail_insert = phase == 'insert'
    c.fail_commit = phase == 'commit'
    # Fail COMMIT only for the write, not the earlier approved read verification.
    if c.fail_commit:
        original = c.failure
        c.failure = lambda: original() if c.store else None
    with pytest.raises(CredentialError) as error:
        login(s)
    assert c.rolled_back and not c.store
    assert error.value.code == CredentialCode.INTEGRITY_FAULT and error.value.__context__ is None


@pytest.mark.parametrize('state', [True, None, 0, 'False'])
@pytest.mark.parametrize('operation', ['login', 'validate', 'revoke'])
def test_actual_autocommit_or_ambiguous_driver_rejected_before_sql(setup, state, operation):
    s, c, engine = setup
    c.connection.dbapi_connection.autocommit = state
    c.get_isolation_level = lambda: pytest.fail('Isolation metadata before AUTOCOMMIT rejection')
    with pytest.raises(CredentialError) as error:
        login(s) if operation == 'login' else getattr(s, operation)(b'x'*32)
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION and not c.statements


def test_naive_database_clock_and_entropy_failure_fail_closed(setup, monkeypatch):
    s, c, engine = setup
    c.clock = c.clock.replace(tzinfo=None)
    with pytest.raises(SessionError) as error:
        login(s)
    assert error.value.code == SessionCode.CLOCK_CONFIGURATION and not c.store
    c.clock = c.clock.replace(tzinfo=timezone.utc)

    def fail(n): raise OSError('synthetic-entropy-detail')

    monkeypatch.setattr(sessions.secrets, 'token_bytes', fail)
    with pytest.raises(SessionError) as error: login(s)
    assert error.value.code == SessionCode.ENTROPY_FAILURE and error.value.__context__ is None
    assert not c.store
