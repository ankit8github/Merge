"""PYTEST_DONT_REWRITE: real PostgreSQL lifecycle checks; never dump token material."""
from datetime import timedelta, timezone
from hashlib import sha256
from queue import Queue
import secrets
from threading import Barrier, Event
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.services import credentials
from app.services.credential_errors import CredentialCode, CredentialError
from app.services.sessions import SessionService
from app.services.session_errors import SessionCode, SessionError
from test_support.races import Outcome, sql, wait, workers


def login(env, account):
    identity, password = account
    return env.sessions.login(username=identity.username, password=password)


def token(material):
    return material.session_token.get_secret_value()


def stamp(env, material):
    with env.connection() as c:
        return sql(c, '''SELECT created_at,expires_at,revoked_at FROM public.auth_sessions
            WHERE token_hash=:digest''', digest=sha256(token(material)).digest()).one()


def seeded_session(env, account, age):
    identity, password = account
    raw, csrf = secrets.token_bytes(32), secrets.token_bytes(32)
    with env.connection() as c:
        created = sql(c, 'SELECT clock_timestamp()').scalar_one().astimezone(timezone.utc) - age
        sql(c, '''INSERT INTO public.auth_sessions(token_hash,user_id,csrf_token,created_at,expires_at)
            VALUES (:digest,:u,:csrf,:created,:expires)''', digest=sha256(raw).digest(), u=identity.user_id,
            csrf=csrf, created=created, expires=created+timedelta(hours=8))
        c.commit()
    return raw, csrf, created + timedelta(hours=8)


def test_verified_login_commits_one_session_usable_by_fresh_service(environment, account):
    env = environment
    material = login(env, account)
    assert env.session_count() == 1
    assert material.principal.user_id == account[0].user_id
    assert material.principal.expires_at-material.created_at == timedelta(hours=8)
    assert material.created_at.tzinfo is timezone.utc
    fresh_service = SessionService(env.engine)
    assert fresh_service.validate(token(material)) == material.principal


def test_uuid_or_registration_identity_cannot_authorize_issuance(environment, account):
    env = environment
    for supplied in (uuid4(), account[0]):
        with pytest.raises(TypeError): env.sessions.login(identity=supplied)
        with pytest.raises(TypeError): env.sessions.login(user_id=supplied)
    assert not hasattr(env.sessions, 'issue')
    assert env.session_count() == 0


def test_seeded_principal_without_credential_cannot_login(environment):
    env = environment
    user, name = uuid4(), env.username()
    env.ids.add(user)
    with env.connection() as c:
        sql(c, 'INSERT INTO public.users(id,display_name) VALUES (:id,:name)', id=user, name=name)
        c.commit()
    with pytest.raises(CredentialError) as error:
        env.sessions.login(username=name, password=secrets.token_urlsafe(32))
    assert error.value.code == CredentialCode.INVALID_CREDENTIALS
    assert env.session_count() == 0 and env.counts() == (1, 0)


def test_digest_only_token_storage_and_sensitive_result(environment, account):
    env = environment
    material = login(env, account)
    raw, csrf = token(material), material.csrf_token.get_secret_value()
    with env.connection() as c:
        row = sql(c, 'SELECT token_hash,csrf_token FROM public.auth_sessions WHERE user_id=:u', u=account[0].user_id).one()
    assert row.token_hash == sha256(raw).digest() and row.token_hash != raw
    assert row.csrf_token == csrf and raw != csrf and len(raw) == len(csrf) == 32
    rendered = (repr(material)+str(material)+repr(material.session_token)+str(material.csrf_token)).encode()
    assert raw not in rendered and csrf not in rendered


def test_independent_issuance_and_session_bound_csrf(environment, account):
    env = environment
    first, second = login(env, account), login(env, account)
    assert token(first) != token(second)
    assert first.csrf_token.get_secret_value() != second.csrf_token.get_secret_value()
    assert env.sessions.verify_csrf(token(first), first.csrf_token.get_secret_value()) == first.principal
    with pytest.raises(SessionError) as error:
        env.sessions.verify_csrf(token(first), second.csrf_token.get_secret_value())
    assert error.value.code == SessionCode.INVALID_CSRF and env.session_count() == 2


@pytest.mark.parametrize('kind', ['expired', 'revoked', 'future', 'unknown', 'malformed'])
def test_invalid_session_rejections(environment, account, kind):
    env = environment
    if kind in ('expired', 'future'):
        raw, csrf, expires = seeded_session(env, account, timedelta(hours=9) if kind == 'expired' else -timedelta(hours=1))
    else:
        material = login(env, account)
        raw = token(material)
        if kind == 'revoked': env.sessions.revoke(raw)
        elif kind == 'unknown': raw = secrets.token_bytes(32)
        else: raw = raw[:-1]
    with pytest.raises(SessionError) as error: env.sessions.validate(raw)
    assert error.value.code == SessionCode.INVALID_SESSION


def test_absolute_expiry_crosses_database_clock_boundary_without_renewal(environment, account):
    env = environment
    raw, csrf, expires = seeded_session(env, account, timedelta(hours=8)-timedelta(seconds=2))
    assert env.sessions.validate(raw).expires_at == expires
    deadline = monotonic() + 5
    with env.connection() as c:
        while monotonic() < deadline:
            if sql(c, 'SELECT clock_timestamp()>=:expires', expires=expires).scalar_one():
                break
            Event().wait(0.01)
        else:
            raise AssertionError('Database clock did not cross bounded expiry deadline')
    for _ in range(2):
        with pytest.raises(SessionError) as error: env.sessions.validate(raw)
        assert error.value.code == SessionCode.INVALID_SESSION
    with env.connection() as c:
        assert sql(c, 'SELECT expires_at FROM public.auth_sessions WHERE token_hash=:digest', digest=sha256(raw).digest()).scalar_one() == expires


def test_session_rejects_credential_that_becomes_unsupported(environment, account):
    env = environment
    material = login(env, account)
    with env.connection() as c:
        sql(c, "UPDATE public.account_credentials SET password_hash='$argon2id$synthetic-invalid-encoding' WHERE user_id=:u", u=account[0].user_id)
        c.commit()
    with pytest.raises(SessionError) as error: env.sessions.validate(token(material))
    assert error.value.code == SessionCode.INVALID_SESSION and env.session_count() == 1


def test_revoke_repeat_unknown_and_terminal_state(environment, account):
    env = environment
    material = login(env, account)
    env.sessions.revoke(token(material))
    first = stamp(env, material)
    env.sessions.revoke(token(material))
    env.sessions.revoke(secrets.token_bytes(32))
    assert stamp(env, material) == first and first.revoked_at is not None
    with pytest.raises(SessionError): env.sessions.validate(token(material))
    with pytest.raises(SessionError): env.sessions.verify_csrf(token(material), material.csrf_token.get_secret_value())
    assert env.session_count() == 1


def test_concurrent_revocations_are_idempotent(environment, account):
    env = environment
    material = login(env, account)
    gate = Barrier(2, timeout=8)

    def overlap(c, cursor, statement, parameters, context, many):
        if 'UPDATE public.auth_sessions' in statement: gate.wait()

    def revoke():
        env.sessions.revoke(token(material))
        return Outcome('committed')

    event.listen(env.engine, 'before_cursor_execute', overlap)
    try:
        assert workers([revoke, revoke]) == [Outcome('committed')]*2
    finally:
        event.remove(env.engine, 'before_cursor_execute', overlap)
    saved = stamp(env, material)
    assert saved.revoked_at is not None
    env.sessions.revoke(token(material))
    assert stamp(env, material) == saved


@pytest.mark.parametrize('phase', ['after_insert', 'commit'])
def test_issuance_failure_rolls_back_all_session_state(environment, account, phase):
    env = environment

    def after(c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.auth_sessions' in statement:
            assert c.connection.dbapi_connection.autocommit is False
            c.info['_session_test_inserted'] = True
            if phase == 'after_insert': raise RuntimeError('Injected session failure')

    def commit(c):
        if c.info.pop('_session_test_inserted', False): raise RuntimeError('Injected session failure')

    event.listen(env.engine, 'after_cursor_execute', after)
    if phase == 'commit': event.listen(env.engine, 'commit', commit)
    try:
        with pytest.raises(RuntimeError, match='^Injected session failure$'): login(env, account)
    finally:
        if phase == 'commit': event.remove(env.engine, 'commit', commit)
        event.remove(env.engine, 'after_cursor_execute', after)
    assert len(env.session_digests) == 1, 'Failure never reached session mutation'
    assert env.session_count() == 0


@pytest.mark.parametrize('operation', ['login', 'validate', 'revoke'])
def test_actual_autocommit_rejected_before_session_sql(environment, account, operation):
    env = environment
    material = login(env, account)
    unsafe = env.engine.execution_options(isolation_level='AUTOCOMMIT')
    service = SessionService(unsafe)
    actual, statements = [], []

    def state(c): actual.append(c.connection.dbapi_connection.autocommit)

    def observe(c, cursor, statement, parameters, context, many):
        if (statement.startswith('SET LOCAL') or 'public.auth_sessions' in statement
                or 'public.account_credentials' in statement or 'FROM public.users' in statement):
            statements.append('unexpected-service-sql')

    event.listen(unsafe, 'engine_connect', state)
    event.listen(unsafe, 'before_cursor_execute', observe)
    try:
        with pytest.raises(CredentialError) as error:
            if operation == 'login': service.login(username=account[0].username, password=account[1])
            else: getattr(service, operation)(token(material))
        assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    finally:
        event.remove(unsafe, 'before_cursor_execute', observe)
        event.remove(unsafe, 'engine_connect', state)
    assert actual == [True] and statements == []
    assert env.sessions.validate(token(material)) == material.principal


def test_changed_credential_snapshot_cannot_issue(environment, account, monkeypatch):
    env = environment
    verified, release = Event(), Event()
    original = env.sessions._credentials._verify_for_session
    new_password = secrets.token_urlsafe(32)
    encoded = credentials._PASSWORDS.hash(new_password)  # Before any transaction.

    def pause(**values):
        snapshot = original(**values)
        verified.set()
        wait(release)
        return snapshot

    monkeypatch.setattr(env.sessions._credentials, '_verify_for_session', pause)

    def attempt():
        try: login(env, account)
        except SessionError as error:
            if error.code != SessionCode.AUTHENTICATION_CHANGED: raise
            return Outcome('authentication-changed')
        raise AssertionError('Stale credential authorized session')

    def change():
        try:
            wait(verified)
            with env.connection() as c:
                sql(c, '''UPDATE public.account_credentials SET password_hash=:encoded,updated_at=clock_timestamp()
                    WHERE user_id=:u''', encoded=encoded, u=account[0].user_id)
                c.commit()
            return Outcome('credential-changed')
        finally: release.set()

    assert workers([attempt, change]) == [Outcome('authentication-changed'), Outcome('credential-changed')]
    assert env.session_count() == 0
    assert env.service.verify_credentials(username=account[0].username, password=new_password) == account[0]


def test_credential_share_lock_protects_check_through_session_commit(environment, account):
    env = environment
    held, release = Event(), Event()
    pids = Queue()
    encoded = credentials._PASSWORDS.hash(secrets.token_urlsafe(32))

    def hold(c, cursor, statement, parameters, context, many):
        if 'FROM public.account_credentials' in statement and 'FOR SHARE' in statement:
            pids.put(('issuer', c.connection.dbapi_connection.info.backend_pid))
            held.set()
            wait(release)

    def issue():
        login(env, account)
        return Outcome('committed')

    def update():
        wait(held)
        with env.connection() as c:
            pids.put(('updater', sql(c, 'SELECT pg_backend_pid()').scalar_one()))
            sql(c, 'UPDATE public.account_credentials SET password_hash=:encoded WHERE user_id=:u', encoded=encoded, u=account[0].user_id)
            c.commit()
        return Outcome('committed')

    def observe():
        try:
            identities = dict(pids.get(timeout=8) for _ in range(2))
            deadline = monotonic()+3
            with env.connection() as c:
                while monotonic() < deadline:
                    if identities['issuer'] in sql(c, 'SELECT pg_blocking_pids(:pid)', pid=identities['updater']).scalar_one():
                        return Outcome('lock-observed')
                    Event().wait(0.01)
            raise AssertionError('Credential SHARE lock wait not observed')
        finally: release.set()

    event.listen(env.engine, 'after_cursor_execute', hold)
    try:
        assert workers([issue, update, observe]) == [Outcome('committed'), Outcome('committed'), Outcome('lock-observed')]
    finally:
        event.remove(env.engine, 'after_cursor_execute', hold)
    assert env.session_count() == 1
