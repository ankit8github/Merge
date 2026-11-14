"""Owner-only k6 orchestrator; fixed benchmark target, real auth, sanitized evidence."""
import argparse
from contextlib import contextmanager
from getpass import getpass
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from threading import Event,Thread
from time import monotonic
import httpx
from sqlalchemy import text
from app.auth import encode_token
from app.services.sessions import SessionService
from release_support.targets import Target,guarded_engine
from release_support.seed import dataset,digest,validate_database
from release_support.evidence import ROOT,destination,sources,receipt
from release_support.benchmark_host import ORIGIN


def disclosures(value):
    required={'client_cpu','client_ram','server_cpu','server_ram','postgres_topology','server_workers','storage','cache_conditions'}
    if not isinstance(value,dict) or set(value)!=required or any(not isinstance(v,str) or not 1<=len(v)<=256 or '\n' in v or v.upper().startswith(('REQUIRED','TODO','UNKNOWN')) for v in value.values()):
        raise ValueError('Complete bounded environment disclosure required')
    if value['server_workers']!='1':raise ValueError('The fixed benchmark host uses one worker')
    return value


def validate_summary(value,exit_code):
    expected=dict(schema_version=1,vus=100,duration_seconds=60,warmup_seconds=20)
    if any(type(value.get(k)) is not int or value[k]!=v for k,v in expected.items()):raise ValueError('Workload mismatch')
    elapsed=value['measured_elapsed_seconds']
    if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or not 60<=elapsed<=66:raise ValueError('Incomplete measured duration')
    metrics=value['metrics'];latency=metrics['board_latency']['values'];errors=metrics['board_errors']['values'];requests=metrics['board_requests']['values']
    fields=[latency['med'],latency['p(95)'],latency['p(99)'],errors['rate'],requests['count'],requests['rate']]
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in fields):raise ValueError('Invalid metric')
    p50,p95,p99,error_rate,count,throughput=fields
    if not 0<=p50<=p95<=p99 or not 0<=error_rate<=1 or count<100 or int(count)!=count or throughput<=0:raise ValueError('Incomplete samples')
    if type(exit_code) is not int or exit_code not in (0,99):raise ValueError('Load process failed')
    passed=p95<200 and error_rate==0
    if (exit_code==0)!=passed:raise ValueError('Threshold/exit mismatch')
    return dict(p50_ms=p50,p95_ms=p95,p99_ms=p99,error_rate=error_rate,requests=int(count),throughput_rps=count/elapsed,
        measured_elapsed_seconds=elapsed,k6_total_window_counter_rate=throughput,target_p95_ms=200,passed=passed)


def check_host(client,cookie,data):
    response=client.get(ORIGIN+'/api/benchmark/preflight',headers={'Cookie':cookie,'Origin':ORIGIN})
    wanted=dict(schema_version=1,database='merge_bench',role='merge_bench_app',revision='0006_profiles',
        hackathon_id=str(data['hackathon_id']),dataset_sha256=digest(data),workers=1)
    if response.status_code!=200 or response.json()!=wanted:raise ValueError('Benchmark host attestation failed; no load allowed')


@contextmanager
def streams(cookies,hackathon,count):
    stop=Event();failed=Event();ready=[Event() for _ in range(count)]
    def consume(index):
        try:
            with httpx.Client(timeout=httpx.Timeout(10,read=10),trust_env=False,follow_redirects=False) as client:
                while not stop.is_set():
                    with client.stream('GET',f'{ORIGIN}/api/hackathons/{hackathon}/events',headers={'Cookie':cookies[index],'Origin':ORIGIN}) as response:
                        if response.status_code!=200 or not response.headers.get('content-type','').startswith('text/event-stream'):raise ValueError()
                        seen=False
                        for line in response.iter_lines():
                            if stop.is_set():return
                            if len(line)>1024:raise ValueError()
                            if line.startswith('event: expired') or line.startswith('event: unavailable'):raise ValueError()
                            if line.startswith('data: '):
                                frame=json.loads(line[6:])
                                if frame.get('hackathon_id')!=str(hackathon) or frame.get('schema_version')!=1:raise ValueError()
                                seen=True;ready[index].set()
                        if not seen:raise ValueError()
        except Exception:
            if not stop.is_set():failed.set()
    threads=[Thread(target=consume,args=(i,),daemon=True) for i in range(count)]
    for thread in threads:thread.start()
    try:
        deadline=monotonic()+15
        for flag in ready:
            if not flag.wait(max(0,deadline-monotonic())):raise ValueError('SSE startup incomplete')
        if failed.is_set():raise ValueError('SSE startup failed')
        yield failed
        if failed.is_set():raise ValueError('SSE overhead run incomplete')
    finally:
        stop.set()
        deadline=monotonic()+12
        for thread in threads:thread.join(max(0,deadline-monotonic()))
        if any(thread.is_alive() for thread in threads):raise ValueError('SSE workers did not stop')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--confirm-merge-bench',action='store_true',required=True)
    p.add_argument('--seed',type=int,default=2026);p.add_argument('--sse-clients',type=int,choices=(0,32),default=32)
    p.add_argument('--environment',type=Path,required=True);args=p.parse_args()
    # Offline preflight before credentials, DB or network.
    hardware=disclosures(json.loads(args.environment.read_text(encoding='utf-8')))
    executable=shutil.which('k6')
    if executable is None:p.error('Install/review k6 separately; no database opened')
    version_output=subprocess.run([executable,'version'],capture_output=True,text=True,timeout=5)
    match=re.match(r'k6 v([0-9]+\.[0-9]+\.[0-9]+)',version_output.stdout)
    if version_output.returncode!=0 or match is None:p.error('k6 version preflight failed; no database opened')
    k6_version=match[1]
    before=sources();data=dataset(args.seed);code=1;metrics=None;version=None;outbox_rows=None
    db_password=os.environ.get('MERGE_RELEASE_DB_PASSWORD') or getpass('Existing merge_bench_app password (hidden): ')
    password=os.environ.get('MERGE_BENCH_PASSWORD') or getpass('Private benchmark cohort password (hidden): ')
    raw=destination('load').with_suffix('.k6.json')
    try:
        with guarded_engine(Target('benchmark',True,db_password)) as (engine,guard):
            with engine.connect() as c:
                c.execute(text('SET TRANSACTION READ ONLY'));validate_database(c,data);version=c.execute(text('SHOW server_version')).scalar_one()
                outbox_rows=c.execute(text('SELECT count(*) FROM public.outbox_events')).scalar_one()
            # Setup outside measurement: real credential/KDF + session issuance.
            # Avoid weakening shared-IP HTTP login throttles for cohort bootstrap.
            sessions=SessionService(engine)
            cookies=['merge_session_dev='+encode_token(sessions.login(username=f'bench_{i:05d}',password=password).session_token.get_secret_value()) for i in range(100)]
            with httpx.Client(timeout=5,trust_env=False,follow_redirects=False) as client:check_host(client,cookies[0],data)
            with streams(cookies,data['hackathon_id'],args.sse_clients):
                env={k:v for k,v in os.environ.items() if not k.startswith(('MERGE_','K6_'))}
                env.update(MERGE_BENCH_SESSIONS=json.dumps(cookies),MERGE_BENCH_HACKATHON=str(data['hackathon_id']),
                    MERGE_BENCH_URL=f'{ORIGIN}/api/hackathons/{data["hackathon_id"]}/teams?limit=20',MERGE_BENCH_SUMMARY=str(raw))
                result=subprocess.run([executable,'run','--quiet',str(ROOT/'load/board.js')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=115)
                metrics=validate_summary(json.loads(raw.read_text()),result.returncode);code=result.returncode
            with engine.connect() as c:
                c.execute(text('SET TRANSACTION READ ONLY'));validate_database(c,data)
    except Exception:
        code=1;print('Benchmark failed/incomplete. Preserve evidence and stop; private output suppressed.')
    report=receipt('load',before,code,dataset_sha256=digest(data),seed=args.seed,users=10000,teams=2000,
        vus=100,duration_seconds=60,warmup_seconds=20,sse_clients=args.sse_clients,metrics=metrics,
        hardware=hardware,postgres_version=version,k6_version=k6_version,outbox_rows=outbox_rows,client_logical_cpus=os.cpu_count(),
        topology='fixed loopback HTTP; PostgreSQL loopback:5432; single benchmark host; direct DB session bootstrap',
        measured=metrics is not None,setup='real credential/session services before measured board requests')
    print(f'Load receipt: {report.name}; exit={code}');raise SystemExit(code)


if __name__=='__main__':main()
