"""Internal PostgreSQL session lifecycle. No HTTP, cookies or memory session store.

Only login(username,password) can issue. A UUID, registration result or externally
supplied authentication object is never an issuance input. Trusted Python/Engine
code is the boundary; private attributes are not a sandbox against malicious code.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from uuid import UUID

from pydantic import SecretBytes
from sqlalchemy.engine import Engine

from app.security.passwords import supported_hash
from app.services.credentials import CredentialService, _query, valid_username
from app.services.session_errors import SessionCode, SessionError

SESSION_LIFETIME = timedelta(hours=8)
TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    user_id: UUID  # Populated only from storage, never client-submitted identity.
    username: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """Sensitive result. SecretBytes requires explicit get_secret_value() to reveal."""
    principal: SessionPrincipal
    created_at: datetime
    session_token: SecretBytes = field(repr=False)
    csrf_token: SecretBytes = field(repr=False)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SessionError(SessionCode.CLOCK_CONFIGURATION)
    return value.astimezone(timezone.utc)


def _raw_token(value: bytes) -> bytes:
    if not isinstance(value, bytes) or len(value) != TOKEN_BYTES:
        raise SessionError(SessionCode.INVALID_SESSION)
    return value


def _new_secret() -> bytes:
    try:
        result = secrets.token_bytes(TOKEN_BYTES)
    except OSError:
        failure = SessionError(SessionCode.ENTROPY_FAILURE)
    else:
        if isinstance(result, bytes) and len(result) == TOKEN_BYTES:
            return result
        failure = SessionError(SessionCode.ENTROPY_FAILURE)
    raise failure from None


class SessionService:
    def __init__(self, engine: Engine):
        # Reuse the reviewed identity transaction owner, fail-closed actual driver
        # guard, deadlines, parameter hiding and sanitized DBAPI error mapping.
        self._credentials = CredentialService(engine)

    def login(self, *, username: str, password: str) -> IssuedSession:
        verified = self._credentials._verify_for_session(username=username, password=password)
        # All Argon2 work above has finished and its read connection is closed.
        token, csrf = _new_secret(), _new_secret()
        digest = sha256(token).digest()

        def issue(c):
            user = _query(c, 'SELECT id FROM public.users WHERE id=:u FOR KEY SHARE',
                          u=verified.identity.user_id).one_or_none()
            # SHARE blocks password/username/timestamp UPDATE or DELETE through
            # session COMMIT. FK KEY SHARE locks are compatible with this lock.
            current = _query(c, '''SELECT user_id,username,password_hash,created_at,updated_at
                FROM public.account_credentials WHERE user_id=:u FOR SHARE''',
                u=verified.identity.user_id).one_or_none()
            if (user is None or current is None or current.user_id != verified.identity.user_id
                    or current.username != verified.identity.username
                    or current.created_at != verified.created_at or current.updated_at != verified.updated_at
                    or not secrets.compare_digest(sha256(current.password_hash.encode('utf-8')).digest(),
                                                  verified.password_fingerprint)):
                raise SessionError(SessionCode.AUTHENTICATION_CHANGED)
            # Database clock is authoritative; normalize aware timestamps to UTC.
            created = _utc(_query(c, 'SELECT clock_timestamp()').scalar_one())
            expires = created + SESSION_LIFETIME
            _query(c, '''INSERT INTO public.auth_sessions
                (token_hash,user_id,csrf_token,created_at,expires_at)
                VALUES (:digest,:u,:csrf,:created,:expires)''', digest=digest,
                u=current.user_id, csrf=csrf, created=created, expires=expires)
            return IssuedSession(SessionPrincipal(current.user_id, current.username, expires),
                                 created, SecretBytes(token), SecretBytes(csrf))

        # No issuance entry point accepts a caller's UUID, Identity or snapshot.
        # No raw material escapes this facade before the owned transaction commits.
        return self._credentials._execute(issue)

    def _read_active(self, token: bytes):
        digest = sha256(_raw_token(token)).digest()

        def lookup(c):
            row = _query(c, '''SELECT s.user_id,c.username,c.password_hash,s.csrf_token,
                s.created_at,s.expires_at,s.revoked_at,clock_timestamp() AS checked_at
                FROM public.auth_sessions s JOIN public.users u ON u.id=s.user_id
                JOIN public.account_credentials c ON c.user_id=s.user_id
                WHERE s.token_hash=:digest''', digest=digest).one_or_none()
            if row is None or row.revoked_at is not None:
                raise SessionError(SessionCode.INVALID_SESSION)
            created, expires, now = _utc(row.created_at), _utc(row.expires_at), _utc(row.checked_at)
            if (not created <= now < expires or expires - created != SESSION_LIFETIME
                    or not valid_username(row.username) or not supported_hash(row.password_hash)):
                raise SessionError(SessionCode.INVALID_SESSION)
            return row

        return self._credentials._execute(lookup, read_only=True)

    def validate(self, session_token: bytes) -> SessionPrincipal:
        row = self._read_active(session_token)
        return SessionPrincipal(row.user_id, row.username, _utc(row.expires_at))

    def verify_csrf(self, session_token: bytes, csrf_token: bytes) -> SessionPrincipal:
        row = self._read_active(session_token)
        if (not isinstance(csrf_token, bytes) or len(csrf_token) != TOKEN_BYTES
                or not secrets.compare_digest(row.csrf_token, csrf_token)):
            raise SessionError(SessionCode.INVALID_CSRF)
        return SessionPrincipal(row.user_id, row.username, _utc(row.expires_at))

    def revoke(self, session_token: bytes) -> None:
        digest = sha256(_raw_token(session_token)).digest()

        def revoke(c):
            # RC UPDATE rechecks NULL after concurrent row waits. Never rewrite a
            # terminal timestamp. Unknown/already-revoked rows are no-ops; an
            # expired retained row may still be marked revoked for bookkeeping.
            _query(c, '''UPDATE public.auth_sessions
                SET revoked_at=GREATEST(clock_timestamp(),created_at)
                WHERE token_hash=:digest AND revoked_at IS NULL''', digest=digest)

        self._credentials._execute(revoke)
