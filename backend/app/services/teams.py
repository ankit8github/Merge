"""Atomic internal creation/join operations. Identity is trusted, not authenticated.

Legacy create/join are internal compatibility facades. Future HTTP must use the
composed idempotent entry points and authenticate/authorize the trusted actor.
Engine ownership prevents caller-controlled partial commits.
"""
from dataclasses import dataclass
from contextlib import nullcontext
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError

from app.services.errors import DomainError, ErrorCode, map_database_error

if TYPE_CHECKING:
    from app.services.idempotency import _StoredReply
    from app.services.transaction_retry import TransactionRetryPolicy


@dataclass(frozen=True)
class TeamResult:
    team_id: UUID
    hackathon_id: UUID
    user_id: UUID
    member_count: int  # Actual rows at mutation time, not a persistent/cached field.


@dataclass(frozen=True, slots=True)
class _CreateTeamRequest:
    """Meaningful inputs only; no outcome UUID is allocated for a replay."""
    hackathon_id: UUID
    actor_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class _CreateTeamCommand:
    hackathon_id: UUID
    actor_id: UUID
    name: str
    team_id: UUID


@dataclass(frozen=True, slots=True)
class _JoinTeamCommand:
    hackathon_id: UUID
    team_id: UUID
    actor_id: UUID


def _uuid(value: UUID) -> None:
    if not isinstance(value, UUID):
        raise DomainError(ErrorCode.INVALID_INPUT)


def _query(c: Connection, statement: str, **parameters):
    from app.services.transaction_retry import _before_statement
    _before_statement(c)
    return c.execute(text(statement), parameters)


class TeamService:
    def __init__(self, engine: Engine, *, retry_policy: 'TransactionRetryPolicy | None' = None):
        if not isinstance(engine, Engine):
            raise TypeError('TeamService requires an Engine, never a caller transaction/session')
        self._engine = engine
        from app.services.transaction_retry import TransactionRetryPolicy
        if retry_policy is not None and not isinstance(retry_policy, TransactionRetryPolicy):
            raise TypeError('TeamService requires a TransactionRetryPolicy')
        self._retry_policy = retry_policy or TransactionRetryPolicy()

    def create_team(self, *, hackathon_id: UUID, actor_id: UUID, name: str) -> TeamResult:
        _uuid(hackathon_id)
        _uuid(actor_id)
        # Match the existing DB name contract, without a new naming policy.
        if not isinstance(name, str) or not 1 <= len(name) <= 120 or not name.strip(' '):
            raise DomainError(ErrorCode.INVALID_INPUT)
        team_id = uuid4()
        command = _CreateTeamCommand(hackathon_id, actor_id, name, team_id)
        return self._execute(lambda c: self._create_team_in_tx(c, command))

    def join_team(self, *, hackathon_id: UUID, team_id: UUID, actor_id: UUID) -> TeamResult:
        for value in (hackathon_id, team_id, actor_id):
            _uuid(value)
        command = _JoinTeamCommand(hackathon_id, team_id, actor_id)
        return self._execute(lambda c: self._join_team_in_tx(c, command))

    def create_team_idempotent(self, *, hackathon_id: UUID, actor_id: UUID,
                               name: str, key: str) -> '_StoredReply':
        """Compose one trusted-actor mutation; return only after _execute commits."""
        # Local import keeps the existing private command/fingerprint dependency
        # acyclic at module load. There is still only one transaction owner.
        from app.services.team_mutations import _create_team_idempotent
        return _create_team_idempotent(self, hackathon_id, actor_id, name, key)

    def join_team_idempotent(self, *, hackathon_id: UUID, team_id: UUID,
                             actor_id: UUID, key: str) -> '_StoredReply':
        """Trusted self-admission, not HTTP authorization or an invite workflow."""
        from app.services.team_mutations import _join_team_idempotent
        return _join_team_idempotent(self, hackathon_id, team_id, actor_id, key)

    def _create_team_in_tx(self, connection: Connection, command: _CreateTeamCommand) -> TeamResult:
        """Private operation on _execute's guarded connection; never owns a transaction."""
        c = connection
        hackathon_id, actor_id = command.hackathon_id, command.actor_id
        name, team_id = command.name, command.team_id
        hackathon = self._lock_subject(c, hackathon_id, actor_id)
        self._require_unassigned(c, hackathon_id, actor_id)
        _query(c, '''INSERT INTO public.teams
                (id,hackathon_id,name,min_team_size,max_team_size,leader_user_id,created_by)
                VALUES (:team,:hackathon,:name,:minimum,:maximum,:actor,:actor)''',
            team=team_id, hackathon=hackathon_id, name=name,
            minimum=hackathon.min_team_size, maximum=hackathon.max_team_size, actor=actor_id)
        # The new team is owned by this transaction. No preexisting team lock needed.
        self._insert_membership(c, hackathon_id, team_id, actor_id)
        return TeamResult(team_id, hackathon_id, actor_id, self._count(c, team_id))

    def _join_team_in_tx(self, connection: Connection, command: _JoinTeamCommand) -> TeamResult:
        """Private operation on _execute's guarded connection; never owns a transaction."""
        c = connection
        hackathon_id, team_id, actor_id = command.hackathon_id, command.team_id, command.actor_id
        self._lock_subject(c, hackathon_id, actor_id)
        team = _query(c, '''SELECT id,deleted_at,max_team_size FROM public.teams
                WHERE id=:team AND hackathon_id=:hackathon FOR NO KEY UPDATE''',
            team=team_id, hackathon=hackathon_id).one_or_none()
        if team is None:
            raise DomainError(ErrorCode.TEAM_NOT_FOUND)
        if team.deleted_at is not None:
            raise DomainError(ErrorCode.TEAM_DELETED)
        return self._admit_locked_in_tx(c, command, team)

    def _admit_locked_in_tx(self, c: Connection, command: _JoinTeamCommand, team) -> TeamResult:
        """Caller holds hackathon, subject user and exact live team locks.

        No lifecycle or new locks here: authorization workflows must check their
        own durable capability under the same owner before calling this helper.
        """
        hackathon_id, team_id, actor_id = command.hackathon_id, command.team_id, command.actor_id
        self._require_unassigned(c, hackathon_id, actor_id)
        # Fresh statement after parent lock: no ORM identity-map count reuse.
        if self._count(c, team_id) >= team.max_team_size:
            raise DomainError(ErrorCode.TEAM_FULL)
        self._insert_membership(c, hackathon_id, team_id, actor_id)
        return TeamResult(team_id, hackathon_id, actor_id, self._count(c, team_id))

    def _execute(self, operation, *, _attempt=None):
        try:
            if _attempt is not None:
                _attempt.check()
            with self._engine.connect() as c:
                self._require_transactional_connection(c)
                with (_attempt.bind(c) if _attempt is not None else nullcontext()):
                    try:
                        with c.begin():
                            _query(c, "SET LOCAL lock_timeout='5s'")
                            _query(c, "SET LOCAL statement_timeout='15s'")
                            result = operation(c)
                            if _attempt is not None:
                                _attempt.before_statement(c)
                                _attempt.phase = 'commit'
                        if _attempt is not None:
                            _attempt.phase = 'committed'
                            _attempt.confirmed_reply = result
                    except DBAPIError as error:
                        if _attempt is not None:
                            _attempt.database_failure(error)
                        raise
                    except Exception:
                        if _attempt is not None:
                            _attempt.failure_classified = True
                            _attempt.ambiguous = _attempt.phase == 'commit'
                        raise
                # Deferred FK/constraint-trigger failures at COMMIT are caught too.
            return result
        except DBAPIError as error:
            if _attempt is not None:
                _attempt.database_failure(error)
            raise map_database_error(error) from None

    @staticmethod
    def _require_transactional_connection(c: Connection) -> None:
        # SQLAlchemy's get_isolation_level() explicitly does NOT report DBAPI
        # AUTOCOMMIT. Use its documented pool-proxy DBAPI accessor and psycopg's
        # actual bool property before any service SQL, including SET LOCAL.
        if (getattr(c.dialect, 'name', None) != 'postgresql'
                or getattr(c.dialect, 'driver', None) != 'psycopg'
                or getattr(c.dialect, 'is_async', None) is not False):
            raise DomainError(ErrorCode.TRANSACTION_CONFIGURATION)
        try:
            autocommit = c.connection.dbapi_connection.autocommit
        except Exception:
            # An absent/unreadable state is not evidence of transaction safety.
            raise DomainError(ErrorCode.TRANSACTION_CONFIGURATION) from None
        if autocommit is not False or c.in_transaction():
            raise DomainError(ErrorCode.TRANSACTION_CONFIGURATION)
        # This metadata query can run only after autocommit has been ruled out.
        if c.get_isolation_level() != 'READ COMMITTED':
            raise DomainError(ErrorCode.TRANSACTION_CONFIGURATION)

    @staticmethod
    def _lock_subject(c, hackathon_id, actor_id):
        hackathon = _query(c, '''SELECT min_team_size,max_team_size FROM public.hackathons
            WHERE id=:hackathon FOR SHARE''', hackathon=hackathon_id).one_or_none()
        if hackathon is None:
            raise DomainError(ErrorCode.HACKATHON_NOT_FOUND)
        user = _query(c, 'SELECT id FROM public.users WHERE id=:actor FOR NO KEY UPDATE', actor=actor_id).one_or_none()
        if user is None:
            raise DomainError(ErrorCode.USER_NOT_FOUND)
        return hackathon

    @staticmethod
    def _require_unassigned(c, hackathon_id, actor_id):
        membership = _query(c, '''SELECT team_id FROM public.memberships
            WHERE hackathon_id=:hackathon AND user_id=:actor''',
            hackathon=hackathon_id, actor=actor_id).one_or_none()
        if membership is not None:
            raise DomainError(ErrorCode.ALREADY_ASSIGNED)

    @staticmethod
    def _insert_membership(c, hackathon_id, team_id, actor_id):
        _query(c, '''INSERT INTO public.memberships(hackathon_id,team_id,user_id)
            VALUES (:hackathon,:team,:actor)''', hackathon=hackathon_id, team=team_id, actor=actor_id)

    @staticmethod
    def _count(c, team_id):
        return _query(c, 'SELECT count(*) FROM public.memberships WHERE team_id=:team', team=team_id).scalar_one()
