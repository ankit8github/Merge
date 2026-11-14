"""Transparent 70/30 ranking from one bounded committed snapshot. No ML."""
import base64
from collections import Counter
from datetime import timezone
from fractions import Fraction
from hashlib import sha256
import json
import re
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import text
from app.services.profiles import ProfileError
from app.services.team_reads import TeamReadService, _uuid

MAX_POOL = 10000
# One SQL statement: authorization, capacity and candidates share a snapshot.
SNAPSHOT = '''SELECT t.leader_user_id,t.max_team_size,
    (SELECT count(*) FROM public.memberships m WHERE m.team_id=t.id) AS member_count,
    (date_trunc('day',statement_timestamp() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC') + interval '12 hours' AS reference_at,
    COALESCE((SELECT json_agg(member ORDER BY member.user_id) FROM
        (SELECT m.user_id,COALESCE(p.skills,'{}'::varchar[]) AS skills,p.timezone
         FROM public.memberships m LEFT JOIN public.participant_profiles p ON p.user_id=m.user_id
         WHERE m.team_id=t.id AND m.hackathon_id=t.hackathon_id
         AND t.leader_user_id=:actor ORDER BY m.user_id LIMIT :bound) member),'[]'::json) AS members,
    COALESCE((SELECT json_agg(candidate ORDER BY candidate.user_id) FROM
        (SELECT u.id AS user_id,u.display_name,a.username,p.skills,p.timezone
         FROM public.users u JOIN public.account_credentials a ON a.user_id=u.id
         JOIN public.participant_profiles p ON p.user_id=u.id
         WHERE p.discoverable AND p.timezone IS NOT NULL AND u.id<>:actor
           AND NOT EXISTS (SELECT 1 FROM public.memberships m WHERE m.user_id=u.id AND m.hackathon_id=t.hackathon_id)
           AND t.leader_user_id=:actor
         ORDER BY u.id LIMIT :bound) candidate),'[]'::json) AS candidates
    FROM public.teams t WHERE t.id=:team AND t.hackathon_id=:hackathon AND t.deleted_at IS NULL'''


def offset_minutes(zone, reference):
    if zone is None:
        return None
    try:
        return int(reference.astimezone(ZoneInfo(zone)).utcoffset().total_seconds() // 60)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ProfileError() from None


def timezone_overlap(offset, member_offsets):
    total = sum(member_offsets.values())
    overlap = Fraction(0)
    for other, count in member_offsets.items():
        distance = None if offset is None or other is None else abs(offset - other) % 1440
        if distance is not None:
            distance = min(distance, 1440-distance)
        if distance is not None:
            overlap += count * Fraction(max(0, 480-distance), 480)
    return overlap / total if total else Fraction(0)


def score_components(skills, coverage, overlap):
    candidate = set(skills)
    novel = sorted(candidate - coverage)
    skill = Fraction(len(novel), len(candidate)) if candidate else Fraction(0)
    score = 70*skill + 30*overlap
    return score, {'new_skills': novel, 'skill_complement': round(float(skill), 6),
        'timezone_overlap': round(float(overlap), 6), 'skill_points': round(float(70*skill), 6),
        'timezone_points': round(float(30*overlap), 6), 'score': round(float(score), 6)}


def components(skills, coverage, zone, member_zones, reference):
    offsets = Counter(offset_minutes(z, reference) for z in member_zones)
    return score_components(skills, coverage, timezone_overlap(offset_minutes(zone, reference), offsets))


def ranked_page(row, hackathon, team, actor, limit, cursor):
    if row is None:
        raise ProfileError('team_not_found')
    if row['leader_user_id'] != actor:
        raise ProfileError('forbidden')
    members, candidates = row['members'], row['candidates']
    if max(len(members), len(candidates), row['member_count']) > MAX_POOL:
        raise ProfileError()
    reference = row['reference_at'].astimezone(timezone.utc)
    coverage = set().union(*(set(m['skills']) for m in members))
    # Include source values and permission/capacity so stale pages fail closed.
    serialized = json.dumps([str(hackathon),str(team),str(actor),str(reference),
        row['max_team_size'],row['member_count'],members,candidates], sort_keys=True, default=str, separators=(',', ':'))
    digest = sha256(serialized.encode()).hexdigest()
    start = 0
    if cursor is not None:
        if not isinstance(cursor, str) or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', cursor) is None:
            raise ProfileError('invalid_request')
        try:
            value = base64.urlsafe_b64decode(cursor+'='*((-len(cursor))%4)).decode('ascii')
            old, position = value.split(':')
            if re.fullmatch('[0-9a-f]{64}',old) is None or re.fullmatch(r'[1-9][0-9]{0,4}',position) is None:
                raise ValueError()
            start = int(position)
            if start > MAX_POOL:
                raise ValueError()
        except (ValueError, UnicodeError):
            raise ProfileError('invalid_request') from None
        if old != digest:
            raise ProfileError('ranking_changed')
    scored = []
    if row['member_count'] < row['max_team_size']:
        # Resolve each member once and reuse exact overlap by candidate zone;
        # avoid candidates x members conversions or retaining a DB connection.
        offsets = Counter(offset_minutes(m['timezone'], reference) for m in members)
        overlaps = {zone: timezone_overlap(offset_minutes(zone, reference), offsets)
            for zone in {c['timezone'] for c in candidates}}
        for candidate in candidates:
            score, explanation = score_components(candidate['skills'], coverage, overlaps[candidate['timezone']])
            scored.append((score, UUID(str(candidate['user_id'])), dict(candidate) | explanation))
    scored.sort(key=lambda v: (-v[0], v[1]))
    if start and start >= len(scored):
        raise ProfileError('invalid_request')
    stop = start + limit
    next_cursor = base64.urlsafe_b64encode(f'{digest}:{stop}'.encode()).decode().rstrip('=') if stop < len(scored) else None
    return dict(hackathon_id=hackathon, team_id=team, user_id=actor, reference_at=reference,
        team_skills=sorted(coverage), skill_weight=0.7, timezone_weight=0.3,
        items=[item[2] for item in scored[start:stop]], next_cursor=next_cursor)


class MatchingService(TeamReadService):
    def suggestions(self, hackathon, team, actor, *, limit=20, cursor=None):
        for value in (hackathon, team, actor):
            _uuid(value)
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ProfileError('invalid_request')
        row = self._read(lambda c: c.execute(text(SNAPSHOT),
            dict(hackathon=hackathon,team=team,actor=actor,bound=MAX_POOL+1)).mappings().one_or_none())
        # Materialize then release the read connection before CPU scoring/sort.
        return ranked_page(row, hackathon, team, actor, limit, cursor)
