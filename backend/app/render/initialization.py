"""Explicit fresh-instance setup only. Never imported by application startup."""
from pathlib import Path
from dataclasses import replace
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import text
from app.production import grants
from app.render import database
from app.render.config import REVISION

LOCK = 50631926061115


def owner(c, target, addresses):
    target.url()
    if target.role != 'migrator': raise ValueError('Explicit Render owner required')
    database.server(c, addresses, role='merge_migrator')
    flags = tuple(c.execute(text("""SELECT r.rolsuper,r.rolcreaterole,
        d.datdba=r.oid,pg_is_in_recovery(),current_setting('transaction_read_only')
        FROM pg_roles r CROSS JOIN pg_database d
        WHERE r.rolname=current_user AND d.datname=current_database()""")).one())
    if flags != (False, True, True, False, 'off'):
        raise ValueError('Restricted Render database owner with CREATE ROLE required')


def empty(c):
    objects = c.execute(text("""SELECT
        (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public')+
        (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public')""")).scalar_one()
    role = c.execute(text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='merge_runtime')")).scalar_one()
    if objects != 0 or role is not False:
        raise ValueError('Only an empty public schema and absent runtime role are accepted')


def claim(c, selected):
    # Caller holds a session advisory lock. This transaction commits BEFORE DDL.
    with c.begin():
        exists = c.execute(text("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='merge_deployment')")).scalar_one()
        if exists:
            rows = c.execute(text('SELECT attempt,source_commit,state FROM merge_deployment.setup_claim')).all()
            if rows != [(selected.attempt, selected.commit, 'complete')]:
                raise ValueError('Previous/unknown setup claim; manual investigation required')
            return False
        empty(c)
        c.execute(text('CREATE SCHEMA merge_deployment AUTHORIZATION merge_migrator'))
        c.execute(text('REVOKE ALL ON SCHEMA merge_deployment FROM PUBLIC'))
        c.execute(text("""CREATE TABLE merge_deployment.setup_claim (
            singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
            attempt uuid NOT NULL, source_commit varchar(40) NOT NULL,
            state text NOT NULL CHECK(state IN ('claimed','complete')),
            created_at timestamptz NOT NULL DEFAULT now())"""))
        c.execute(text('REVOKE ALL ON TABLE merge_deployment.setup_claim FROM PUBLIC'))
        c.execute(text("INSERT INTO merge_deployment.setup_claim(attempt,source_commit,state) VALUES (:attempt,:commit,'claimed')"),
                  dict(attempt=selected.attempt, commit=selected.commit))
    return True


def upgrade(c, selected, addresses):
    root = Path(__file__).resolve().parents[2]
    cfg = Config()
    cfg.set_main_option('script_location', str(root / 'render_alembic'))
    cfg.set_main_option('version_locations', str(root / 'alembic/versions'))
    cfg.set_main_option('path_separator', 'os')
    cfg.attributes.update(render_connection=c, render_target=selected.target, render_addresses=addresses)
    command.upgrade(cfg, REVISION)


def apply(c, selected, addresses):
    # A failed DDL transaction leaves the durable claim intact, blocking retries.
    with c.begin():
        owner(c, selected.target, addresses)
        empty(c)
        # Compute SCRAM verifier client-side: raw password never enters SQL text.
        verifier = c.connection.dbapi_connection.pgconn.encrypt_password(
            selected.runtime_password.get_secret_value().encode(), b'merge_runtime', b'scram-sha-256').decode()
        statement = sql.SQL('CREATE ROLE merge_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Literal(verifier)).as_string()
        c.exec_driver_sql(statement)
        c.execute(text('REVOKE ALL ON DATABASE merge_prod FROM PUBLIC'))
        c.execute(text('GRANT CONNECT ON DATABASE merge_prod TO merge_runtime'))
        c.execute(text('REVOKE ALL ON SCHEMA public FROM PUBLIC'))
        c.execute(text('GRANT USAGE ON SCHEMA public TO merge_runtime'))
        upgrade(c, selected, addresses)
        grants.apply(c, REVISION)
        c.execute(text('INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:id,:name,:minimum,:maximum)'),
                  dict(id=selected.catalog_id, name=selected.catalog_name, minimum=selected.minimum, maximum=selected.maximum))
        if c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() != [REVISION]:
            raise ValueError('Exact schema revision required')
        changed = c.execute(text("UPDATE merge_deployment.setup_claim SET state='complete' WHERE singleton AND attempt=:attempt AND source_commit=:commit AND state='claimed'"),
                            dict(attempt=selected.attempt, commit=selected.commit)).rowcount
        if changed != 1: raise ValueError('Setup claim changed; roll back')


def initialize(selected):
    addresses = database.private_addresses(selected.target)
    resource = database.setup_engine(selected.target, addresses)
    try:
        with resource.connect() as c:
            owner(c, selected.target, addresses)
            locked = c.execute(text('SELECT pg_try_advisory_lock(:key)'), dict(key=LOCK)).scalar_one()
            c.commit()
            if locked is not True: raise ValueError('Another explicit setup is active')
            try:
                if claim(c, selected): apply(c, selected, addresses)
            finally:
                c.rollback()
                c.execute(text('SELECT pg_advisory_unlock(:key)'), dict(key=LOCK))
                c.commit()
    finally:
        resource.dispose()
    # Completed claims may only repeat this read-only runtime verification.
    runtime = replace(selected.target, role='runtime', password=selected.runtime_password)
    resource = database.engine(runtime)
    try:
        database.ready(resource)
    finally:
        resource.dispose()
    return dict(initialized=True, revision=REVISION, source_commit=selected.commit, attempt=str(selected.attempt))
