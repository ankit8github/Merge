"""Bounded composed-operation orchestration; TeamService._execute owns all I/O.

No SQLSTATE/error text, request data or proof is retained beyond this call. Pool
info holds only the current attempt's deadline/phase, never authoritative state.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from math import isfinite
from random import uniform
from re import fullmatch
from time import monotonic, sleep

from sqlalchemy import text

from app.services.errors import DomainError, ErrorCode

_ATTEMPT_KEY = object()
_now = monotonic
_sleep = sleep


@dataclass(frozen=True, slots=True)
class TransactionRetryPolicy:
    total_seconds: float = 30.0
    jitter_ms: int = 50

    def __post_init__(self):
        if (type(self.total_seconds) not in (int, float) or not 1 <= self.total_seconds <= 60
                or not isfinite(self.total_seconds)
                or type(self.jitter_ms) is not int or not 0 <= self.jitter_ms <= 250):
            raise ValueError('Invalid transaction retry policy')


def _deadline(uncertain=False):
    raise DomainError(ErrorCode.OUTCOME_UNCERTAIN if uncertain else ErrorCode.TRANSACTION_DEADLINE,
                      retryable=True) from None


@dataclass(slots=True, repr=False)
class _Attempt:
    deadline: float
    phase: str = 'work'
    confirmed_abort: bool = False
    confirmed_failure: bool = False
    ambiguous: bool = False
    failure_classified: bool = False
    reserved_new: bool = False
    replayed_reply: object = field(default=None, repr=False)
    confirmed_reply: object = field(default=None, repr=False)

    def check(self):
        remaining = self.deadline - _now()
        if remaining <= 0:
            _deadline()
        return remaining

    @contextmanager
    def bind(self, connection):
        # Capture info before errors can invalidate the connection. Cleanup must
        # never access connection.info and accidentally reconnect an invalid handle.
        info = connection.info
        if _ATTEMPT_KEY in info:
            raise DomainError(ErrorCode.TRANSACTION_CONFIGURATION)
        info[_ATTEMPT_KEY] = self
        try:
            yield
        finally:
            info.pop(_ATTEMPT_KEY, None)

    def before_statement(self, connection):
        milliseconds = max(1, int(self.check() * 1000))
        # Direct execute bypasses teams._query's hook, so this cannot recurse.
        # Both settings are local to the same already-guarded owned transaction.
        connection.execute(text("SELECT set_config('statement_timeout', :statement, true), "
                                "set_config('lock_timeout', :lock, true)"),
                           {'statement': f'{min(15000, milliseconds)}ms',
                            'lock': f'{min(5000, milliseconds)}ms'})
        self.check()

    def database_failure(self, error):
        if self.failure_classified:
            return  # Cleanup must not replace the original transaction evidence.
        self.failure_classified = True
        state = getattr(error.orig, 'sqlstate', None)
        self.confirmed_abort = state in ('40P01', '40001')
        # Conservative known server aborts at COMMIT. All other COMMIT errors
        # (including missing/connection/unknown SQLSTATE) require reconciliation.
        self.confirmed_failure = (self.confirmed_abort or state in ('55P03', '57014')
                                  or isinstance(state, str) and fullmatch(r'[0-9A-Z]{5}', state)
                                  is not None and state[:2] in ('22', '23'))
        self.ambiguous = self.phase == 'commit' and not self.confirmed_failure


def _before_statement(connection):
    attempt = getattr(connection, 'info', {}).get(_ATTEMPT_KEY)
    if attempt is not None:
        attempt.before_statement(connection)


def _note_reservation(connection, reservation):
    attempt = getattr(connection, 'info', {}).get(_ATTEMPT_KEY)
    if attempt is None:
        return
    from app.services.idempotency import _Reservation, _StoredReply
    if isinstance(reservation, _StoredReply):
        attempt.replayed_reply = reservation
    elif isinstance(reservation, _Reservation):
        attempt.reserved_new = True
    else:
        raise DomainError(ErrorCode.INTEGRITY_FAULT)


def _run_composed(service, operation):
    policy = service._retry_policy
    deadline = _now() + policy.total_seconds
    uncertain = False
    for index in range(3):  # Includes reconciliation: never a fourth transaction.
        remaining = deadline - _now()
        if remaining <= 0:
            _deadline(uncertain)
        if index:
            delay = min(remaining, uniform(0, policy.jitter_ms / 1000))
            if delay:
                _sleep(delay)  # Only after the preceding owner has fully unwound.
            if _now() >= deadline:
                _deadline(uncertain)
        attempt = _Attempt(deadline)
        try:
            return service._execute(operation, _attempt=attempt)
        except Exception:
            # These proofs were obtained from the DB, not the locally completed
            # uncommitted reply. _execute has already unwound every context here.
            if attempt.confirmed_reply is not None:
                return attempt.confirmed_reply
            if attempt.replayed_reply is not None:
                return attempt.replayed_reply
            if attempt.reserved_new:
                uncertain = False  # Same-key INSERT waited and won: old tx did not commit.
            if attempt.ambiguous or attempt.phase == 'commit' and not attempt.confirmed_failure:
                uncertain = True
                if index == 2:
                    _deadline(True)
                continue
            if uncertain:
                if attempt.confirmed_abort and index < 2:
                    continue
                _deadline(True)
            if attempt.confirmed_abort and index < 2:
                continue
            raise
