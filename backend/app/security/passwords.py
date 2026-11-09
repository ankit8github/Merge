"""Fixed Argon2id profile with one process-wide, non-queuing work budget.

No logging, plaintext persistence, rehashing or password normalization. The dummy
hash is generated in memory before account lookup, never loaded from user data.
"""
import re
import secrets
from threading import BoundedSemaphore

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

from app.services.credential_errors import CredentialCode, CredentialError

MEMORY_KIB = 19456
ITERATIONS = 2
PARALLELISM = 1
SALT_BYTES = 16
HASH_BYTES = 32
MAX_HASH_WORKERS = 2
_SLOTS = BoundedSemaphore(MAX_HASH_WORKERS)
_ENCODED = re.compile(
    rf'\$argon2id\$v=19\$m={MEMORY_KIB},t={ITERATIONS},p={PARALLELISM}'
    r'\$[A-Za-z0-9+/]{22}\$[A-Za-z0-9+/]{43}'
)


def valid_password(value: object) -> bool:
    if not isinstance(value, str) or not 15 <= len(value) <= 128:
        return False
    try:
        value.encode('utf-8', errors='strict')
    except UnicodeEncodeError:
        return False
    return True


class PasswordCodec:
    def __init__(self):
        self._hasher = PasswordHasher(time_cost=ITERATIONS, memory_cost=MEMORY_KIB,
            parallelism=PARALLELISM, hash_len=HASH_BYTES, salt_len=SALT_BYTES,
            encoding='utf-8', type=Type.ID)
        # No fixed usable password/hash in source; initialization precedes lookup.
        self._dummy_hash = self.hash(secrets.token_urlsafe(32))

    def _work(self, operation):
        if not _SLOTS.acquire(blocking=False):
            raise CredentialError(CredentialCode.HASHING_BUSY, retryable=True)
        try:
            return operation()
        except (HashingError, VerificationError, InvalidHashError, MemoryError):
            failure = CredentialError(CredentialCode.HASHING_FAILURE)
        finally:
            _SLOTS.release()
        # Raise after leaving the native exception handler: do not attach its
        # exception object/details as this error's implicit context.
        raise failure from None

    def hash(self, password: str) -> str:
        if not valid_password(password):
            raise CredentialError(CredentialCode.INVALID_INPUT)
        return self._work(lambda: self._hasher.hash(password))

    def verify(self, encoded: str | None, password: str) -> bool:
        if not valid_password(password):
            return False
        # Hash data is database-owned, never a client-supplied parameter. Still
        # reject unexpected profiles before native code can allocate their costs.
        supported = isinstance(encoded, str) and _ENCODED.fullmatch(encoded) is not None
        target = encoded if supported else self._dummy_hash

        def check():
            try:
                return self._hasher.verify(target, password)
            except VerifyMismatchError:
                return False
            except (VerificationError, InvalidHashError):
                # Malformed stored encodings fail closed with dummy-cost work.
                try:
                    self._hasher.verify(self._dummy_hash, password)
                except VerifyMismatchError:
                    pass
                return False

        matched = self._work(check)
        return bool(supported and matched)
