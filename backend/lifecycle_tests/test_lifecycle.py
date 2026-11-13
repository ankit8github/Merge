"""PYTEST_DONT_REWRITE: real PostgreSQL schedules, only via explicit guarded runner."""
from threading import Barrier, Event, Lock, Thread
from time import monotonic
from uuid import UUID, uuid4
import pytest
from test_support.races import sql, workers, Outcome
from test_support.invitation_race import rooted_waiters
from sqlalchemy import event
from lifecycle_tests.conftest import headers


@pytest.fixture
def subject(environment,client):
    db=environment; h=uuid4(); db.hackathons.append(h)
    with db.connection() as c:
        sql(c,"INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:h,:name,2,3)",h=h,name='m019a_'+h.hex)
        c.commit()
    accounts=[db.account() for _ in range(3)]
    created=client.post(f'/api/hackathons/{h}/teams',headers=headers(accounts[0][1],'create'),json={'name':'Lifecycle'})
    assert created.status_code==201
    return h,UUID(created.json()['data']['team_id']),accounts


def path(s): return f'/api/hackathons/{s[0]}/teams/{s[1]}'


def admit(client,s,index):
    issued=client.post(path(s)+'/invitations',headers=headers(s[2][0][1],'issue-'+str(index)),json={'recipient_id':str(s[2][index][0])})
    assert issued.status_code==201
    grant=issued.json()['data']['id']
    r=client.post(path(s)+f'/invitations/{grant}/redeem',headers=headers(s[2][index][1],'redeem-'+str(index)),json={})
    assert r.status_code==200


def leave(client,s,index,key='leave'):
    return client.post(path(s)+'/leave',headers=headers(s[2][index][1],key),json={})


def remove(client,s,index,key='remove'):
    return client.post(path(s)+f'/members/{s[2][index][0]}/remove',headers=headers(s[2][0][1],key),json={})


def race(actions):
    gate=Barrier(len(actions),timeout=8)
    def run(action):
        gate.wait(); r=action(); return Outcome(str(r.status_code),r.json().get('error',{}).get('code',''))
    return workers([lambda a=a:run(a) for a in actions])


def observed_departures(client,db,s):
    """Require two actual team-lock waiters rooted at this test's observer."""
    held=Event(); changed=Event(); mutex=Lock(); pids=set(); observed=[]; errors=[]
    def record(c,cursor,statement,parameters,context,many):
        if ('FROM public.teams' in statement and 'FOR NO KEY UPDATE' in statement
                and isinstance(parameters,dict) and parameters.get('team')==s[1]):
            with mutex: pids.add(c.connection.dbapi_connection.info.backend_pid)
            changed.set()
    def observe():
        try:
            with db.connection() as c:
                owner=sql(c,'SELECT pg_backend_pid()').scalar_one()
                sql(c,'SELECT id FROM public.teams WHERE id=:t FOR NO KEY UPDATE',t=s[1]); held.set()
                deadline=monotonic()+3
                while monotonic()<deadline:
                    with mutex: candidates=list(pids)
                    if len(candidates)>=2:
                        rows=sql(c,'''SELECT pid,pg_blocking_pids(pid) AS blockers FROM pg_stat_activity WHERE pid=ANY(CAST(:pids AS integer[]))
                            AND datname=current_database() AND usename=current_user AND wait_event_type='Lock'
                            ''',pids=candidates).mappings().all()
                        count=rooted_waiters(rows,owner,{pid:pid for pid in candidates})
                        if count>=2:
                            observed.append(count); c.commit(); return
                    changed.wait(.01); changed.clear()
                raise AssertionError('Lifecycle overlap not observed')
        except Exception: errors.append('lifecycle_overlap_failed')
        finally: held.set()
    event.listen(db.engine,'before_cursor_execute',record)
    observer=Thread(target=observe,daemon=True); observer.start()
    try:
        assert held.wait(8)
        results=race([lambda i=i:leave(client,s,i) for i in range(3)])
    finally:
        observer.join(5); event.remove(db.engine,'before_cursor_execute',record)
    assert not observer.is_alive() and not errors and observed and min(observed)>=2
    return results


def test_member_leave_removal_final_deletion_and_reads(client,environment,subject):
    s=subject; admit(client,s,1); admit(client,s,2)
    assert leave(client,s,2).status_code==200
    first=remove(client,s,1); assert first.status_code==200
    assert remove(client,s,1).content==first.content
    assert leave(client,s,0).json()['data']['deleted'] is True
    assert client.get(path(s),headers=headers(s[2][0][1])).status_code==404
    assert client.get(f'/api/hackathons/{s[0]}/me/team',headers=headers(s[2][0][1])).json()=={'team':None}
    assert client.get(f'/api/hackathons/{s[0]}/teams',headers=headers(s[2][0][1])).json()['items']==[]


def test_succession_and_old_leader_permissions(client,environment,subject):
    s=subject; admit(client,s,1); admit(client,s,2)
    # Establish a real successful removal receipt before changing leadership.
    assert remove(client,s,2).status_code==200
    with environment.connection() as c:
        expected=sql(c,'SELECT user_id FROM public.memberships WHERE team_id=:t AND user_id<>:u ORDER BY joined_at,user_id LIMIT 1',t=s[1],u=s[2][0][0]).scalar_one()
    response=leave(client,s,0); assert response.status_code==200
    assert response.json()['data']['leader_user_id']==str(expected)
    assert remove(client,s,2).status_code==403  # Exact original key is still unauthorized.
    assert client.get(path(s)+'/members',headers=headers(s[2][0][1])).status_code==403
    assert client.get(path(s)+'/members',headers=headers(s[2][1][1])).status_code==200


def test_simultaneous_departures_delete_only_at_final_departure(client,environment,subject):
    s=subject; admit(client,s,1); admit(client,s,2)
    results=observed_departures(client,environment,s)
    assert [r.status for r in results]==['200']*3
    leader,deleted=environment.team(s[1]); assert leader is None and deleted is not None
    assert environment.roster(s[1])==set()


def test_same_key_departure_contention_has_one_effect(client,environment,subject):
    s=subject; admit(client,s,1)
    results=race([lambda:leave(client,s,1),lambda:leave(client,s,1)])
    assert [r.status for r in results]==['200','200']
    with environment.connection() as c:
        assert sql(c,"SELECT count(*) FROM public.audit_events WHERE team_id=:t AND action='team.leave.v1'",t=s[1]).scalar_one()==1


def test_remove_vs_subject_leave(client,environment,subject):
    s=subject; admit(client,s,1)
    results=race([lambda:remove(client,s,1),lambda:leave(client,s,1)])
    assert sorted(r.status for r in results)==['200','409']
    assert next(r for r in results if r.status=='409').state=='member_not_found'
    assert environment.roster(s[1])=={s[2][0][0]}


def test_leader_departure_vs_removal(client,environment,subject):
    s=subject; admit(client,s,1)
    results=race([lambda:leave(client,s,0),lambda:remove(client,s,1)])
    assert results[0].status=='200' and results[1].status in ('200','403')


def test_leader_departure_vs_request_approval(client,environment,subject):
    s=subject; admit(client,s,1)
    request=client.post(path(s)+'/join-requests',headers=headers(s[2][2][1],'request'),json={})
    assert request.status_code==201
    target=request.json()['data']['id']
    results=race([lambda:leave(client,s,0),lambda:client.post(path(s)+f'/join-requests/{target}/decision',
        headers=headers(s[2][0][1],'approve'),json={'decision':'approve'})])
    assert results[0].status=='200' and results[1].status in ('200','403')


def test_final_departure_vs_invitation_redemption(client,environment,subject):
    s=subject
    grant=client.post(path(s)+'/invitations',headers=headers(s[2][0][1],'issue'),json={'recipient_id':str(s[2][1][0])}).json()['data']['id']
    results=race([lambda:leave(client,s,0),lambda:client.post(path(s)+f'/invitations/{grant}/redeem',headers=headers(s[2][1][1],'redeem'),json={})])
    assert results[0].status=='200' and results[1].status in ('200','404')


def test_departure_vs_same_user_cross_team_admission(client,environment,subject):
    s=subject; admit(client,s,1)
    founder,session=environment.account()
    other=client.post(f'/api/hackathons/{s[0]}/teams',headers=headers(session,'other'),json={'name':'Other'}).json()['data']['team_id']
    base=f'/api/hackathons/{s[0]}/teams/{other}'
    grant=client.post(base+'/invitations',headers=headers(session,'issue-other'),json={'recipient_id':str(s[2][1][0])}).json()['data']['id']
    results=race([lambda:leave(client,s,1),lambda:client.post(base+f'/invitations/{grant}/redeem',headers=headers(s[2][1][1],'redeem-other'),json={})])
    assert results[0].status=='200' and results[1].status in ('200','409')
    if results[1].status=='409': assert results[1].state=='already_assigned'
    with environment.connection() as c:
        assert sql(c,'SELECT count(*) FROM public.memberships WHERE hackathon_id=:h AND user_id=:u',h=s[0],u=s[2][1][0]).scalar_one()<=1


def test_real_outbox_failure_rolls_back_departure(client,environment,subject,monkeypatch):
    from app.services import lifecycle
    s=subject
    def fail(*a,**kw): raise RuntimeError('synthetic-outbox-failure')
    monkeypatch.setattr(lifecycle,'_outbox_in_tx',fail)
    assert leave(client,s,0).status_code==503
    assert environment.roster(s[1])=={s[2][0][0]}
    leader,deleted=environment.team(s[1]); assert leader==s[2][0][0] and deleted is None
