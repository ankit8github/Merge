"""PYTEST_DONT_REWRITE: real guarded PostgreSQL tests; never dump password/hash values."""
import secrets
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.services.credentials import CredentialService
from app.services.credential_errors import CredentialCode, CredentialError
from test_support.races import Outcome, sql, workers


def test_registration_commits_one_user_and_credential(environment, password):
    env = environment
    name = env.username()
    result = env.service.register(username=name, password=password)
    assert result.username == name
    assert env.counts() == (1, 1)
    with env.connection() as c:
        assert sql(c, 'SELECT user_id FROM public.account_credentials WHERE username=:n', n=name).scalar_one() == result.user_id


@pytest.mark.parametrize('kind', ['username', 'unicode', 'short_password', 'long_password', 'display_name', 'surrogate'])
def test_invalid_registration_has_zero_writes(environment, password, kind):
    env = environment
    args = dict(username=env.username(), password=password)
    if kind == 'username': args['username'] = 'Uppercase'
    elif kind == 'unicode': args['username'] = '\u00e9'*4
    elif kind == 'short_password': args['password'] = 'x'*14
    elif kind == 'long_password': args['password'] = 'x'*129
    elif kind == 'display_name': args['display_name'] = ' '
    else: args['password'] = '\ud800'*15
    with pytest.raises(CredentialError) as error:
        env.service.register(**args)
    assert error.value.code == CredentialCode.INVALID_INPUT
    assert env.counts() == (0, 0)


def test_duplicate_username_rolls_back_new_user(environment, password):
    env = environment
    name = env.username()
    env.service.register(username=name, password=password)
    with pytest.raises(CredentialError) as error:
        env.service.register(username=name, password=password)
    assert error.value.code == CredentialCode.USERNAME_UNAVAILABLE
    assert env.counts() == (1, 1)
    assert env.states == [('23505', 'uq_credentials_username')]


def test_concurrent_duplicate_username_has_one_committed_account(environment, password):
    env = environment
    name = env.username()
    gate = Barrier(2, timeout=8)

    def overlap(c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.account_credentials' in statement:
            # Both transactions have inserted their private user before either
            # attempts the unique username insert. No sleep-based race proof.
            gate.wait()

    def register():
        try:
            env.service.register(username=name, password=password)
            return Outcome('committed')
        except CredentialError as error:
            if error.code != CredentialCode.USERNAME_UNAVAILABLE:
                raise
            return Outcome('rejected', '23505', 'uq_credentials_username')

    event.listen(env.engine, 'before_cursor_execute', overlap)
    try:
        outcomes = workers([register, register])
    finally:
        event.remove(env.engine, 'before_cursor_execute', overlap)
    assert sorted(x.status for x in outcomes) == ['committed', 'rejected']
    assert env.states == [('23505', 'uq_credentials_username')]
    assert env.counts() == (1, 1), 'Failed competitor left a user or credential'
    print('Observed expected PostgreSQL username conflict: 23505 / uq_credentials_username')


@pytest.mark.parametrize('stage', ['after_user', 'after_credential', 'commit'])
def test_injected_failure_rolls_back_all_writes(environment, password, stage):
    env = environment
    name = env.username()

    def after(c, cursor, statement, parameters, context, many):
        target = 'INSERT INTO public.users' if stage == 'after_user' else 'INSERT INTO public.account_credentials'
        if target in statement:
            raise RuntimeError('Injected credential failure')

    def commit(c):
        raise RuntimeError('Injected credential failure')

    label, listener = ('commit', commit) if stage == 'commit' else ('after_cursor_execute', after)
    event.listen(env.engine, label, listener)
    try:
        with pytest.raises(RuntimeError, match='^Injected credential failure$'):
            env.service.register(username=name, password=password)
    finally:
        event.remove(env.engine, label, listener)
    assert len(env.ids) == 1, 'Failure injection did not reach user mutation'
    assert env.counts() == (0, 0)


def test_existing_user_with_same_display_name_is_not_claimed(environment, password):
    env = environment
    seeded, name = uuid4(), env.username()
    env.ids.add(seeded)
    with env.connection() as c:
        sql(c, 'INSERT INTO public.users(id,display_name) VALUES (:id,:name)', id=seeded, name=name)
        c.commit()
    result = env.service.register(username=name, password=password, display_name=name)
    assert result.user_id != seeded
    with env.connection() as c:
        assert sql(c, 'SELECT count(*) FROM public.account_credentials WHERE user_id=:id', id=seeded).scalar_one() == 0
        assert sql(c, 'SELECT display_name FROM public.users WHERE id=:id', id=seeded).scalar_one() == name
    assert env.counts() == (2, 1)


def test_successful_verification_preserves_hash_and_creates_no_session(environment, password):
    env = environment
    identity = env.service.register(username=env.username(), password=password)
    with env.connection() as c:
        stored = sql(c, 'SELECT password_hash FROM public.account_credentials WHERE user_id=:u', u=identity.user_id).scalar_one()
    assert stored != password and stored.startswith('$argon2id$v=19$'), 'Password storage failed'
    assert env.service.verify_credentials(username=identity.username, password=password) == identity
    with env.connection() as c:
        after = sql(c, 'SELECT password_hash FROM public.account_credentials WHERE user_id=:u', u=identity.user_id).scalar_one()
    assert stored == after, 'Verification rewrote the credential'
    assert env.counts() == (1, 1)


def test_wrong_password_and_unknown_user_have_identical_public_error(environment, password):
    env = environment
    identity = env.service.register(username=env.username(), password=password)
    errors = []
    for name, phrase in [(identity.username, secrets.token_urlsafe(32)), (env.username(), password)]:
        with pytest.raises(CredentialError) as error:
            env.service.verify_credentials(username=name, password=phrase)
        errors.append((error.value.code, error.value.args, error.value.retryable))
    assert errors == [(CredentialCode.INVALID_CREDENTIALS, ('invalid_credentials',), False)]*2
    assert env.counts() == (1, 1)


def test_real_autocommit_is_rejected_before_any_domain_statement(environment, password):
    env = environment
    unsafe = env.engine.execution_options(isolation_level='AUTOCOMMIT')
    statements, actual = [], []

    def observe(c, cursor, statement, parameters, context, many):
        if statement.startswith('SET LOCAL') or 'INSERT INTO public.' in statement or 'FROM public.account_credentials' in statement:
            statements.append('unexpected-domain-sql')

    def state(c):
        actual.append(c.connection.dbapi_connection.autocommit)

    event.listen(unsafe, 'engine_connect', state)
    event.listen(unsafe, 'before_cursor_execute', observe)
    try:
        with pytest.raises(CredentialError) as error:
            CredentialService(unsafe).register(username=env.username(), password=password)
        assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    finally:
        event.remove(unsafe, 'before_cursor_execute', observe)
        event.remove(unsafe, 'engine_connect', state)
    assert actual == [True], 'Test did not observe actual DBAPI AUTOCOMMIT'
    assert statements == [] and env.counts() == (0, 0)
    with env.engine.connect() as c:
        assert c.connection.dbapi_connection.autocommit is False


def test_malformed_stored_hash_fails_closed_without_rewrite(environment, password):
    env = environment
    identity = env.service.register(username=env.username(), password=password)
    with env.connection() as c:
        sql(c, "UPDATE public.account_credentials SET password_hash='$argon2id$synthetic-invalid-encoding' WHERE user_id=:u", u=identity.user_id)
        c.commit()
    with pytest.raises(CredentialError) as error:
        env.service.verify_credentials(username=identity.username, password=password)
    assert error.value.code == CredentialCode.INVALID_CREDENTIALS
    with env.connection() as c:
        assert sql(c, "SELECT password_hash='$argon2id$synthetic-invalid-encoding' FROM public.account_credentials WHERE user_id=:u", u=identity.user_id).scalar_one()
    assert env.counts() == (1, 1)
