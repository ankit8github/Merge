"""PYTEST_DONT_REWRITE: exact-0005 retained HTTP tests; no private diagnostics."""
from threading import Event, Lock, Thread
from uuid import UUID, uuid4
import pytest
from sqlalchemy import event
from app.invitation_api import get_invitation_service
from app.services.invitations import InvitationService
from admission_tests.test_admission import snapshot as admission_snapshot
from invitation_tests.conftest import headers
from test_support.races import sql, workers, Outcome
from test_support.invitation_race import (ArrivalGate, assert_race_state, observe_overlap,
    tracked_caller,record_target_wait)


def path(s): return f'/api/hackathons/{s[0]}/teams/{s[1]}/invitations'


def issue(client,s,recipient,key='issue',issued=None):
    return client.post(path(s),headers=headers(issued or s[3],key),json={'recipient_id':str(recipient)})


def redeem(client,s,invitation,issued=None,key='redeem'):
    return client.post(path(s)+'/'+str(invitation)+'/redeem',headers=headers(issued or s[5],key),json={})


def snapshot(db,h):
    saved=admission_snapshot(db,h)
    with db.connection() as c:
        sql(c,'SET TRANSACTION READ ONLY')
        saved['invitations']=sql(c,'SELECT to_jsonb(i) FROM public.invitations i WHERE hackathon_id=:h ORDER BY id',h=h).scalars().all()
    return saved


def test_issue_private_inbox_redemption_and_exact_replay(client,environment,subject):
    s=subject; first=issue(client,s,s[4]); assert first.status_code==201
    i=first.json()['data']['id']; saved=snapshot(environment,s[0])
    assert issue(client,s,s[4]).content==first.content and snapshot(environment,s[0])==saved
    own=f'/api/hackathons/{s[0]}/invitations/mine'
    assert client.get(own,headers=headers(s[5])).json()['items'][0]['available'] is True
    assert client.get(own,headers=headers(s[3])).json()['items']==[]
    winner=redeem(client,s,i); assert winner.status_code==200
    saved=snapshot(environment,s[0])
    assert redeem(client,s,i).content==winner.content and snapshot(environment,s[0])==saved
    assert redeem(client,s,i,key='different').json()['error']['code']=='invitation_redeemed'
    assert environment.roster(s[1])=={s[2],s[4]}


@pytest.mark.parametrize('kind',['missing','csrf','origin','identity','forged'])
def test_unauthorized_redemption_never_changes_domain(client,environment,subject,kind):
    s=subject; i=issue(client,s,s[4]).json()['data']['id']; supplied=headers(s[5]); body={}
    expected=403
    if kind=='missing': supplied.pop('Cookie'); expected=401
    if kind=='csrf': supplied['X-CSRF-Token']='bad'
    if kind=='origin': supplied['Origin']='https://other.example'
    if kind=='identity': supplied['X-Actor-ID']=str(s[2]); expected=422
    if kind=='forged': body={'actor_id':str(s[4])}; expected=422
    saved=snapshot(environment,s[0])
    response=client.post(path(s)+'/'+i+'/redeem',headers=supplied,json=body)
    assert response.status_code==expected and snapshot(environment,s[0])==saved


def test_nonleader_issue_wrong_recipient_and_command_reuse(client,environment,subject):
    s=subject
    assert issue(client,s,s[4],issued=s[5]).status_code==403
    first=issue(client,s,s[4]); assert first.status_code==201
    i=first.json()['data']['id']; saved=snapshot(environment,s[0])
    assert redeem(client,s,i,issued=s[3]).status_code==404
    assert issue(client,s,s[2]).json()['error']['code']=='idempotency_mismatch'
    assert snapshot(environment,s[0])==saved


@pytest.mark.parametrize('replay',[True,False])
def test_stale_issuer_rejects_redemption_and_issue_replay(client,environment,subject,replay):
    s=subject
    # A valid replacement must already be a member; no production transfer route.
    first=issue(client,s,s[4]); assert first.status_code==201
    i=first.json()['data']['id']
    if replay:
        assert redeem(client,s,i).status_code==200
        replacement=s[4]
    else:
        replacement,_=environment.account()
        environment.teams.join_team_idempotent(hackathon_id=s[0],team_id=s[1],actor_id=replacement,key='replacement')
    with environment.connection() as c:
        sql(c,'SELECT id FROM public.hackathons WHERE id=:h FOR SHARE',h=s[0])
        for u in sorted([s[2],replacement]): sql(c,'SELECT id FROM public.users WHERE id=:u FOR NO KEY UPDATE',u=u)
        sql(c,'SELECT id FROM public.teams WHERE id=:t FOR NO KEY UPDATE',t=s[1])
        sql(c,'UPDATE public.teams SET leader_user_id=:u WHERE id=:t',u=replacement,t=s[1]); c.commit()
    saved=snapshot(environment,s[0])
    assert redeem(client,s,i).json()['error']['code']=='invitation_stale'
    assert issue(client,s,s[4]).status_code==403
    assert snapshot(environment,s[0])==saved


def test_distinct_authenticated_50_caller_last_seat(client,environment,subject):
    s=subject; accounts=[environment.account() for _ in range(50)]
    actors=[user for user,_ in accounts]
    assert len(set(actors))==50 and s[2] not in actors
    assert len({issued.session_token.get_secret_value() for _,issued in accounts})==50
    assert len({issued.csrf_token.get_secret_value() for _,issued in accounts})==50
    ids=[]
    for n,(user,_) in enumerate(accounts):
        response=issue(client,s,user,key='grant-'+str(n)); assert response.status_code==201
        grant=response.json()['data']
        assert grant['recipient_id']==str(user) and grant['issued_by']==str(s[2])
        assert grant['hackathon_id']==str(s[0]) and grant['team_id']==str(s[1]) and grant['status']=='pending'
        ids.append(grant['id'])
    baseline=snapshot(environment,s[0]); assert len(baseline['memberships'])==1
    assert baseline['teams'][0]['version']==51
    assert {r['id']:r['recipient_id'] for r in baseline['invitations']}==dict(zip(ids,map(str,actors)))
    gate=ArrivalGate(actors); pid_lock=Lock(); pids={}; changed=Event()
    observer_errors=[]; observed=[]; successes={}

    class GatedService(InvitationService):
        def redeem(self,**kwargs):
            gate.enter(kwargs['actor_id'])  # After actual cookie/CSRF dependencies.
            return super().redeem(**kwargs)

        def _redeem_in_tx(self,c,scope,team_id,invitation):
            with tracked_caller(c,scope.actor_id,pids,pid_lock):
                return super()._redeem_in_tx(c,scope,team_id,invitation)

    def record(c,cursor,statement,parameters,context,many):
        record_target_wait(c,statement,parameters,gate,s[0],s[1],pids,pid_lock,changed)

    async def configure():
        import anyio.to_thread
        limiter=anyio.to_thread.current_default_thread_limiter()
        previous=limiter.total_tokens; limiter.total_tokens=64
        return limiter,previous

    limiter,previous=client.portal.call(configure)
    client.app.dependency_overrides[get_invitation_service]=lambda:GatedService(environment.engine)
    event.listen(environment.engine,'before_cursor_execute',record)

    def observe():
        try:
            observed.append(observe_overlap(gate,environment,s[1],pids,pid_lock,changed))
        except Exception:
            observer_errors.append('overlap_observation_failed')
        finally: gate.release.set()

    observer=Thread(target=observe,daemon=True); observer.start()
    try:
        def action(index):
            response=redeem(client,s,ids[index],issued=accounts[index][1],key='redeem-'+str(index))
            if response.status_code==200:
                assert response.json()['data']['recipient_id']==str(actors[index])
                assert response.json()['data']['id']==ids[index]
                with pid_lock: successes[index]=response.content
            return Outcome(str(response.status_code),response.json().get('error',{}).get('code',''))
        outcomes=workers([lambda n=n:action(n) for n in range(50)])
    finally:
        gate.release.set(); observer.join(5)
        event.remove(environment.engine,'before_cursor_execute',record)
        client.app.dependency_overrides[get_invitation_service]=lambda:environment.invitations
        async def restore(): limiter.total_tokens=previous
        client.portal.call(restore)
    assert not observer.is_alive() and not observer_errors and observed and min(observed)>=2
    gate.verify()
    saved=snapshot(environment,s[0]); assert_race_state(saved,ids,outcomes,s[2],s[1])
    winner=next(n for n,o in enumerate(outcomes) if o.status=='200')
    replay=redeem(client,s,ids[winner],issued=accounts[winner][1],key='redeem-'+str(winner))
    assert replay.status_code==200 and replay.content==successes[winner]
    assert snapshot(environment,s[0])==saved


def test_same_recipient_cross_team_redemptions_keep_one_membership(client,environment,subject):
    from threading import Barrier
    s=subject; leader,session=environment.account()
    created=environment.teams.create_team_idempotent(hackathon_id=s[0],actor_id=leader,name='Second invitation team',key='other')
    other=(s[0],UUID(created.body()['data']['team_id']),leader,session,s[4],s[5])
    a=issue(client,s,s[4]).json()['data']['id']
    b=issue(client,other,s[4],key='issue-other').json()['data']['id']
    gate=Barrier(2,timeout=8)
    def action(scope,invitation,key):
        gate.wait(); response=redeem(client,scope,invitation,key=key)
        return Outcome(str(response.status_code),response.json().get('error',{}).get('code',''))
    results=workers([lambda:action(s,a,'a'),lambda:action(other,b,'b')])
    assert sorted(r.status for r in results)==['200','409']
    assert next(r for r in results if r.status=='409').state=='already_assigned'
    with environment.connection() as c:
        sql(c,'SET TRANSACTION READ ONLY')
        assert sql(c,'SELECT count(*) FROM public.memberships WHERE hackathon_id=:h AND user_id=:u',h=s[0],u=s[4]).scalar_one()==1
        assert sql(c,"SELECT count(*) FROM public.invitations WHERE hackathon_id=:h AND status='pending'",h=s[0]).scalar_one()==1


@pytest.mark.parametrize('replay',[False,True])
def test_expired_retained_grant_is_not_consumed_or_replayed(client,environment,subject,replay):
    # Fixture-only past grant: use one owned transaction and the normal complete
    # issue audit/outbox chain. Immutable production rows are never edited.
    from app.services.invitations import command,FIELDS
    from app.services.idempotency import _reserve_in_tx,_complete_in_tx
    s=subject; service=environment.invitations
    scope=command(s[0],s[1],s[2],'expired-fixture',recipient=s[4])
    def seed(c):
        reserved=_reserve_in_tx(c,scope)
        team=service._lock(c,s[0],s[1],(s[2],s[4]))
        assert team.leader_user_id==s[2]
        row=sql(c,f'''WITH stamp AS (SELECT clock_timestamp()-INTERVAL '25 hours' AS at)
            INSERT INTO public.invitations(id,hackathon_id,team_id,recipient_id,issued_by,created_at,expires_at)
            SELECT :id,:h,:t,:u,:actor,at,at+INTERVAL '24 hours' FROM stamp RETURNING {FIELDS}''',
            id=uuid4(),h=s[0],t=s[1],u=s[4],actor=s[2]).mappings().one()
        service._record_invitation(c,reserved,row,False)
        return _complete_in_tx(c,reserved,service._reply(row,201))
    reply=service._execute(seed); i=reply.body()['data']['id']
    if replay:
        def seed_redemption(c):
            scope=command(s[0],s[1],s[4],'redeem',invitation=UUID(i))
            reserved=_reserve_in_tx(c,scope)
            team=service._lock(c,s[0],s[1],(s[4],))
            row=sql(c,f'SELECT {FIELDS} FROM public.invitations WHERE id=:id FOR NO KEY UPDATE',id=UUID(i)).mappings().one()
            assert row['recipient_id']==s[4] and row['issued_by']==team.leader_user_id
            from app.services.teams import _JoinTeamCommand
            service._admit_locked_in_tx(c,_JoinTeamCommand(s[0],s[1],s[4]),team)
            row=sql(c,f'''UPDATE public.invitations SET status='redeemed',redeemed_at=expires_at-INTERVAL '1 minute'
                WHERE id=:id RETURNING {FIELDS}''',id=UUID(i)).mappings().one()
            service._record_invitation(c,reserved,row,True)
            return _complete_in_tx(c,reserved,service._reply(row,200))
        assert service._execute(seed_redemption).http_status==200
    saved=snapshot(environment,s[0])
    response=redeem(client,s,i)
    assert response.status_code==409 and response.json()['error']['code']=='invitation_expired'
    assert snapshot(environment,s[0])==saved
