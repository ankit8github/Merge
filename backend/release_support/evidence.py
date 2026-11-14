"""Source-bound, metadata-only evidence. No exception/body/credential serialization."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]


def sources():
    def git(*args):
        return subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}',*args],cwd=ROOT,text=True).splitlines()
    paths=sorted(set(git('ls-files')+git('ls-files','--others','--exclude-standard')))
    hashes={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in paths if (ROOT/p).is_file()}
    return {'head':git('rev-parse','HEAD')[0],'files':hashes}


def destination(prefix):
    if prefix not in ('migration','profiles','realtime','ci','seed','load'): raise ValueError('Unknown evidence kind')
    directory=ROOT/'backend/test-results/release'
    for p in (directory.parent,directory):
        if p.is_symlink() or p.resolve()!=p.parent.resolve()/p.name: raise ValueError('Evidence redirect rejected')
        p.mkdir(exist_ok=True)
    return directory/f'{prefix}-{uuid4().hex}.json'


def write(path,data):
    with path.open('x',encoding='utf-8') as stream: json.dump(data,stream,indent=2,allow_nan=False)


def receipt(kind,before,code,**metadata):
    after=sources()
    data=dict(schema_version=1,kind=kind,recorded_at=datetime.now(timezone.utc).isoformat(),
        source=before,source_unchanged=before==after,native_exit_code=int(code),
        environment={'python':platform.python_version(),'platform':platform.system(),'machine':platform.machine()},**metadata)
    path=destination(kind); write(path,data)
    if before!=after: raise ValueError('Source changed during validation; evidence uncertified')
    return path


def validate_test_report(data,suite,revision,count,code):
    if (type(code) is not int or code!=0 or data.get('schema_version')!=1 or data.get('suite')!=suite
        or data.get('revision')!=revision or data.get('repetitions')!=1 or data.get('status')!='passed'
        or data.get('stage')!='pytest' or type(data.get('collected')) is not int or data['collected']!=count
        or type(data.get('teardowns_completed')) is not int or data['teardowns_completed']!=count
        or type(data.get('skipped')) is not int or data['skipped']!=0 or data.get('failures')!=[]
        or 'active_node' not in data or data['active_node'] is not None or type(data.get('exit_code')) is not int or data['exit_code']!=0
        or data.get('invariant_verification')!='suite_and_fixture_checks_completed'):
        raise ValueError('Required acceptance evidence incomplete')
