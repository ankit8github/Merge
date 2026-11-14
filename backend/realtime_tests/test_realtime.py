"""PYTEST_DONT_REWRITE: PostgreSQL visibility/permission schedules. Never offline evidence."""
from uuid import uuid4
from app.services.lifecycle import command
from app.services.realtime import RealtimeService
from realtime_tests.conftest import headers
from test_support.races import sql


def snapshots(db,s):
    service=RealtimeService(db.engine)
    return [service.revision(s[0],a[0]) for a in s[2]]


def path(s): return f'/api/hackathons/{s[0]}/teams/{s[1]}'


def test_uncommitted_departure_and_rollback_are_invisible(environment,subject):
    db,s=environment,subject; before=snapshots(db,s)
    with db.connection() as c:
        scope=command(s[0],s[1],s[2][0][0],'rollback')
        db.lifecycle._change(c,scope,s[1],s[2][0][0],False)
        assert snapshots(db,s)==before
        c.rollback()
    assert snapshots(db,s)==before and db.roster(s[1])=={s[2][0][0]}


def test_late_commit_after_another_team_and_exact_replay(environment,client,subject):
    db,s=environment,subject; before=snapshots(db,s)
    with db.connection() as c:
        scope=command(s[0],s[1],s[2][0][0],'late-leave')
        reply=db.lifecycle._change(c,scope,s[1],s[2][0][0],False)
        assert snapshots(db,s)==before
        other=client.post(f'/api/hackathons/{s[0]}/teams',headers=headers(s[2][1][1],'other'),json={'name':'Other'})
        assert other.status_code==201
        intermediate=snapshots(db,s); assert all(a!=b for a,b in zip(before,intermediate))
        c.commit()
    after=snapshots(db,s); assert all(a!=b for a,b in zip(intermediate,after))
    replay=db.lifecycle.leave(hackathon_id=s[0],team_id=s[1],actor_id=s[2][0][0],key='late-leave')
    assert replay.body()==reply.body() and snapshots(db,s)==after
    assert db.team(s[1])[1] is not None and db.roster(s[1])==set()


def test_request_privacy_hackathon_isolation_and_succession(environment,client,subject):
    db,s=environment,subject; service=RealtimeService(db.engine); other=uuid4(); db.hackathons.append(other)
    with db.connection() as c:
        sql(c,'INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:h,:name,2,3)',h=other,name='m020a_'+other.hex)
        c.commit()
    isolated=service.revision(other,s[2][2][0]); before=snapshots(db,s)
    request=client.post(path(s)+'/join-requests',headers=headers(s[2][1][1],'request'),json={})
    assert request.status_code==201
    private=snapshots(db,s); assert private[0]!=before[0] and private[1]!=before[1] and private[2]==before[2]
    decision=client.post(path(s)+f"/join-requests/{request.json()['data']['id']}/decision",
        headers=headers(s[2][0][1],'approve'),json={'decision':'approve'})
    assert decision.status_code==200
    admitted=snapshots(db,s); assert all(a!=b for a,b in zip(private,admitted))
    assert client.post(path(s)+'/leave',headers=headers(s[2][0][1],'leave'),json={}).status_code==200
    assert all(a!=b for a,b in zip(admitted,snapshots(db,s)))
    assert db.team(s[1])[0]==s[2][1][0] and service.revision(other,s[2][2][0])==isolated


def test_invitation_recipient_isolation_redemption_and_removal(environment,client,subject):
    db,s=environment,subject; before=snapshots(db,s)
    issued=client.post(path(s)+'/invitations',headers=headers(s[2][0][1],'issue'),json={'recipient_id':str(s[2][1][0])})
    assert issued.status_code==201
    private=snapshots(db,s); assert private[0]==before[0] and private[1]!=before[1] and private[2]==before[2]
    redeemed=client.post(path(s)+f"/invitations/{issued.json()['data']['id']}/redeem",headers=headers(s[2][1][1],'redeem'),json={})
    assert redeemed.status_code==200
    after=snapshots(db,s); assert all(a!=b for a,b in zip(private,after))
    removed=client.post(path(s)+f'/members/{s[2][1][0]}/remove',headers=headers(s[2][0][1],'remove'),json={})
    assert removed.status_code==200 and all(a!=b for a,b in zip(after,snapshots(db,s)))
    assert db.reads.my_team(s[0],s[2][1][0]).team is None
