"""Fixed profile suite. No migrations, arbitrary test selectors or DB URLs."""
import argparse
from getpass import getpass
import os
from pathlib import Path
import pytest
from release_support.targets import Target,guarded_engine,REVISION
from release_support.evidence import sources,receipt,validate_test_report
from test_support.diagnostics import Diagnostics

EXPECTED=30


class Plugin:
    def __init__(self,target): self.target=target;self.passed=[]
    def pytest_configure(self,config): config._merge_profile_target=self.target
    def pytest_collection_finish(self,session):
        nodes=[Diagnostics.node_id(item.nodeid) for item in session.items]
        if len(nodes)!=EXPECTED or len(set(nodes))!=EXPECTED or any('withheld' in node for node in nodes):
            raise ValueError('Required unique safe case roster missing; no tests may execute')
    def pytest_runtest_logreport(self,report):
        if report.when=='call' and report.passed: self.passed.append(Diagnostics.node_id(report.nodeid))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--confirm-profile-test',action='store_true',required=True);args=p.parse_args()
    if not __debug__: p.error('Assertions must be enabled')
    before=sources();password=os.environ.get('MERGE_RELEASE_DB_PASSWORD') or getpass('Existing merge_app password (hidden): ')
    target=Target('profiles',True,password);plugin=Plugin(target)
    root=Path(__file__).resolve().parents[1];diagnostics=Diagnostics(root,'profiles',REVISION,1);code=1
    try:
        with guarded_engine(target): pass
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';os.environ.pop('PYTEST_ADDOPTS',None);os.environ.pop('PYTEST_PLUGINS',None)
        code=int(diagnostics.run_pytest([str(root/'profile_tests'),'-q','-x','--tb=no','--show-capture=no','--assert=plain',
            '--confirm-profile-test','-p','no:cacheprovider','-o','addopts=','-o','log_cli=false','-o','log_file='+os.devnull],plugins=[plugin,diagnostics]))
        diagnostics.finish(code);validate_test_report(diagnostics.data,'profiles',REVISION,EXPECTED,code)
        if len(plugin.passed)!=EXPECTED or len(set(plugin.passed))!=EXPECTED: raise ValueError('Missing successful cases')
    except BaseException:
        code=1;diagnostics.finish(code)
    path=receipt('profiles',before,code,report=diagnostics.data,passed_nodes=plugin.passed)
    print(f'Profile acceptance receipt: {path.name}; exit={code}');raise SystemExit(code)


if __name__=='__main__':main()
