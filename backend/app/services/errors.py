"""Stable internal errors. Do not expose driver text or infer HTTP status here."""
from enum import StrEnum

from sqlalchemy.exc import DBAPIError


class ErrorCode(StrEnum):
    INVALID_INPUT = 'invalid_input'
    IDEMPOTENCY_MISMATCH = 'idempotency_mismatch'
    HACKATHON_NOT_FOUND = 'hackathon_not_found'
    USER_NOT_FOUND = 'user_not_found'
    TEAM_NOT_FOUND = 'team_not_found'
    TEAM_DELETED = 'team_deleted'
    ALREADY_ASSIGNED = 'already_assigned'
    TEAM_FULL = 'team_full'
    FORBIDDEN = 'forbidden'
    REQUEST_NOT_FOUND = 'request_not_found'
    REQUEST_RESOLVED = 'request_resolved'
    TRANSACTION_CONFLICT = 'transaction_conflict'
    TRANSACTION_DEADLINE = 'transaction_deadline'
    OUTCOME_UNCERTAIN = 'outcome_uncertain'
    LOCK_TIMEOUT = 'lock_timeout'
    STATEMENT_TIMEOUT = 'statement_timeout'
    INTEGRITY_FAULT = 'integrity_fault'
    DATABASE_FAILURE = 'database_failure'
    TRANSACTION_CONFIGURATION = 'transaction_configuration'


class DomainError(Exception):
    def __init__(self, code: ErrorCode, *, retryable: bool = False):
        self.code = code
        self.retryable = retryable
        super().__init__(code.value)


def map_database_error(error: DBAPIError) -> DomainError:
    state = getattr(error.orig, 'sqlstate', None)
    constraint = getattr(getattr(error.orig, 'diag', None), 'constraint_name', None)
    expected = {
        ('23505', 'pk_memberships'): ErrorCode.ALREADY_ASSIGNED,
        ('23514', 'ct_team_capacity'): ErrorCode.TEAM_FULL,
        ('23514', 'guard_team_deleted'): ErrorCode.TEAM_DELETED,
    }
    if (state, constraint) in expected:
        return DomainError(expected[state, constraint])
    if state in ('40P01', '40001'):
        return DomainError(ErrorCode.TRANSACTION_CONFLICT, retryable=True)
    if state == '55P03':
        return DomainError(ErrorCode.LOCK_TIMEOUT, retryable=True)
    if state == '57014':
        return DomainError(ErrorCode.STATEMENT_TIMEOUT)
    if isinstance(state, str) and state.startswith('23'):
        return DomainError(ErrorCode.INTEGRITY_FAULT)
    return DomainError(ErrorCode.DATABASE_FAILURE)
