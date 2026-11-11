"""Recipient-bound admission; the existing owner commits the complete chain."""
from hashlib import sha256
from uuid import UUID, uuid4

from app.services.admission import AdmissionService
from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import (_IdempotencyCommand, _Fingerprint, _StoredReply,
    _canonical, _key, _reserve_in_tx, _complete_in_tx)
from app.services.teams import _JoinTeamCommand, _query, _uuid, TeamResult
from app.services.team_mutations import _state, _fault, _outbox_in_tx
from app.services.transaction_retry import _run_composed, _note_reservation

FIELDS = 'id,hackathon_id,team_id,recipient_id,issued_by,status,created_at,expires_at,redeemed_at'


class InvitationError(DomainError):
    pass


def deny(code):
    raise InvitationError(code)


def dto(row):
    from datetime import datetime
    return {k: str(row[k]) if isinstance(row[k], UUID) else
            row[k].isoformat() if isinstance(row[k], datetime) else row[k] for k in FIELDS.split(',')}


def command(h, t, actor, key, *, recipient=None, invitation=None):
    for value in (h, t, actor): _uuid(value)
    _key(key)
    if (recipient is None) == (invitation is None): deny(ErrorCode.INVALID_INPUT)
    target = recipient if recipient is not None else invitation
    _uuid(target)
    operation = 'invitation.issue.v1' if recipient is not None else 'invitation.redeem.v1'
    document = dict(schema_version=1, actor_id=str(actor), hackathon_id=str(h), operation=operation,
        command={'team_id':str(t), 'recipient_id' if recipient is not None else 'invitation_id':str(target)})
    return _IdempotencyCommand(actor, h, operation, key,
        _Fingerprint(sha256(_canonical(document).encode('utf-8')).digest()))


class InvitationService(AdmissionService):
    def _run_invitation(self, operation):
        try:
            return _run_composed(self, operation)
        except DomainError as error:
            raise InvitationError(error.code, retryable=error.retryable) from None

    def issue(self, *, hackathon_id, team_id, actor_id, recipient_id, key):
        scope = command(hackathon_id, team_id, actor_id, key, recipient=recipient_id)
        return self._run_invitation(lambda c: self._issue_in_tx(c, scope, team_id, recipient_id))

    def redeem(self, *, hackathon_id, team_id, actor_id, invitation_id, key):
        scope = command(hackathon_id, team_id, actor_id, key, invitation=invitation_id)
        return self._run_invitation(lambda c: self._redeem_in_tx(c, scope, team_id, invitation_id))

    def _issue_in_tx(self, c, scope, team_id, recipient):
        reserved = _reserve_in_tx(c, scope)
        if not isinstance(reserved, _StoredReply): _note_reservation(c, reserved)
        # Defer missing-user disclosure until current leader authorization, while
        # still taking every existing user lock before the team lock.
        if _query(c,'SELECT id FROM public.hackathons WHERE id=:h FOR SHARE',h=scope.hackathon_id).one_or_none() is None:
            deny(ErrorCode.HACKATHON_NOT_FOUND)
        missing = False
        for user in sorted({scope.actor_id,recipient}):
            if _query(c,'SELECT id FROM public.users WHERE id=:actor FOR NO KEY UPDATE',actor=user).one_or_none() is None:
                missing = True
        team = _query(c,'''SELECT id,leader_user_id,deleted_at,max_team_size FROM public.teams
            WHERE id=:team AND hackathon_id=:h FOR NO KEY UPDATE''',team=team_id,h=scope.hackathon_id).one_or_none()
        if team is None or team.deleted_at is not None: deny(ErrorCode.TEAM_NOT_FOUND)
        if team.leader_user_id != scope.actor_id: deny(ErrorCode.FORBIDDEN)
        if missing: deny(ErrorCode.USER_NOT_FOUND)
        if isinstance(reserved, _StoredReply):
            _note_reservation(c, reserved)
            return reserved
        row = _query(c, f'''WITH stamp AS (SELECT clock_timestamp() AS at)
            INSERT INTO public.invitations(id,hackathon_id,team_id,recipient_id,issued_by,created_at,expires_at)
            SELECT :id,:h,:team,:recipient,:actor,at,at+INTERVAL '24 hours' FROM stamp
            RETURNING {FIELDS}''', id=uuid4(), h=scope.hackathon_id, team=team_id,
            recipient=recipient, actor=scope.actor_id).mappings().one()
        self._record_invitation(c, reserved, row, False)
        return _complete_in_tx(c, reserved, self._reply(row, 201))

    def _redeem_in_tx(self, c, scope, team_id, invitation):
        reserved = _reserve_in_tx(c, scope)
        if not isinstance(reserved, _StoredReply): _note_reservation(c, reserved)
        # Immutable identity lookup takes no auxiliary lock before user/team locks.
        identity = _query(c, '''SELECT recipient_id FROM public.invitations
            WHERE id=:id AND hackathon_id=:h AND team_id=:team AND recipient_id=:actor''',
            id=invitation, h=scope.hackathon_id, team=team_id, actor=scope.actor_id).scalar_one_or_none()
        team = self._lock(c, scope.hackathon_id, team_id, (scope.actor_id,))
        if identity != scope.actor_id: deny(ErrorCode.INVITATION_NOT_FOUND)
        row = _query(c, f'''SELECT {FIELDS} FROM public.invitations WHERE id=:id
            AND hackathon_id=:h AND team_id=:team AND recipient_id=:actor FOR NO KEY UPDATE''',
            id=invitation, h=scope.hackathon_id, team=team_id, actor=scope.actor_id).mappings().one_or_none()
        if row is None: deny(ErrorCode.INVITATION_NOT_FOUND)
        if row['issued_by'] != team.leader_user_id: deny(ErrorCode.INVITATION_STALE)
        now = _query(c, 'SELECT clock_timestamp()').scalar_one()
        if row['expires_at'] <= now: deny(ErrorCode.INVITATION_EXPIRED)
        # Never note a replay before current recipient/leader/expiry authorization.
        if isinstance(reserved, _StoredReply):
            _note_reservation(c, reserved)
            return reserved
        if row['status'] != 'pending': deny(ErrorCode.INVITATION_REDEEMED)
        self._admit_locked_in_tx(c, _JoinTeamCommand(scope.hackathon_id, team_id, scope.actor_id), team)
        row = _query(c, f'''UPDATE public.invitations SET status='redeemed',redeemed_at=:at
            WHERE id=:id AND status='pending' RETURNING {FIELDS}''', id=invitation,at=now).mappings().one()
        self._record_invitation(c, reserved, row, True)
        return _complete_in_tx(c, reserved, self._reply(row, 200))

    @staticmethod
    def _reply(row, status):
        return _StoredReply._from_values(status, dict(schema_version=1,data=dto(row)),
            {'content-type':'application/json','cache-control':'no-store'})

    def _record_invitation(self, c, reserved, invitation, admitted):
        team_id, h, subject = invitation['team_id'], invitation['hackathon_id'], invitation['recipient_id']
        row = _query(c, '''UPDATE public.teams SET version=version+1,updated_at=clock_timestamp()
            WHERE id=:team AND hackathon_id=:h AND version<9223372036854775807 AND deleted_at IS NULL
            RETURNING version,leader_user_id,min_team_size,max_team_size''', team=team_id,h=h).mappings().one_or_none()
        if row is None: _fault()
        count = self._count(c, team_id)
        member = _query(c, '''SELECT EXISTS(SELECT 1 FROM public.memberships
            WHERE hackathon_id=:h AND team_id=:team AND user_id=:actor)''',h=h,team=team_id,actor=subject).scalar_one()
        if admitted and not member: _fault()
        old = _state(row,count-int(admitted),subject,member and not admitted,row['version']-1)
        new = _state(row,count,subject,member,row['version'])
        old['invitation'] = {'id':str(invitation['id']),'status':'pending'} if admitted else None
        new['invitation'] = {'id':str(invitation['id']),'status':invitation['status']}
        audit = uuid4()
        saved = _query(c, '''INSERT INTO public.audit_events
            (id,idempotency_record_id,actor_id,hackathon_id,team_id,team_version,action,old_state,new_state)
            VALUES (:id,:reservation,:actor,:hackathon,:team,:version,:action,CAST(:before AS jsonb),CAST(:after AS jsonb)) RETURNING id''',
            id=audit,reservation=reserved.record_id,actor=reserved.command.actor_id,hackathon=h,team=team_id,
            version=row['version'],action=reserved.command.operation,before=_canonical(old),after=_canonical(new)).scalar_one_or_none()
        if saved != audit: _fault()
        _outbox_in_tx(c,audit,TeamResult(team_id,h,subject,count),row['version'])

    def mine(self, *, hackathon_id, actor_id, limit=20, cursor=None):
        _uuid(hackathon_id); _uuid(actor_id)
        if type(limit) is not int or not 1 <= limit <= 100: deny(ErrorCode.INVALID_INPUT)
        if cursor is not None: _uuid(cursor)
        def read(c):
            _query(c,'SET TRANSACTION READ ONLY')
            valid = _query(c, '''SELECT CAST(:cursor AS uuid) IS NULL OR EXISTS(SELECT 1 FROM public.invitations
                WHERE id=CAST(:cursor AS uuid) AND hackathon_id=:h AND recipient_id=:actor)''',
                cursor=cursor,h=hackathon_id,actor=actor_id).scalar_one()
            if not valid: deny(ErrorCode.INVALID_INPUT)
            rows = _query(c, f'''SELECT {','.join('i.'+k for k in FIELDS.split(','))},
                (i.status='pending' AND i.expires_at>clock_timestamp() AND t.deleted_at IS NULL
                 AND t.leader_user_id=i.issued_by) AS available
                FROM public.invitations i JOIN public.teams t ON t.id=i.team_id AND t.hackathon_id=i.hackathon_id
                WHERE i.hackathon_id=:h AND i.recipient_id=:actor AND (CAST(:cursor AS uuid) IS NULL OR i.id>CAST(:cursor AS uuid))
                ORDER BY i.id LIMIT :size''',h=hackathon_id,actor=actor_id,cursor=cursor,size=limit+1).mappings().all()
            items = [dto(r)|{'available':r['available']} for r in rows[:limit]]
            return {'items':items,'next_cursor':items[-1]['id'] if len(rows)>limit else None}
        return self._execute(read)
