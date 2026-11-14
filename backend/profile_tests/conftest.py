"""Separate retained exact-0006 fixtures; never adopts exact-0005 records."""
from contextlib import contextmanager
import secrets
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretBytes
from app.auth import AuthServices,get_services
from app.main import create_app
from app.profile_api import get_profile_service,get_matching_service
from app.realtime_api import get_realtime_service
from app.admission_api import get_admission_service
from app.invitation_api import get_invitation_service
from app.lifecycle_api import get_lifecycle_service
from app.read_api import get_read_service
from app.team_api import get_team_service
from app.security.auth_policy import AuthSettings
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.teams import TeamService
from app.services.admission import AdmissionService
from app.services.invitations import InvitationService
from app.services.lifecycle import LifecycleService
from app.services.team_reads import TeamReadService
from app.services.profiles import ProfileService
from app.services.matching import MatchingService
from app.services.realtime import RealtimeService
from app.services.throttling import ThrottleService,ThrottlePolicy
from admission_tests.conftest import AdmissionDatabase,headers,ORIGIN
from lifecycle_tests.conftest import LifecycleDatabase
from test_support.races import RaceDatabase,sql
from release_support.targets import guarded_engine


def pytest_addoption(parser): parser.addoption('--confirm-profile-test',action='store_true')


class ProfileDatabase(LifecycleDatabase):
    def __init__(self,target,engine,guard):
        RaceDatabase.__init__(self,target); self.engine=engine;self.guard=guard;self.users=[]

    @contextmanager
    def connection(self):
        with self.engine.connect() as c: yield c

    def account(self):
        account=AdmissionDatabase.account(self);self.users.append(account[0]);return account

    def check(self):
        super().check()
        from app.profile_models import ProfileBody
        with self.connection() as c:
            sql(c,'SET TRANSACTION READ ONLY')
            for r in sql(c,'SELECT * FROM public.participant_profiles WHERE user_id=ANY(:ids)',ids=self.users).mappings():
                parsed=ProfileBody(skills=r['skills'],timezone=r['timezone'],discoverable=r['discoverable'],version=r['version'])
                assert parsed.skills==r['skills'] and r['version']>=1


@pytest.fixture
def environment(request):
    target=getattr(request.config,'_merge_profile_target',None)
    if not request.config.getoption('--confirm-profile-test') or target is None or target.kind!='profiles':
        pytest.fail('Use release_support.acceptance; no database opened',pytrace=False)
    with guarded_engine(target) as (engine,guard):
        db=ProfileDatabase(target,engine,guard)
        for name,service in [('credentials',CredentialService),('sessions',SessionService),('teams',TeamService),
            ('admission',AdmissionService),('invitations',InvitationService),('lifecycle',LifecycleService),
            ('reads',TeamReadService),('profiles',ProfileService),('matching',MatchingService),('realtime',RealtimeService)]:
            setattr(db,name,service(engine))
        try: yield db
        finally: db.check()


@pytest.fixture
def client(environment):
    db=environment; secret=secrets.token_bytes(32)
    app=create_app(AuthSettings(origin=ORIGIN,throttle_secret=secret.hex()))
    services=AuthServices(db.credentials,db.sessions,ThrottleService(db.engine,secret=SecretBytes(secret),policy=ThrottlePolicy()))
    app.dependency_overrides.update({get_services:lambda:services,get_read_service:lambda:db.reads,
        get_team_service:lambda:db.teams,get_admission_service:lambda:db.admission,get_invitation_service:lambda:db.invitations,
        get_lifecycle_service:lambda:db.lifecycle,get_profile_service:lambda:db.profiles,
        get_matching_service:lambda:db.matching,get_realtime_service:lambda:db.realtime})
    with TestClient(app,base_url=ORIGIN,client=('192.0.2.1',50000)) as value: yield value
    assert app.state.auth_engine is None


@pytest.fixture
def subject(environment,client):
    db=environment;h=uuid4();db.hackathons.append(h)
    with db.connection() as c:
        sql(c,'INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:h,:name,2,4)',h=h,name='batchb_'+h.hex);c.commit()
    accounts=[db.account() for _ in range(4)]
    result=client.post(f'/api/hackathons/{h}/teams',headers=headers(accounts[0][1],'create'),json={'name':'Profile acceptance'})
    assert result.status_code==201
    from uuid import UUID
    return h,UUID(result.json()['data']['team_id']),accounts
