"""Create ONLY fresh production roles/schema grants in a new empty merge_prod."""
import json
import psycopg
from psycopg import sql
from app.production.config import load,secret_file,DATABASE,DB_HOST,DB_ADDRESS,SafeParser


def initialize(c,runtime,migrator):
    if tuple(c.execute('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()').fetchone()) not in (
        (DATABASE,'postgres',DB_ADDRESS,5432),(DATABASE,'postgres',DB_ADDRESS+'/32',5432)):
        raise ValueError('Unexpected production bootstrap identity')
    if c.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname IN ('merge_runtime','merge_migrator')) OR EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public') OR EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public')").fetchone()[0]:
        raise ValueError('Production bootstrap requires fresh role/schema namespace')
    for role,password in [('merge_runtime',runtime),('merge_migrator',migrator)]:
        c.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(role),sql.Literal(password.get_secret_value())))
    c.execute('REVOKE ALL ON DATABASE merge_prod FROM PUBLIC')
    c.execute('GRANT CONNECT ON DATABASE merge_prod TO merge_runtime,merge_migrator')
    c.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
    c.execute('GRANT USAGE ON SCHEMA public TO merge_runtime,merge_migrator')
    c.execute('GRANT CREATE ON SCHEMA public TO merge_migrator')


def main():
    p=SafeParser(description=__doc__);p.add_argument('--confirm-new-merge-prod',action='store_true',required=True);p.parse_args()
    code=1
    try:
        migrator=load('migrator');runtime=secret_file('runtime_db_password');admin=secret_file('admin_db_password')
        if len({admin.get_secret_value(),runtime.get_secret_value(),migrator.password.get_secret_value()})!=3:raise ValueError('Distinct DB secrets required')
        with psycopg.connect(host=DB_HOST,port=5432,dbname=DATABASE,user='postgres',password=admin.get_secret_value(),
            connect_timeout=5,options='-c statement_timeout=15000 -c lock_timeout=5000') as c:
            initialize(c,runtime,migrator.password)
        code=0
    except Exception:pass
    print(json.dumps(dict(action='bootstrap',database=DATABASE,native_exit_code=code)))
    raise SystemExit(code)


if __name__=='__main__':main()
