"""Owned READ ONLY snapshots for authenticated discovery; no mutation dependency."""
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from app.read_models import HackathonPage, HackathonView, LeaderView, MyTeam, TeamPage, TeamView


class ReadError(Exception):
    """Fixed codes only. No SQL, parameters, driver text or caller input."""
    def __init__(self, code='service_unavailable'):
        if code not in ('service_unavailable', 'invalid_request', 'hackathon_not_found', 'team_not_found'):
            code = 'service_unavailable'
        self.code = code
        super().__init__(code)


def _uuid(value):
    if not isinstance(value, UUID):
        raise ReadError('invalid_request')


def _page(limit, cursor):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ReadError('invalid_request')
    if cursor is not None:
        _uuid(cursor)


def _team(row):
    # All values, including count and leader, come from the SAME SQL snapshot.
    return TeamView(id=row['team_id'], hackathon_id=row['scope_id'], name=row['name'],
        min_team_size=row['min_team_size'], max_team_size=row['max_team_size'],
        member_count=row['member_count'],
        readiness='ready' if row['member_count'] >= row['min_team_size'] else 'forming',
        leader=LeaderView(user_id=row['leader_user_id'], display_name=row['leader_name']),
        created_at=row['created_at'])


# Projection is fixed, independent of caller input. Counts use the existing
# (team_id,user_id) index; projection/COUNT runs on at most limit+1 page rows.
_PROJECTION = '''h.id AS scope_id,p.id AS team_id,p.name,p.min_team_size,p.max_team_size,
    p.leader_user_id,p.created_at,u.display_name AS leader_name,
    CASE WHEN p.id IS NULL THEN NULL ELSE
      (SELECT count(*) FROM public.memberships m WHERE m.team_id=p.id) END AS member_count'''


class TeamReadService:
    def __init__(self, engine: Engine):
        if not isinstance(engine, Engine):
            raise TypeError('TeamReadService requires an Engine')
        self._engine = engine

    @staticmethod
    def _guard(c):
        # Missing/unreadable driver state is not evidence of transaction safety.
        try:
            valid = (c.dialect.name == 'postgresql' and c.dialect.driver == 'psycopg'
                and c.dialect.is_async is False
                and c.connection.dbapi_connection.autocommit is False
                and not c.in_transaction() and c.get_isolation_level() == 'READ COMMITTED')
        except Exception:
            valid = False
        if not valid:
            raise ReadError() from None

    def _read(self, operation):
        try:
            with self._engine.connect() as c:
                # Logical begin is not sufficient evidence against AUTOCOMMIT.
                self._guard(c)
                with c.begin():
                    c.execute(text('SET TRANSACTION READ ONLY'))
                    c.execute(text("SET LOCAL lock_timeout='5s'"))
                    c.execute(text("SET LOCAL statement_timeout='15s'"))
                    result = operation(c)
            return result
        except DBAPIError:
            raise ReadError() from None

    def hackathons(self, *, limit=20, cursor=None) -> HackathonPage:
        _page(limit, cursor)
        def lookup(c):
            rows = c.execute(text('''SELECT id,name,min_team_size,max_team_size
                FROM public.hackathons WHERE CAST(:cursor AS uuid) IS NULL OR id>CAST(:cursor AS uuid)
                ORDER BY id ASC LIMIT :fetch'''), dict(cursor=cursor, fetch=limit+1)).mappings().all()
            items = [HackathonView(**row) for row in rows[:limit]]
            return HackathonPage(items=items, next_cursor=items[-1].id if len(rows)>limit else None)
        return self._read(lookup)

    def teams(self, hackathon_id: UUID, *, limit=20, cursor=None) -> TeamPage:
        _uuid(hackathon_id)
        _page(limit, cursor)
        def lookup(c):
            rows = c.execute(text('SELECT '+_PROJECTION+''',a.id AS cursor_id
                FROM public.hackathons h
                LEFT JOIN public.teams a ON a.id=CAST(:cursor AS uuid) AND a.hackathon_id=h.id
                LEFT JOIN LATERAL (
                    SELECT t.id,t.name,t.min_team_size,t.max_team_size,t.leader_user_id,t.created_at
                    FROM public.teams t WHERE t.hackathon_id=h.id AND t.deleted_at IS NULL
                      AND (CAST(:cursor AS uuid) IS NULL OR (t.created_at,t.id)<(a.created_at,a.id))
                    ORDER BY t.created_at DESC,t.id DESC LIMIT :fetch
                ) p ON true LEFT JOIN public.users u ON u.id=p.leader_user_id
                WHERE h.id=:hackathon ORDER BY p.created_at DESC,p.id DESC'''),
                dict(hackathon=hackathon_id, cursor=cursor, fetch=limit+1)).mappings().all()
            if not rows:
                raise ReadError('hackathon_not_found')
            if cursor is not None and rows[0]['cursor_id'] is None:
                raise ReadError('invalid_request')
            present = [row for row in rows if row['team_id'] is not None]
            items = [_team(row) for row in present[:limit]]
            return TeamPage(items=items, next_cursor=items[-1].id if len(present)>limit else None)
        return self._read(lookup)

    def team(self, hackathon_id: UUID, team_id: UUID) -> TeamView:
        _uuid(hackathon_id)
        _uuid(team_id)
        def lookup(c):
            row = c.execute(text('SELECT '+_PROJECTION+'''
                FROM public.hackathons h LEFT JOIN public.teams p
                  ON p.hackathon_id=h.id AND p.id=:team AND p.deleted_at IS NULL
                LEFT JOIN public.users u ON u.id=p.leader_user_id WHERE h.id=:hackathon'''),
                dict(hackathon=hackathon_id, team=team_id)).mappings().one_or_none()
            if row is None:
                raise ReadError('hackathon_not_found')
            if row['team_id'] is None:
                raise ReadError('team_not_found')
            return _team(row)
        return self._read(lookup)

    def my_team(self, hackathon_id: UUID, trusted_user_id: UUID) -> MyTeam:
        _uuid(hackathon_id)
        _uuid(trusted_user_id)
        def lookup(c):
            row = c.execute(text('SELECT '+_PROJECTION+'''
                FROM public.hackathons h LEFT JOIN public.memberships own
                  ON own.hackathon_id=h.id AND own.user_id=:actor
                LEFT JOIN public.teams p ON p.id=own.team_id AND p.hackathon_id=h.id AND p.deleted_at IS NULL
                LEFT JOIN public.users u ON u.id=p.leader_user_id WHERE h.id=:hackathon'''),
                dict(hackathon=hackathon_id, actor=trusted_user_id)).mappings().one_or_none()
            if row is None:
                raise ReadError('hackathon_not_found')
            return MyTeam(team=None if row['team_id'] is None else _team(row))
        return self._read(lookup)
