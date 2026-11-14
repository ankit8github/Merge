"""New fixed targets; legacy merge_test guardrails are deliberately independent."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Event
from sqlalchemy import URL, create_engine, event, text

REVISION = '0006_profiles'
PREVIOUS = '0005_invitations'
TARGETS = {'profiles': ('merge_profile_test','merge_app'), 'benchmark': ('merge_bench','merge_bench_app')}


@dataclass(frozen=True, repr=False)
class Target:
    kind: str
    confirmed: bool
    password: str = field(repr=False)
    host: str = '127.0.0.1'
    port: int = 5432

    def url(self):
        if self.kind not in TARGETS or self.confirmed is not True or self.host!='127.0.0.1' or self.port!=5432 or not self.password:
            raise ValueError('Explicit fixed release target required')
        db,role=TARGETS[self.kind]
        return URL.create('postgresql+psycopg',username=role,password=self.password,host=self.host,port=self.port,database=db)


def identity(c, target):
    target.url()  # Validate BEFORE issuing SQL, even for directly supplied handles.
    db,role=TARGETS[target.kind]
    row=tuple(c.execute(text('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()')).one())
    if row not in ((db,role,'127.0.0.1',5432),(db,role,'127.0.0.1/32',5432)):
        raise ValueError('Release target identity rejected')
    flags=tuple(c.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user')).one())
    if any(flags): raise ValueError('Privileged release role rejected')
    if c.execute(text('SELECT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user))')).scalar_one():
        raise ValueError('Release role membership rejected')


class Guard:
    def __init__(self,target,revision):
        if revision not in (None,PREVIOUS,REVISION): raise ValueError('Unsupported release revision')
        target.url(); self.target=target; self.revision=revision; self.failed=Event()

    def __call__(self,c):
        try:
            if self.failed.is_set() or c.in_transaction() or c.in_nested_transaction(): raise ValueError()
            if (c.dialect.name!='postgresql' or c.dialect.driver!='psycopg' or c.dialect.is_async is not False
                or c.connection.dbapi_connection.autocommit is not False or c.get_execution_options().get('isolation_level')=='AUTOCOMMIT'):
                raise ValueError()
            c.execute(text('SET TRANSACTION READ ONLY')); identity(c,self.target)
            settings=tuple(c.execute(text("SELECT current_setting('transaction_isolation'),current_setting('default_transaction_isolation'),current_setting('transaction_read_only'),current_setting('lock_timeout'),current_setting('statement_timeout')")).one())
            if settings!=('read committed','read committed','on','5s','15s'): raise ValueError()
            exists=c.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL")).scalar_one()
            revisions=c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() if exists else []
            if revisions != ([] if self.revision is None else [self.revision]): raise ValueError()
            c.rollback()
        except BaseException:
            self.failed.set()
            try: c.invalidate()
            except Exception: pass
            raise ValueError('Release connection guard rejected; stop') from None


@contextmanager
def guarded_engine(target,revision=REVISION):
    url=target.url()
    engine=create_engine(url,hide_parameters=True,isolation_level='READ COMMITTED',
        execution_options={'schema_translate_map':{None:'public'}},
        connect_args={'connect_timeout':5,'options':'-c statement_timeout=15000 -c lock_timeout=5000'})
    guard=Guard(target,revision); event.listen(engine,'engine_connect',guard)
    try:
        with engine.connect(): pass
        yield engine,guard
        if guard.failed.is_set(): raise ValueError('A release connection failed')
    finally: engine.dispose()
