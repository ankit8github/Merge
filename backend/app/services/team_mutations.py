"""Private atomic composition. Never owns a connection, transaction or retry.

Actor UUIDs are supplied by trusted internal code. A future HTTP boundary must
derive them from an authenticated principal and apply current authorization.
"""
from uuid import UUID, uuid4

from sqlalchemy.engine import Connection

from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import (
    _command, _reserve_in_tx, _complete_in_tx, _StoredReply, _canonical,
)
from app.services.teams import (
    TeamService, TeamResult, _CreateTeamCommand, _CreateTeamRequest, _JoinTeamCommand, _query,
)


def _create_team_idempotent(service: TeamService, hackathon_id: UUID, actor_id: UUID,
                            name: str, key: str) -> _StoredReply:
    request = _CreateTeamRequest(hackathon_id, actor_id, name)
    scope = _command(request, key)  # Full validation before acquiring a connection.
    return service._execute(lambda c: _mutate_in_tx(service, c, request, scope))


def _join_team_idempotent(service: TeamService, hackathon_id: UUID, team_id: UUID,
                          actor_id: UUID, key: str) -> _StoredReply:
    request = _JoinTeamCommand(hackathon_id, team_id, actor_id)
    scope = _command(request, key)
    return service._execute(lambda c: _mutate_in_tx(service, c, request, scope))


def _fault():
    raise DomainError(ErrorCode.INTEGRITY_FAULT) from None


def _state(row, count: int, subject: UUID, member: bool, version: int) -> dict:
    return {'schema_version': 1,
            'team': {'version': version, 'member_count': count,
                     'leader_user_id': str(row['leader_user_id']),
                     'min_team_size': row['min_team_size'], 'max_team_size': row['max_team_size'],
                     'readiness': 'ready' if count >= row['min_team_size'] else 'forming'},
            'subject': {'user_id': str(subject), 'member': member}}


def _version_in_tx(c: Connection, result: TeamResult, creating: bool):
    if creating:
        row = _query(c, '''SELECT version,leader_user_id,min_team_size,max_team_size
            FROM public.teams WHERE id=:team AND hackathon_id=:hackathon AND deleted_at IS NULL''',
            team=result.team_id, hackathon=result.hackathon_id).mappings().one_or_none()
    else:
        # _join_team_in_tx retains its NO KEY UPDATE lock through the owner's
        # commit. No new user/team lock or pre-lock snapshot is introduced here.
        row = _query(c, '''UPDATE public.teams SET version=version+1,updated_at=clock_timestamp()
            WHERE id=:team AND hackathon_id=:hackathon AND deleted_at IS NULL
              AND version<9223372036854775807
            RETURNING version,leader_user_id,min_team_size,max_team_size''',
            team=result.team_id, hackathon=result.hackathon_id).mappings().one_or_none()
    if (row is None or type(row['version']) is not int or not 1 <= row['version'] < 2**63
            or not isinstance(row['leader_user_id'], UUID)
            or not 1 <= result.member_count <= row['max_team_size']
            or (creating and (row['version'] != 1 or result.member_count != 1
                              or row['leader_user_id'] != result.user_id))
            or (not creating and (row['version'] < 2 or result.member_count < 2))):
        _fault()
    return row


def _audit_in_tx(c, reservation, result, row, creating):
    version = row['version']
    after = _state(row, result.member_count, result.user_id, True, version)
    # Exactly one membership was inserted. Join does not change leader or sizes,
    # and the existing parent lock excludes another supported mutation throughout.
    before = None if creating else _state(row, result.member_count-1, result.user_id, False, version-1)
    audit_id = uuid4()
    saved = _query(c, '''INSERT INTO public.audit_events
        (id,idempotency_record_id,actor_id,hackathon_id,team_id,team_version,action,old_state,new_state)
        VALUES (:id,:reservation,:actor,:hackathon,:team,:version,:action,
                CAST(:before AS jsonb),CAST(:after AS jsonb)) RETURNING id''',
        id=audit_id, reservation=reservation.record_id, actor=reservation.command.actor_id,
        hackathon=result.hackathon_id, team=result.team_id, version=version,
        action=reservation.command.operation,
        before=None if before is None else _canonical(before), after=_canonical(after)).scalar_one_or_none()
    if saved != audit_id:
        _fault()
    return audit_id


def _outbox_in_tx(c, audit_id, result, version):
    event_id = uuid4()
    payload = {'hackathon_id': str(result.hackathon_id), 'team_id': str(result.team_id),
               'team_version': version}
    saved = _query(c, '''INSERT INTO public.outbox_events
        (id,audit_event_id,event_type,schema_version,payload,published_at,attempt_count)
        VALUES (:id,:audit,'team.changed.v1',1,CAST(:payload AS jsonb),NULL,0) RETURNING id''',
        id=event_id, audit=audit_id, payload=_canonical(payload)).scalar_one_or_none()
    if saved != event_id:
        _fault()


def _mutate_in_tx(service, c, request, scope) -> _StoredReply:
    reservation = _reserve_in_tx(c, scope)
    if isinstance(reservation, _StoredReply):
        return reservation  # No IDs, domain locks, versions, audit or outbox writes.
    creating = isinstance(request, _CreateTeamRequest)
    if creating:
        command = _CreateTeamCommand(request.hackathon_id, request.actor_id, request.name, uuid4())
        result = service._create_team_in_tx(c, command)
    else:
        result = service._join_team_in_tx(c, request)
    row = _version_in_tx(c, result, creating)
    audit_id = _audit_in_tx(c, reservation, result, row, creating)
    _outbox_in_tx(c, audit_id, result, row['version'])
    reply = _StoredReply._from_values(201 if creating else 200,
        {'schema_version': 1, 'data': {'team_id': str(result.team_id),
         'hackathon_id': str(result.hackathon_id), 'user_id': str(result.user_id),
         'member_count': result.member_count, 'team_version': row['version']}},
        {'content-type': 'application/json', 'cache-control': 'no-store'})
    return _complete_in_tx(c, reservation, reply)
