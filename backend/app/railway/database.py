"""Private DNS-pinned PostgreSQL 17 guard; production identity never falls back."""
from ipaddress import ip_address, ip_interface, ip_network
import socket
from threading import Event
from sqlalchemy import create_engine, event, text
from app.railway.config import DATABASE, DB_HOST, DB_PORT, ROLES, REVISION, PREVIOUS
from app.production.database import ready  # Same table/grant/revision readiness.

NETWORKS = tuple(map(ip_network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
                                 '100.64.0.0/10', 'fc00::/7')))


def private_addresses():
    addresses = {str(ip_address(item[4][0])) for item in
                 socket.getaddrinfo(DB_HOST, DB_PORT, type=socket.SOCK_STREAM)}
    if not addresses or any(not any(ip_address(a) in n for n in NETWORKS) for a in addresses):
        raise ValueError('Private Railway DNS addresses required')
    return tuple(sorted(addresses))


def server(c, addresses, *, db=DATABASE, role):
    who = tuple(c.execute(text('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()')).one())
    if len(who) != 4 or who[:2] != (db, role) or who[3] != DB_PORT:
        raise ValueError('Railway database identity rejected')
    if str(ip_interface(who[2]).ip) not in addresses:
        raise ValueError('Railway database server address rejected')
    version = int(c.execute(text("SELECT current_setting('server_version_num')")).scalar_one())
    if not 170000 <= version < 180000:
        raise ValueError('PostgreSQL major 17 required')
    if c.execute(text('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()')).scalar_one() is not True:
        raise ValueError('Encrypted private PostgreSQL connection required')


def identity(c, target, addresses):
    target.url()
    server(c, addresses, role=ROLES[target.role])
    flags = tuple(c.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user')).one())
    if flags != (False,) * 5 or c.execute(text('SELECT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user))')).scalar_one():
        raise ValueError('Railway role authority rejected')
    permissions = tuple(c.execute(text("SELECT has_database_privilege(current_user,current_database(),'CONNECT'),has_schema_privilege(current_user,'public','USAGE'),has_schema_privilege(current_user,'public','CREATE'),has_database_privilege(current_user,current_database(),'CREATE'),has_database_privilege(current_user,current_database(),'TEMP')")).one())
    if permissions != (True, True, target.role == 'migrator', False, False):
        raise ValueError('Railway schema privileges rejected')


class Guard:
    def __init__(self, target, addresses, revision=REVISION):
        target.url()
        if revision not in (None, PREVIOUS, REVISION) or target.role == 'runtime' and revision != REVISION:
            raise ValueError('Unsupported Railway revision')
        if not addresses or any(not any(ip_address(a) in n for n in NETWORKS) for a in addresses):
            raise ValueError('Private Railway server addresses required')
        self.target, self.addresses, self.revision = target, tuple(addresses), revision
        self.failed = Event()

    def __call__(self, c):
        try:
            if (self.failed.is_set() or c.in_transaction() or c.in_nested_transaction()
                or c.dialect.name != 'postgresql' or c.dialect.driver != 'psycopg'
                or c.dialect.is_async is not False or c.connection.dbapi_connection.autocommit is not False
                or c.get_execution_options().get('isolation_level') == 'AUTOCOMMIT'):
                raise ValueError()
            c.execute(text('SET TRANSACTION READ ONLY'))
            identity(c, self.target, self.addresses)
            settings = tuple(c.execute(text("SELECT current_setting('transaction_isolation'),current_setting('default_transaction_isolation'),current_setting('transaction_read_only'),current_setting('lock_timeout'),current_setting('statement_timeout'),current_setting('default_transaction_read_only'),pg_is_in_recovery()")).one())
            if settings != ('read committed', 'read committed', 'on', '5s', '15s', 'off', False):
                raise ValueError()
            exists = c.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL")).scalar_one()
            versions = c.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() if exists else []
            if versions != ([] if self.revision is None else [self.revision]): raise ValueError()
            c.rollback()
        except BaseException:
            self.failed.set()
            try: c.invalidate()
            except Exception: pass
            raise ValueError('Railway connection rejected; stop') from None


def engine(target, revision=REVISION, *, addresses=None):
    addresses = private_addresses() if addresses is None else addresses
    guard = Guard(target, addresses, revision)
    result = create_engine(target.url(), hide_parameters=True, echo=False,
        isolation_level='READ COMMITTED', pool_size=5, max_overflow=5, pool_timeout=5,
        pool_recycle=1800, execution_options={'schema_translate_map': {None: 'public'}},
        connect_args={'hostaddr': addresses[0], 'sslmode': 'require', 'connect_timeout': 5,
                      'options': '-c statement_timeout=15000 -c lock_timeout=5000 -c search_path=public'})
    event.listen(result, 'engine_connect', guard)
    return result
