"""Owner-only prepare/migrate/verify for NEW targets; never retained merge_test."""
import argparse
from getpass import getpass
import os
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from release_support.targets import Target,TARGETS,PREVIOUS,REVISION,guarded_engine
from release_support.evidence import sources,receipt

TABLES=('users','hackathons','teams','memberships','idempotency_records','audit_events','outbox_events',
        'account_credentials','auth_sessions','auth_throttle_buckets','join_requests','invitations')


def snapshot(c):
    # All old tables, including invitations, are locked and fingerprinted in the
    # migration's OWN transaction. Hashes never include raw row contents in reports.
    result={}
    for name in TABLES:
        c.execute(text(f'LOCK TABLE public.{name} IN SHARE MODE'))
        result[name]=tuple(c.execute(text(f"SELECT count(*),coalesce(md5(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text))),md5('')) FROM public.{name} t")).one())
    return result


def migrate(c,target,action):
    if action not in ('prepare','migrate'): raise ValueError('Unknown migration action')
    if c.in_transaction(): raise ValueError('Migration requires unowned fresh handle')
    root=Path(__file__).resolve().parents[1]
    config=Config(); config.set_main_option('path_separator','os')
    config.set_main_option('script_location',str(root/'release_alembic'))
    config.set_main_option('version_locations',str(root/'alembic/versions'))
    config.attributes.update(release_connection=c,release_target=target)
    with c.begin():
        c.execute(text("SET LOCAL lock_timeout='5s'"));c.execute(text("SET LOCAL statement_timeout='15s'"))
        if action=='prepare':
            count=c.execute(text("SELECT (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public')+(SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public')")).scalar_one()
            if count: raise ValueError('Prepare requires completely empty public schema')
            before=None
        else:
            if c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()!=[PREVIOUS]: raise ValueError('Migration requires exact 0005')
            before=snapshot(c)
        command.upgrade(config,PREVIOUS if action=='prepare' else REVISION)
        if before is not None and snapshot(c)!=before: raise ValueError('Old rows changed; DDL rolled back')
        if c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()!=[PREVIOUS if action=='prepare' else REVISION]: raise ValueError('Migration outcome mismatch')
    return {'old_tables_preserved':before is not None,'old_counts':None if before is None else {k:v[0] for k,v in before.items()}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','migrate','verify'))
    parser.add_argument('--target',choices=TARGETS,required=True)
    parser.add_argument('--confirm-target',required=True)
    args=parser.parse_args()
    if args.confirm_target!=TARGETS[args.target][0]: parser.error('Explicit target confirmation mismatch')
    password=os.environ.get('MERGE_RELEASE_DB_PASSWORD') or getpass('Existing target role password (hidden): ')
    before=sources(); code=1; metadata={}
    try:
        revision={'prepare':None,'migrate':PREVIOUS,'verify':REVISION}[args.action]
        target=Target(args.target,True,password)
        with guarded_engine(target,revision) as (engine,guard):
            with engine.connect() as c:
                # Guard revision belongs to the start state; no checkout after DDL.
                if args.action!='verify': metadata=migrate(c,target,args.action)
        code=0
    except Exception:
        print('Release database action failed; details suppressed. Preserve state; stop.')
    path=receipt('migration',before,code,target=args.target,action=args.action,**metadata)
    print(f'Receipt: {path.name}'); raise SystemExit(code)


if __name__=='__main__': main()
