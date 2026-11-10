"""PYTEST_DONT_REWRITE: real PostgreSQL HTTP reads; no private exception dumps."""
from datetime import timedelta
from threading import Event
from uuid import uuid4
import secrets

import pytest
from sqlalchemy import event

from app.auth import encode_token
from app.read_api import get_read_service
from app.services.team_reads import TeamReadService
from session_tests.test_sessions import seeded_session
from test_support.races import Outcome, sql, wait, workers


def paths(h,t):
    return ['/api/hackathons',f'/api/hackathons/{h}/teams',
            f'/api/hackathons/{h}/teams/{t}',f'/api/hackathons/{h}/me/team']


def private(r):
    assert r.headers['cache-control']=='no-store, private'
    assert 'set-cookie' not in r.headers and 'access-control-allow-origin' not in r.headers


def shape(team):
    assert set(team)=={'id','hackathon_id','name','min_team_size','max_team_size','member_count','readiness','leader','created_at'}
    assert set(team['leader'])=={'user_id','display_name'}
    assert 1<=team['member_count']<=team['max_team_size']
    assert team['readiness']==('ready' if team['member_count']>=team['min_team_size'] else 'forming')


@pytest.mark.parametrize('index',range(4))
def test_no_cookie_or_identity_header_is_not_authentication(client,subject,index):
    h,users,teams=subject
    r=client.get(paths(h,teams[0])[index],headers={'X-User-ID':str(users[0])})
    assert r.status_code==401 and r.json()['error']['code']=='invalid_session'
    private(r)


@pytest.mark.parametrize('index',range(4))
@pytest.mark.parametrize('kind',['forged','expired','revoked'])
def test_real_invalid_session_rejected(client,environment,subject,account,index,kind):
    h,users,teams=subject
    if kind=='expired':
        raw,_,_=seeded_session(environment,account,timedelta(hours=9))
    elif kind=='revoked':
        issued=environment.sessions.login(username=account[0].username,password=account[1])
        raw=issued.session_token.get_secret_value()
        environment.sessions.revoke(raw)
    else: raw=secrets.token_bytes(32)
    r=client.get(paths(h,teams[0])[index],headers={'Cookie':'__Host-merge_session='+encode_token(raw)})
    assert r.status_code==401 and r.json()['error']['code']=='invalid_session'
    private(r)


def test_authenticated_discovery_and_own_membership_only(authorized,environment,subject,account):
    client,issued=authorized
    h,users,teams=subject
    assert client.get(paths(h,teams[0])[3]).json()=={'team':None}
    environment.teams.join_team(hackathon_id=h,team_id=teams[0],actor_id=account[0].user_id)
    listing=client.get(paths(h,teams[0])[1])
    assert listing.status_code==200 and len(listing.json()['items'])==3
    detail=client.get(paths(h,teams[0])[2])
    assert detail.status_code==200 and detail.json()['member_count']==2
    assert detail.json()['leader']==dict(user_id=str(users[0]),display_name='Public display')
    mine=client.get(paths(h,teams[0])[3])
    assert mine.status_code==200 and mine.json()['team']==detail.json()
    for r in (listing,detail,mine): private(r)
    shape(detail.json())
    # A foreign identity is rejected, never used to select membership.
    r=client.get(paths(h,teams[0])[3],headers={'X-User-ID':str(users[1])})
    assert r.status_code==422


def test_deterministic_keyset_pagination_and_real_counts(authorized,environment,subject):
    client,_=authorized
    h,users,teams=subject
    ordered=sorted(teams,reverse=True)  # All created_at values share seed transaction's now().
    url=paths(h,teams[0])[1]
    first=client.get(url,params={'limit':2})
    assert first.status_code==200
    body=first.json()
    assert [t['id'] for t in body['items']]==list(map(str,ordered[:2]))
    assert body['next_cursor']==str(ordered[1])
    assert client.get(url,params={'limit':2}).json()==body
    second=client.get(url,params={'limit':2,'cursor':body['next_cursor']})
    assert second.status_code==200 and second.json()['next_cursor'] is None
    assert [t['id'] for t in second.json()['items']]==[str(ordered[2])]
    for team in body['items']+second.json()['items']:
        shape(team)
        assert team['member_count']==1 and team['readiness']=='forming'
    # Catalog ordering also matches the actual primary-key slice, even with retained fixtures.
    with environment.connection() as c:
        expected=sql(c,'SELECT id FROM public.hackathons ORDER BY id ASC LIMIT 3').scalars().all()
    catalog=client.get('/api/hackathons',params={'limit':2})
    assert catalog.status_code==200
    assert [h['id'] for h in catalog.json()['items']]==list(map(str,expected[:2]))
    assert catalog.json()['next_cursor']==(str(expected[1]) if len(expected)>2 else None)


def test_scope_missing_deleted_and_tombstone_cursor(authorized,environment,subject):
    client,_=authorized
    h,users,teams=subject
    other,_,_=environment.seed_discovery()
    r=client.get(f'/api/hackathons/{other}/teams/{teams[0]}')
    assert r.status_code==404 and r.json()['error']['code']=='team_not_found'
    r=client.get(f'/api/hackathons/{uuid4()}/teams')
    assert r.status_code==404 and r.json()['error']['code']=='hackathon_not_found'
    r=client.get(paths(h,teams[0])[1],params={'cursor':str(uuid4())})
    assert r.status_code==422
    tombstone=uuid4()
    # Legal retained tombstone fixture; no DELETE, trigger weakening or cleanup.
    with environment.connection() as c:
        sql(c,'''INSERT INTO public.teams(id,hackathon_id,name,min_team_size,max_team_size,
            leader_user_id,created_by,deleted_at) VALUES (:t,:h,'Hidden tombstone',2,3,NULL,:u,clock_timestamp())''',
            t=tombstone,h=h,u=users[0])
        c.commit()
    assert client.get(f'/api/hackathons/{h}/teams/{tombstone}').status_code==404
    r=client.get(paths(h,teams[0])[1],params={'cursor':str(tombstone)})
    assert r.status_code==200 and len(r.json()['items'])==3
    assert all(t['id']!=str(tombstone) for t in r.json()['items'])


@pytest.mark.parametrize('query',['limit=0','limit=101','limit=bad','cursor=not-a-uuid','actor_id=forged'])
def test_real_query_bounds(authorized,subject,query):
    client,_=authorized
    h,users,teams=subject
    r=client.get(paths(h,teams[0])[1]+'?'+query)
    assert r.status_code==422 and r.json()['error']['code']=='invalid_request'
    private(r)


@pytest.mark.parametrize('part',['hackathon','team'])
def test_real_invalid_uuid_paths(authorized,subject,part):
    client,_=authorized
    h,users,teams=subject
    path=f'/api/hackathons/{h}/teams/{teams[0]}'
    path=path.replace(str(h) if part=='hackathon' else str(teams[0]),'private-invalid-uuid')
    r=client.get(path)
    assert r.status_code==422 and r.json()['error']['code']=='invalid_request'
    assert 'private-invalid-uuid' not in r.text
    private(r)


def test_real_reads_are_readonly_and_exclude_private_material(authorized,environment,subject,account,caplog):
    client,issued=authorized
    h,users,teams=subject
    queries=[]
    def observe(c,cursor,statement,parameters,context,many):
        queries.append(statement)
        if 'AS scope_id' in statement or statement.startswith('SELECT id,name,min_team_size'):
            assert sql(c,'SHOW transaction_read_only').scalar_one()=='on'
    event.listen(environment.engine,'before_cursor_execute',observe)
    try:
        for path in paths(h,teams[0]):
            r=client.get(path)
            assert r.status_code==200
            private(r)
            for forbidden in ('csrf_token','username','password','token_hash','audit','request_hash'):
                assert forbidden not in r.text
            assert account[1] not in r.text+caplog.text
            assert encode_token(issued.session_token.get_secret_value()) not in r.text+caplog.text
        assert not any(q.lstrip().startswith(('INSERT','UPDATE','DELETE')) for q in queries)
        assert not any('FOR UPDATE' in q or 'FOR SHARE' in q or 'FOR NO KEY UPDATE' in q for q in queries)
    finally:
        event.remove(environment.engine,'before_cursor_execute',observe)


def test_real_autocommit_guard_fails_before_domain_query(authorized,environment,subject):
    client,_=authorized
    h,users,teams=subject
    engine=environment.engine.execution_options(isolation_level='AUTOCOMMIT')
    queries=[]
    def observe(c,cursor,statement,parameters,context,many): queries.append(statement)
    client.app.dependency_overrides[get_read_service]=lambda:TeamReadService(engine)
    event.listen(engine,'before_cursor_execute',observe)
    try:
        r=client.get(paths(h,teams[0])[1])
        assert r.status_code==503 and r.json()['error']['code']=='service_unavailable'
        assert not any('FROM public.teams' in q or 'FROM public.hackathons' in q for q in queries)
    finally:
        event.remove(engine,'before_cursor_execute',observe)


def test_uncommitted_join_is_invisible_then_all_response_shapes_are_committed(authorized,environment,subject,account):
    client,_=authorized
    h,users,teams=subject
    held,release=Event(),Event()
    def hold(c,cursor,statement,parameters,context,many):
        if 'INSERT INTO public.memberships' in statement:
            assert context.compiled_parameters[0]['actor']==account[0].user_id
            held.set()
            wait(release)
    def mutate():
        environment.teams.join_team(hackathon_id=h,team_id=teams[0],actor_id=account[0].user_id)
        return Outcome('joined')
    def read():
        try:
            wait(held)
            listing=client.get(paths(h,teams[0])[1])
            detail=client.get(paths(h,teams[0])[2])
            mine=client.get(paths(h,teams[0])[3])
            assert listing.status_code==detail.status_code==mine.status_code==200
            assert all(t['member_count']==1 for t in listing.json()['items'])
            assert detail.json()['member_count']==1 and mine.json()=={'team':None}
            shape(detail.json())
            return Outcome('old-snapshot')
        finally: release.set()
    event.listen(environment.engine,'after_cursor_execute',hold)
    try:
        assert workers([mutate,read])==[Outcome('joined'),Outcome('old-snapshot')]
    finally:
        release.set()
        event.remove(environment.engine,'after_cursor_execute',hold)
    detail=client.get(paths(h,teams[0])[2])
    mine=client.get(paths(h,teams[0])[3])
    assert detail.status_code==mine.status_code==200
    assert detail.json()['member_count']==2 and detail.json()['readiness']=='ready'
    assert mine.json()['team']==detail.json()
    shape(detail.json())
