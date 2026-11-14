"""Committed invalidation snapshots; no dispatcher, writes or event-history cursor."""
from hashlib import sha256
from uuid import UUID

from sqlalchemy import text

from app.services.team_reads import TeamReadService, ReadError, _uuid


# Public changes affect the authenticated board. Private operations have the
# same requester/current-leader or recipient boundary as canonical private reads.
# Separate counters prevent a loss of private visibility masking a public change.
SNAPSHOT = '''SELECT
    (SELECT count(*) FROM visible WHERE public_change) AS public_count,
    (SELECT count(*) FROM visible WHERE NOT public_change AND private_change) AS private_count
    FROM public.hackathons h WHERE h.id=:hackathon'''
SNAPSHOT = '''WITH visible AS (
    SELECT (a.action IN ('team.create.v1','team.join.v1','team.leave.v1','member.remove.v1','invitation.redeem.v1')
        OR (a.action='request.decide.v1' AND a.new_state->'request'->>'status'='approved')) AS public_change,
      ((a.action IN ('request.create.v1','request.decide.v1') AND
          (r.requester_id=:actor OR (t.leader_user_id=:actor AND t.deleted_at IS NULL)))
        OR (a.action='invitation.issue.v1' AND i.recipient_id=:actor)) AS private_change
    FROM public.outbox_events o JOIN public.audit_events a ON a.id=o.audit_event_id
    JOIN public.teams t ON t.id=a.team_id AND t.hackathon_id=a.hackathon_id
    LEFT JOIN public.join_requests r ON r.id::text=a.new_state->'request'->>'id'
        AND r.hackathon_id=a.hackathon_id AND r.team_id=a.team_id
    LEFT JOIN public.invitations i ON i.id::text=a.new_state->'invitation'->>'id'
        AND i.hackathon_id=a.hackathon_id AND i.team_id=a.team_id
    WHERE a.hackathon_id=:hackathon AND o.event_type='team.changed.v1' AND o.schema_version=1
) ''' + SNAPSHOT


def fingerprint(hackathon: UUID, actor: UUID, public: int, private: int) -> str:
    if type(public) is not int or type(private) is not int or min(public, private) < 0:
        raise ReadError()
    return sha256(f'v1:{hackathon}:{actor}:{public}:{private}'.encode('ascii')).hexdigest()


class RealtimeService(TeamReadService):
    def revision(self, hackathon_id: UUID, actor_id: UUID) -> str:
        _uuid(hackathon_id); _uuid(actor_id)
        def sample(c):
            row = c.execute(text(SNAPSHOT), {'hackathon': hackathon_id, 'actor': actor_id}).mappings().one_or_none()
            if row is None:
                raise ReadError('hackathon_not_found')
            return fingerprint(hackathon_id, actor_id, row['public_count'], row['private_count'])
        return self._read(sample)
