"""Independent production guards; old local/test/release targets never change."""
from threading import Event
from sqlalchemy import create_engine,event,text
from app.production.config import DATABASE,DB_ADDRESS,ROLES,REVISION,PREVIOUS


def identity(c,config):
    config.url()
    who=tuple(c.execute(text('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()')).one())
    if who not in ((DATABASE,ROLES[config.role],DB_ADDRESS,5432),(DATABASE,ROLES[config.role],DB_ADDRESS+'/32',5432)):
        raise ValueError('Production database identity rejected')
    flags=tuple(c.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user')).one())
    if any(flags) or c.execute(text('SELECT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user))')).scalar_one():
        raise ValueError('Production role authority rejected')
    permissions=tuple(c.execute(text("SELECT has_database_privilege(current_user,current_database(),'CONNECT'),has_schema_privilege(current_user,'public','USAGE'),has_schema_privilege(current_user,'public','CREATE'),has_database_privilege(current_user,current_database(),'CREATE'),has_database_privilege(current_user,current_database(),'TEMP')")).one())
    if permissions!=(True,True,config.role=='migrator',False,False):
        raise ValueError('Production schema privileges rejected')


class Guard:
    def __init__(self,config,revision=REVISION):
        config.url()
        if revision not in (None,PREVIOUS,REVISION) or config.role=='runtime' and revision!=REVISION:
            raise ValueError('Unsupported production revision')
        self.config=config;self.revision=revision;self.failed=Event()

    def __call__(self,c):
        try:
            if (self.failed.is_set() or c.in_transaction() or c.in_nested_transaction()
                or c.dialect.name!='postgresql' or c.dialect.driver!='psycopg' or c.dialect.is_async is not False
                or c.connection.dbapi_connection.autocommit is not False or c.get_execution_options().get('isolation_level')=='AUTOCOMMIT'):
                raise ValueError()
            c.execute(text('SET TRANSACTION READ ONLY'));identity(c,self.config)
            settings=tuple(c.execute(text("SELECT current_setting('transaction_isolation'),current_setting('default_transaction_isolation'),current_setting('transaction_read_only'),current_setting('lock_timeout'),current_setting('statement_timeout'),current_setting('default_transaction_read_only'),pg_is_in_recovery()")).one())
            if settings!=('read committed','read committed','on','5s','15s','off',False):raise ValueError()
            exists=c.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL")).scalar_one()
            revisions=c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() if exists else []
            if revisions != ([] if self.revision is None else [self.revision]):raise ValueError()
            c.rollback()
        except BaseException:
            self.failed.set()
            try:c.invalidate()
            except Exception:pass
            raise ValueError('Production connection rejected; stop') from None


def engine(config,revision=REVISION):
    guard=Guard(config,revision)
    result=create_engine(config.url(),hide_parameters=True,echo=False,isolation_level='READ COMMITTED',
        pool_size=5,max_overflow=5,pool_timeout=5,pool_recycle=1800,
        execution_options={'schema_translate_map':{None:'public'}},
        connect_args={'connect_timeout':5,'options':'-c statement_timeout=15000 -c lock_timeout=5000 -c search_path=public'})
    event.listen(result,'engine_connect',guard)
    return result


def ready(engine):
    # Revision and identity checked on each connection; schema drift fails too.
    from app.db.base import Base
    import app.models
    with engine.connect() as c:
        c.execute(text('SET TRANSACTION READ ONLY'))
        expected=set(Base.metadata.tables)
        actual=set(c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars())
        if actual!=expected|{'alembic_version'}:raise ValueError('Production table inventory mismatch')
        from app.production.grants import verify
        verify(c)
        c.execute(text('SELECT 1 FROM public.participant_profiles LIMIT 1'))
