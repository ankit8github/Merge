"""Credential errors contain fixed codes only, never input or driver text."""
from enum import StrEnum

from sqlalchemy.exc import DBAPIError


class CredentialCode(StrEnum):
    INVALID_INPUT = 'invalid_input'
    USERNAME_UNAVAILABLE = 'username_unavailable'
    INVALID_CREDENTIALS = 'invalid_credentials'
    HASHING_BUSY = 'hashing_busy'
    HASHING_FAILURE = 'hashing_failure'
    TRANSACTION_CONFIGURATION = 'transaction_configuration'
    TRANSACTION_CONFLICT = 'transaction_conflict'
    LOCK_TIMEOUT = 'lock_timeout'
    STATEMENT_TIMEOUT = 'statement_timeout'
    INTEGRITY_FAULT = 'integrity_fault'
    DATABASE_FAILURE = 'database_failure'


class CredentialError(Exception):
    def __init__(self, code: CredentialCode, *, retryable: bool = False):
        self.code = code
        self.retryable = retryable
        super().__init__(code.value)


def credential_database_error(error: DBAPIError) -> CredentialError:
    state = getattr(error.orig, 'sqlstate', None)
    constraint = getattr(getattr(error.orig, 'diag', None), 'constraint_name', None)
    if (state, constraint) == ('23505', 'uq_credentials_username'):
        return CredentialError(CredentialCode.USERNAME_UNAVAILABLE)
    if state in ('40P01', '40001'):
        return CredentialError(CredentialCode.TRANSACTION_CONFLICT, retryable=True)
    if state == '55P03':
        return CredentialError(CredentialCode.LOCK_TIMEOUT, retryable=True)
    if state == '57014':
        return CredentialError(CredentialCode.STATEMENT_TIMEOUT)
    if isinstance(state, str) and state.startswith('23'):
        return CredentialError(CredentialCode.INTEGRITY_FAULT)
    return CredentialError(CredentialCode.DATABASE_FAILURE)
