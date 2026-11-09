"""PYTEST_DONT_REWRITE: database-free ownership tests, no secret assertion dumps."""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.services import credentials as module
from app.services.credential_errors import CredentialCode, CredentialError, credential_database_error

PHRASE = 'synthetic registration unit passphrase'


def driver_error(state, constraint):
    original = RuntimeError('synthetic-sensitive-detail')
    original.sqlstate = state
    original.diag = SimpleNamespace(constraint_name=constraint)
    return IntegrityError('synthetic SQL', {}, original)


class Connection:
    def __init__(self):
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.statements = []
        self.active = self.closed = self.committed = self.rolled_back = False
        self.record = None
        self.failure = None
        self.commit_failure = None

    def get_isolation_level(self):
        return 'READ COMMITTED'

    def in_transaction(self):
        return self.active

    @contextmanager
    def begin(self):
        self.active = True
        try:
            yield
            if self.commit_failure:
                raise self.commit_failure
            self.committed = True
        except Exception:
            self.rolled_back = True
            raise
        finally:
            self.active = False

    def execute(self, statement, values):
        query = str(statement)
        self.statements.append(query)
        if 'INSERT INTO public.account_credentials' in query and self.failure:
            raise self.failure
        return SimpleNamespace(one_or_none=lambda: self.record)


def service(c):
    engine = MagicMock(spec=Engine)
    engine.hide_parameters = True
    engine.echo = False

    @contextmanager
    def connect():
        c.closed = False
        try:
            yield c
        finally:
            c.closed = True

    engine.connect.side_effect = connect
    return module.CredentialService(engine)


def test_registration_hashes_before_connection_and_returns_after_commit(monkeypatch):
    c = Connection()
    s = service(c)

    def hash_password(password):
        s._engine.connect.assert_not_called()
        assert not c.active
        return 'synthetic-hash-result'

    monkeypatch.setattr(module._PASSWORDS, 'hash', hash_password)
    result = s.register(username='test_name', password=PHRASE)
    assert c.closed and c.committed
    assert result.username == 'test_name'
    assert 'INSERT INTO public.users' in c.statements[2]
    assert 'INSERT INTO public.account_credentials' in c.statements[3]
    assert not any('SELECT' in q for q in c.statements), 'Check-then-insert introduced'
    with pytest.raises(FrozenInstanceError):
        result.username = 'changed'


@pytest.mark.parametrize('kind', ['uppercase', 'short_name', 'long_name', 'unicode_name',
                                  'newline_name', 'short_password', 'long_password',
                                  'empty_display', 'long_display', 'nul_display', 'surrogate'])
def test_invalid_registration_never_hashes_or_connects(monkeypatch, kind):
    c = Connection()
    s = service(c)
    args = dict(username='valid_name', password=PHRASE)
    edits = {
        'uppercase': ('username', 'Uppercase'), 'short_name': ('username', 'ab'),
        'long_name': ('username', 'a'*33), 'unicode_name': ('username', '\u00e9'*4),
        'newline_name': ('username', 'abc\n'), 'short_password': ('password', 'x'*14),
        'long_password': ('password', 'x'*129), 'empty_display': ('display_name', ' '),
        'long_display': ('display_name', 'x'*81), 'nul_display': ('display_name', '\x00'),
        'surrogate': ('password', '\ud800'*15),
    }
    key, value = edits[kind]
    args[key] = value
    monkeypatch.setattr(module._PASSWORDS, 'hash', lambda *a: pytest.fail('Hash work reached'))
    with pytest.raises(CredentialError) as error:
        s.register(**args)
    assert error.value.code == CredentialCode.INVALID_INPUT
    s._engine.connect.assert_not_called()


@pytest.mark.parametrize('stage', ['statement', 'commit'])
def test_registration_rolls_back_before_safe_mapping(monkeypatch, stage):
    c = Connection()
    if stage == 'statement':
        c.failure = driver_error('23505', 'uq_credentials_username')
    else:
        c.commit_failure = driver_error('23514', 'unexpected_guard')
    monkeypatch.setattr(module._PASSWORDS, 'hash', lambda p: 'synthetic-hash-result')
    with pytest.raises(CredentialError) as error:
        service(c).register(username='valid_name', password=PHRASE)
    expected = CredentialCode.USERNAME_UNAVAILABLE if stage == 'statement' else CredentialCode.INTEGRITY_FAULT
    assert error.value.code == expected
    assert c.rolled_back and c.closed and not c.committed
    assert str(error.value) == expected.value
    assert error.value.__context__ is None


@pytest.mark.parametrize('kind', ['username', 'password'])
def test_invalid_verification_has_only_generic_error_without_lookup(kind):
    c = Connection()
    s = service(c)
    args = dict(username='valid_name', password=PHRASE)
    args[kind] = 'x'
    with pytest.raises(CredentialError) as error:
        s.verify_credentials(**args)
    assert error.value.args == ('invalid_credentials',)
    s._engine.connect.assert_not_called()


@pytest.mark.parametrize('state', [True, None, 0, 'False'])
def test_autocommit_and_ambiguous_states_rejected_before_service_sql(monkeypatch, state):
    c = Connection()
    c.connection.dbapi_connection.autocommit = state
    c.get_isolation_level = lambda: pytest.fail('Isolation query before autocommit guard')
    monkeypatch.setattr(module._PASSWORDS, 'hash', lambda p: 'synthetic-hash-result')
    with pytest.raises(CredentialError) as error:
        service(c).register(username='valid_name', password=PHRASE)
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    assert c.statements == [] and not c.committed


@pytest.mark.parametrize('kind', ['dialect', 'driver', 'async', 'missing_driver_state', 'isolation', 'active', 'unreadable'])
def test_unsupported_transaction_contract_fails_closed(monkeypatch, kind):
    c = Connection()
    if kind == 'dialect': c.dialect.name = 'sqlite'
    elif kind == 'driver': c.dialect.driver = 'other'
    elif kind == 'async': c.dialect.is_async = True
    elif kind == 'missing_driver_state': c.connection = object()
    elif kind == 'isolation': c.get_isolation_level = lambda: 'SERIALIZABLE'
    elif kind == 'active': c.active = True
    else: c.get_isolation_level = lambda: (_ for _ in ()).throw(RuntimeError('synthetic-sensitive-detail'))
    monkeypatch.setattr(module._PASSWORDS, 'hash', lambda p: 'synthetic-hash-result')
    with pytest.raises(CredentialError) as error:
        service(c).register(username='valid_name', password=PHRASE)
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    assert c.statements == []


@pytest.mark.parametrize('exists', [True, False])
def test_wrong_and_unknown_credentials_share_public_error_and_no_open_transaction(monkeypatch, exists):
    c = Connection()
    c.record = SimpleNamespace(user_id=uuid4(), username='valid_name', password_hash='synthetic-stored-value') if exists else None
    s = service(c)
    calls = []

    def verify(encoded, password):
        assert c.closed and not c.active, 'Database transaction held during hashing'
        calls.append(encoded is not None)
        return False

    monkeypatch.setattr(module._PASSWORDS, 'verify', verify)
    with pytest.raises(CredentialError) as error:
        s.verify_credentials(username='valid_name', password=PHRASE)
    assert error.value.args == ('invalid_credentials',)
    assert calls == [exists]
    assert c.statements[0] == 'SET TRANSACTION READ ONLY'
    assert not any('INSERT' in q or 'UPDATE' in q or 'FOR UPDATE' in q for q in c.statements)


def test_correct_credentials_return_identity_without_hash_write(monkeypatch):
    c = Connection()
    c.record = SimpleNamespace(user_id=uuid4(), username='valid_name', password_hash='synthetic-stored-value')
    monkeypatch.setattr(module._PASSWORDS, 'verify', lambda *a: True)
    result = service(c).verify_credentials(username='valid_name', password=PHRASE)
    assert result == module.CredentialIdentity(c.record.user_id, c.record.username)
    assert not any('UPDATE' in q for q in c.statements)


def test_no_caller_user_id_can_be_supplied():
    c = Connection()
    with pytest.raises(TypeError):
        service(c).register(username='valid_name', password=PHRASE, user_id=uuid4())
    assert not c.statements


@pytest.mark.parametrize(('state', 'constraint', 'expected'), [
    ('23505', 'uq_credentials_username', CredentialCode.USERNAME_UNAVAILABLE),
    ('23505', 'pk_users', CredentialCode.INTEGRITY_FAULT),
    ('23503', 'fk_credentials_user', CredentialCode.INTEGRITY_FAULT),
    ('40P01', None, CredentialCode.TRANSACTION_CONFLICT),
    ('40001', None, CredentialCode.TRANSACTION_CONFLICT),
    ('55P03', None, CredentialCode.LOCK_TIMEOUT),
    ('57014', None, CredentialCode.STATEMENT_TIMEOUT),
    ('08006', None, CredentialCode.DATABASE_FAILURE),
])
def test_auth_error_mapping_is_narrow_and_fixed(state, constraint, expected):
    error = credential_database_error(driver_error(state, constraint))
    assert error.code == expected and str(error) == expected.value


def test_engine_configuration_rejects_parameter_logging_and_debug_rows():
    for hide, echo in [(False, False), (True, True), (True, 'debug')]:
        engine = MagicMock(spec=Engine)
        engine.hide_parameters, engine.echo = hide, echo
        with pytest.raises(CredentialError):
            module.CredentialService(engine)
    with pytest.raises(TypeError):
        module.CredentialService(object())
