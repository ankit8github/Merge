"""Explicit guarded targets. Legacy commands never silently move past 0002."""
from sqlalchemy import text

DOMAIN_REVISION = '0002_domain'
AUTH_REVISION = '0003_auth'
ADMISSION_REVISION = '0004_admission'
TARGET_REVISIONS = (DOMAIN_REVISION, AUTH_REVISION, ADMISSION_REVISION)
DOMAIN_TABLES = ('users', 'hackathons', 'teams', 'memberships', 'idempotency_records', 'audit_events', 'outbox_events')


def validate_migration_start(revisions, target):
    if target not in TARGET_REVISIONS:
        raise ValueError('Unsupported explicit test migration target')
    allowed = ([], [DOMAIN_REVISION]) if target == DOMAIN_REVISION else ([DOMAIN_REVISION], [AUTH_REVISION])
    if target == ADMISSION_REVISION:
        allowed = ([AUTH_REVISION], [ADMISSION_REVISION])
    if revisions not in allowed:
        raise ValueError('Unexpected migration state; no downgrade, adoption or repair is allowed')


def domain_snapshot(connection):
    """Metadata-free aggregate fingerprints; never print existing row contents."""
    # Migration-only on merge_test: prevent concurrent fixture writers while
    # comparing before/after in the same externally owned migration transaction.
    tables = ','.join('public.' + name for name in DOMAIN_TABLES)
    connection.execute(text('LOCK TABLE ' + tables + ' IN SHARE MODE'))
    return {name: tuple(connection.execute(text(f'''SELECT count(*),
        coalesce(md5(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text))),md5(''))
        FROM public.{name} t''')).one()) for name in DOMAIN_TABLES}


def admission_snapshot(connection):
    """Preserve existing auth rows too; never return or print their private values."""
    snapshot = domain_snapshot(connection)
    for name in ('account_credentials', 'auth_sessions', 'auth_throttle_buckets'):
        connection.execute(text(f'LOCK TABLE public.{name} IN SHARE MODE'))
        snapshot[name] = tuple(connection.execute(text(f'''SELECT count(*),
            coalesce(md5(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text))),md5(''))
            FROM public.{name} t''')).one())
    return snapshot
