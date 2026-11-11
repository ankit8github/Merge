"""R1 evidence-oracle and migration guards, entirely database-free."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest

from admission_tests.test_admission import assert_final_seat_state
from test_support.races import Outcome
from test_auth_http import api


@pytest.fixture
def race_state():
    leader,team,user,loser=[str(uuid4()) for _ in range(4)]
    requests=[str(uuid4()),str(uuid4())]
    records=[dict(id=str(uuid4()),operation=operation,state='completed') for operation in
        ('team.create.v1','request.create.v1','request.create.v1','request.decide.v1')]
    records[-1].update(actor_id=leader,http_status=200,response_body={'data':{'id':requests[0],'status':'approved'}})
    audits=[]
    for index,record in enumerate(records):
        admitted=index==3
        audits.append(dict(id=str(uuid4()),idempotency_record_id=record['id'],team_version=index+1,
            action=record['operation'],new_state={'team':{'member_count':2 if admitted else 1},
                'request':{'id':requests[0],'status':'approved'} if admitted else None,
                'subject':{'user_id':user,'member':admitted}},
            old_state={'request':{'id':requests[0],'status':'pending'}} if admitted else None))
    state={'join_requests':[dict(id=r,team_id=team,requester_id=u,status=status,
                resolved_at='2026-11-10T00:00:00Z' if index==0 else None,resolved_by=leader if index==0 else None)
            for index,(r,u,status) in enumerate(zip(requests,[user,loser],['approved','pending']))],
        'memberships':[{'user_id':u,'team_id':team} for u in (leader,user)],
        'teams':[dict(id=team,max_team_size=2,version=4,leader_user_id=leader)],
        'idempotency_records':records,'audit_events':audits,
        'outbox_events':[{'audit_event_id':a['id']} for a in audits]}
    return state,requests,[Outcome('200'),Outcome('409','team_full')],leader,team


def test_final_seat_oracle_accepts_one_complete_admission(race_state):
    assert_final_seat_state(*race_state)


@pytest.mark.parametrize('corruption',['loser-resolved','loser-decider','extra-success-record',
    'version-gap','missing-outbox','wrong-winner','bad-audit-count'])
def test_final_seat_oracle_rejects_false_concurrency_evidence(race_state,corruption):
    state,requests,results,leader,team=deepcopy(race_state)
    if corruption=='loser-resolved': state['join_requests'][1]['status']='rejected'
    if corruption=='loser-decider': state['join_requests'][1]['resolved_by']=leader
    if corruption=='extra-success-record': state['idempotency_records'].append(dict(state['idempotency_records'][-1]))
    if corruption=='version-gap':
        state['teams'][0]['version']=5
        state['audit_events'][-1]['team_version']=5
    if corruption=='missing-outbox': state['outbox_events'].pop()
    if corruption=='wrong-winner': state['memberships'][1]['user_id']=state['join_requests'][1]['requester_id']
    if corruption=='bad-audit-count': state['audit_events'][-1]['new_state']['team']['member_count']=1
    with pytest.raises(AssertionError): assert_final_seat_state(state,requests,results,leader,team)


def test_migration_object_collision_refuses_before_any_ddl(monkeypatch):
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0004_admission.py'
    spec=importlib.util.spec_from_file_location('admission_collision',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    calls=[]
    connection=SimpleNamespace(execute=lambda statement:SimpleNamespace(one=lambda:('existing',None,None,None)))
    monkeypatch.setattr(module,'op',SimpleNamespace(get_context=lambda:SimpleNamespace(as_sql=False),
        get_bind=lambda:connection,execute=lambda statement:calls.append(statement)))
    with pytest.raises(RuntimeError,match='no adoption'): module.upgrade()
    assert calls==[]


def test_nonempty_preservation_snapshot_reads_all_ten_legacy_tables_without_data_writes():
    from test_support.revisions import admission_snapshot, DOMAIN_TABLES
    queries=[]
    def execute(statement):
        query=str(statement); queries.append(query)
        assert query.startswith(('LOCK TABLE','SELECT count(*)'))
        return SimpleNamespace(one=lambda:(7,'aggregate-only-test-fingerprint'))
    snapshot=admission_snapshot(SimpleNamespace(execute=execute))
    expected=set(DOMAIN_TABLES)|{'account_credentials','auth_sessions','auth_throttle_buckets'}
    assert set(snapshot)==expected and all(value[0]==7 for value in snapshot.values())
    assert sum(q.startswith('SELECT count(*)') for q in queries)==10
    for name in expected:
        assert any('public.'+name in q and 'IN SHARE MODE' in q for q in queries)


@pytest.mark.parametrize('revision',[['0004_admission'],['0003_auth'],[],['0004_admission','other']])
def test_admission_connection_guard_requires_exact_revision_and_invalidates_failures(revision):
    from admission_tests.conftest import guard
    c=MagicMock()
    c.connection.dbapi_connection.autocommit=False
    c.get_execution_options.return_value={}
    c.get_isolation_level.return_value='READ COMMITTED'
    def execute(statement,parameters=None):
        q=str(statement)
        if 'current_database()' in q: return SimpleNamespace(one=lambda:('merge_test','merge_app','127.0.0.1',5432))
        if 'version_num' in q: return SimpleNamespace(scalars=lambda:SimpleNamespace(all=lambda:revision))
        return SimpleNamespace(one=lambda:('5s','15s'))
    c.execute.side_effect=execute
    if revision==['0004_admission']:
        guard(c); c.rollback.assert_called_once(); c.invalidate.assert_not_called()
    else:
        with pytest.raises(RuntimeError,match='connection guard failed'): guard(c)
        c.invalidate.assert_called_once(); c.rollback.assert_not_called()


def test_guarded_http_client_overrides_all_real_database_paths_without_settings(api,monkeypatch):
    from sqlalchemy.engine import Engine
    from admission_tests.conftest import client as guarded_client
    from app.auth import encode_token
    from app.services.admission import AdmissionService
    from app.services.team_reads import TeamReadService
    from app.services.teams import TeamService
    import app.core.config
    import app.db.session
    def forbidden(*args,**kwargs): pytest.fail('Ordinary settings or database reached')
    monkeypatch.setattr(app.core.config,'Settings',forbidden)
    monkeypatch.setattr(app.db.session,'build_engine',forbidden)
    engine=MagicMock(spec=Engine)
    engine.hide_parameters=True; engine.echo=False; engine.connect.side_effect=forbidden
    service=MagicMock(spec=AdmissionService); service.own_request.return_value={'request':None}
    env=SimpleNamespace(engine=engine,credentials=api.services.credentials,sessions=api.services.sessions,
        teams=MagicMock(spec=TeamService),reads=MagicMock(spec=TeamReadService),admission=service)
    fixture=guarded_client.__wrapped__(env)
    client=next(fixture)
    try:
        client.cookies.set('__Host-merge_session',encode_token(api.issued.session_token.get_secret_value()))
        response=client.get(f'/api/hackathons/{uuid4()}/teams/{uuid4()}/join-requests/mine')
        assert response.status_code==200 and response.json()=={'request':None}
        engine.connect.assert_not_called()
    finally:
        with pytest.raises(StopIteration): next(fixture)
