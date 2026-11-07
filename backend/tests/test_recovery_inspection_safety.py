"""Static regression checks only; these do not execute or parse SQL on a server."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'inspect_merge_test_recovery.sql'


def source():
    return SCRIPT.read_text(encoding='utf-8')


def executable_sql():
    return re.sub(r'--[^\n]*', '', source())


def test_recovery_transaction_and_connection_guards():
    sql = executable_sql()
    assert r'\set ON_ERROR_STOP on' in sql
    assert 'BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;' in sql
    for guard in (
        "current_database() IS DISTINCT FROM 'merge_test'",
        "current_user IS DISTINCT FROM 'postgres'",
        "session_user IS DISTINCT FROM 'postgres'",
        "inet_server_addr() IS DISTINCT FROM '127.0.0.1'::inet",
        'inet_server_port() IS DISTINCT FROM 5432',
    ):
        assert guard in sql
    assert sql.index('RAISE EXCEPTION') < sql.index('SELECT current_database() AS database')
    assert sql.rstrip().endswith('COMMIT;')


def test_recovery_has_no_mutations_credentials_or_executable_psql_escape():
    sql = executable_sql()
    # Conservative token ban includes strings; metadata aliases use app_* names.
    assert not re.search(r'\b(GRANT|REVOKE|CREATE|ALTER|DROP|TRUNCATE|UPDATE|INSERT|DELETE|COPY|CALL|EXECUTE)\b',
                         re.sub(r"'[^']*'", "''", sql), re.I)
    assert not re.search(r'pg_authid|rolpassword|passwd|pg_read_file|pg_execute|dblink', sql, re.I)
    commands = re.findall(r'\\([A-Za-z_!]+)', sql)
    assert set(commands) == {'set', 'pset', 'gset', 'if', 'else', 'echo', 'endif'}
    assert 'merge_dev' not in sql


def test_recovery_reports_metadata_and_guards_optional_revision():
    sql = executable_sql()
    for metadata in ('datacl::text', 'nspacl::text', 'has_database_privilege',
                     'has_schema_privilege', 'pg_roles', 'pg_auth_members',
                     'pg_class', 'pg_proc', 'pg_type', 'pg_namespace'):
        assert metadata in sql
    assert 'SELECT *' not in sql
    assert "to_regclass('public.alembic_version') IS NOT NULL" in sql
    start = sql.index(r'\if :recovery_version_exists')
    query = sql.index('SELECT version_num AS alembic_revision FROM public.alembic_version;')
    assert start < query < sql.index(r'\else') < sql.index(r'\endif')
    # Only Alembic version metadata may be read outside catalog relations.
    relation_sql = re.sub(r'\bIS\s+DISTINCT\s+FROM\b', '', sql, flags=re.I)
    relation_sql = re.sub(r"'[^']*'", "''", relation_sql)
    relations = re.findall(r'\b(?:FROM|JOIN)\s+([\w.]+)', relation_sql, re.I)
    assert all(name.startswith('pg_') or name == 'public.alembic_version'
               for name in relations)


def test_original_preflight_still_refuses_existing_target():
    preflight = (ROOT / 'scripts' / 'inspect_merge_test.sql').read_text(encoding='utf-8')
    assert "IF EXISTS (SELECT FROM pg_database WHERE datname = 'merge_test') THEN" in preflight
    assert "RAISE EXCEPTION 'merge_test already exists. Stop for owner review.';" in preflight
