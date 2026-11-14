"""PYTEST_DONT_REWRITE: real PostgreSQL/profile/ranking HTTP acceptance; retained."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID,uuid4
import pytest
from sqlalchemy.exc import DBAPIError
from app.profile_models import ProfileBody
from app.services.profiles import ProfileError
from profile_tests.conftest import headers
from test_support.races import sql


def profile(client,account,**values):
    body=dict(skills=['python'],timezone='UTC',discoverable=True,version=0)|values
    return client.post('/api/me/profile',headers=headers(account[1],'profile'),json=body)


def path(s): return f'/api/hackathons/{s[0]}/teams/{s[1]}'


def rank(client,s,account=None,suffix=''):
    return client.get(path(s)+'/suggestions'+suffix,headers=headers((account or s[2][0])[1],'read'))


def fresh_rows(client,s):
    # Global opt-in is intentional. Retained older users are never deleted or
    # hidden by test-only service filters; inspect only this case's fresh IDs.
    ids={str(a[0]) for a in s[2]};rows=[];cursor=None
    for _ in range(501):
        response=rank(client,s,suffix='' if cursor is None else '?cursor='+cursor)
        assert response.status_code==200
        page=response.json();rows.extend(r for r in page['items'] if r['user_id'] in ids)
        cursor=page['next_cursor']
        if cursor is None:return rows
    raise AssertionError('Ranking pagination bound exceeded')


def test_own_default_update_and_conflict(client,subject):
    a=subject[2][0];h=headers(a[1],'read')
    before=client.get('/api/me/profile',headers=h);assert before.status_code==200 and before.json()['version']==0
    saved=profile(client,a,skills=[' Python ','SQL','python']);assert saved.status_code==200
    assert saved.json()['skills']==['python','sql'] and saved.json()['version']==1
    assert profile(client,a).status_code==409
    assert client.get('/api/me/profile',headers=h).json()==saved.json()


@pytest.mark.parametrize('field,value',[
    ('skills',['']),('skills',['bad skill']),('skills',['x'*33]),('skills',['a']*21),
    ('timezone','Mars/Base'),('timezone',None),('version',True),('discoverable','true')],ids=[str(i) for i in range(8)])
def test_invalid_authenticated_updates_have_no_profile(client,subject,environment,field,value):
    a=subject[2][1];assert profile(client,a,**{field:value}).status_code==422
    assert environment.profiles.get(a[0]).version==0


@pytest.mark.parametrize('kind',['missing','csrf','origin','actor','extra'])
def test_http_permission_boundaries(client,subject,environment,kind):
    a=subject[2][1];hs=headers(a[1],'profile');body=dict(skills=[],timezone=None,discoverable=False,version=0)
    if kind=='missing': hs.pop('Cookie')
    elif kind=='csrf': hs.pop('X-CSRF-Token')
    elif kind=='origin': hs['Origin']='https://wrong.example'
    elif kind=='actor': hs['X-Actor-ID']=str(subject[2][2][0])
    else: body['user_id']=str(subject[2][2][0])
    response=client.post('/api/me/profile',headers=hs,json=body)
    assert response.status_code==(401 if kind=='missing' else 403 if kind in ('csrf','origin') else 422)
    assert environment.profiles.get(a[0]).version==0 and environment.profiles.get(subject[2][2][0]).version==0


def test_stable_explained_ties_and_optout(client,subject):
    for a in subject[2][1:3]: assert profile(client,a,skills=['sql']).status_code==200
    assert profile(client,subject[2][3],discoverable=False).status_code==200
    response=rank(client,subject);assert response.status_code==200
    rows=fresh_rows(client,subject);assert [r['user_id'] for r in rows]==sorted(str(a[0]) for a in subject[2][1:3])
    assert all(r['skill_complement']==1 and r['timezone_overlap']==0 and r['score']==70 for r in rows)
    assert all(r['skill_points']+r['timezone_points']==r['score'] for r in rows)


def test_exact_formula_and_empty_skills(client,subject):
    assert profile(client,subject[2][0],skills=['python']).status_code==200
    assert profile(client,subject[2][1],skills=['python','sql']).status_code==200
    assert profile(client,subject[2][2],skills=[]).status_code==200
    rows=fresh_rows(client,subject);assert [r['score'] for r in rows]==[65,30]


def test_nonleader_foreign_and_deleted_team_denied(client,subject):
    assert rank(client,subject,subject[2][1]).status_code==403
    assert client.get(f'/api/hackathons/{uuid4()}/teams/{subject[1]}/suggestions',headers=headers(subject[2][0][1],'r')).status_code==404
    assert client.post(path(subject)+'/leave',headers=headers(subject[2][0][1],'leave'),json={}).status_code==200
    assert rank(client,subject).status_code==404


def test_membership_eligibility_and_lifecycle(client,subject,environment):
    a=subject[2][1];before=environment.realtime.revision(subject[0],a[0])
    assert profile(client,a,skills=['sql']).status_code==200
    assert environment.realtime.revision(subject[0],a[0])==before
    issued=client.post(path(subject)+'/invitations',headers=headers(subject[2][0][1],'issue'),json={'recipient_id':str(a[0])})
    assert issued.status_code==201
    assert client.post(path(subject)+'/invitations/'+issued.json()['data']['id']+'/redeem',headers=headers(a[1],'redeem'),json={}).status_code==200
    assert fresh_rows(client,subject)==[]
    assert client.post(path(subject)+'/leave',headers=headers(a[1],'leave'),json={}).status_code==200
    assert fresh_rows(client,subject)[0]['user_id']==str(a[0])
    assert environment.realtime.revision(subject[0],a[0])!=before


def test_other_hackathon_membership_is_eligible_until_current_team_full(client,subject,environment):
    other=uuid4();environment.hackathons.append(other)
    with environment.connection() as c:
        sql(c,'INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:h,:name,2,4)',h=other,name='batchb_'+other.hex);c.commit()
    a=subject[2][1];assert profile(client,a,skills=['sql']).status_code==200
    assert client.post(f'/api/hackathons/{other}/teams',headers=headers(a[1],'other'),json={'name':'Other scope'}).status_code==201
    assert fresh_rows(client,subject)[0]['user_id']==str(a[0])
    for index,person in enumerate(subject[2][1:]):
        issued=client.post(path(subject)+'/invitations',headers=headers(subject[2][0][1],f'issue-{index}'),json={'recipient_id':str(person[0])})
        assert issued.status_code==201
        assert client.post(path(subject)+'/invitations/'+issued.json()['data']['id']+'/redeem',headers=headers(person[1],f'redeem-{index}'),json={}).status_code==200
    assert rank(client,subject).json()['items']==[]


def test_snapshot_cursor_rejects_changed_profiles(client,subject):
    for a in subject[2][1:]: assert profile(client,a,skills=['sql']).status_code==200
    page=rank(client,subject,suffix='?limit=1').json();assert page['next_cursor']
    nextpage=rank(client,subject,suffix='?limit=1&cursor='+page['next_cursor']);assert nextpage.status_code==200
    assert nextpage.json()['items'][0]['user_id']!=page['items'][0]['user_id']
    assert profile(client,subject[2][1],skills=[],version=1).status_code==200
    assert rank(client,subject,suffix='?cursor='+page['next_cursor']).status_code==409


@pytest.mark.parametrize('suffix',['?limit=0','?limit=21','?actor_id=forged','?cursor=bad!'],ids=['0','1','2','3'])
def test_bounded_rank_queries(client,subject,suffix): assert rank(client,subject,suffix=suffix).status_code==422


def test_cas_simultaneous_updates_one_winner(environment,subject):
    a=subject[2][1];barrier=Barrier(2,timeout=10)
    def save(skill):
        barrier.wait()
        try:
            environment.profiles.update(a[0],ProfileBody(skills=[skill],timezone='UTC',discoverable=True,version=0));return 'saved'
        except ProfileError as e: return e.code
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(save,['sql','react']))
    assert sorted(results)==['profile_changed','saved'] and environment.profiles.get(a[0]).version==1


@pytest.mark.parametrize('bad', ['ARRAY[NULL]::varchar[]',"ARRAY['bad skill']::varchar[]","ARRAY['x,y']::varchar[]"],ids=['0','1','2'])
def test_real_constraints_and_rollback(environment,subject,bad):
    a=subject[2][1]
    with environment.connection() as c:
        with pytest.raises(DBAPIError): sql(c,f'INSERT INTO public.participant_profiles(user_id,skills) VALUES (:u,{bad})',u=a[0])
        c.rollback()
    assert environment.profiles.get(a[0]).version==0


def test_uncommitted_profile_is_invisible_and_rollback_clean(environment,subject,client):
    a=subject[2][1]
    with environment.connection() as c:
        sql(c,"INSERT INTO public.participant_profiles(user_id,skills,timezone,discoverable) VALUES (:u,ARRAY['sql'],'UTC',true)",u=a[0])
        assert environment.profiles.get(a[0]).version==0 and fresh_rows(client,subject)==[]
        c.rollback()
    assert environment.profiles.get(a[0]).version==0


def test_profile_schema_and_foreign_key_rollback(environment,subject):
    with environment.connection() as c:
        names=set(sql(c,"SELECT conname FROM pg_constraint WHERE conrelid='public.participant_profiles'::regclass").scalars())
        assert names=={'pk_participant_profiles','fk_profiles_user','ck_profiles_skills','ck_profiles_timezone','ck_profiles_discovery','ck_profiles_version'}
        indexes=sql(c,"SELECT indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='participant_profiles'").scalars().all()
        assert len(indexes)==1 and 'UNIQUE INDEX pk_participant_profiles' in indexes[0] and '(user_id)' in indexes[0]
        with pytest.raises(DBAPIError):sql(c,'INSERT INTO public.participant_profiles(user_id) VALUES (:u)',u=uuid4())
        c.rollback()
