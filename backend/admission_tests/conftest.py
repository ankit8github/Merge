"""Guarded retained admission fixtures. Import/collection never connects."""
from contextlib import contextmanager
from uuid import uuid4
import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretBytes
from sqlalchemy import event

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from app.auth import AuthServices, encode_token, get_services
from app.admission_api import get_admission_service
from app.main import create_app
from app.read_api import get_read_service
from app.team_api import get_team_service
from app.security.auth_policy import AuthSettings
from app.services.admission import AdmissionService
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.team_reads import TeamReadService
from app.services.teams import TeamService
from app.services.throttling import ThrottlePolicy, ThrottleService
from test_support.database import assert_test_identity
from test_support.races import RaceDatabase, sql

ORIGIN='https://merge.example'


def guard(c):
    try:
        assert c.connection.dbapi_connection.autocommit is False
        assert c.get_execution_options().get('isolation_level') != 'AUTOCOMMIT'
        assert_test_identity(c)
        assert sql(c,'SELECT version_num FROM public.alembic_version').scalars().all()==['0004_admission']
        assert tuple(sql(c,"SELECT current_setting('lock_timeout'),current_setting('statement_timeout')").one())==('5s','15s')
        c.rollback()
    except Exception:
        c.invalidate()
        raise RuntimeError('Admission test connection guard failed') from None


class AdmissionDatabase(RaceDatabase):
    @contextmanager
    def connection(self):
        with super().connection() as c:
            guard(c)
            yield c

    def account(self):
        password=secrets.token_urlsafe(32)
        identity=self.credentials.register(username='admit_'+uuid4().hex[:24],password=password)
        issued=self.sessions.login(username=identity.username,password=password)
        return identity.user_id,issued

    def check(self):
        self.check_invariants()
        with self.connection() as c:
            sql(c,'SET TRANSACTION READ ONLY')
            for h in self.hackathons:
                requests=sql(c,'SELECT * FROM public.join_requests WHERE hackathon_id=:h',h=h).mappings().all()
                for r in requests:
                    assert (r['status']=='pending') == (r['resolved_at'] is None and r['resolved_by'] is None)
                    assert r['status'] in ('pending','approved','rejected')
                    assert sql(c,'SELECT count(*) FROM public.teams WHERE id=:t AND hackathon_id=:h',t=r['team_id'],h=h).scalar_one()==1
                    if r['status']=='approved':
                        assert sql(c,'SELECT count(*) FROM public.memberships WHERE hackathon_id=:h AND team_id=:t AND user_id=:u',h=h,t=r['team_id'],u=r['requester_id']).scalar_one()==1
                    changes=sql(c,"SELECT action FROM public.audit_events WHERE hackathon_id=:h AND new_state->'request'->>'id'=:r",h=h,r=str(r['id'])).scalars().all()
                    assert changes.count('request.create.v1')==1
                    assert changes.count('request.decide.v1')==int(r['status']!='pending')
                rows=sql(c,'''SELECT r.*,a.id AS audit_id,a.actor_id AS audit_actor,a.action,a.team_version,
                    a.new_state,o.id AS event_id,o.payload FROM public.idempotency_records r
                    LEFT JOIN public.audit_events a ON a.idempotency_record_id=r.id
                    LEFT JOIN public.outbox_events o ON o.audit_event_id=a.id
                    WHERE r.hackathon_id=:h''',h=h).mappings().all()
                for r in rows:
                    assert r['state']=='completed'
                    assert r['response_headers']=={'cache-control':'no-store','content-type':'application/json'}
                    if r['audit_id'] is None:
                        assert r['operation']=='request.create.v1' and r['http_status']==200
                        assert any(str(q['id'])==r['response_body']['data']['id'] for q in requests)
                    else:
                        assert r['event_id'] and r['audit_actor']==r['actor_id'] and r['action']==r['operation']
                        assert r['payload']['team_version']==r['team_version']==r['new_state']['team']['version']
                teams=sql(c,'''SELECT t.id,t.version,coalesce(max(a.team_version),1) AS latest,
                    count(a.id) AS changes FROM public.teams t LEFT JOIN public.audit_events a ON a.team_id=t.id
                    WHERE t.hackathon_id=:h GROUP BY t.id''',h=h).mappings().all()
                for t in teams:
                    assert t['version']==t['latest']
                    assert t['changes']==t['version']  # Every fixture team is created through composed creation.
        print('Fresh admission/request/membership/audit/outbox invariants verified; fixtures retained',flush=True)


@pytest.fixture
def environment(request,repetition):
    settings=getattr(request.config,'_merge_concurrency_settings',None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded --suite admission --revision 0004_admission; no database opened',pytrace=False)
    db=AdmissionDatabase(settings)
    with db.connection() as anchor:
        db.engine=anchor.engine
        event.listen(db.engine,'engine_connect',guard)
        db.admission=AdmissionService(db.engine)
        db.teams=TeamService(db.engine)
        db.credentials=CredentialService(db.engine)
        db.sessions=SessionService(db.engine)
        db.reads=TeamReadService(db.engine)
        try:
            yield db
        finally:
            try: db.check()
            finally: event.remove(db.engine,'engine_connect',guard)


@pytest.fixture
def client(environment):
    db=environment
    secret=secrets.token_bytes(32)
    app=create_app(AuthSettings(origin=ORIGIN,throttle_secret=secret.hex()))
    services=AuthServices(db.credentials,db.sessions,ThrottleService(db.engine,
        secret=SecretBytes(secret),policy=ThrottlePolicy()))
    app.dependency_overrides.update({get_services:lambda:services,get_read_service:lambda:db.reads,
        get_team_service:lambda:db.teams,get_admission_service:lambda:db.admission})
    with TestClient(app,base_url=ORIGIN,client=('192.0.2.1',50000)) as client:
        yield client
    assert app.state.auth_engine is None


@pytest.fixture
def subject(environment):
    db=environment
    h,_,_=db.seed(maximum=2,teams=0)
    leader,leader_session=db.account()
    user,user_session=db.account()
    reply=db.teams.create_team_idempotent(hackathon_id=h,actor_id=leader,name='Retained admission test',key='team')
    from uuid import UUID
    return h,UUID(reply.body()['data']['team_id']),leader,leader_session,user,user_session


def headers(issued,key='request'):
    return {'Origin':ORIGIN,'Idempotency-Key':key,
        'X-CSRF-Token':encode_token(issued.csrf_token.get_secret_value()),
        'Cookie':'__Host-merge_session='+encode_token(issued.session_token.get_secret_value())}
