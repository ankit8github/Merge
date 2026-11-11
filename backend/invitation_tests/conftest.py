"""Retained exact-0005 fixtures; collection does not open a database."""
from contextlib import contextmanager
import secrets
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretBytes
from sqlalchemy import event
from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from admission_tests.conftest import AdmissionDatabase, headers, subject, ORIGIN
from app.auth import AuthServices, get_services
from app.main import create_app
from app.admission_api import get_admission_service
from app.invitation_api import get_invitation_service
from app.read_api import get_read_service
from app.team_api import get_team_service
from app.security.auth_policy import AuthSettings
from app.services.admission import AdmissionService
from app.services.invitations import InvitationService
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.team_reads import TeamReadService
from app.services.teams import TeamService
from app.services.throttling import ThrottlePolicy, ThrottleService
from test_support.database import assert_test_identity
from test_support.races import RaceDatabase, sql


def guard(c):
    try:
        assert c.connection.dbapi_connection.autocommit is False
        assert c.get_execution_options().get('isolation_level')!='AUTOCOMMIT'
        assert_test_identity(c)
        assert sql(c,'SELECT version_num FROM public.alembic_version').scalars().all()==['0005_invitations']
        assert tuple(sql(c,"SELECT current_setting('lock_timeout'),current_setting('statement_timeout')").one())==('5s','15s')
        c.rollback()
    except Exception:
        c.invalidate()
        raise RuntimeError('Invitation test connection guard failed') from None


class InvitationDatabase(AdmissionDatabase):
    @contextmanager
    def connection(self):
        with RaceDatabase.connection(self) as c:
            guard(c)
            yield c

    def check(self):
        super().check()
        with self.connection() as c:
            sql(c,'SET TRANSACTION READ ONLY')
            for h in self.hackathons:
                rows=sql(c,'SELECT * FROM public.invitations WHERE hackathon_id=:h',h=h).mappings().all()
                for r in rows:
                    assert (r['status']=='pending')==(r['redeemed_at'] is None)
                    assert r['expires_at']>r['created_at']
                    if r['status']=='redeemed':
                        assert r['created_at']<=r['redeemed_at']<r['expires_at']
                        assert sql(c,'''SELECT count(*) FROM public.memberships WHERE hackathon_id=:h
                            AND team_id=:t AND user_id=:u''',h=h,t=r['team_id'],u=r['recipient_id']).scalar_one()==1
                    actions=sql(c,"SELECT action FROM public.audit_events WHERE hackathon_id=:h AND new_state->'invitation'->>'id'=:i",h=h,i=str(r['id'])).scalars().all()
                    assert actions.count('invitation.issue.v1')==1
                    assert actions.count('invitation.redeem.v1')==int(r['status']=='redeemed')


@pytest.fixture
def environment(request,repetition):
    settings=getattr(request.config,'_merge_concurrency_settings',None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded --suite invitations --revision 0005_invitations; no database opened',pytrace=False)
    db=InvitationDatabase(settings)
    with db.connection() as anchor:
        db.engine=anchor.engine
        event.listen(db.engine,'engine_connect',guard)
        db.teams=TeamService(db.engine); db.admission=AdmissionService(db.engine)
        db.invitations=InvitationService(db.engine)
        db.credentials=CredentialService(db.engine); db.sessions=SessionService(db.engine)
        db.reads=TeamReadService(db.engine)
        try: yield db
        finally:
            try: db.check()
            finally: event.remove(db.engine,'engine_connect',guard)


@pytest.fixture
def client(environment):
    db=environment; secret=secrets.token_bytes(32)
    app=create_app(AuthSettings(origin=ORIGIN,throttle_secret=secret.hex()))
    services=AuthServices(db.credentials,db.sessions,ThrottleService(db.engine,secret=SecretBytes(secret),policy=ThrottlePolicy()))
    app.dependency_overrides.update({get_services:lambda:services,get_read_service:lambda:db.reads,
        get_team_service:lambda:db.teams,get_admission_service:lambda:db.admission,get_invitation_service:lambda:db.invitations})
    with TestClient(app,base_url=ORIGIN,client=('192.0.2.1',50000)) as value: yield value
    assert app.state.auth_engine is None
