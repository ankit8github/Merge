"""Durable leader-authorized admission under the existing single transaction owner."""
from hashlib import sha256
from datetime import datetime
from uuid import UUID, uuid4

from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import (_IdempotencyCommand, _Fingerprint, _StoredReply,
    _canonical, _key, _reserve_in_tx, _complete_in_tx)
from app.services.teams import TeamService, TeamResult, _JoinTeamCommand, _uuid, _query
from app.services.team_mutations import _outbox_in_tx, _state, _fault
from app.services.transaction_retry import _run_composed, _note_reservation

FIELDS = 'id,hackathon_id,team_id,requester_id,status,created_at,resolved_at'


class AdmissionError(DomainError):
    """Separate HTTP mapping; legacy team-create errors keep their contract."""


def _deny(code):
    raise AdmissionError(code)


def _dto(row):
    return {key: str(row[key]) if isinstance(row[key], UUID) else
            row[key].isoformat() if isinstance(row[key], datetime)
            else row[key] for key in FIELDS.split(',')}


def _command(hackathon, team, actor, key, request=None, decision=None):
    for value in (hackathon, team, actor):
        _uuid(value)
    _key(key)
    operation = 'request.create.v1'
    meaningful = {'team_id': str(team)}
    if request is not None:
        _uuid(request)
        if decision not in ('approve', 'reject'):
            _deny(ErrorCode.INVALID_INPUT)
        operation = 'request.decide.v1'
        meaningful.update(request_id=str(request), decision=decision)
    elif decision is not None:
        _deny(ErrorCode.INVALID_INPUT)
    document = dict(schema_version=1, actor_id=str(actor), hackathon_id=str(hackathon),
                    operation=operation, command=meaningful)
    return _IdempotencyCommand(actor, hackathon, operation, key,
        _Fingerprint(sha256(_canonical(document).encode('utf-8')).digest()))


def _reply(row, status=200):
    return _StoredReply._from_values(status, {'schema_version': 1, 'data': _dto(row)},
        {'content-type': 'application/json', 'cache-control': 'no-store'})


def _run(service, operation):
    try:
        return _run_composed(service, operation)
    except DomainError as error:
        # Include deferred constraint errors mapped by the shared owner, without
        # changing legacy creation/join HTTP error contracts.
        raise AdmissionError(error.code, retryable=error.retryable) from None


class AdmissionService(TeamService):
    def create_request(self, *, hackathon_id: UUID, team_id: UUID, actor_id: UUID, key: str) -> _StoredReply:
        scope = _command(hackathon_id, team_id, actor_id, key)
        return _run(self, lambda c: self._change(c, scope, team_id))

    def decide_request(self, *, hackathon_id: UUID, team_id: UUID, actor_id: UUID,
                       request_id: UUID, decision: str, key: str) -> _StoredReply:
        _uuid(request_id)
        scope = _command(hackathon_id, team_id, actor_id, key, request_id, decision)
        return _run(self, lambda c: self._change(c, scope, team_id, request_id, decision))

    def _lock(self, c, hackathon, team_id, users):
        if _query(c, 'SELECT id FROM public.hackathons WHERE id=:h FOR SHARE', h=hackathon).one_or_none() is None:
            _deny(ErrorCode.HACKATHON_NOT_FOUND)
        for user in sorted(set(users)):
            if _query(c, 'SELECT id FROM public.users WHERE id=:actor FOR NO KEY UPDATE', actor=user).one_or_none() is None:
                _deny(ErrorCode.USER_NOT_FOUND)
        team = _query(c, '''SELECT id,leader_user_id,deleted_at,max_team_size FROM public.teams
            WHERE id=:team AND hackathon_id=:h FOR NO KEY UPDATE''', team=team_id, h=hackathon).one_or_none()
        if team is None or team.deleted_at is not None:
            _deny(ErrorCode.TEAM_NOT_FOUND)
        return team

    def _change(self, c, scope, team_id, request_id=None, decision=None):
        reserved = _reserve_in_tx(c, scope)
        if not isinstance(reserved, _StoredReply):
            _note_reservation(c, reserved)
        h, actor = scope.hackathon_id, scope.actor_id
        subject = actor
        if request_id is not None:
            # Identity is DB-immutable. No row lock before the user/team locks.
            identity = _query(c, '''SELECT requester_id FROM public.join_requests
                WHERE id=:id AND hackathon_id=:h AND team_id=:team''',
                id=request_id, h=h, team=team_id).scalar_one_or_none()
            # Lock/check leader even for an unknown request: do not reveal existence.
            subject = identity if identity is not None else actor
        team = self._lock(c, h, team_id, (actor, subject))
        if request_id is not None and team.leader_user_id != actor:
            _deny(ErrorCode.FORBIDDEN)
        if request_id is None:
            row = _query(c, f'''SELECT {FIELDS} FROM public.join_requests
                WHERE hackathon_id=:h AND team_id=:team AND requester_id=:actor FOR NO KEY UPDATE''',
                h=h, team=team_id, actor=actor).mappings().one_or_none()
        else:
            row = _query(c, f'''SELECT {FIELDS} FROM public.join_requests
                WHERE id=:id AND hackathon_id=:h AND team_id=:team FOR NO KEY UPDATE''',
                id=request_id, h=h, team=team_id).mappings().one_or_none()
            if row is None:
                _deny(ErrorCode.REQUEST_NOT_FOUND)
            if row['requester_id'] != subject:
                _fault()
        # Replay is immutable, but current authorization is still required.
        if isinstance(reserved, _StoredReply):
            # The runner may return a noted replay despite later exceptions.
            # Do not grant that proof before current authorization succeeds.
            _note_reservation(c, reserved)
            return reserved
        if request_id is None and row is not None:
            return _complete_in_tx(c, reserved, _reply(row))
        before = None if row is None else dict(row)
        if request_id is None:
            self._require_unassigned(c, h, actor)
            row = _query(c, f'''INSERT INTO public.join_requests(id,hackathon_id,team_id,requester_id)
                VALUES (:id,:h,:team,:actor) RETURNING {FIELDS}''',
                id=uuid4(), h=h, team=team_id, actor=actor).mappings().one()
        else:
            if row['status'] != 'pending':
                _deny(ErrorCode.REQUEST_RESOLVED)
            if decision == 'approve':
                self._admit_locked_in_tx(c, _JoinTeamCommand(h, team_id, subject), team)
            row = _query(c, f'''UPDATE public.join_requests
                SET status=:status,resolved_at=clock_timestamp(),resolved_by=:actor
                WHERE id=:id AND status='pending' RETURNING {FIELDS}''',
                id=request_id, actor=actor, status='approved' if decision == 'approve' else 'rejected').mappings().one()
        self._record(c, reserved, team_id, subject, before, row)
        return _complete_in_tx(c, reserved, _reply(row, 201 if request_id is None else 200))

    def _record(self, c, reserved, team_id, subject, before, after):
        row = _query(c, '''UPDATE public.teams SET version=version+1,updated_at=clock_timestamp()
            WHERE id=:team AND hackathon_id=:h AND version<9223372036854775807 AND deleted_at IS NULL
            RETURNING version,leader_user_id,min_team_size,max_team_size''',
            team=team_id, h=reserved.command.hackathon_id).mappings().one_or_none()
        if row is None:
            _fault()
        count = self._count(c, team_id)
        admitted = after['status'] == 'approved'
        member = _query(c, '''SELECT EXISTS(SELECT 1 FROM public.memberships
            WHERE hackathon_id=:h AND team_id=:team AND user_id=:actor)''',
            h=reserved.command.hackathon_id, team=team_id, actor=subject).scalar_one()
        if admitted and not member:
            _fault()
        old = _state(row, count-int(admitted), subject, member and not admitted, row['version']-1)
        new = _state(row, count, subject, member, row['version'])
        old['request'] = None if before is None else {'id': str(before['id']), 'status': before['status']}
        new['request'] = {'id': str(after['id']), 'status': after['status']}
        audit = uuid4()
        saved = _query(c, '''INSERT INTO public.audit_events
            (id,idempotency_record_id,actor_id,hackathon_id,team_id,team_version,action,old_state,new_state)
            VALUES (:id,:reservation,:actor,:hackathon,:team,:version,:action,CAST(:before AS jsonb),CAST(:after AS jsonb)) RETURNING id''',
            id=audit, reservation=reserved.record_id, actor=reserved.command.actor_id,
            hackathon=reserved.command.hackathon_id, team=team_id, version=row['version'],
            action=reserved.command.operation, before=_canonical(old), after=_canonical(new)).scalar_one_or_none()
        if saved != audit:
            _fault()
        result = TeamResult(team_id, reserved.command.hackathon_id, subject, count)
        _outbox_in_tx(c, audit, result, row['version'])

    def own_request(self, *, hackathon_id: UUID, team_id: UUID, actor_id: UUID) -> dict:
        for value in (hackathon_id, team_id, actor_id): _uuid(value)
        def read(c):
            _query(c, 'SET TRANSACTION READ ONLY')
            row = _query(c, '''SELECT t.id, (SELECT row_to_json(r) FROM public.join_requests r
                WHERE r.team_id=t.id AND r.hackathon_id=t.hackathon_id AND r.requester_id=:actor) AS request
                FROM public.teams t WHERE t.id=:team AND t.hackathon_id=:h AND t.deleted_at IS NULL''',
                h=hackathon_id, team=team_id, actor=actor_id).mappings().one_or_none()
            if row is None: _deny(ErrorCode.TEAM_NOT_FOUND)
            return {'request': None if row['request'] is None else _dto(row['request'])}
        return self._execute(read)

    def pending_requests(self, *, hackathon_id: UUID, team_id: UUID, actor_id: UUID,
                         limit: int = 20, cursor: UUID | None = None) -> dict:
        for value in (hackathon_id, team_id, actor_id): _uuid(value)
        if type(limit) is not int or not 1 <= limit <= 100: _deny(ErrorCode.INVALID_INPUT)
        if cursor is not None: _uuid(cursor)
        def read(c):
            _query(c, 'SET TRANSACTION READ ONLY')
            row = _query(c, '''SELECT t.leader_user_id,
                (CAST(:cursor AS uuid) IS NULL OR EXISTS(SELECT 1 FROM public.join_requests a
                    WHERE a.id=CAST(:cursor AS uuid) AND a.team_id=t.id AND a.hackathon_id=t.hackathon_id)) AS cursor_ok,
                COALESCE((SELECT json_agg(page ORDER BY page.id) FROM
                    (SELECT r.* FROM public.join_requests r
                     WHERE r.team_id=t.id AND r.hackathon_id=t.hackathon_id AND r.status='pending'
                     AND (CAST(:cursor AS uuid) IS NULL OR r.id>CAST(:cursor AS uuid))
                     AND t.leader_user_id=:actor ORDER BY r.id LIMIT :size) page),'[]'::json) AS items
                FROM public.teams t WHERE t.id=:team AND t.hackathon_id=:h AND t.deleted_at IS NULL''',
                h=hackathon_id, team=team_id, actor=actor_id, cursor=cursor, size=limit+1).mappings().one_or_none()
            if row is None: _deny(ErrorCode.TEAM_NOT_FOUND)
            if row['leader_user_id'] != actor_id: _deny(ErrorCode.FORBIDDEN)
            if not row['cursor_ok']: _deny(ErrorCode.INVALID_INPUT)
            items = [_dto(item) for item in row['items'][:limit]]
            return {'items': items, 'next_cursor': items[-1]['id'] if len(row['items'])>limit else None}
        return self._execute(read)
