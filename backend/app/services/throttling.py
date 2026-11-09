"""Durable, short auth admission transactions; no password/session work here."""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import hmac
from ipaddress import ip_address
from math import ceil

from pydantic import SecretBytes
from sqlalchemy.engine import Engine

from app.services.credentials import CredentialService, _query, valid_username
from app.services.credential_errors import CredentialCode, CredentialError


class ThrottleExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__('rate_limited')


@dataclass(frozen=True, slots=True)
class ThrottlePolicy:
    window_seconds: int = 300
    login_account: int = 5
    login_ip: int = 30
    register_ip: int = 5

    def __post_init__(self):
        bounds = ((self.window_seconds, 1, 3600), (self.login_account, 1, 100),
                  (self.login_ip, 1, 500), (self.register_ip, 1, 50))
        if any(type(value) is not int or not low <= value <= high for value, low, high in bounds):
            raise CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)


@dataclass(frozen=True, slots=True)
class _Decision:
    allowed: bool
    retry_after: int


_CONSUME = '''WITH stamp AS MATERIALIZED (SELECT clock_timestamp() AS at),
    bounds AS MATERIALIZED (
        SELECT date_bin(make_interval(secs => :seconds), at,
                        TIMESTAMPTZ '1970-01-01 00:00:00+00') AS start
        FROM stamp),
    charged AS (
        INSERT INTO public.auth_throttle_buckets AS bucket
            (scope,key_hash,window_start,attempts,expires_at)
        SELECT :scope,:key,start,1,start+make_interval(secs => :seconds) FROM bounds WHERE true
        ON CONFLICT (scope,key_hash,window_start) DO UPDATE
            SET attempts=LEAST(bucket.attempts,:maximum)+1
        RETURNING attempts,expires_at)
    SELECT attempts,expires_at,
           (SELECT start+make_interval(secs => :seconds) FROM bounds) AS expected_expiry,
           clock_timestamp() AS checked_at FROM charged'''


class ThrottleService:
    def __init__(self, engine: Engine, *, secret: SecretBytes, policy: ThrottlePolicy):
        if not isinstance(secret, SecretBytes) or len(secret.get_secret_value()) != 32:
            raise CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)
        if not isinstance(policy, ThrottlePolicy):
            raise CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)
        self._owner = CredentialService(engine)
        self._secret = secret
        self._policy = policy

    def _key(self, scope: str, identifier: str) -> bytes:
        return hmac.digest(self._secret.get_secret_value(),
                           (scope+'\0'+identifier).encode('ascii'), sha256)

    def _consume(self, connection, scope: str, identifier: str, maximum: int) -> _Decision:
        row = _query(connection, _CONSUME, scope='auth:v1:'+scope,
                     key=self._key(scope, identifier), seconds=self._policy.window_seconds,
                     maximum=maximum).one()
        # Fail closed on corrupt or conflicting policy state; never disguise an
        # integrity/configuration failure as an expected 429.
        timestamps = (row.expires_at, row.expected_expiry, row.checked_at)
        if (type(row.attempts) is not int or not 1 <= row.attempts <= maximum+1
                or any(not isinstance(value, datetime) or value.tzinfo is None
                       or value.utcoffset() is None for value in timestamps)
                or row.expires_at != row.expected_expiry
                ):
            raise CredentialError(CredentialCode.INTEGRITY_FAULT)
        retry = max(1, min(self._policy.window_seconds,
                           ceil((row.expires_at-row.checked_at).total_seconds())))
        return _Decision(row.attempts <= maximum, retry)

    def check(self, *, operation: str, client_ip: str, username: str | None = None) -> None:
        if operation not in ('login', 'register') or not isinstance(client_ip, str) or '%' in client_ip:
            raise CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)
        try:
            address = ip_address(client_ip)
        except ValueError:
            failure = CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)
        else:
            failure = None
        if failure is not None:
            raise failure from None
        canonical_ip = str(getattr(address, 'ipv4_mapped', None) or address)
        # HTTP already enforces this exact canonical account representation.
        if operation == 'login' and not valid_username(username):
            raise CredentialError(CredentialCode.TRANSACTION_CONFIGURATION)

        def admit(c):
            _query(c, "SET LOCAL lock_timeout='1s'")
            _query(c, "SET LOCAL statement_timeout='2s'")
            ip_limit = self._policy.login_ip if operation == 'login' else self._policy.register_ip
            decision = self._consume(c, operation+'_ip', canonical_ip, ip_limit)
            if not decision.allowed or operation == 'register':
                return decision
            return self._consume(c, 'login_account', username, self._policy.login_account)

        decision = self._owner._execute(admit)
        # Raising inside the transaction would roll back the attempt counters.
        if not decision.allowed:
            raise ThrottleExceeded(decision.retry_after)
