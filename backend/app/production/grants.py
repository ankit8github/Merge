"""Frozen runtime grants for revision 0006, including column rights for row locks."""
from sqlalchemy import text

TABLE_RIGHTS={
    'users':('SELECT','INSERT'), 'hackathons':('SELECT',),
    'account_credentials':('SELECT','INSERT'),
    'auth_sessions':('SELECT','INSERT','UPDATE'),
    'auth_throttle_buckets':('SELECT','INSERT','UPDATE'),
    'teams':('SELECT','INSERT','UPDATE'),
    'memberships':('SELECT','INSERT','DELETE'),
    'idempotency_records':('SELECT','INSERT','UPDATE'),
    'audit_events':('SELECT','INSERT'), 'outbox_events':('SELECT','INSERT'),
    'join_requests':('SELECT','INSERT','UPDATE'),
    'invitations':('SELECT','INSERT','UPDATE'),
    'participant_profiles':('SELECT','INSERT','UPDATE'),
    'alembic_version':('SELECT',),
}
LOCK_COLUMNS={'users':'id','hackathons':'id','account_credentials':'user_id'}


def apply(c,revision):
    # Target identity and migration transaction are checked by the caller/env.
    for table,rights in TABLE_RIGHTS.items():
        if table=='participant_profiles' and revision!='0006_profiles':continue
        c.execute(text(f'REVOKE ALL ON TABLE public.{table} FROM PUBLIC,merge_runtime'))
        c.execute(text(f'GRANT {",".join(rights)} ON TABLE public.{table} TO merge_runtime'))
    for table,column in LOCK_COLUMNS.items():
        c.execute(text(f'GRANT UPDATE({column}) ON TABLE public.{table} TO merge_runtime'))
    c.execute(text('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC'))
    c.execute(text('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO merge_runtime'))


def verify(c):
    # Two fixed SQL statements, rather than one network round trip per privilege.
    rights=('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')
    rows=c.execute(text("""SELECT t.name,p.privilege,
        has_table_privilege(current_user,'public.'||t.name,p.privilege) AS allowed
        FROM unnest(CAST(:tables AS text[])) AS t(name)
        CROSS JOIN unnest(CAST(:rights AS text[])) AS p(privilege)"""),dict(tables=list(TABLE_RIGHTS),rights=list(rights))).mappings().all()
    actual={(r['name'],r['privilege']):r['allowed'] for r in rows}
    wanted={(name,right):right in allowed for name,allowed in TABLE_RIGHTS.items() for right in rights}
    if len(rows)!=len(wanted) or actual!=wanted:raise ValueError('Runtime table privileges mismatch')
    locks=c.execute(text("""SELECT name,col,
        has_column_privilege(current_user,'public.'||name,col,'UPDATE') AS allowed
        FROM unnest(CAST(:tables AS text[]),CAST(:columns AS text[])) AS v(name,col)"""),
        dict(tables=list(LOCK_COLUMNS),columns=list(LOCK_COLUMNS.values()))).mappings().all()
    if len(locks)!=len(LOCK_COLUMNS) or {(r['name'],r['col']):r['allowed'] for r in locks}!={(t,c):True for t,c in LOCK_COLUMNS.items()}:
        raise ValueError('Runtime row-lock privileges missing')
