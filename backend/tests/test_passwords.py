"""PYTEST_DONT_REWRITE: keep password/hash values out of assertion output."""
from threading import Barrier, Event, Thread
from types import SimpleNamespace

from argon2 import extract_parameters
from argon2.exceptions import HashingError
from argon2.low_level import Type
import pytest

from app.security import passwords
from app.services.credential_errors import CredentialCode, CredentialError

PHRASE = 'synthetic passphrase for unit tests'


@pytest.fixture(scope='module')
def codec():
    return passwords.PasswordCodec()


def test_real_argon2id_profile_salt_roundtrip_and_mismatch(codec):
    first, second = codec.hash(PHRASE), codec.hash(PHRASE)
    parameters = extract_parameters(first)
    assert (parameters.type, parameters.version, parameters.memory_cost,
            parameters.time_cost, parameters.parallelism, parameters.salt_len,
            parameters.hash_len) == (Type.ID, 19, 19456, 2, 1, 16, 32)
    assert first != PHRASE and first != second, 'Hashing/salting failed'
    assert codec.verify(first, PHRASE), 'Correct password rejected'
    assert not codec.verify(first, PHRASE + '!'), 'Wrong password accepted'


@pytest.mark.parametrize('kind', ['minimum', 'maximum', 'unicode', 'spaces', 'nul'])
def test_passwords_are_not_trimmed_normalized_or_truncated(codec, kind):
    phrase = {'minimum': 'x'*15, 'maximum': 'x'*128, 'unicode': '\u00e9'*15,
              'spaces': ' '*15, 'nul': 'x'*15 + '\x00'}[kind]
    encoded = codec.hash(phrase)
    assert codec.verify(encoded, phrase), 'Allowed passphrase rejected'
    if kind == 'spaces':
        assert not codec.verify(encoded, phrase + 'x'), 'Whitespace was lost'
    if kind == 'unicode':
        assert not codec.verify(encoded, 'e\u0301'*15), 'Implicit normalization'


@pytest.mark.parametrize('kind', ['short', 'long', 'none', 'bytes', 'surrogate'])
def test_invalid_password_policy_has_fixed_error(codec, kind):
    phrase = {'short': 'x'*14, 'long': 'x'*129, 'none': None,
              'bytes': b'x'*20, 'surrogate': '\ud800'*15}[kind]
    with pytest.raises(CredentialError) as error:
        codec.hash(phrase)
    assert str(error.value) == 'invalid_input'


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'cost', 'type'])
def test_missing_or_unsupported_hash_performs_one_dummy_verification(codec, monkeypatch, kind):
    actual = codec.hash(PHRASE)
    supplied = {'missing': None, 'malformed': '$argon2id$synthetic',
                'cost': actual.replace('m=19456', 'm=999999999'),
                'type': actual.replace('argon2id', 'argon2i')}[kind]
    original = codec._hasher.verify
    calls = []

    def verify(encoded, password):
        calls.append(encoded is codec._dummy_hash)
        return original(encoded, password)

    monkeypatch.setattr(codec, '_hasher', SimpleNamespace(verify=verify))
    assert not codec.verify(supplied, PHRASE), 'Invalid stored hash accepted'
    assert calls == [True], 'Dummy verification was bypassed'


def test_process_budget_is_shared_fail_fast_and_released(codec, monkeypatch):
    second_codec = passwords.PasswordCodec()
    entered = Barrier(3, timeout=5)
    release = Event()
    outcomes = []

    def blocked(password):
        entered.wait()
        if not release.wait(5):
            raise AssertionError('Work release deadline')
        return 'synthetic-result'

    monkeypatch.setattr(codec, '_hasher', SimpleNamespace(hash=blocked))

    def worker():
        try:
            codec.hash(PHRASE)
            outcomes.append('done')
        except Exception:
            outcomes.append('failure')

    threads = [Thread(target=worker, daemon=True) for _ in range(2)]
    try:
        for t in threads:
            t.start()
        entered.wait()
        with pytest.raises(CredentialError) as error:
            second_codec.hash(PHRASE)
        assert error.value.code == CredentialCode.HASHING_BUSY
    finally:
        release.set()
        for t in threads:
            t.join(6)
    assert not any(t.is_alive() for t in threads), 'Hash worker deadline'
    assert outcomes == ['done', 'done'], 'Hash worker failed'
    assert second_codec.verify(second_codec.hash(PHRASE), PHRASE), 'Slots not released'


def test_native_failure_is_sanitized_and_does_not_consume_slot(codec, monkeypatch):
    def fail(password):
        raise HashingError('synthetic-sensitive-detail')

    with monkeypatch.context() as m:
        m.setattr(codec, '_hasher', SimpleNamespace(hash=fail))
        with pytest.raises(CredentialError) as error:
            codec.hash(PHRASE)
        assert str(error.value) == 'hashing_failure'
        assert error.value.__suppress_context__
        assert error.value.__context__ is None
    assert codec.verify(codec.hash(PHRASE), PHRASE)
