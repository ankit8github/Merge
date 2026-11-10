"""Guarded retained read-API fixtures. Collection never opens PostgreSQL."""
from contextlib import contextmanager
from threading import Lock
from uuid import uuid4
import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretBytes
from sqlalchemy import event

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from session_tests.conftest import account
from app.auth import AuthServices, encode_token, get_services
from app.main import create_app
from app.read_api import get_read_service
from app.security.auth_policy import AuthSettings
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.team_reads import TeamReadService
from app.services.teams import TeamService
from app.services.throttling import ThrottlePolicy, ThrottleService
from test_support.database import assert_test_identity
from test_support.races import RaceDatabase, sql

ORIGIN = 'https://merge.example'


class ReadEnvironment(RaceDatabase):
    def __init__(self, settings):
        super().__init__(settings)
        self.ids = set()
        self.mutex = Lock()

    @staticmethod
    def username(): return 'read_' + uuid4().hex[:24]

    @contextmanager
    def connection(self):
        with super().connection() as c:
            assert sql(c,'SELECT version_num FROM public.alembic_version').scalars().all()==['0003_auth']
            c.rollback()
            yield c

    def track(self,c,cursor,statement,parameters,context,many):
        if 'INSERT INTO public.users' in statement:
            values=context.compiled_parameters[0]
            with self.mutex:
                self.ids.add(values.get('u') or values.get('id'))

    def seed_discovery(self):
        h,users,teams=uuid4(),[uuid4() for _ in range(8)],[uuid4() for _ in range(3)]
        self.hackathons.append(h)
        with self.connection() as c:
            sql(c,"INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:h,'Read fixture',2,3)",h=h)
            for u in users:
                sql(c,"INSERT INTO public.users(id,display_name) VALUES (:id,'Public display')",id=u)
            for t,u in zip(teams,users):
                sql(c,'''INSERT INTO public.teams(id,hackathon_id,name,min_team_size,max_team_size,leader_user_id,created_by)
                    VALUES (:t,:h,'Read team',2,3,:u,:u)''',t=t,h=h,u=u)
                sql(c,'INSERT INTO public.memberships(hackathon_id,team_id,user_id) VALUES (:h,:t,:u)',h=h,t=t,u=u)
            c.commit()
        return h,users,teams

    def check(self):
        self.check_invariants()
        with self.connection() as c:
            sql(c,'SET TRANSACTION READ ONLY')
            ids=list(self.ids)
            if ids:
                assert sql(c,'''SELECT count(*) FROM public.auth_sessions s
                    LEFT JOIN public.users u ON u.id=s.user_id
                    LEFT JOIN public.account_credentials a ON a.user_id=s.user_id
                    WHERE s.user_id=ANY(:ids) AND (u.id IS NULL OR a.user_id IS NULL
                      OR octet_length(s.token_hash)<>32 OR octet_length(s.csrf_token)<>32
                      OR s.expires_at<>s.created_at+interval '8 hours' OR s.revoked_at<s.created_at)''',ids=ids).scalar_one()==0
            for h in self.hackathons:
                for table in ('idempotency_records','audit_events'):
                    assert sql(c,f'SELECT count(*) FROM public.{table} WHERE hackathon_id=:h',h=h).scalar_one()==0
                assert sql(c,'''SELECT count(*) FROM public.outbox_events o JOIN public.audit_events a
                    ON a.id=o.audit_event_id WHERE a.hackathon_id=:h''',h=h).scalar_one()==0
        print('Fresh read API fixture/session/team invariants verified; fixtures retained',flush=True)


@pytest.fixture
def environment(request,repetition):
    settings=getattr(request.config,'_merge_concurrency_settings',None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded --suite reads --revision 0003_auth; no database opened',pytrace=False)
    env=ReadEnvironment(settings)
    with env.connection() as anchor:
        env.engine=anchor.engine
        def guard(c):
            assert_test_identity(c)
            assert sql(c,'SELECT version_num FROM public.alembic_version').scalars().all()==['0003_auth']
            c.rollback()
        event.listen(env.engine,'engine_connect',guard)
        event.listen(env.engine,'after_cursor_execute',env.track)
        env.service,env.sessions=CredentialService(env.engine),SessionService(env.engine)
        env.reads,env.teams=TeamReadService(env.engine),TeamService(env.engine)
        try:
            yield env
        finally:
            try: env.check()
            finally:
                event.remove(env.engine,'after_cursor_execute',env.track)
                event.remove(env.engine,'engine_connect',guard)


@pytest.fixture
def subject(environment): return environment.seed_discovery()


@pytest.fixture
def client(environment):
    key=secrets.token_bytes(32)
    app=create_app(AuthSettings(origin=ORIGIN,throttle_secret=key.hex()))
    services=AuthServices(environment.service,environment.sessions,
        ThrottleService(environment.engine,secret=SecretBytes(key),policy=ThrottlePolicy()))
    app.dependency_overrides[get_services]=lambda:services
    app.dependency_overrides[get_read_service]=lambda:environment.reads
    with TestClient(app,base_url=ORIGIN,client=('192.0.2.1',50000)) as client:
        yield client
    assert app.state.auth_engine is None,'Ordinary runtime database was initialized'


@pytest.fixture
def authorized(client,environment,account):
    identity,password=account
    issued=environment.sessions.login(username=identity.username,password=password)
    client.cookies.set('__Host-merge_session',encode_token(issued.session_token.get_secret_value()))
    return client,issued
