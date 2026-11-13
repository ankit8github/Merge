"""Leave/removal composition under the existing transaction and retry owner."""
from hashlib import sha256
from uuid import uuid4

from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import (_IdempotencyCommand, _Fingerprint, _StoredReply,
    _canonical, _key, _reserve_in_tx, _complete_in_tx)
from app.services.teams import TeamService, TeamResult, _query, _uuid
from app.services.team_mutations import _outbox_in_tx, _fault
from app.services.transaction_retry import _run_composed, _note_reservation


class LifecycleError(DomainError):
    """Narrow HTTP mapping, preserving existing adapters' error contracts."""


def deny(code):
    raise LifecycleError(code)


def command(h, t, actor, key, subject=None):
    for value in (h, t, actor): _uuid(value)
    _key(key)
    operation = 'team.leave.v1' if subject is None else 'member.remove.v1'
    target = actor if subject is None else subject
    _uuid(target)
    if subject == actor: deny(ErrorCode.USE_LEAVE)
    document = dict(schema_version=1, actor_id=str(actor), hackathon_id=str(h),
        operation=operation, command=dict(team_id=str(t), user_id=str(target)))
    return _IdempotencyCommand(actor, h, operation, key,
        _Fingerprint(sha256(_canonical(document).encode('utf-8')).digest()))


def state(team, count, subject, member):
    deleted = team['deleted_at'] is not None
    return dict(schema_version=1, subject=dict(user_id=str(subject), member=member), team=dict(
        version=team['version'], member_count=count,
        leader_user_id=None if team['leader_user_id'] is None else str(team['leader_user_id']),
        min_team_size=team['min_team_size'], max_team_size=team['max_team_size'], deleted=deleted,
        readiness='deleted' if deleted else 'ready' if count >= team['min_team_size'] else 'forming'))


class LifecycleService(TeamService):
    def leave(self, *, hackathon_id, team_id, actor_id, key):
        scope = command(hackathon_id, team_id, actor_id, key)
        return self._run(lambda c: self._change(c, scope, team_id, actor_id, False))

    def remove(self, *, hackathon_id, team_id, actor_id, user_id, key):
        scope = command(hackathon_id, team_id, actor_id, key, user_id)
        return self._run(lambda c: self._change(c, scope, team_id, user_id, True))

    def _run(self, operation):
        try:
            return _run_composed(self, operation)
        except DomainError as error:
            raise LifecycleError(error.code, retryable=error.retryable) from None

    def _change(self, c, scope, team_id, subject, removing):
        reserved = _reserve_in_tx(c, scope)
        if isinstance(reserved, _StoredReply) and not removing:
            # This authenticated actor owns the old receipt, even after deletion
            # or joining elsewhere. Never execute a second departure on replay.
            _note_reservation(c, reserved)
            return reserved
        if not isinstance(reserved, _StoredReply): _note_reservation(c, reserved)
        h, actor = scope.hackathon_id, scope.actor_id
        if _query(c, 'SELECT id FROM public.hackathons WHERE id=:h FOR SHARE', h=h).one_or_none() is None:
            deny(ErrorCode.HACKATHON_NOT_FOUND)
        missing = False
        for user in sorted({actor, subject}):
            if _query(c, 'SELECT id FROM public.users WHERE id=:actor FOR NO KEY UPDATE', actor=user).one_or_none() is None:
                missing = True
        team = _query(c, '''SELECT id,leader_user_id,deleted_at,min_team_size,max_team_size,version
            FROM public.teams WHERE id=:team AND hackathon_id=:h FOR NO KEY UPDATE''',
            team=team_id, h=h).mappings().one_or_none()
        if team is None or team['deleted_at'] is not None: deny(ErrorCode.TEAM_NOT_FOUND)
        if removing and team['leader_user_id'] != actor: deny(ErrorCode.FORBIDDEN)
        if isinstance(reserved, _StoredReply):
            _note_reservation(c, reserved)  # Only after current leader authorization.
            return reserved
        if missing: deny(ErrorCode.MEMBER_NOT_FOUND)
        member = _query(c, '''SELECT user_id FROM public.memberships
            WHERE hackathon_id=:h AND team_id=:team AND user_id=:subject''',
            h=h, team=team_id, subject=subject).scalar_one_or_none()
        if member != subject: deny(ErrorCode.MEMBER_NOT_FOUND)
        before = state(team, self._count(c, team_id), subject, True)
        removed = _query(c, '''DELETE FROM public.memberships
            WHERE hackathon_id=:h AND team_id=:team AND user_id=:subject RETURNING user_id''',
            h=h, team=team_id, subject=subject).scalar_one_or_none()
        if removed != subject: _fault()
        count = self._count(c, team_id)
        leader = team['leader_user_id']
        if leader == subject:
            # Parent lock protects all roster writers. No late user/row lock.
            leader = _query(c, '''SELECT user_id FROM public.memberships
                WHERE team_id=:team ORDER BY joined_at,user_id LIMIT 1''', team=team_id).scalar_one_or_none()
        if count != before['team']['member_count'] - 1 or (leader is None) != (count == 0): _fault()
        after = _query(c, '''UPDATE public.teams
            SET leader_user_id=:leader,deleted_at=CASE WHEN :deleted THEN clock_timestamp() ELSE NULL END,
                version=version+1,updated_at=clock_timestamp()
            WHERE id=:team AND hackathon_id=:h AND deleted_at IS NULL AND version<9223372036854775807
            RETURNING id,leader_user_id,deleted_at,min_team_size,max_team_size,version''',
            leader=leader, deleted=count == 0, team=team_id, h=h).mappings().one_or_none()
        if after is None: _fault()
        audit = uuid4()
        saved = _query(c, '''INSERT INTO public.audit_events
            (id,idempotency_record_id,actor_id,hackathon_id,team_id,team_version,action,old_state,new_state)
            VALUES (:id,:reservation,:actor,:hackathon,:team,:version,:action,CAST(:before AS jsonb),CAST(:after AS jsonb)) RETURNING id''',
            id=audit, reservation=reserved.record_id, actor=actor, hackathon=h, team=team_id,
            version=after['version'], action=scope.operation, before=_canonical(before),
            after=_canonical(state(after, count, subject, False))).scalar_one_or_none()
        if saved != audit: _fault()
        _outbox_in_tx(c, audit, TeamResult(team_id, h, subject, count), after['version'])
        reply = _StoredReply._from_values(200, dict(schema_version=1, data=dict(
            hackathon_id=str(h), team_id=str(team_id), user_id=str(subject), member_count=count,
            team_version=after['version'], leader_user_id=None if leader is None else str(leader), deleted=count == 0)),
            {'content-type':'application/json', 'cache-control':'no-store'})
        return _complete_in_tx(c, reserved, reply)

    def members(self, *, hackathon_id, team_id, actor_id, limit=20, cursor=None):
        for value in (hackathon_id, team_id, actor_id): _uuid(value)
        if type(limit) is not int or not 1 <= limit <= 100: deny(ErrorCode.INVALID_INPUT)
        if cursor is not None: _uuid(cursor)
        def read(c):
            _query(c, 'SET TRANSACTION READ ONLY')
            row = _query(c, '''SELECT
                EXISTS(SELECT 1 FROM public.memberships m WHERE m.team_id=t.id AND m.hackathon_id=t.hackathon_id AND m.user_id=:actor) AS allowed,
                (CAST(:cursor AS uuid) IS NULL OR EXISTS(SELECT 1 FROM public.memberships m WHERE m.team_id=t.id AND m.user_id=CAST(:cursor AS uuid))) AS cursor_ok,
                COALESCE((SELECT json_agg(page ORDER BY page.user_id) FROM
                    (SELECT m.user_id,u.display_name,m.joined_at FROM public.memberships m
                     JOIN public.users u ON u.id=m.user_id WHERE m.team_id=t.id
                     AND (CAST(:cursor AS uuid) IS NULL OR m.user_id>CAST(:cursor AS uuid))
                     AND EXISTS(SELECT 1 FROM public.memberships own WHERE own.team_id=t.id AND own.user_id=:actor)
                     ORDER BY m.user_id LIMIT :size) page),'[]'::json) AS items
                FROM public.teams t WHERE t.id=:team AND t.hackathon_id=:h AND t.deleted_at IS NULL''',
                actor=actor_id, cursor=cursor, size=limit+1, team=team_id, h=hackathon_id).mappings().one_or_none()
            if row is None: deny(ErrorCode.TEAM_NOT_FOUND)
            if not row['allowed']: deny(ErrorCode.FORBIDDEN)
            if not row['cursor_ok']: deny(ErrorCode.INVALID_INPUT)
            items = row['items'][:limit]
            return dict(items=items, next_cursor=items[-1]['user_id'] if len(row['items'])>limit else None)
        try:
            return self._execute(read)
        except DomainError as error:
            raise LifecycleError(error.code, retryable=error.retryable) from None
