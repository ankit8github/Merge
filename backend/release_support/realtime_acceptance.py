"""Source-bound wrapper of the unchanged exact-0005 four-case SSE runner."""
import argparse
from getpass import getpass
from hashlib import sha256
import json
import os
import subprocess
import sys
from release_support.evidence import ROOT,sources,receipt,validate_test_report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--confirm-merge-test',action='store_true',required=True);p.parse_args()
    before=sources();code=1;data=None;report_hash=None
    password=os.environ.get('MERGE_TEST_DB_PASSWORD')
    if password is None:
        if not sys.stdin.isatty():p.error('Hidden interactive credential or private MERGE_TEST_DB_PASSWORD required')
        password=getpass('Existing merge_app password (hidden): ')
    if not password:p.error('Nonempty explicit credential required')
    try:
        directory=ROOT/'backend/test-results/guarded';old=set(directory.glob('run-*.json'))
        result=subprocess.run([sys.executable,'-m','test_support.concurrency','--confirm-merge-test',
            '--suite','realtime','--revision','0005_invitations','--repetitions','1'],
            cwd=ROOT/'backend',env=dict(os.environ,MERGE_TEST_DB_PASSWORD=password),
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=600)
        new=set(directory.glob('run-*.json'))-old
        if len(new)!=1:raise ValueError('Missing/ambiguous SSE evidence')
        path=new.pop();data=json.loads(path.read_text());report_hash=sha256(path.read_bytes()).hexdigest()
        validate_test_report(data,'realtime','0005_invitations',4,result.returncode);code=0
    except Exception:print('SSE acceptance incomplete; preserve fixtures and stop. Private output suppressed.')
    path=receipt('realtime',before,code,report=data,report_sha256=report_hash)
    print(f'SSE receipt: {path.name}; exit={code}');raise SystemExit(code)


if __name__=='__main__':main()
