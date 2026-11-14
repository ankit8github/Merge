"""GitHub-hosted ephemeral-container orchestration; NOT a local provisioning tool."""
import argparse
import ast
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from hashlib import sha256
from release_support.evidence import ROOT,sources,receipt,validate_test_report

PLANS={
    '0003_auth':(('auth-api',18),('team-api',35)),
    '0004_admission':(('admission',35),),
    '0005_invitations':(('invitations',13),('lifecycle',10),('realtime',4)),
    '0006_profiles':(('profiles',30),),
}


def require_ci(env):
    if env.get('GITHUB_ACTIONS')!='true' or env.get('CI')!='true' or env.get('RUNNER_ENVIRONMENT')!='github-hosted' or not env.get('CI_ADMIN_PASSWORD'):
        raise ValueError('Only explicit GitHub-hosted ephemeral CI is supported')


def bootstrap(revision,password):
    require_ci(os.environ)
    import psycopg
    from psycopg import sql
    database='merge_profile_test' if revision=='0006_profiles' else 'merge_test'
    with psycopg.connect(host='127.0.0.1',port=5432,dbname='postgres',user='postgres',password=os.environ['CI_ADMIN_PASSWORD'],autocommit=True,connect_timeout=5) as c:
        identity=c.execute('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()').fetchone()
        if identity not in (('postgres','postgres','127.0.0.1',5432),('postgres','postgres','127.0.0.1/32',5432)):raise ValueError('CI bootstrap identity rejected')
        if c.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='merge_app') OR EXISTS(SELECT 1 FROM pg_database WHERE datname IN ('merge_test','merge_profile_test','merge_dev','merge_bench'))").fetchone()[0]:raise ValueError('CI requires fresh role/database namespace; no adoption')
        c.execute(sql.SQL('CREATE ROLE merge_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Literal(password)))
        c.execute(sql.SQL('CREATE DATABASE {} OWNER merge_app TEMPLATE template0').format(sql.Identifier(database)))
        c.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
    with psycopg.connect(host='127.0.0.1',port=5432,dbname=database,user='postgres',password=os.environ['CI_ADMIN_PASSWORD'],autocommit=True,connect_timeout=5) as c:
        c.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC');c.execute('GRANT USAGE,CREATE ON SCHEMA public TO merge_app')


def child(arguments,env,timeout=1200):
    # Discard potentially private third-party tracebacks; only native code and
    # allowlisted diagnostic JSON are retained by the parent.
    return subprocess.run([sys.executable,'-m',*arguments],cwd=ROOT/'backend',env=env,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=timeout).returncode


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revision',choices=PLANS,required=True)
    p.add_argument('--confirm-ephemeral-postgres',action='store_true',required=True);args=p.parse_args()
    require_ci(os.environ);before=sources();steps=[];code=1
    try:
        password=secrets.token_urlsafe(32);bootstrap(args.revision,password)
        env=dict(os.environ,MERGE_TEST_DB_PASSWORD=password,MERGE_RELEASE_DB_PASSWORD=password)
        if args.revision=='0006_profiles':
            for action in ('prepare','migrate','verify'):
                rc=child(['release_support.migrations',action,'--target','profiles','--confirm-target','merge_profile_test'],env)
                steps.append(dict(action=action,native_exit_code=rc))
                if rc:raise ValueError('CI migration failed')
        else:
            revisions=['0002_domain','0003_auth','0004_admission','0005_invitations']
            for revision in revisions[:revisions.index(args.revision)+1]:
                rc=child(['test_support.database','migrate','--confirm-merge-test','--revision',revision],env)
                steps.append(dict(action=revision,native_exit_code=rc))
                if rc:raise ValueError('CI migration failed')
        for suite,count in PLANS[args.revision]:
            directory=ROOT/'backend/test-results/guarded';old=set(directory.glob('run-*.json'))
            if suite=='profiles': command=['release_support.acceptance','--confirm-profile-test']
            else:command=['test_support.concurrency','--confirm-merge-test','--suite',suite,'--revision',args.revision,'--repetitions','1']
            rc=child(command,env);new=set(directory.glob('run-*.json'))-old
            if len(new)!=1:raise ValueError('Missing/ambiguous diagnostic report')
            path=new.pop();data=json.loads(path.read_text())
            steps.append(dict(suite=suite,native_exit_code=rc,report_sha256=sha256(path.read_bytes()).hexdigest(),report=data))
            validate_test_report(data,suite,args.revision,count,rc)
            if suite=='invitations':
                tree=ast.parse((ROOT/'backend/invitation_tests/test_invitations.py').read_text())
                if not any(isinstance(n,ast.FunctionDef) and n.name=='test_distinct_authenticated_50_caller_last_seat' for n in ast.walk(tree)):raise ValueError('Required G1 case missing')
        code=0
    except Exception:print('Required CI acceptance incomplete; details suppressed. Inspect sanitized receipts.')
    report=receipt('ci',before,code,revision=args.revision,steps=steps,
        expected_api_cases=sum(n for s,n in PLANS[args.revision] if s not in ('lifecycle','realtime')),
        isolated_postgres=True,required_race=args.revision=='0005_invitations')
    print(f'CI receipt: {report.name}; exit={code}');raise SystemExit(code)


if __name__=='__main__':main()
