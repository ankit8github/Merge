"""Private, synchronous primitives; the caller owns the connection and transaction.

Never return a newly completed reply to a client until the owner commits. There
are deliberately no public mutation entry points or automatic transaction retries.
"""
from dataclasses import dataclass, field
from hashlib import sha256
from hmac import compare_digest
import json
from uuid import UUID, uuid4

from sqlalchemy.engine import Connection

from app.services.errors import DomainError, ErrorCode
from app.services.teams import _CreateTeamCommand, _CreateTeamRequest, _JoinTeamCommand, _query

_OPERATIONS = ('team.create.v1', 'team.join.v1', 'request.create.v1', 'request.decide.v1',
               'invitation.issue.v1', 'invitation.redeem.v1', 'team.leave.v1', 'member.remove.v1')
_MAX_REPLY_BYTES = 16_384
_HEADERS = {'content-type': 'application/json', 'cache-control': 'no-store'}


def _invalid():
    raise DomainError(ErrorCode.INVALID_INPUT) from None


def _fault():
    raise DomainError(ErrorCode.INTEGRITY_FAULT) from None


def _key(value: str) -> None:
    # Match ck_idempotency_key exactly, including leading/trailing/all spaces.
    if not isinstance(value, str) or not 1 <= len(value) <= 128 or any(
            not ' ' <= char <= '~' for char in value):
        _invalid()


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True, slots=True, repr=False)
class _Fingerprint:
    digest: bytes = field(repr=False)

    def __post_init__(self):
        if type(self.digest) is not bytes or len(self.digest) != 32:
            _invalid()


@dataclass(frozen=True, slots=True, repr=False)
class _IdempotencyCommand:
    actor_id: UUID
    hackathon_id: UUID
    operation: str
    key: str = field(repr=False)
    fingerprint: _Fingerprint = field(repr=False)

    def __post_init__(self):
        _key(self.key)
        if (not isinstance(self.actor_id, UUID) or not isinstance(self.hackathon_id, UUID)
                or self.operation not in _OPERATIONS
                or not isinstance(self.fingerprint, _Fingerprint)):
            _invalid()


def _command(command: _CreateTeamCommand | _CreateTeamRequest | _JoinTeamCommand, key: str) -> _IdempotencyCommand:
    """Validate and fingerprint meaningful inputs, without normalizing user text."""
    _key(key)
    if not isinstance(command, (_CreateTeamCommand, _CreateTeamRequest, _JoinTeamCommand)):
        _invalid()
    if not isinstance(command.actor_id, UUID) or not isinstance(command.hackathon_id, UUID):
        _invalid()
    if isinstance(command, (_CreateTeamCommand, _CreateTeamRequest)):
        name = command.name
        if not isinstance(name, str) or not 1 <= len(name) <= 120 or not name.strip(' ') or '\x00' in name:
            _invalid()
        operation, meaningful = _OPERATIONS[0], {'name': name}
    else:
        if not isinstance(command.team_id, UUID):
            _invalid()
        operation, meaningful = _OPERATIONS[1], {'team_id': str(command.team_id)}
    document = {'schema_version': 1, 'actor_id': str(command.actor_id),
                'hackathon_id': str(command.hackathon_id), 'operation': operation,
                'command': meaningful}
    try:
        serialized = _canonical(document).encode('utf-8')
    except (ValueError, UnicodeError):
        _invalid()
    return _IdempotencyCommand(command.actor_id, command.hackathon_id, operation,
                               key, _Fingerprint(sha256(serialized).digest()))


def _reply_json(body) -> str:
    """Bound work and JSONB-compatible values before serialization or storage."""
    budget = 1024

    def visit(value, depth):
        nonlocal budget
        budget -= 1
        if budget < 0 or depth > 8:
            _fault()
        if value is None or type(value) is bool:
            return
        if type(value) is int and -(2**63) <= value < 2**63:
            return
        if type(value) is str:
            if len(value) > 4096 or '\x00' in value:
                _fault()
            return
        if type(value) is list and len(value) <= 128:
            for item in value:
                visit(item, depth + 1)
            return
        if type(value) is dict and len(value) <= 128:
            for key, item in value.items():
                if type(key) is not str:
                    _fault()
                visit(key, depth + 1)
                visit(item, depth + 1)
            return
        _fault()

    if (type(body) is not dict or len(body) != 2 or set(body) != {'schema_version', 'data'}
            or type(body['schema_version']) is not int or body['schema_version'] != 1
            or type(body['data']) is not dict):
        _fault()
    visit(body, 0)
    try:
        serialized = _canonical(body)
        if len(serialized.encode('utf-8')) > _MAX_REPLY_BYTES:
            _fault()
    except (ValueError, UnicodeError):
        _fault()
    return serialized


@dataclass(frozen=True, slots=True, repr=False)
class _StoredReply:
    http_status: int
    _body_json: str = field(repr=False)
    headers: tuple[tuple[str, str], ...] = field(repr=False)

    def __post_init__(self):
        if type(self.http_status) is not int or not 200 <= self.http_status <= 299:
            _fault()
        if type(self._body_json) is not str or len(self._body_json) > _MAX_REPLY_BYTES:
            _fault()
        try:
            body = json.loads(self._body_json)
        except (ValueError, RecursionError):
            _fault()
        if _reply_json(body) != self._body_json:
            _fault()
        if (type(self.headers) is not tuple or len(self.headers) > len(_HEADERS)
                or any(type(pair) is not tuple or len(pair) != 2
                       or type(pair[0]) is not str or type(pair[1]) is not str
                       or _HEADERS.get(pair[0]) != pair[1] for pair in self.headers)
                or len({pair[0] for pair in self.headers}) != len(self.headers)):
            _fault()

    @classmethod
    def _from_values(cls, status: int, body: dict, headers: dict):
        if type(headers) is not dict or len(headers) > len(_HEADERS):
            _fault()
        if any(type(k) is not str or type(v) is not str for k, v in headers.items()):
            _fault()
        return cls(status, _reply_json(body), tuple(sorted(headers.items())))

    def body(self) -> dict:
        return json.loads(self._body_json)  # Fresh value; caller cannot mutate retained state.


@dataclass(frozen=True, slots=True, repr=False)
class _Reservation:
    record_id: UUID
    command: _IdempotencyCommand = field(repr=False)
    connection: Connection = field(repr=False)
    transaction: object = field(repr=False)


def _active_transaction(connection: Connection):
    """Reject actual DBAPI AUTOCOMMIT before reservation SQL, including direct use."""
    try:
        transaction = connection.get_transaction()
        valid = (connection.dialect.name == 'postgresql'
                 and connection.dialect.driver == 'psycopg'
                 and connection.dialect.is_async is False
                 and connection.connection.dbapi_connection.autocommit is False
                 and transaction is not None and transaction.is_active
                 and connection.in_transaction() and not connection.in_nested_transaction()
                 and connection.get_isolation_level() == 'READ COMMITTED')
    except Exception:
        valid = False
    if not valid:
        raise DomainError(ErrorCode.TRANSACTION_CONFIGURATION)
    return transaction


def _scope(command: _IdempotencyCommand) -> dict:
    return {'actor': command.actor_id, 'hackathon': command.hackathon_id,
            'operation': command.operation, 'key': command.key,
            'fingerprint': command.fingerprint.digest}


def _reserve_in_tx(connection: Connection, command: _IdempotencyCommand) -> _Reservation | _StoredReply:
    if not isinstance(command, _IdempotencyCommand):
        _invalid()
    command.__post_init__()
    transaction = _active_transaction(connection)
    record_id = _query(connection, '''INSERT INTO public.idempotency_records
        (id,actor_id,hackathon_id,operation,key,request_hash)
        VALUES (:id,:actor,:hackathon,:operation,:key,:fingerprint)
        ON CONFLICT ON CONSTRAINT uq_idempotency_scope DO NOTHING RETURNING id''',
        id=uuid4(), **_scope(command)).scalar_one_or_none()
    if record_id is not None:
        if not isinstance(record_id, UUID):
            _fault()
        return _Reservation(record_id, command, connection, transaction)

    # A separate statement is essential: READ COMMITTED gets a fresh snapshot
    # after ON CONFLICT has waited for a previously invisible winning INSERT.
    row = _query(connection, '''SELECT actor_id,hackathon_id,operation,key,request_hash,
        state,http_status,response_body,response_headers FROM public.idempotency_records
        WHERE actor_id=:actor AND operation=:operation AND key=:key''',
        actor=command.actor_id, operation=command.operation, key=command.key).mappings().one_or_none()
    if (row is None or row['actor_id'] != command.actor_id
            or row['operation'] != command.operation or row['key'] != command.key):
        _fault()
    if row['state'] != 'completed':
        _fault()
    if (not isinstance(row['request_hash'], bytes) or len(row['request_hash']) != 32
            or not isinstance(row['hackathon_id'], UUID)):
        _fault()
    if row['hackathon_id'] != command.hackathon_id or not compare_digest(row['request_hash'], command.fingerprint.digest):
        raise DomainError(ErrorCode.IDEMPOTENCY_MISMATCH) from None
    return _StoredReply._from_values(row['http_status'], row['response_body'], row['response_headers'])


def _complete_in_tx(connection: Connection, reservation: _Reservation, reply: _StoredReply) -> _StoredReply:
    transaction = _active_transaction(connection)
    if (not isinstance(reservation, _Reservation) or reservation.connection is not connection
            or reservation.transaction is not transaction or not isinstance(reply, _StoredReply)):
        _fault()
    reply.__post_init__()
    record_id = _query(connection, '''UPDATE public.idempotency_records
        SET state='completed',http_status=:status,response_body=CAST(:body AS jsonb),
            response_headers=CAST(:headers AS jsonb),completed_at=clock_timestamp()
        WHERE id=:id AND actor_id=:actor AND hackathon_id=:hackathon
          AND operation=:operation AND key=:key AND request_hash=:fingerprint
          AND state='pending' RETURNING id''', id=reservation.record_id,
        status=reply.http_status, body=reply._body_json,
        headers=_canonical(dict(reply.headers)), **_scope(reservation.command)).scalar_one_or_none()
    if record_id != reservation.record_id:
        _fault()
    return reply
