"""Offline verification of a successful, source-bound release receipt."""
import argparse
import json
import math
from pathlib import Path
from release_support.evidence import ROOT,sources,validate_test_report
from release_support.targets import REVISION
from release_support.ci import PLANS
from release_support.load import disclosures


def validate(data,current):
    if (data.get('schema_version')!=1 or data.get('source_unchanged') is not True or data.get('source')!=current
        or type(data.get('native_exit_code')) is not int or data['native_exit_code']!=0):raise ValueError('Unsuccessful or stale source-bound receipt')
    kind=data.get('kind')
    if kind in ('profiles','realtime'):
        suite,revision,count=('profiles',REVISION,30) if kind=='profiles' else ('realtime','0005_invitations',4)
        validate_test_report(data['report'],suite,revision,count,0)
        if kind=='profiles' and (len(data['passed_nodes'])!=count or len(set(data['passed_nodes']))!=count):raise ValueError('Successful roster incomplete')
    elif kind=='ci':
        plan=PLANS[data['revision']];steps=data['steps']
        if any(type(s.get('native_exit_code')) is not int or s['native_exit_code']!=0 for s in steps):raise ValueError('CI step failed')
        actual=[s for s in steps if 'suite' in s]
        if [s['suite'] for s in actual]!=[suite for suite,count in plan]:raise ValueError('Required CI suite missing')
        migrations=[s.get('action') for s in steps if 'action' in s]
        wanted=['prepare','migrate','verify'] if data['revision']==REVISION else list(PLANS)[:list(PLANS).index(data['revision'])+1]
        if data['revision']!=REVISION:wanted=['0002_domain',*wanted]
        if migrations!=wanted or data.get('isolated_postgres') is not True:raise ValueError('CI migrations incomplete')
        for step,(suite,count) in zip(actual,plan):validate_test_report(step['report'],suite,data['revision'],count,0)
    elif kind=='migration':
        if data.get('target') not in ('profiles','benchmark') or data.get('action') not in ('prepare','migrate','verify'):raise ValueError('Migration contract mismatch')
        if data['action']=='migrate' and (data.get('old_tables_preserved') is not True or len(data.get('old_counts',{}))!=12):raise ValueError('Preservation missing')
    elif kind=='seed':
        counts=data.get('counts',{})
        wanted=dict(users=10000,credentials=10000,profiles=10000,hackathons=1,teams=2000,memberships=5000,duplicates=0,invalid_teams=0,orphans=0)
        if counts!=wanted or any(type(v) is not int for v in counts.values()):raise ValueError('Scale dataset counts incomplete')
    elif kind=='load':
        m=data.get('metrics') or {};disclosures(data['hardware'])
        numeric=('p50_ms','p95_ms','p99_ms','error_rate','requests','measured_elapsed_seconds','throughput_rps')
        if any(type(m.get(k)) not in (int,float) or not math.isfinite(m[k]) or m[k]<0 for k in numeric):raise ValueError('Invalid performance aggregates')
        if (data.get('measured') is not True or data.get('users')!=10000 or data.get('teams')!=2000 or data.get('vus')!=100
            or data.get('duration_seconds')!=60 or data.get('warmup_seconds')!=20 or data.get('sse_clients') not in (0,32)
            or m.get('passed') is not True or not 0<=m['p50_ms']<=m['p95_ms']<200 or m['p99_ms']<m['p95_ms']
            or m['error_rate']!=0 or m['requests']<100 or not 60<=m['measured_elapsed_seconds']<=66
            or abs(m['throughput_rps']-m['requests']/m['measured_elapsed_seconds'])>1e-9
            or not data.get('postgres_version') or not data.get('k6_version') or type(data.get('outbox_rows')) is not int):raise ValueError('Performance evidence incomplete')
    else:raise ValueError('Unknown receipt kind')
    return kind


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('receipt',type=Path);args=p.parse_args()
    try:
        path=args.receipt.absolute();directory=ROOT/'backend/test-results/release'
        if path.parent!=directory or path.is_symlink() or directory.resolve()!=directory or path.stat().st_size>2_000_000:raise ValueError('Receipt path rejected')
        kind=validate(json.loads(path.read_text(encoding='utf-8')),sources())
    except Exception:p.exit(1,'Receipt NOT CERTIFIED (failed, stale, incomplete or invalid).\n')
    print(f'{kind} receipt passed offline integrity checks; provenance is local, not a signature.')


if __name__=='__main__':main()
