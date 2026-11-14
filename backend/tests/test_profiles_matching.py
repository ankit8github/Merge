"""Offline validation/HTTP/transaction/scoring evidence; no PostgreSQL claims."""
from datetime import datetime, timezone
from fractions import Fraction
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import ValidationError
import pytest
from sqlalchemy.engine import Engine

from app import profile_api
from app.auth import encode_token
from app.profile_models import ProfileBody, ZONES
from app.services.matching import MatchingService, SNAPSHOT, components, ranked_page
from app.services.profiles import ProfileError, ProfileService
from test_auth_http import api, ORIGIN, assert_private
from test_team_reads import Connection

AT = datetime(2026,11,14,12,tzinfo=timezone.utc)


def body(**values):
    return dict(skills=[' Python ','python','C++'],timezone='Asia/Kolkata',discoverable=True,version=0)|values


def test_profile_normalization_and_private_default_acceptance():
    assert len(ZONES)>100
    assert ProfileBody(**body()).skills==['c++','python']
    assert ProfileBody(**body(skills=[],timezone=None,discoverable=False)).skills==[]


@pytest.mark.parametrize('value',[
    {'skills':['']},{'skills':['two words']},{'skills':['x'*33]}, {'skills':['python,sql']},
    {'skills':['a']*21},{'skills':[42]},{'skills':'python'},{'skills':['☃']},
    {'timezone':'Mars/Base'},{'timezone':'../UTC'},{'timezone':' UTC'}, {'timezone':'Factory'},
    {'timezone':None},{'version':True},{'version':-1},{'discoverable':'true'},{'user_id':str(uuid4())},
])
def test_invalid_profiles_rejected(value):
    with pytest.raises(ValidationError): ProfileBody(**body(**value))


@pytest.fixture
def profiles(api):
    p=MagicMock(spec=ProfileService); m=MagicMock(spec=MatchingService)
    actor=api.issued.principal.user_id
    p.get.return_value=p.update.return_value=dict(user_id=actor,display_name='Unit',username='unit_user',
        skills=[],timezone=None,discoverable=False,version=0)
    h,t=uuid4(),uuid4()
    m.suggestions.return_value=dict(hackathon_id=h,team_id=t,user_id=actor,reference_at=AT,
        team_skills=[],skill_weight=.7,timezone_weight=.3,items=[],next_cursor=None)
    api.app.dependency_overrides[profile_api.get_profile_service]=lambda:p
    api.app.dependency_overrides[profile_api.get_matching_service]=lambda:m
    headers={'Cookie':'__Host-merge_session='+encode_token(api.issued.session_token.get_secret_value()),
        'Origin':ORIGIN,'X-CSRF-Token':encode_token(api.issued.csrf_token.get_secret_value())}
    return SimpleNamespace(api=api,p=p,m=m,headers=headers,h=h,t=t,actor=actor,
        path=f'/api/hackathons/{h}/teams/{t}/suggestions')


def test_own_profile_and_leader_ranking_contract(profiles):
    r=profiles
    for path in ('/api/me/profile',r.path):
        response=r.api.client.get(path,headers=r.headers)
        assert response.status_code==200; assert_private(response)
        assert 'csrf' not in response.text and 'password' not in response.text
    r.p.get.assert_called_once_with(r.actor)
    r.m.suggestions.assert_called_once_with(r.h,r.t,r.actor,limit=20,cursor=None)
    response=r.api.client.post('/api/me/profile',headers=r.headers,json=body())
    assert response.status_code==200
    actor,submitted=r.p.update.call_args.args
    assert actor==r.actor and submitted.skills==['c++','python']
    r.api.services.sessions.verify_csrf.assert_called_once()


@pytest.mark.parametrize('route',['profile','ranking'])
@pytest.mark.parametrize('kind,status',[('guest',401),('origin',403),('actor',422)])
def test_profile_and_ranking_reads_enforce_session_scope(profiles,route,kind,status):
    r=profiles; headers=dict(r.headers)
    if kind=='guest': headers.pop('Cookie')
    elif kind=='origin': headers['Origin']='https://other.example'
    else: headers['X-User-ID']=str(uuid4())
    response=r.api.client.get('/api/me/profile' if route=='profile' else r.path,headers=headers)
    assert response.status_code==status
    r.p.get.assert_not_called(); r.m.suggestions.assert_not_called()


@pytest.mark.parametrize('kind,status',[
    ('guest',401),('origin',403),('fetch',403),('csrf',403),('actor',422),('query',422),
    ('skills',422),('zone',422),('extra',422),('version',422),('media',415),
])
def test_update_policy_never_writes(profiles,kind,status):
    r=profiles; headers=dict(r.headers); payload=body(); path='/api/me/profile'
    if kind=='guest': headers.pop('Cookie')
    elif kind=='origin': headers['Origin']='https://other.example'
    elif kind=='fetch': headers['Sec-Fetch-Site']='cross-site'
    elif kind=='csrf': headers.pop('X-CSRF-Token')
    elif kind=='actor': headers['X-Actor-ID']=str(uuid4())
    elif kind=='query': path+='?user_id='+str(uuid4())
    elif kind=='skills': payload['skills']=['']
    elif kind=='zone': payload['timezone']='invented'
    elif kind=='extra': payload['user_id']=str(uuid4())
    elif kind=='version': payload['version']=False
    if kind=='media': response=r.api.client.post(path,headers=headers,content='invalid')
    else: response=r.api.client.post(path,headers=headers,json=payload)
    assert response.status_code==status; assert_private(response); r.p.update.assert_not_called()


@pytest.mark.parametrize('suffix',['?limit=0','?limit=21','?limit=1&limit=2','?cursor=bad!','?cursor='+('a'*129),'?actor_id=x'])
def test_ranking_invalid_queries_never_read(profiles,suffix):
    r=profiles
    assert r.api.client.get(r.path+suffix,headers=r.headers).status_code==422
    r.m.suggestions.assert_not_called()


@pytest.mark.parametrize('code,status',[('forbidden',403),('team_not_found',404),('ranking_changed',409),('service_unavailable',503)])
def test_matching_denials_are_sanitized(profiles,code,status):
    r=profiles; r.m.suggestions.side_effect=ProfileError(code)
    response=r.api.client.get(r.path,headers=r.headers)
    assert response.status_code==status and response.json()['error']['code']==code
    assert_private(response)


def test_exact_formula_empty_skills_and_missing_zones():
    score,v=components(['python','sql'],{'python'},'UTC',['UTC'],AT)
    assert score==65 and v['new_skills']==['sql'] and v['skill_points']==35 and v['timezone_points']==30
    score,v=components([],set(),'UTC',[None,'UTC'],AT)
    assert score==15 and v['skill_complement']==0 and v['timezone_overlap']==.5
    score,v=components(['sql'],{'python'},'Asia/Kolkata',['UTC'],AT)
    assert score==70+30*Fraction(150,480)
    assert v['timezone_points']==9.375 and v['skill_complement']==1
    assert components([],set(),'Pacific/Kiritimati',['Pacific/Honolulu'],AT)[0]==30
    assert components([],set(),'UTC',['Asia/Tokyo'],AT)[0]==0


def snapshot(actor,**overrides):
    return dict(leader_user_id=actor,max_team_size=3,member_count=1,reference_at=AT,
        members=[dict(user_id=str(actor),skills=['python'],timezone='UTC')],
        candidates=[dict(user_id=str(UUID(int=i)),display_name=f'User {i}',username=f'user_{i}',skills=['sql'],timezone='UTC') for i in (4,2,3)])|overrides


def test_stable_ties_pages_and_stale_snapshot_restart():
    h,t,a=uuid4(),uuid4(),uuid4(); row=snapshot(a)
    first=ranked_page(row,h,t,a,2,None)
    assert [v['user_id'] for v in first['items']]==[str(UUID(int=2)),str(UUID(int=3))]
    assert [v['score'] for v in first['items']]==[100,100]
    second=ranked_page(row,h,t,a,2,first['next_cursor'])
    assert [v['user_id'] for v in second['items']]==[str(UUID(int=4))] and second['next_cursor'] is None
    for changed in (snapshot(a,max_team_size=4),snapshot(a,candidates=[]),snapshot(a,reference_at=datetime(2026,11,15,12,tzinfo=timezone.utc))):
        with pytest.raises(ProfileError,match='ranking_changed'): ranked_page(changed,h,t,a,2,first['next_cursor'])
    with pytest.raises(ProfileError,match='ranking_changed'): ranked_page(row,uuid4(),t,a,2,first['next_cursor'])


def test_missing_deleted_foreign_unauthorized_full_and_pool_bounds():
    h,t,a=uuid4(),uuid4(),uuid4()
    with pytest.raises(ProfileError,match='team_not_found'): ranked_page(None,h,t,a,20,None)
    with pytest.raises(ProfileError,match='forbidden'): ranked_page(snapshot(uuid4()),h,t,a,20,None)
    assert ranked_page(snapshot(a,member_count=3),h,t,a,20,None)['items']==[]
    with pytest.raises(ProfileError,match='service_unavailable'):
        ranked_page(snapshot(a,candidates=[{}]*10001),h,t,a,20,None)


@pytest.mark.parametrize('cursor',['','!','a'*129,'YQ','____'])
def test_cursor_malformed_fails_closed(cursor):
    h,t,a=uuid4(),uuid4(),uuid4()
    with pytest.raises(ProfileError,match='invalid_request'): ranked_page(snapshot(a),h,t,a,20,cursor)


def test_one_owned_read_snapshot_eligibility_and_resources():
    c=Connection(); h,t,a=uuid4(),uuid4(),uuid4(); c.rows=[snapshot(a)]
    engine=MagicMock(spec=Engine); engine.connect.return_value.__enter__.return_value=c
    result=MatchingService(engine).suggestions(h,t,a)
    assert len(result['items'])==3 and c.events==['begin','commit'] and not c.active
    engine.connect.return_value.__exit__.assert_called_once()
    assert len(c.queries)==4
    for clause in ('p.discoverable','p.timezone IS NOT NULL','u.id<>:actor','m.hackathon_id=t.hackathon_id',
                   'NOT EXISTS','t.deleted_at IS NULL','t.leader_user_id=:actor','JOIN public.account_credentials'):
        assert clause in SNAPSHOT
    assert c.queries[-1][1]==dict(hackathon=h,team=t,actor=a,bound=10001)


def test_ranking_cpu_work_starts_after_connection_release(monkeypatch):
    from app.services import matching
    c=Connection(); h,t,a=uuid4(),uuid4(),uuid4(); c.rows=[snapshot(a)]
    engine=MagicMock(spec=Engine); engine.connect.return_value.__enter__.return_value=c
    original=matching.score_components
    def checked(*args):
        assert not c.active
        engine.connect.return_value.__exit__.assert_called_once()
        return original(*args)
    monkeypatch.setattr(matching,'score_components',checked)
    assert len(MatchingService(engine).suggestions(h,t,a)['items'])==3


def test_profile_cas_write_owner_and_conflict_rollback():
    a=uuid4(); c=Connection()
    # Reuse read-owner connection guard, with controlled returning rows.
    row=dict(user_id=a,display_name='Name',username='name',skills=['c++','python'],timezone='Asia/Kolkata',discoverable=True,version=1)
    original=c.execute
    def execute(statement,params=None):
        if str(statement).startswith('SELECT'):
            c.queries.append((str(statement),params)); return SimpleNamespace(mappings=lambda:SimpleNamespace(one_or_none=lambda:row))
        result=original(statement,params)
        return SimpleNamespace(scalar_one_or_none=lambda:a) if str(statement).startswith(('INSERT','UPDATE')) else result
    c.execute=execute
    engine=MagicMock(spec=Engine); engine.connect.return_value.__enter__.return_value=c
    service=ProfileService(engine)
    assert service.update(a,ProfileBody(**body())).version==1
    assert c.events==['begin','commit'] and not c.active
    assert 'ON CONFLICT (user_id) DO NOTHING' in c.queries[2][0]
    c.execute=lambda statement,params=None: SimpleNamespace(scalar_one_or_none=lambda:None)
    with pytest.raises(ProfileError,match='profile_changed'): service.update(a,ProfileBody(**body(version=1)))
    assert c.events[-1]=='rollback' and not c.active


def test_profile_migration_only_renders_offline_and_legacy_guards_remain():
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0006_profiles.py'
    spec=importlib.util.spec_from_file_location('profile_revision',path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.revision=='0006_profiles' and module.down_revision=='0005_invitations'
    output=io.StringIO(); context=MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':output})
    with Operations.context(context): module.upgrade()
    sql=output.getvalue()
    assert 'CREATE TABLE public.participant_profiles' in sql
    for unsafe in ('DROP ','DELETE ','UPDATE public.','CREATE OR REPLACE','GRANT '): assert unsafe not in sql
    with pytest.raises(RuntimeError): module.downgrade()
    from test_support.revisions import TARGET_REVISIONS
    assert '0006_profiles' not in TARGET_REVISIONS


def test_new_api_dependency_has_no_engine_fallback():
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(auth_engine=None)))
    for dependency in (profile_api.get_profile_service,profile_api.get_matching_service):
        with pytest.raises(ProfileError): dependency(request,MagicMock())
