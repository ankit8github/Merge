"""Explicit one-shot Railway production operations. Never ordinary startup."""
import json
import os
from pathlib import Path
from uuid import UUID
import psycopg
from psycopg import sql
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from app.railway import config, database
from app.production import grants
from app.production.migrate import catalog
from release_support.migrations import snapshot


def migration(c, target, addresses, action):
    if target.role != 'migrator' or action not in ('prepare', 'migrate') or c.in_transaction():
        raise ValueError('Explicit Railway migration owner required')
    root = Path(__file__).resolve().parents[2]
    cfg = Config()
    cfg.set_main_option('script_location', str(root / 'railway_alembic'))
    cfg.set_main_option('version_locations', str(root / 'alembic/versions'))
    cfg.set_main_option('path_separator', 'os')
    cfg.attributes.update(railway_connection=c, railway_target=target, railway_addresses=addresses)
    final = config.PREVIOUS if action == 'prepare' else config.REVISION
    with c.begin():
        database.identity(c, target, addresses)
        c.execute(text("SET LOCAL lock_timeout='5s'"))
        c.execute(text("SET LOCAL statement_timeout='15s'"))
        if action == 'prepare':
            objects = c.execute(text("SELECT (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public')+(SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public')")).scalar_one()
            if objects: raise ValueError('Empty production schema required')
            before = None
        else:
            if c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() != [config.PREVIOUS]:
                raise ValueError('Exact 0005 required')
            before = snapshot(c)
        command.upgrade(cfg, final)
        grants.apply(c, final)
        if before is not None and snapshot(c) != before: raise ValueError('Old rows changed; rollback DDL')
        if c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() != [final]:
            raise ValueError('Migration revision mismatch')
    return {'revision': final, 'old_tables_preserved': before is not None}


def bootstrap(env, target, addresses):
    admin = config.secret(env.get('MERGE_RAILWAY_ADMIN_PASSWORD'))
    runtime = config.secret(env.get('MERGE_RAILWAY_RUNTIME_PASSWORD'))
    if len({admin.get_secret_value(), runtime.get_secret_value(), target.password.get_secret_value()}) != 3:
        raise ValueError('Distinct fresh production passwords required')
    kwargs = dict(host=config.DB_HOST, hostaddr=addresses[0], port=config.DB_PORT,
                  user='postgres', password=admin.get_secret_value(), sslmode='require',
                  connect_timeout=5, options='-c statement_timeout=15000 -c lock_timeout=5000 -c log_statement=none -c log_min_error_statement=panic')
    # Railway may already have its default 'railway' DB. Only create a NEW
    # merge_prod; never adopt/rename/reset the template database or old Merge DBs.
    with psycopg.connect(dbname='postgres', autocommit=True, **kwargs) as c:
        _bootstrap_server(c, addresses, db='postgres')
        exists = c.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname IN ('merge_runtime','merge_migrator','merge_app','merge_owner','merge_bench_app')) OR EXISTS(SELECT 1 FROM pg_database WHERE datname IN ('merge_prod','merge_dev','merge_test','merge_profile_test','merge_bench'))").fetchone()[0]
        if exists: raise ValueError('Fresh production database/role namespace required')
        with c.transaction():
            c.execute("SET LOCAL password_encryption='scram-sha-256'")
            for name, password in [('merge_runtime', runtime), ('merge_migrator', target.password)]:
                c.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(name), sql.Literal(password.get_secret_value())))
        # CREATE DATABASE cannot share the role transaction. A partial failure
        # stops; there is deliberately no destructive cleanup or blind retry.
        c.execute('CREATE DATABASE merge_prod TEMPLATE template0')
    with psycopg.connect(dbname=config.DATABASE, **kwargs) as c:
        _bootstrap_server(c, addresses, db=config.DATABASE)
        c.execute('REVOKE ALL ON DATABASE merge_prod FROM PUBLIC')
        c.execute('GRANT CONNECT ON DATABASE merge_prod TO merge_runtime,merge_migrator')
        c.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
        c.execute('GRANT USAGE ON SCHEMA public TO merge_runtime,merge_migrator')
        c.execute('GRANT CREATE ON SCHEMA public TO merge_migrator')


def _bootstrap_server(c, addresses, *, db):
    who = c.execute('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()').fetchone()
    from ipaddress import ip_interface
    if who[:2] != (db, 'postgres') or str(ip_interface(who[2]).ip) not in addresses or who[3] != 5432:
        raise ValueError('Railway bootstrap identity rejected')
    version = int(c.execute("SELECT current_setting('server_version_num')").fetchone()[0])
    if not 170000 <= version < 180000: raise ValueError('PostgreSQL 17 required')
    if c.execute('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()[0] is not True:
        raise ValueError('Encrypted private bootstrap required')


def main():
    parser = config.SafeParser(description=__doc__)
    parser.add_argument('--confirm-merge-prod', action='store_true', required=True)
    parser.parse_args()
    code = 1
    stage = 'configuration'
    resource = None
    result = {}
    try:
        action, target = config.operation_environment(os.environ)
        stage = action
        addresses = database.private_addresses()
        if action == 'bootstrap': bootstrap(os.environ, target, addresses)
        else:
            revision = {'prepare': None, 'migrate': config.PREVIOUS, 'verify': config.REVISION, 'catalog': config.REVISION}[action]
            resource = database.engine(target, revision, addresses=addresses)
            with resource.connect() as c:
                if action in ('prepare', 'migrate'): result = migration(c, target, addresses, action)
                elif action == 'catalog':
                    result = catalog(c, UUID(os.environ['MERGE_RAILWAY_CATALOG_ID']),
                        os.environ['MERGE_RAILWAY_CATALOG_NAME'], int(os.environ['MERGE_RAILWAY_CATALOG_MIN']),
                        int(os.environ['MERGE_RAILWAY_CATALOG_MAX']))
        code = 0
    except Exception: pass
    finally:
        if resource is not None:
            try: resource.dispose()
            except Exception: code = 1
    print(json.dumps({'action': stage, 'database': config.DATABASE, 'native_exit_code': code, **result}))
    raise SystemExit(code)


if __name__ == '__main__': main()
