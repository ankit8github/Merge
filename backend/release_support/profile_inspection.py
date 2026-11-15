"""Owner-run fixed-profile SELECT-only snapshot; hidden input, never automatic retry."""
import argparse
import ast
import getpass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import warnings
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
TABLES = ('users','hackathons','teams','memberships','idempotency_records','audit_events','outbox_events','account_credentials','auth_sessions','auth_throttle_buckets','join_requests','invitations')
TARGET = dict(host='127.0.0.1',port=5432,dbname='merge_profile_test',user='merge_app')

def source():
    def git(*args):
        return subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),*args],cwd=ROOT,text=True).splitlines()
    paths=sorted(set(git('ls-files')+git('ls-files','--others','--exclude-standard')))
    return dict(head=git('rev-parse','HEAD')[0],files={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in paths if (ROOT/p).is_file()})

def expected():
    ddl=[]
    for path in sorted((ROOT/'backend/alembic/versions').glob('000[1-5]_*.py')):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('TABLE_DDL','FUNCTION_DDL','GUARD_DDL','VALIDATE_DDL') for t in node.targets):
                value=ast.literal_eval(node.value)
                ddl.extend(value if isinstance(value,tuple) else [value])
    ddl+=['CREATE INDEX ix_requests_pending ON public.join_requests(team_id,id) WHERE status=\'pending\'', 'CREATE INDEX ix_invitations_inbox ON public.invitations(hackathon_id,recipient_id,id)']
    return ddl

def acquire_password():
    """Use an existing process credential or hidden console input; never persist it."""
    value=os.environ.get('MERGE_RELEASE_DB_PASSWORD') or os.environ.get('PGPASSWORD')
    if not value:
        # fallback_getpass warns BEFORE reading: an unavailable hidden console
        # must stop here rather than fall back to echoed stdin.
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            value=getpass.getpass('Existing merge_app password (hidden): ')
    if not value:
        raise ValueError('Password required; inspection not started')
    return value


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-profile-test',action='store_true',required=True)
    parser.parse_args(argv)
    result=dict(schema_version=1,kind='profile_0005_readonly_inspection',started_at=datetime.now(timezone.utc).isoformat(),target=TARGET,source=source(),collector_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),checks={},observed={},query_count=0,connection_attempts=0,status='blocked',stage='credential_preflight')
    code=1
    def check(name,ok):
        result['checks'][name]=bool(ok)
        if not ok: raise ValueError('Required inspection condition failed')
    try:
        check('fixed_profile_target', TARGET==dict(host='127.0.0.1',port=5432,dbname='merge_profile_test',user='merge_app') and TARGET['dbname'] not in ('merge_dev','merge_test'))
        result['expected_ddl']=expected()
        kwargs=dict(TARGET,hostaddr='127.0.0.1',connect_timeout=5,autocommit=False,row_factory=dict_row,application_name='merge_profile_0005_readonly_inspection',options='-c default_transaction_read_only=on -c statement_timeout=15000 -c lock_timeout=5000 -c search_path=pg_catalog')
        # Explicit address/target/user prevent libpq environment redirection.
        kwargs['password']=acquire_password()
        result['connection_attempts']=1
        result['stage']='connect'
        c=psycopg.connect(**kwargs)
        try:
            c.read_only=True
            c.isolation_level=psycopg.IsolationLevel.REPEATABLE_READ
            def query(statement,params=None):
                # Only allow SELECT. Transaction BEGIN/ROLLBACK are driver controlled.
                rendered=statement.as_string(c) if isinstance(statement,sql.Composable) else statement
                if not rendered.lstrip().upper().startswith('SELECT '):raise ValueError('Non-SELECT inspection rejected')
                result['query_count']+=1
                return c.execute(statement,params).fetchall()
            result['stage']='identity_and_transaction'
            ident=query("SELECT current_database() AS database,current_user AS role,session_user AS session_role,host(inet_server_addr()) AS host,inet_server_port() AS port,current_setting('server_version') AS server_version,current_setting('transaction_read_only') AS read_only,current_setting('default_transaction_read_only') AS default_read_only,current_setting('transaction_isolation') AS isolation,current_setting('statement_timeout') AS statement_timeout,current_setting('lock_timeout') AS lock_timeout")[0]
            result['observed']['identity']=ident
            check('actual_identity', all(ident[k]==v for k,v in dict(database='merge_profile_test',role='merge_app',session_role='merge_app',host='127.0.0.1',port=5432).items()))
            check('restricted_readonly_transaction',ident['read_only']=='on' and ident['default_read_only']=='on' and ident['isolation']=='repeatable read' and ident['statement_timeout']=='15s' and ident['lock_timeout']=='5s' and c.autocommit is False)
            role=query('SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=current_user')[0]
            members=query('SELECT pg_catalog.pg_get_userbyid(roleid) AS parent_role,admin_option FROM pg_catalog.pg_auth_members WHERE member=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user)')
            result['observed'].update(role=role,memberships=members)
            check('unprivileged_login_role',role['rolcanlogin'] and not any(role[k] for k in ('rolsuper','rolcreatedb','rolcreaterole','rolreplication','rolbypassrls')) and members==[])
            result['stage']='catalog_inventory'
            relations=query("SELECT c.relname,c.relkind,pg_catalog.pg_get_userbyid(c.relowner) AS owner,c.relrowsecurity,c.relforcerowsecurity,c.relpersistence FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname")
            result['observed']['relations']=relations
            check('exact_application_table_set',sorted(r['relname'] for r in relations if r['relkind']=='r')==sorted((*TABLES,'alembic_version')))
            check('no_unexpected_relation_kinds',all(r['relkind'] in ('r','i') for r in relations))
            check('relation_ownership_and_visibility',all(r['owner']=='merge_app' and not r['relrowsecurity'] and not r['relforcerowsecurity'] and r['relpersistence']=='p' for r in relations))
            revisions=query('SELECT version_num FROM public.alembic_version')
            result['observed']['revision_rows']=revisions
            check('exact_0005_revision',revisions==[{'version_num':'0005_invitations'}])
            profile=query("SELECT pg_catalog.to_regclass('public.participant_profiles') IS NULL AS relation_absent,pg_catalog.to_regtype('public.participant_profiles') IS NULL AS type_absent,pg_catalog.to_regtype('public._participant_profiles') IS NULL AS array_type_absent")[0]
            result['observed']['profiles']=profile
            check('profile_objects_absent',all(profile.values()))
            counts={}
            for table in TABLES:
                counts[table]=query(sql.SQL('SELECT count(*) AS count FROM {}.{}').format(sql.Identifier('public'),sql.Identifier(table)))[0]['count']
            result['observed']['table_counts']=counts
            check('all_twelve_application_tables_empty',all(n==0 for n in counts.values()))
            result['observed']['columns']=query("SELECT c.relname AS table_name,a.attnum,a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod) AS data_type,a.attnotnull,a.attidentity,a.attgenerated,pg_catalog.pg_get_expr(d.adbin,d.adrelid) AS default_expression FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname='public' AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum")
            result['observed']['constraints']=query("SELECT c.relname AS table_name,k.conname,k.contype,k.convalidated,k.condeferrable,k.condeferred,pg_catalog.pg_get_constraintdef(k.oid,true) AS definition,ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY x(attnum,ord) JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum=x.attnum ORDER BY x.ord) AS columns,r.relname AS referenced_table,ARRAY(SELECT a.attname FROM unnest(k.confkey) WITH ORDINALITY x(attnum,ord) JOIN pg_catalog.pg_attribute a ON a.attrelid=r.oid AND a.attnum=x.attnum ORDER BY x.ord) AS referenced_columns,k.confupdtype,k.confdeltype,k.confmatchtype FROM pg_catalog.pg_constraint k JOIN pg_catalog.pg_class c ON c.oid=k.conrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_catalog.pg_class r ON r.oid=k.confrelid WHERE n.nspname='public' ORDER BY c.relname,k.conname")
            result['observed']['indexes']=query("SELECT t.relname AS table_name,c.relname AS index_name,i.indisunique,i.indisprimary,i.indisvalid,i.indisready,pg_catalog.pg_get_indexdef(i.indexrelid) AS definition FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class c ON c.oid=i.indexrelid JOIN pg_catalog.pg_class t ON t.oid=i.indrelid JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public' ORDER BY t.relname,c.relname")
            result['observed']['triggers']=query("SELECT c.relname AS table_name,t.tgname,t.tgenabled,t.tgdeferrable,t.tginitdeferred,t.tgtype,p.proname AS function_name,nf.nspname AS function_schema,pg_catalog.pg_get_triggerdef(t.oid,true) AS definition FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid JOIN pg_catalog.pg_namespace nf ON nf.oid=p.pronamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname")
            result['observed']['internal_triggers']=query("SELECT c.relname AS table_name,count(*) AS count,bool_and(t.tgenabled='O') AS all_enabled FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND t.tgisinternal GROUP BY c.relname ORDER BY c.relname")
            result['observed']['functions']=query("SELECT p.proname,pg_catalog.pg_get_function_identity_arguments(p.oid) AS arguments,pg_catalog.pg_get_function_result(p.oid) AS result_type,pg_catalog.pg_get_userbyid(p.proowner) AS owner,l.lanname,p.provolatile,p.prosecdef,p.proconfig,p.prosrc AS body FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace JOIN pg_catalog.pg_language l ON l.oid=p.prolang WHERE n.nspname='public' ORDER BY p.proname,arguments")
            result['observed']['types']=query("SELECT t.typname,t.typtype,t.typcategory,pg_catalog.pg_get_userbyid(t.typowner) AS owner FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public' ORDER BY t.typname")
            result['stage']='ownership_and_grants'
            result['observed']['database']=query("SELECT d.datname,pg_catalog.pg_get_userbyid(d.datdba) AS owner,d.datallowconn,d.datistemplate FROM pg_catalog.pg_database d WHERE d.datname=current_database()")[0]
            result['observed']['database_acl']=query("SELECT CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(a.grantee) END AS grantee,a.privilege_type,a.is_grantable FROM pg_catalog.pg_database d CROSS JOIN LATERAL pg_catalog.aclexplode(coalesce(d.datacl,pg_catalog.acldefault('d',d.datdba))) a WHERE d.datname=current_database() ORDER BY grantee,a.privilege_type")
            result['observed']['schema']=query("SELECT n.nspname,pg_catalog.pg_get_userbyid(n.nspowner) AS owner,pg_catalog.has_schema_privilege(current_user,n.oid,'USAGE') AS can_use,pg_catalog.has_schema_privilege(current_user,n.oid,'CREATE') AS can_create FROM pg_catalog.pg_namespace n WHERE n.nspname='public'")[0]
            result['observed']['schema_acl']=query("SELECT CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(a.grantee) END AS grantee,a.privilege_type,a.is_grantable FROM pg_catalog.pg_namespace n CROSS JOIN LATERAL pg_catalog.aclexplode(coalesce(n.nspacl,pg_catalog.acldefault('n',n.nspowner))) a WHERE n.nspname='public' ORDER BY grantee,a.privilege_type")
            result['observed']['relation_acl']=query("SELECT c.relname,CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(a.grantee) END AS grantee,a.privilege_type,a.is_grantable FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL pg_catalog.aclexplode(coalesce(c.relacl,pg_catalog.acldefault('r',c.relowner))) a WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname,grantee,a.privilege_type")
            result['observed']['default_acl']=query("SELECT pg_catalog.pg_get_userbyid(d.defaclrole) AS role,n.nspname,d.defaclobjtype,d.defaclacl::text AS acl FROM pg_catalog.pg_default_acl d LEFT JOIN pg_catalog.pg_namespace n ON n.oid=d.defaclnamespace WHERE d.defaclrole=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) OR n.nspname='public' ORDER BY role,n.nspname,d.defaclobjtype")
            db=result['observed']['database'];schema=result['observed']['schema']
            check('database_ownership',db['owner']=='merge_app' and db['datallowconn'] and not db['datistemplate'])
            check('database_acl',all(r['grantee']=='merge_app' for r in result['observed']['database_acl']) and {r['privilege_type'] for r in result['observed']['database_acl']}=={'CONNECT','CREATE','TEMPORARY'})
            check('schema_ownership_and_grants',schema['owner'] in ('pg_database_owner','postgres','merge_app') and schema['can_use'] and schema['can_create'] and all(r['grantee'] in ('merge_app',schema['owner']) for r in result['observed']['schema_acl']) and {r['privilege_type'] for r in result['observed']['schema_acl'] if r['grantee']=='merge_app'}=={'USAGE','CREATE'})
            check('no_unexpected_table_grantees',all(r['grantee']=='merge_app' for r in result['observed']['relation_acl']))
            check('no_unexpected_default_acl',result['observed']['default_acl']==[])
            check('constraints_validated',all(r['convalidated'] for r in result['observed']['constraints']))
            check('indexes_valid_and_ready',all(r['indisvalid'] and r['indisready'] for r in result['observed']['indexes']))
            check('all_recorded_triggers_enabled',all(r['tgenabled']=='O' for r in result['observed']['triggers']) and all(r['all_enabled'] for r in result['observed']['internal_triggers']))
            result['stage']='snapshot_complete'
        finally:
            c.rollback()
            c.close()
        check('source_unchanged',result['source']==source())
        result['status']='snapshot_complete_requires_definition_review'
        code=0
    except (Exception,KeyboardInterrupt) as e:
        # Never serialize exception messages, connection strings, credentials or rows.
        result['failure']={'stage':result['stage'],'exception_class':type(e).__name__,'sqlstate':getattr(e,'sqlstate',None)}
    result['completed_at']=datetime.now(timezone.utc).isoformat()
    result['exit_intent']=code
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return code

if __name__=='__main__':
    # Direct owner invocation always retains evidence and an independent native exit.
    from release_support.profile_inspection_capture import main as capture_main
    sys.exit(capture_main())
