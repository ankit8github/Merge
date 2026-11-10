"""Read-only browser-run evidence. No fixture creation, migration or cleanup."""
from dataclasses import dataclass, field
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from app.services.credentials import valid_username
from test_support.database import DiagnosticFailure


class AccountScope(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True, hide_input_in_errors=True)
    user_id: UUID
    username: str
    login_attempts: int = Field(ge=0, le=30)
    logout_attempts: int = Field(ge=0, le=30)

    @field_validator('username')
    @classmethod
    def username_valid(cls, value):
        if not valid_username(value):
            raise ValueError('Invalid scope')
        return value


class RunScope(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True, hide_input_in_errors=True)
    run_id: UUID
    accounts: tuple[AccountScope, ...] = Field(min_length=1, max_length=3)

    @field_validator('accounts')
    @classmethod
    def distinct(cls, accounts):
        if (len({a.user_id for a in accounts}) != len(accounts)
                or len({a.username for a in accounts}) != len(accounts)):
            raise ValueError('Invalid scope')
        return accounts


# Fixed identifiers only. Never interpolate a manifest value into SQL.
UNCHANGED_TABLES = ('users', 'hackathons', 'teams', 'memberships',
                    'idempotency_records', 'audit_events', 'outbox_events', 'account_credentials')


@dataclass(repr=False)
class Snapshot:
    unchanged: dict = field(default_factory=dict)
    sessions: dict = field(default_factory=dict)
    buckets: dict = field(default_factory=dict)


def snapshot(connection, scope):
    """READ ONLY evidence, held privately in memory; no row or fingerprint output.

    READ COMMITTED statements need an exclusive run (no unrelated writers).
    Fingerprints detect changes, not adversarial database tampering.
    """
    connection.execute(text('SET TRANSACTION READ ONLY'))
    for account in scope.accounts:
        found = connection.execute(text('''SELECT user_id FROM public.account_credentials
            WHERE username=:name'''), {'name': account.username}).scalar_one_or_none()
        if found != account.user_id:
            raise DiagnosticFailure('verification')
    bad = connection.execute(text('''SELECT count(*) FROM (
        SELECT t.id FROM public.teams t JOIN public.hackathons h ON h.id=t.hackathon_id
        LEFT JOIN public.memberships m ON m.team_id=t.id
        GROUP BY t.id,h.id
        HAVING t.min_team_size<>h.min_team_size OR t.max_team_size<>h.max_team_size
          OR (t.deleted_at IS NULL AND (count(m.user_id)<1 OR count(m.user_id)>t.max_team_size
              OR t.leader_user_id IS NULL OR NOT coalesce(bool_or(m.user_id=t.leader_user_id),false)
              OR NOT coalesce(bool_and(m.hackathon_id=t.hackathon_id),false)))
          OR (t.deleted_at IS NOT NULL AND (count(m.user_id)<>0 OR t.leader_user_id IS NOT NULL))
        UNION ALL
        SELECT m.team_id FROM public.memberships m LEFT JOIN public.teams t
          ON t.id=m.team_id AND t.hackathon_id=m.hackathon_id WHERE t.id IS NULL
        UNION ALL
        SELECT min(team_id::text)::uuid FROM public.memberships
          GROUP BY hackathon_id,user_id HAVING count(*)>1
        ) broken''')).scalar_one()
    invalid_sessions = connection.execute(text('''SELECT count(*) FROM public.auth_sessions s
        LEFT JOIN public.users u ON u.id=s.user_id
        LEFT JOIN public.account_credentials a ON a.user_id=s.user_id
        WHERE u.id IS NULL OR a.user_id IS NULL OR octet_length(s.token_hash)<>32
          OR octet_length(s.csrf_token)<>32 OR s.expires_at<>s.created_at+interval '8 hours'
          OR s.revoked_at<s.created_at''')).scalar_one()
    if bad or invalid_sessions:
        raise DiagnosticFailure('verification')
    result = Snapshot()
    for table in UNCHANGED_TABLES:
        result.unchanged[table] = tuple(connection.execute(text(f'''SELECT count(*),
            coalesce(md5(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text))),md5(''))
            FROM public.{table} t''')).one())
    result.sessions = {row[0]: tuple(row[1:]) for row in connection.execute(text('''SELECT
        token_hash,user_id,md5((to_jsonb(s)-'revoked_at')::text),revoked_at
        FROM public.auth_sessions s''')).all()}
    result.buckets = {tuple(row[:3]): tuple(row[3:]) for row in connection.execute(text('''SELECT
        scope,key_hash,window_start,attempts,expires_at,md5(to_jsonb(b)::text)
        FROM public.auth_throttle_buckets b''')).all()}
    connection.rollback()
    return result


def compare(before, after, scope, throttle):
    """Only scoped new sessions/revocations and run-key login buckets may change."""
    if before.unchanged != after.unchanged or not before.sessions.keys() <= after.sessions.keys():
        raise DiagnosticFailure('verification')
    accounts = {a.user_id: a for a in scope.accounts}
    added, revoked = {}, {}
    for key, (user, fingerprint, at) in after.sessions.items():
        old = before.sessions.get(key)
        if old is None:
            added[user] = added.get(user, 0) + 1
            if at is not None:
                revoked[user] = revoked.get(user, 0) + 1
        elif old != (user, fingerprint, at):
            if old[:2] != (user, fingerprint) or old[2] is not None or at is None:
                raise DiagnosticFailure('verification')
            revoked[user] = revoked.get(user, 0) + 1
    for effects, budget in ((added, 'login_attempts'), (revoked, 'logout_attempts')):
        for user, count in effects.items():
            if user not in accounts or count > getattr(accounts[user], budget):
                raise DiagnosticFailure('verification')
    allowed = {('auth:v1:login_ip', throttle._key('login_ip', '127.0.0.1')):
               sum(a.login_attempts for a in scope.accounts)}
    allowed.update({('auth:v1:login_account', throttle._key('login_account', a.username)):
                    a.login_attempts for a in scope.accounts})
    totals = {}
    if not before.buckets.keys() <= after.buckets.keys():
        raise DiagnosticFailure('verification')
    for key, current in after.buckets.items():
        old = before.buckets.get(key)
        if old == current:
            continue
        pair = key[:2]
        # A fresh run key must have no preexisting buckets. Saturation means a
        # counter is a lower bound on charges; HTTP budgets enforce the cap.
        if pair not in allowed or old is not None or not 1 <= current[0] <= allowed[pair]:
            raise DiagnosticFailure('verification')
        totals[pair] = totals.get(pair, 0) + current[0]
    if any(count > allowed[pair] for pair, count in totals.items()):
        raise DiagnosticFailure('verification')
