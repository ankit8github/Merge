"""Offline negative tests of the real lifecycle acceptance checker; no database."""
from contextlib import contextmanager
from copy import deepcopy
from threading import Event
from types import SimpleNamespace
from uuid import uuid4
import pytest
from lifecycle_tests.conftest import LifecycleDatabase


class Result:
    def __init__(self,value): self.value=value
    def mappings(self): return self
    def all(self): return self.value
    def scalar_one(self): return self.value
    def __iter__(self): return iter(self.value)


@pytest.fixture
def checker():
    h,t,u=uuid4(),uuid4(),uuid4()
    first=dict(version=1,member_count=1,leader_user_id=str(u),min_team_size=2,max_team_size=3,readiness='forming')
    last=dict(version=2,member_count=0,leader_user_id=None,min_team_size=2,max_team_size=3,readiness='deleted',deleted=True)
    rows=[]
    for version,operation,state in [(1,'team.create.v1',first),(2,'team.leave.v1',last)]:
        rows.append(dict(state='completed',actor_id=u,owner=u,action=operation,operation=operation,
            event_id=uuid4(),event_type='team.changed.v1',event_schema=1,published_at=None,attempt_count=0,
            payload=dict(hackathon_id=str(h),team_id=str(t),team_version=version),team_id=t,team_version=version,
            new_state=dict(schema_version=1,subject=dict(user_id=str(u),member=version==1),team=deepcopy(state)),
            old_state=None if version==1 else dict(schema_version=1,subject=dict(user_id=str(u),member=True),team=deepcopy(first)),
            http_status=201 if version==1 else 200,response_headers={'content-type':'application/json','cache-control':'no-store'},
            response_body=dict(schema_version=1,data=dict(hackathon_id=str(h),team_id=str(t),user_id=str(u),
                member_count=0,team_version=2,leader_user_id=None,deleted=True))))
    class Connection:
        def execute(self,statement,parameters):
            q=str(statement)
            if 'SELECT a.*' in q: return Result(rows)
            if 'SELECT t.id,t.version' in q: return Result([dict(id=t,version=2,leader_user_id=None,deleted_at='retained',count=0)])
            if 'count(*)' in q: return Result(2 if 'public.outbox_events o JOIN' in q else 0)
            return Result([])
    @contextmanager
    def connection(): yield Connection()
    db=LifecycleDatabase(None); db.hackathons=[h]; db.connection=connection
    db.check_invariants=lambda:None
    assert not db.guard.failed.is_set()
    return db,rows


def test_acceptance_checker_accepts_consistent_fixture(checker):
    db,_=checker; db.check()


@pytest.mark.parametrize('field',['hackathon_id','team_id','member_count','team_version','schema_version','http_status','response_headers','event_type'])
def test_acceptance_checker_rejects_corrupt_receipt_or_delivery_metadata(checker,field):
    db,rows=checker; row=rows[-1]
    if field in ('hackathon_id','team_id'): row['response_body']['data'][field]=str(uuid4())
    elif field in ('member_count','team_version'): row['response_body']['data'][field]=99
    elif field=='schema_version': row['response_body'][field]=99
    elif field=='http_status': row[field]=201
    elif field=='response_headers': row[field]={'content-type':'text/plain'}
    else: row[field]='wrong.event'
    with pytest.raises(AssertionError): db.check()
