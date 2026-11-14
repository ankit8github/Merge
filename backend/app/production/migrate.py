"""Owner-only explicit production migration/catalog actions; no cleanup/downgrade."""
import json
from pathlib import Path
from uuid import UUID
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from app.production import config,database,grants
from release_support.migrations import snapshot


def migrate(c,target,action):
    if target.role!='migrator' or action not in ('prepare','migrate') or c.in_transaction():
        raise ValueError('Explicit production migration owner required')
    root=Path(__file__).resolve().parents[2]
    cfg=Config();cfg.set_main_option('script_location',str(root/'production_alembic'))
    cfg.set_main_option('version_locations',str(root/'alembic/versions'));cfg.set_main_option('path_separator','os')
    cfg.attributes.update(production_connection=c,production_config=target)
    final=config.PREVIOUS if action=='prepare' else config.REVISION
    with c.begin():
        database.identity(c,target)
        c.execute(text("SET LOCAL lock_timeout='5s'"));c.execute(text("SET LOCAL statement_timeout='15s'"))
        if action=='prepare':
            objects=c.execute(text("SELECT (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public')+(SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public')")).scalar_one()
            if objects:raise ValueError('Prepare requires empty production schema')
            before=None
        else:
            if c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()!=[config.PREVIOUS]:raise ValueError('Exact 0005 required')
            before=snapshot(c)  # Reuse Batch B, including all twelve old tables.
        command.upgrade(cfg,final);grants.apply(c,final)
        if before is not None and snapshot(c)!=before:raise ValueError('Old rows changed; roll back DDL')
        if c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()!=[final]:raise ValueError('Revision mismatch')
    return dict(revision=final,old_counts=None if before is None else {k:v[0] for k,v in before.items()})


def catalog(c,identifier,name,minimum,maximum):
    # Administrator-owned configuration, not participant team mutation.
    if not isinstance(identifier,UUID) or not isinstance(name,str) or not 1<=len(name)<=120 or not name.strip() or '\x00' in name or not 1<=minimum<=maximum<=100:
        raise ValueError('Invalid bounded catalog input')
    with c.begin():
        c.execute(text('INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:id,:name,:minimum,:maximum)'),
            dict(id=identifier,name=name,minimum=minimum,maximum=maximum))
    return dict(hackathon_id=str(identifier))


def main():
    p=config.SafeParser(description=__doc__);p.add_argument('action',choices=('prepare','migrate','verify','catalog'))
    p.add_argument('--confirm-merge-prod',action='store_true',required=True)
    p.add_argument('--id',type=UUID);p.add_argument('--name');p.add_argument('--min-size',type=int);p.add_argument('--max-size',type=int);args=p.parse_args()
    if args.action=='catalog' and any(v is None for v in (args.id,args.name,args.min_size,args.max_size)):p.error('Explicit catalog ID/name/sizes required')
    if args.action!='catalog' and any(v is not None for v in (args.id,args.name,args.min_size,args.max_size)):p.error('Catalog arguments require catalog action')
    result={};code=1;resource=None
    try:
        target=config.load('migrator');revision={'prepare':None,'migrate':config.PREVIOUS,'verify':config.REVISION,'catalog':config.REVISION}[args.action]
        resource=database.engine(target,revision)
        with resource.connect() as c:
            if args.action in ('prepare','migrate'):result=migrate(c,target,args.action)
            elif args.action=='catalog':result=catalog(c,args.id,args.name,args.min_size,args.max_size)
        code=0
    except Exception:pass
    finally:
        if resource is not None:
            try:resource.dispose()
            except Exception:code=1
    print(json.dumps(dict(action=args.action,database=config.DATABASE,native_exit_code=code,**result)))
    raise SystemExit(code)


if __name__=='__main__':main()
