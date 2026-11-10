"""Retained composed-mutation fixtures, fixed merge_test/0003_auth only."""
from contextlib import contextmanager

import pytest
from sqlalchemy import event

from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from app.services.idempotency import _StoredReply
from app.services.teams import TeamService
from test_support.database import assert_test_identity
from test_support.races import RaceDatabase, sql


def revision(c):
    assert sql(c,'SELECT version_num FROM public.alembic_version').scalars().all()==['0003_auth']


class MutationDatabase(RaceDatabase):
    @contextmanager
    def connection(self):
        with super().connection() as c:
            revision(c)
            c.rollback()
            yield c

    def check_chains(self):
        with self.connection() as c:
            sql(c,'SET TRANSACTION READ ONLY')
            for h in self.hackathons:
                records=sql(c,'''SELECT r.id,r.actor_id,r.operation,r.state,r.http_status,r.response_body,
                    r.response_headers,a.id AS audit_id,a.actor_id AS audit_actor,a.action,a.team_id,
                    a.team_version,a.old_state,a.new_state,o.id AS event_id,o.event_type,
                    o.schema_version,o.payload,o.published_at,o.attempt_count
                    FROM public.idempotency_records r
                    LEFT JOIN public.audit_events a ON a.idempotency_record_id=r.id AND a.hackathon_id=r.hackathon_id
                    LEFT JOIN public.outbox_events o ON o.audit_event_id=a.id
                    WHERE r.hackathon_id=:h ORDER BY a.team_id,a.team_version''',h=h).mappings().all()
                latest={}
                for row in records:
                    assert row['state']=='completed' and row['audit_id'] and row['event_id']
                    reply=_StoredReply._from_values(row['http_status'],row['response_body'],row['response_headers'])
                    data=reply.body()['data']
                    assert row['audit_actor']==row['actor_id'] and row['action']==row['operation']
                    assert data==dict(team_id=str(row['team_id']),hackathon_id=str(h),user_id=str(row['actor_id']),
                                     team_version=row['team_version'],member_count=row['new_state']['team']['member_count'])
                    after=row['new_state']
                    assert after['schema_version']==1 and after['subject']==dict(user_id=str(row['actor_id']),member=True)
                    assert after['team']['version']==row['team_version']
                    assert set(after)=={'schema_version','team','subject'}
                    assert set(after['team'])=={'version','member_count','leader_user_id','min_team_size','max_team_size','readiness'}
                    assert after['team']['readiness']==('ready' if after['team']['member_count']>=after['team']['min_team_size'] else 'forming')
                    if row['operation']=='team.create.v1':
                        assert row['old_state'] is None and row['team_version']==1 and reply.http_status==201
                        assert after['team']['member_count']==1 and after['team']['leader_user_id']==str(row['actor_id'])
                    else:
                        assert row['operation']=='team.join.v1' and reply.http_status==200
                        before=row['old_state']
                        assert before['schema_version']==1 and set(before)==set(after)
                        assert before['subject']==dict(user_id=str(row['actor_id']),member=False)
                        assert before['team']['member_count']+1==after['team']['member_count']
                        assert before['team']['version']+1==row['team_version']
                        for field in ('leader_user_id','min_team_size','max_team_size'):
                            assert before['team'][field]==after['team'][field]
                        assert before['team']['readiness']==('ready' if before['team']['member_count']>=before['team']['min_team_size'] else 'forming')
                    assert row['event_type']=='team.changed.v1' and row['schema_version']==1
                    assert row['published_at'] is None and row['attempt_count']==0
                    assert row['payload']==dict(hackathon_id=str(h),team_id=str(row['team_id']),team_version=row['team_version'])
                    previous=latest.get(row['team_id'])
                    assert row['team_version']==(1 if previous is None else previous['version']+1)
                    latest[row['team_id']]=after['team']
                teams=sql(c,'''SELECT t.id,t.version,t.leader_user_id,count(m.user_id) AS members
                    FROM public.teams t LEFT JOIN public.memberships m ON m.team_id=t.id
                    WHERE t.hackathon_id=:h GROUP BY t.id''',h=h).mappings().all()
                assert len(teams)==len(latest)
                for row in teams:
                    assert row['version']==latest[row['id']]['version']
                    assert row['members']==latest[row['id']]['member_count']
                    assert str(row['leader_user_id'])==latest[row['id']]['leader_user_id']
                assert sql(c,'SELECT count(*) FROM public.audit_events WHERE hackathon_id=:h',h=h).scalar_one()==len(records)
        self.check_invariants()
        print('Fresh composed mutation chains and committed-state invariants verified; fixtures retained',flush=True)


@pytest.fixture
def environment(request,repetition):
    settings=getattr(request.config,'_merge_concurrency_settings',None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use guarded mutations suite at explicit 0003_auth; no database opened',pytrace=False)
    db=MutationDatabase(settings)
    try:
        with db.connection() as anchor:
            db.engine=anchor.engine
            def guard(c):
                assert_test_identity(c)
                revision(c)
                c.rollback()
            event.listen(db.engine,'engine_connect',guard)
            try:
                db.service=TeamService(db.engine)
                yield db
            finally:
                event.remove(db.engine,'engine_connect',guard)
    finally:
        db.check_chains()


@pytest.fixture
def subject(environment):
    h,users,_=environment.seed(maximum=3,teams=0)
    return h,users
