"""Offline final join of native host/observer exits and owner browser observations.

No database/browser/service startup. Native 'browser' is the evidence verifier
process. No browser-engine exit is invented for a manually operated browser.
"""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from release_support.evidence import ROOT,sources
from release_support.integrated_plan import load_plan,digest,validate_receipt,TARGET
from release_support.integrated_ledger import require,DENIALS
from release_support.integrated_run import DIRECTORY,read_report,new_path,write_new


def certify(process_path,browser_path):
    source=sources();plan=load_plan();process=read_report(process_path)
    process_hash=sha256(Path(process_path).read_bytes()).hexdigest()
    require(process.get('schema_version')==1 and process.get('kind')=='integrated-process' and process.get('action')=='serve'
        and process.get('run_id')==plan['run_id'] and process.get('status')=='passed' and process.get('source')==source
        and process.get('source_unchanged') is True and type(process.get('native_exit_code')) is int and process['native_exit_code']==0)
    worker_path=DIRECTORY/process['worker_report'];host=read_report(worker_path)
    require(sha256(worker_path.read_bytes()).hexdigest()==process['worker_sha256'])
    require(host.get('kind')=='integrated-host-step' and host.get('action')=='serve' and host.get('status')=='passed'
        and host.get('source')==source and host.get('source_unchanged') is True and host.get('run_id')==plan['run_id']
        and host.get('plan_sha256')==digest(plan) and host.get('target')==TARGET)
    require(host.get('denial_codes')==DENIALS)
    require(host.get('start_marker')==f"campaign-{plan['run_id']}.json")
    marker_path=DIRECTORY/host['start_marker'];marker=read_report(marker_path)
    require(sha256(marker_path.read_bytes()).hexdigest()==host.get('start_marker_sha256')
        and marker.get('kind')=='integrated-start-marker' and marker.get('status')=='started_not_certified'
        and marker.get('run_id')==plan['run_id'] and marker.get('source')==source
        and marker.get('plan_sha256')==digest(plan) and marker.get('target')==TARGET)
    observer_path=DIRECTORY/host['observer_report'];observer=read_report(observer_path)
    require(sha256(observer_path.read_bytes()).hexdigest()==host['observer_sha256'] and observer.get('status')=='passed'
        and type(observer.get('native_exit_code')) is int and observer['native_exit_code']==0
        and type(host.get('observer_native_exit')) is int and host['observer_native_exit']==0
        and observer.get('totals')==host.get('totals') and observer.get('invariants')==host.get('invariants'))
    browser_path=Path(browser_path).absolute();browser=read_report(browser_path)
    browser_hash=sha256(browser_path.read_bytes()).hexdigest()
    # Fixed verifier/executable; no arbitrary process command or target URL.
    result=subprocess.run(['node',str(ROOT/'frontend/test_support/integratedEvidence.mjs'),str(browser_path)],
        cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=15)
    require(result.returncode==0 and json.loads(result.stdout).get('status')=='observed_evidence_integrity_passed')
    require(sha256(browser_path.read_bytes()).hexdigest()==browser_hash
        and sha256(Path(process_path).read_bytes()).hexdigest()==process_hash
        and sha256(worker_path.read_bytes()).hexdigest()==process['worker_sha256']
        and sha256(marker_path.read_bytes()).hexdigest()==host['start_marker_sha256']
        and sha256(observer_path.read_bytes()).hexdigest()==host['observer_sha256'])
    require(browser.get('source')==source and browser.get('source_unchanged') is True and browser.get('plan_sha256')==digest(plan))
    at=lambda value:datetime.fromisoformat(value)
    require(at(host['started_at'])<=at(browser['started_at'])<=at(browser['finished_at'])<=at(host['finished_at']))
    data={k:host[k] for k in ('totals','commands','profile_statuses','security_statuses','invariants',
        'host_drained','budget_enforced_by_host','actual_bindings_verified','denial_codes')}
    data.update(schema_version=1,kind='integrated-browser',run_id=plan['run_id'],plan_sha256=digest(plan),target=TARGET,
        source=source,source_unchanged=sources()==source,status='passed',failures=[],skipped=[],active_checkpoint=None,
        native_exits=dict(host=process['native_exit_code'],observer=host['observer_native_exit'],browser=result.returncode),
        native_exit_roles=dict(host='native_host_process',observer='native_readonly_observer_process',browser='native_browser_evidence_verifier'),
        browser_engine_exit='not_captured',checkpoints=browser['checkpoints'],observations=browser['observations'],
        browser_evidence_sha256=browser_hash,host_receipt_sha256=process_hash)
    require(validate_receipt(data,plan,source)=='metadata_consistent_requires_evidence_review')
    return data


def main(argv=None):
    from test_support.browser import SafeParser
    p=SafeParser(description=__doc__);p.add_argument('--host-process',type=Path,required=True);p.add_argument('--browser-observations',type=Path,required=True)
    args=p.parse_args(argv);code=1
    try:data=certify(args.host_process,args.browser_observations);code=0
    except BaseException:data=dict(status='failed',invariants='not_certified')
    path=new_path('certification');write_new(path,data)
    print(f'Integrated evidence review: {path.name}; exit={code}; local evidence requires owner review.')
    return code


if __name__=='__main__':raise SystemExit(main())
