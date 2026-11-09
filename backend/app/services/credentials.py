"""Internal registration and credential verification; no session issuance.

Only fresh server-generated principals can be registered. Caller-owned sessions,
connections, UUIDs and already-open transactions cannot split the operation.
"""
from dataclasses import dataclass
import re
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError

from app.security.passwords import PasswordCodec, valid_password
from app.services.credential_errors import CredentialCode, CredentialError, credential_database_error

_USERNAME = re.compile(r'[a-z0-9_]{3,32}', flags=re.ASCII)
# Shared default; all codec instances additionally share the process-wide budget.
_PASSWORDS = PasswordCodec()


@dataclass(frozen=True)
class CredentialIdentity:
    user_id: UUID
    username: str


def valid_username(value: object) -> bool:
    return isinstance(value, str) and _USERNAME.fullmatch(value) is not None


def _valid_text(value: str) -> bool:
    try:
        value.encode('utf-8', errors='strict')
    except UnicodeEncodeError:
        return False
    return True


def _query(c, statement, **values):
    return c.execute(text(statement), values)


class CredentialService:
    def __init__(self, engine: Engine):
        if not isinstance(engine, Engine):
            raise TypeError('CredentialService requires an Engine')
        # Avoid SQL parameter/debug-row logging of the encoded password hash.
        if engine.hide_parameters is not True or engine.echo not in (False, None):
            raise CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)
        self._engine = engine

    @staticmethod
    def _require_transactional_connection(c: Connection) -> None:
        try:
            supported = (c.dialect.name == 'postgresql' and c.dialect.driver == 'psycopg'
                         and c.dialect.is_async is False)
            if not supported or c.connection.dbapi_connection.autocommit is not False or c.in_transaction():
                raise CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)
            if c.get_isolation_level() != 'READ COMMITTED':
                raise CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)
        except CredentialError:
            raise
        except Exception:
            failure = CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)
        else:
            return
        raise failure from None

    def _execute(self, operation, *, read_only=False):
        try:
            with self._engine.connect() as c:
                self._require_transactional_connection(c)
                with c.begin():
                    if read_only:
                        _query(c, 'SET TRANSACTION READ ONLY')
                    _query(c, "SET LOCAL lock_timeout='5s'")
                    _query(c, "SET LOCAL statement_timeout='15s'")
                    result = operation(c)
            return result
        except DBAPIError as error:
            failure = credential_database_error(error)
        # A fresh fixed-code exception, with no raw DBAPI exception/parameters
        # attached as context. Never log traceback locals containing secrets.
        raise failure from None

    def register(self, *, username: str, password: str, display_name: str | None = None) -> CredentialIdentity:
        if not valid_username(username) or not valid_password(password):
            raise CredentialError(CredentialCode.INVALID_INPUT)
        name = username if display_name is None else display_name
        if not isinstance(name, str) or not 1 <= len(name) <= 80 or not name.strip(' ') or '\x00' in name:
            raise CredentialError(CredentialCode.INVALID_INPUT)
        if not _valid_text(name):
            raise CredentialError(CredentialCode.INVALID_INPUT)
        # Expensive work before acquiring a connection, transaction or row lock.
        encoded = _PASSWORDS.hash(password)
        user_id = uuid4()

        def create(c):
            _query(c, 'INSERT INTO public.users(id,display_name) VALUES (:u,:name)', u=user_id, name=name)
            # No preflight username check: the unique constraint decides races.
            _query(c, '''INSERT INTO public.account_credentials(user_id,username,password_hash)
                VALUES (:u,:username,:encoded)''', u=user_id, username=username, encoded=encoded)
            return CredentialIdentity(user_id, username)

        return self._execute(create)

    def verify_credentials(self, *, username: str, password: str) -> CredentialIdentity:
        if not valid_username(username) or not valid_password(password):
            raise CredentialError(CredentialCode.INVALID_CREDENTIALS)

        def lookup(c):
            return _query(c, '''SELECT user_id,username,password_hash FROM public.account_credentials
                WHERE username=:username''', username=username).one_or_none()

        record = self._execute(lookup, read_only=True)
        # No open database transaction/connection during real OR dummy Argon2.
        encoded = None if record is None else record.password_hash
        matched = _PASSWORDS.verify(encoded, password)
        if record is None or not matched:
            raise CredentialError(CredentialCode.INVALID_CREDENTIALS)
        # No hash update, rehash, session, cookie or claimed HTTP authorization.
        return CredentialIdentity(record.user_id, record.username)
