"""Fresh retained lifecycle fixtures. Collection never opens a database."""
from contextlib import contextmanager
import secrets
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretBytes
from sqlalchemy import event
from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from admission_tests.conftest import AdmissionDatabase, headers, ORIGIN
from app.auth import AuthServices, get_services
from app.main import create_app
from app.admission_api import get_admission_service
from app.invitation_api import get_invitation_service
from app.lifecycle_api import get_lifecycle_service
from app.read_api import get_read_service
from app.team_api import get_team_service
from app.security.auth_policy import AuthSettings
from app.services.admission import AdmissionService
from app.services.credentials import CredentialService
from app.services.invitations import InvitationService
from app.services.lifecycle import LifecycleService
from app.services.sessions import SessionService
from app.services.team_reads import TeamReadService
from app.services.teams import TeamService
from app.services.throttling import ThrottleService, ThrottlePolicy
from test_support.browser_full import ConnectionGuard
from test_support.races import RaceDatabase, sql


class LifecycleDatabase(RaceDatabase):
    account = AdmissionDatabase.account

    def __init__(self, settings):
        super().__init__(settings)
        self.guard=ConnectionGuard()  # Initial, fresh, pooled and observer connections.

    @contextmanager
    def connection(self):
        with super().connection() as c:
            self.guard(c)
            yield c

    def check(self):
        self.check_invariants()
        with self.connection() as c:
            sql(c,'SET TRANSACTION READ ONLY')
            for h in self.hackathons:
                rows=sql(c,'''SELECT a.*,r.actor_id AS owner,r.operation,r.state,r.http_status,r.response_body,r.response_headers,
                    o.id AS event_id,o.event_type,o.schema_version AS event_schema,o.payload,o.published_at,o.attempt_count
                    FROM public.audit_events a JOIN public.idempotency_records r ON r.id=a.idempotency_record_id
                    LEFT JOIN public.outbox_events o ON o.audit_event_id=a.id
                    WHERE a.hackathon_id=:h ORDER BY a.team_id,a.team_version''',h=h).mappings().all()
                latest={}
                for r in rows:
                    assert r['state']=='completed' and r['actor_id']==r['owner'] and r['action']==r['operation']
                    assert r['event_id'] and r['published_at'] is None and r['attempt_count']==0
                    assert r['event_type']=='team.changed.v1' and r['event_schema']==1
                    assert r['response_headers']=={'content-type':'application/json','cache-control':'no-store'}
                    assert r['payload']==dict(hackathon_id=str(h),team_id=str(r['team_id']),team_version=r['team_version'])
                    assert r['new_state']['team']['version']==r['team_version']
                    prior=latest.get(r['team_id'])
                    assert r['team_version']==(prior['version']+1 if prior else 1)
                    if r['operation'] in ('team.leave.v1','member.remove.v1'):
                        old,new=r['old_state'],r['new_state']; receipt=r['response_body']['data']
                        assert old['subject']['member'] and not new['subject']['member']
                        assert old['team']['member_count']==new['team']['member_count']+1
                        assert old['team']['version']+1==r['team_version']
                        assert new['team']['deleted']==(new['team']['member_count']==0)
                        assert new['team']['deleted']==(new['team']['leader_user_id'] is None)
                        assert new['team']['readiness']==('deleted' if new['team']['deleted'] else
                            'ready' if new['team']['member_count']>=new['team']['min_team_size'] else 'forming')
                        if prior:
                            for field in ('version','member_count','leader_user_id','min_team_size','max_team_size','readiness'):
                                assert old['team'][field]==prior[field]
                        for field in ('min_team_size','max_team_size'):
                            assert old['team'][field]==new['team'][field]
                        assert r['http_status']==200
                        assert r['response_body']==dict(schema_version=1,data=dict(
                            hackathon_id=str(h),team_id=str(r['team_id']),user_id=new['subject']['user_id'],
                            member_count=new['team']['member_count'],team_version=r['team_version'],
                            leader_user_id=new['team']['leader_user_id'],deleted=new['team']['deleted']))
                        assert type(receipt['member_count']) is int and type(receipt['team_version']) is int
                        assert type(receipt['deleted']) is bool
                        if r['operation']=='member.remove.v1':
                            assert str(r['actor_id'])!=new['subject']['user_id']
                            assert old['team']['leader_user_id']==new['team']['leader_user_id']==str(r['actor_id'])
                        else:
                            assert new['subject']['user_id']==str(r['actor_id'])
                    latest[r['team_id']]=r['new_state']['team']
                teams=sql(c,'''SELECT t.id,t.version,t.leader_user_id,t.deleted_at,count(m.user_id) AS count
                    FROM public.teams t LEFT JOIN public.memberships m ON m.team_id=t.id
                    WHERE t.hackathon_id=:h GROUP BY t.id''',h=h).mappings().all()
                assert len(teams)==len(latest)
                for t in teams:
                    last=latest[t['id']]
                    assert t['version']==last['version'] and t['count']==last['member_count']
                    assert (None if t['leader_user_id'] is None else str(t['leader_user_id']))==last['leader_user_id']
                    assert (t['deleted_at'] is not None)==last.get('deleted',False)
                assert sql(c,'SELECT count(*) FROM public.outbox_events o JOIN public.audit_events a ON a.id=o.audit_event_id WHERE a.hackathon_id=:h',h=h).scalar_one()==len(rows)
                assert sql(c,"SELECT count(*) FROM public.idempotency_records WHERE hackathon_id=:h AND state<>'completed'",h=h).scalar_one()==0
                assert sql(c,'''SELECT count(*) FROM public.idempotency_records r
                    LEFT JOIN public.audit_events a ON a.idempotency_record_id=r.id
                    WHERE r.hackathon_id=:h AND a.id IS NULL
                    AND NOT (r.operation='request.create.v1' AND r.http_status=200)''',h=h).scalar_one()==0
                # Admission remains a historical fact after an audited departure.
                for r in sql(c,'SELECT id,status FROM public.join_requests WHERE hackathon_id=:h',h=h).mappings():
                    actions=sql(c,"SELECT action FROM public.audit_events WHERE hackathon_id=:h AND new_state->'request'->>'id'=:id",h=h,id=str(r['id'])).scalars().all()
                    assert actions.count('request.create.v1')==1
                    assert actions.count('request.decide.v1')==int(r['status']!='pending')
                for r in sql(c,'SELECT id,status,created_at,expires_at,redeemed_at FROM public.invitations WHERE hackathon_id=:h',h=h).mappings():
                    assert r['expires_at']>r['created_at']
                    assert (r['status']=='pending')==(r['redeemed_at'] is None)
                    actions=sql(c,"SELECT action FROM public.audit_events WHERE hackathon_id=:h AND new_state->'invitation'->>'id'=:id",h=h,id=str(r['id'])).scalars().all()
                    assert actions.count('invitation.issue.v1')==1
                    assert actions.count('invitation.redeem.v1')==int(r['status']=='redeemed')
        assert not self.guard.failed.is_set()
        print('Fresh lifecycle chains and committed invariants verified; fixtures retained.',flush=True)


@pytest.fixture
def environment(request,repetition):
    settings=getattr(request.config,'_merge_concurrency_settings',None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded lifecycle suite at explicit 0005_invitations; no database opened',pytrace=False)
    db=LifecycleDatabase(settings)
    with db.connection() as anchor:
        db.engine=anchor.engine
        event.listen(db.engine,'engine_connect',db.guard)
        db.teams=TeamService(db.engine); db.admission=AdmissionService(db.engine)
        db.invitations=InvitationService(db.engine); db.lifecycle=LifecycleService(db.engine)
        db.credentials=CredentialService(db.engine); db.sessions=SessionService(db.engine); db.reads=TeamReadService(db.engine)
        try: yield db
        finally:
            try: db.check()
            finally: event.remove(db.engine,'engine_connect',db.guard)


@pytest.fixture
def client(environment):
    db=environment; secret=secrets.token_bytes(32)
    app=create_app(AuthSettings(origin=ORIGIN,throttle_secret=secret.hex()))
    services=AuthServices(db.credentials,db.sessions,ThrottleService(db.engine,secret=SecretBytes(secret),policy=ThrottlePolicy()))
    app.dependency_overrides.update({get_services:lambda:services,get_read_service:lambda:db.reads,
        get_team_service:lambda:db.teams,get_admission_service:lambda:db.admission,
        get_invitation_service:lambda:db.invitations,get_lifecycle_service:lambda:db.lifecycle})
    with TestClient(app,base_url=ORIGIN,client=('192.0.2.1',50000)) as value: yield value
    assert app.state.auth_engine is None
