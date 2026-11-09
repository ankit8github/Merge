"""Real PostgreSQL storage checks; no login/session service or real credentials."""
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, configure_mappers

import app.models
from app.db.base import Base
from app.models import AccountCredential, AuthSession
from test_support.races import sql

SYNTHETIC_HASH = '$argon2id$synthetic-storage-only-not-a-real-password-hash'


def credential(c, user, username=None):
    username = username or ('u_' + uuid4().hex[:20])
    sql(c, '''INSERT INTO public.account_credentials(user_id,username,password_hash)
        VALUES (:u,:name,:hash)''', u=user, name=username, hash=SYNTHETIC_HASH)


def session(c, user, digest=None, csrf=None, suffix=''):
    # Synthetic random identifiers for row isolation, not issued authentication.
    digest = uuid4().bytes + uuid4().bytes if digest is None else digest
    csrf = uuid4().bytes + uuid4().bytes if csrf is None else csrf
    sql(c, '''INSERT INTO public.auth_sessions(token_hash,user_id,csrf_token)
        VALUES (:digest,:u,:csrf)''' + suffix, digest=digest, u=user, csrf=csrf)
    return digest


def rejected(c, action, state, constraints):
    with c.begin_nested() as savepoint:
        with pytest.raises(IntegrityError) as error:
            action()
        assert error.value.orig.sqlstate == state
        assert error.value.orig.diag.constraint_name in constraints
        print('expected SQLSTATE:', state, 'constraint:', error.value.orig.diag.constraint_name)
        savepoint.rollback()


def test_valid_credential_session_and_relationships(connection, user):
    credential(connection, user)
    digest = session(connection, user)
    assert sql(connection, "SELECT expires_at=created_at+interval '8 hours',revoked_at IS NULL FROM public.auth_sessions WHERE token_hash=:d", d=digest).one() == (True, True)
    configure_mappers()
    with Session(bind=connection, join_transaction_mode='create_savepoint') as orm:
        record = orm.get(AuthSession, digest)
        assert record.user.id == user and record.credential.user_id == user
        assert len(orm.get(AccountCredential, user).sessions) == 1


def test_duplicate_canonical_username(connection, user):
    username = 'dupe_' + uuid4().hex[:20]
    credential(connection, user, username)
    other = uuid4()
    sql(connection, "INSERT INTO public.users(id,display_name) VALUES (:u,'other')", u=other)
    rejected(connection, lambda: credential(connection, other, username), '23505', {'uq_credentials_username'})


@pytest.mark.parametrize('username', ['ab', 'Uppercase', 'has space', 'has-dash', 'nonascii_é', 'trail\n'])
def test_noncanonical_username_rejected(connection, user, username):
    rejected(connection, lambda: credential(connection, user, username), '23514', {'ck_credentials_username'})


@pytest.mark.parametrize('length', [0, 31, 33])
def test_invalid_session_digest_length(connection, user, length):
    credential(connection, user)
    rejected(connection, lambda: session(connection, user, digest=b'x'*length), '23514', {'ck_sessions_digest'})


def test_invalid_csrf_length(connection, user):
    credential(connection, user)
    rejected(connection, lambda: session(connection, user, csrf=b'x'*31), '23514', {'ck_sessions_csrf'})


def test_unknown_user_credential_rejected(connection):
    rejected(connection, lambda: credential(connection, uuid4()), '23503', {'fk_credentials_user'})


def test_unknown_user_session_rejected(connection):
    rejected(connection, lambda: session(connection, uuid4()), '23503', {'fk_sessions_user', 'fk_sessions_credentials'})


def test_existing_user_without_credential_cannot_have_session(connection, user):
    rejected(connection, lambda: session(connection, user), '23503', {'fk_sessions_credentials'})
    assert sql(connection, 'SELECT count(*) FROM public.account_credentials WHERE user_id=:u', u=user).scalar_one() == 0


def test_invalid_expiration_relationship(connection, user):
    credential(connection, user)
    rejected(connection, lambda: sql(connection, '''INSERT INTO public.auth_sessions(token_hash,user_id,csrf_token,expires_at)
        VALUES (:d,:u,:csrf,now()+interval '9 hours')''', d=uuid4().bytes*2, u=user, csrf=b'c'*32), '23514', {'ck_sessions_expiration'})


def test_revocation_before_creation_rejected(connection, user):
    credential(connection, user)
    digest = session(connection, user)
    rejected(connection, lambda: sql(connection, "UPDATE public.auth_sessions SET revoked_at=created_at-interval '1 second' WHERE token_hash=:d", d=digest), '23514', {'ck_sessions_revocation'})


@pytest.mark.parametrize('field', ['lifetime', 'revocation'])
def test_infinite_session_timestamps_rejected(connection, user, field):
    credential(connection, user)
    if field == 'lifetime':
        action = lambda: sql(connection, '''INSERT INTO public.auth_sessions(token_hash,user_id,csrf_token,created_at,expires_at)
            VALUES (:d,:u,:csrf,'infinity','infinity')''', d=uuid4().bytes*2, u=user, csrf=b'c'*32)
    else:
        action = lambda: sql(connection, '''INSERT INTO public.auth_sessions(token_hash,user_id,csrf_token,revoked_at)
            VALUES (:d,:u,:csrf,'infinity')''', d=uuid4().bytes*2, u=user, csrf=b'c'*32)
    rejected(connection, action, '23514', {'ck_sessions_finite'})


def test_revocation_is_terminal_and_lifetime_immutable(connection, user):
    credential(connection, user)
    digest = session(connection, user)
    sql(connection, 'UPDATE public.auth_sessions SET revoked_at=now() WHERE token_hash=:d', d=digest)
    rejected(connection, lambda: sql(connection, 'UPDATE public.auth_sessions SET revoked_at=NULL WHERE token_hash=:d', d=digest), '23514', {'guard_sessions_revoked'})
    rejected(connection, lambda: sql(connection, "UPDATE public.auth_sessions SET created_at=created_at+interval '1 hour',expires_at=expires_at+interval '1 hour' WHERE token_hash=:d", d=digest), '23514', {'guard_sessions_identity'})


def test_credential_identity_and_timestamps(connection, user):
    credential(connection, user)
    rejected(connection, lambda: sql(connection, 'UPDATE public.account_credentials SET user_id=:other WHERE user_id=:u', other=uuid4(), u=user), '23514', {'guard_credentials_identity'})
    rejected(connection, lambda: sql(connection, "UPDATE public.account_credentials SET updated_at=created_at-interval '1 second' WHERE user_id=:u", u=user), '23514', {'ck_credentials_timestamps'})


def test_deleting_credential_with_session_rejected(connection, user):
    credential(connection, user)
    session(connection, user)
    rejected(connection, lambda: sql(connection, 'DELETE FROM public.account_credentials WHERE user_id=:u', u=user), '23503', {'fk_sessions_credentials'})


def test_storage_hash_marker_rejects_plaintext(connection, user):
    rejected(connection, lambda: sql(connection, 'INSERT INTO public.account_credentials(user_id,username,password_hash) VALUES (:u,:name,:value)', u=user, name='plain_name', value='synthetic-invalid-format'), '23514', {'ck_credentials_hash_format'})


def test_throttle_counter_and_expiration_checks(connection):
    key = uuid4().bytes*2
    for attempts, duration, constraint in [(-1, '1 minute', 'ck_throttle_attempts'), (0, '-1 second', 'ck_throttle_expiration')]:
        rejected(connection, lambda: sql(connection, '''INSERT INTO public.auth_throttle_buckets(scope,key_hash,window_start,attempts,expires_at)
            VALUES ('login.ip',:key,now(),:attempts,now()+CAST(:duration AS interval))''', key=key, attempts=attempts, duration=duration), '23514', {constraint})
    sql(connection, "INSERT INTO public.auth_throttle_buckets(scope,key_hash,window_start,expires_at) VALUES ('login.ip',:key,now(),now()+interval '1 minute')", key=key)
    assert sql(connection, 'SELECT attempts FROM public.auth_throttle_buckets WHERE key_hash=:key', key=key).scalar_one() == 0


def test_uncredentialed_user_and_existing_users_unchanged(connection, user):
    before = sql(connection, 'SELECT id,display_name,created_at FROM public.users ORDER BY id').all()
    credentials_before = set(sql(connection, 'SELECT user_id FROM public.account_credentials').scalars())
    credential(connection, user)
    session(connection, user)
    after = sql(connection, 'SELECT id,display_name,created_at FROM public.users ORDER BY id').all()
    assert before == after
    # No automatic adoption of any existing user by the tested inserts.
    assert set(sql(connection, 'SELECT user_id FROM public.account_credentials').scalars()) == credentials_before | {user}


def test_auth_metadata_matches_migrated_database(connection):
    context = MigrationContext.configure(connection, opts={'include_schemas': True, 'compare_type': True, 'compare_server_default': True})
    assert compare_metadata(context, Base.metadata) == []
    config = sql(connection, "SELECT proconfig,prosecdef FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND proname='merge_guard_auth_row'").one()
    assert config == (['search_path=pg_catalog, pg_temp'], False)
