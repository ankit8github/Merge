"""PYTEST_DONT_REWRITE: owner-run PostgreSQL HTTP admission; no cleanup or private dumps."""
from threading import Barrier
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import event
from sqlalchemy.exc import DBAPIError

from admission_tests.conftest import headers
from test_support.races import Outcome, sql, workers


def path(s):
    return f'/api/hackathons/{s[0]}/teams/{s[1]}/join-requests'


def request(client,s,key='request',issued=None):
    return client.post(path(s),headers=headers(issued or s[5],key),json={})


def decide(client,s,r,key='decision',decision='approve',issued=None):
    return client.post(path(s)+'/'+str(r)+'/decision',headers=headers(issued or s[3],key),json={'decision':decision})


def snapshot(db,h):
    with db.connection() as c:
        sql(c,'SET TRANSACTION READ ONLY')
        state={name:sql(c,f'SELECT to_jsonb(t) FROM public.{name} t WHERE hackathon_id=:h ORDER BY to_jsonb(t)::text',h=h).scalars().all()
            for name in ('teams','memberships','join_requests','idempotency_records','audit_events')}
        state['outbox_events']=sql(c,'''SELECT to_jsonb(o) FROM public.outbox_events o
            JOIN public.audit_events a ON a.id=o.audit_event_id WHERE a.hackathon_id=:h
            ORDER BY to_jsonb(o)::text''',h=h).scalars().all()
        return state


def assert_final_seat_state(state,request_ids,results,leader,team):
    """Fresh committed oracle, shared with offline negative regressions."""
    winners=[r for r,outcome in zip(request_ids,results) if outcome.status=='200']
    assert len(winners)==1 and len(results)==len(request_ids)
    assert all(o.status=='200' or (o.status=='409' and o.state=='team_full') for o in results)
    requests={r['id']:r for r in state['join_requests']}
    assert len(requests)==len(state['join_requests'])==len(request_ids) and set(requests)==set(request_ids)
    for request_id,r in requests.items():
        won=request_id==winners[0]
        assert r['team_id']==str(team) and r['status']==('approved' if won else 'pending')
        assert (r['resolved_at'] is not None)==won
        assert r['resolved_by']==(str(leader) if won else None)
    winner=requests[winners[0]]['requester_id']
    assert len(state['memberships'])==2
    assert {m['user_id'] for m in state['memberships']}=={str(leader),winner}
    assert all(m['team_id']==str(team) for m in state['memberships'])
    assert len(state['teams'])==1
    target=state['teams'][0]
    expected=len(request_ids)+2  # Founder + each request + exactly one decision.
    assert target['id']==str(team) and target['max_team_size']==2 and target['version']==expected
    assert target['leader_user_id']==str(leader)
    records=state['idempotency_records']; audits=state['audit_events']; outbox=state['outbox_events']
    assert len(records)==len(audits)==len(outbox)==expected
    for operation,count in [('team.create.v1',1),('request.create.v1',len(request_ids)),('request.decide.v1',1)]:
        assert sum(r['operation']==operation for r in records)==count
    assert all(r['state']=='completed' for r in records)
    decision=next(r for r in records if r['operation']=='request.decide.v1')
    assert decision['actor_id']==str(leader) and decision['http_status']==200
    assert decision['response_body']['data']['id']==winners[0] and decision['response_body']['data']['status']=='approved'
    assert sorted(a['team_version'] for a in audits)==list(range(1,expected+1))
    assert {a['idempotency_record_id'] for a in audits}=={r['id'] for r in records}
    assert {o['audit_event_id'] for o in outbox}=={a['id'] for a in audits}
    for audit in audits:
        new=audit['new_state']; admitted=audit['action']=='request.decide.v1'
        assert new['team']['member_count']==(2 if admitted else 1)
        if admitted:
            assert new['request']=={'id':winners[0],'status':'approved'}
            assert new['subject']=={'user_id':winner,'member':True}
            assert audit['old_state']['request']=={'id':winners[0],'status':'pending'}


def test_creation_private_status_duplicate_and_exact_replay(client,environment,subject):
    s=subject
    assert client.get(path(s)+'/mine',headers=headers(s[5])).json()=={'request':None}
    first=request(client,s)
    assert first.status_code==201
    saved=snapshot(environment,s[0])
    assert request(client,s).content==first.content and snapshot(environment,s[0])==saved
    duplicate=request(client,s,key='duplicate')
    assert duplicate.status_code==200 and duplicate.json()==first.json()
    own=client.get(path(s)+'/mine',headers=headers(s[5])).json()['request']
    assert own['id']==first.json()['data']['id'] and 'resolved_by' not in own
    assert client.get(path(s)+'/mine',headers=headers(s[3])).json()=={'request':None}
    listed=client.get(path(s),headers=headers(s[3]))
    assert listed.status_code==200 and listed.json()['items'][0]['id']==own['id']


@pytest.mark.parametrize('decision',['approve','reject'])
def test_decision_atomic_chain_stored_replay_and_other_key_conflict(client,environment,subject,decision):
    s=subject; r=request(client,s).json()['data']['id']
    first=decide(client,s,r,decision=decision)
    assert first.status_code==200 and first.json()['data']['status']==('approved' if decision=='approve' else 'rejected')
    saved=snapshot(environment,s[0])
    assert decide(client,s,r,decision=decision).content==first.content and snapshot(environment,s[0])==saved
    assert decide(client,s,r,key='other',decision=decision).json()['error']['code']=='request_resolved'
    assert environment.roster(s[1])==({s[2],s[4]} if decision=='approve' else {s[2]})
    assert client.get(path(s),headers=headers(s[3])).json()['items']==[]


@pytest.mark.parametrize('kind',['missing','expired','revoked','csrf','origin','metadata','body','key'])
def test_real_security_rejections_never_write(client,environment,subject,kind):
    s=subject; supplied=headers(s[5]); body={}; expected=403
    if kind=='missing': supplied.pop('Cookie'); expected=401
    if kind=='expired':
        from session_tests.test_sessions import seeded_session
        from datetime import timedelta
        import secrets
        password=secrets.token_urlsafe(32)
        identity=environment.credentials.register(username='exp_'+uuid4().hex[:24],password=password)
        raw,csrf,_=seeded_session(environment, (identity,password),timedelta(hours=9))
        from app.auth import encode_token
        supplied['Cookie']='__Host-merge_session='+encode_token(raw)
        supplied['X-CSRF-Token']=encode_token(csrf); expected=401
    if kind=='revoked': environment.sessions.revoke(s[5].session_token.get_secret_value()); expected=401
    if kind=='csrf': supplied['X-CSRF-Token']='bad'
    if kind=='origin': supplied['Origin']='https://evil.example'
    if kind=='metadata': supplied['Sec-Fetch-Site']='cross-site'
    if kind=='body': body={'actor_id':'untrusted'}; expected=422
    if kind=='key': supplied.pop('Idempotency-Key'); expected=422
    saved=snapshot(environment,s[0])
    r=client.post(path(s),headers=supplied,json=body)
    assert r.status_code==expected and snapshot(environment,s[0])==saved


def test_unauthorized_views_decisions_and_scope_binding(client,environment,subject):
    s=subject; r=request(client,s).json()['data']['id']; saved=snapshot(environment,s[0])
    assert client.get(path(s),headers=headers(s[5])).status_code==403
    assert decide(client,s,r,issued=s[5]).status_code==403
    other=environment.teams.create_team_idempotent(hackathon_id=s[0],actor_id=uuid_user(environment),name='Other team',key='other')
    t=UUID(other.body()['data']['team_id'])
    assert client.post(path(s).replace(str(s[1]),str(t))+'/'+r+'/decision',headers=headers(s[3]),json={'decision':'approve'}).status_code==403
    assert decide(client,s,uuid4()).status_code==404
    h2,_,_=environment.seed(teams=0)
    assert client.post(path(s).replace(str(s[0]),str(h2))+'/'+r+'/decision',headers=headers(s[3]),json={'decision':'approve'}).status_code==404
    assert snapshot(environment,s[0])['join_requests']==saved['join_requests']


def uuid_user(db):
    return db.account()[0]


@pytest.mark.parametrize('matching',[True,False])
def test_concurrent_decisions_same_request_have_one_effect(client,environment,subject,matching):
    s=subject; r=request(client,s).json()['data']['id']; gate=Barrier(2,timeout=8)
    def action(key):
        gate.wait()
        response=decide(client,s,r,key=key)
        return Outcome(str(response.status_code),response.json().get('error',{}).get('code',''))
    outcomes=workers([lambda:action('same'),lambda:action('same' if matching else 'other')])
    assert [o.status for o in outcomes].count('200')==(2 if matching else 1)
    assert all(o.status in ('200','409') for o in outcomes)
    assert environment.roster(s[1])=={s[2],s[4]}


@pytest.mark.parametrize('candidates',[2,50])
def test_authenticated_final_seat_approval_race(client,environment,subject,candidates):
    s=subject; requests=[]
    for _ in range(candidates):
        user,issued=environment.account()
        r=request(client,s,issued=issued)
        assert r.status_code==201 and r.json()['data']['requester_id']==str(user)
        requests.append(r.json()['data']['id'])
    gate=Barrier(candidates,timeout=15)
    def action(r):
        gate.wait()
        response=decide(client,s,r,key='approve-'+r)
        return Outcome(str(response.status_code),response.json().get('error',{}).get('code',''))
    results=workers([lambda r=r:action(r) for r in requests])
    assert sum(r.status=='200' for r in results)==1
    assert sum(r.status=='409' and r.state=='team_full' for r in results)==candidates-1
    assert len(environment.roster(s[1]))==2
    assert_final_seat_state(snapshot(environment,s[0]),requests,results,s[2],s[1])


def test_same_requester_competing_teams_maintains_one_membership(client,environment,subject):
    s=subject
    other_leader,other_session=environment.account()
    reply=environment.teams.create_team_idempotent(hackathon_id=s[0],actor_id=other_leader,name='Other target',key='other-target')
    other=(s[0],UUID(reply.body()['data']['team_id']),other_leader,other_session,s[4],s[5])
    a=request(client,s).json()['data']['id']; b=request(client,other,key='other-request').json()['data']['id']
    gate=Barrier(2,timeout=8)
    def action(scope,r):
        gate.wait(); response=decide(client,scope,r,key='approve-'+r)
        return Outcome(str(response.status_code),response.json().get('error',{}).get('code',''))
    results=workers([lambda:action(s,a),lambda:action(other,b)])
    assert sorted(r.status for r in results)==['200','409']
    assert next(r for r in results if r.status=='409').state=='already_assigned'


@pytest.mark.parametrize('replay',[True,False])
def test_replaced_leader_cannot_replay_or_decide(client,environment,subject,replay):
    s=subject; r=request(client,s).json()['data']['id']
    if replay: assert decide(client,s,r,decision='reject').status_code==200
    # Admit a replacement using the existing trusted fixture service, then make
    # a scoped raw fixture leadership change under the established locks.
    replacement,_=environment.account()
    environment.teams.join_team_idempotent(hackathon_id=s[0],team_id=s[1],actor_id=replacement,key='replacement-member')
    with environment.connection() as c:
        sql(c,'SELECT id FROM public.hackathons WHERE id=:h FOR SHARE',h=s[0])
        for user in sorted([s[2],replacement]): sql(c,'SELECT id FROM public.users WHERE id=:u FOR NO KEY UPDATE',u=user)
        sql(c,'SELECT id FROM public.teams WHERE id=:t FOR NO KEY UPDATE',t=s[1])
        sql(c,'UPDATE public.teams SET leader_user_id=:u WHERE id=:t',u=replacement,t=s[1]); c.commit()
    assert decide(client,s,r,decision='reject').status_code==403
    assert client.get(path(s),headers=headers(s[3])).status_code==403


@pytest.mark.parametrize('matching',[True,False])
def test_concurrent_request_creation_retains_one_transition(client,environment,subject,matching):
    gate=Barrier(2,timeout=8)
    def action(key):
        gate.wait(); r=request(client,subject,key=key)
        return Outcome(str(r.status_code),r.json().get('data',{}).get('id',''))
    results=workers([lambda:action('one'),lambda:action('one' if matching else 'two')])
    assert all(r.status in ('200','201') for r in results) and results[0].state==results[1].state
    saved=snapshot(environment,subject[0])
    assert len(saved['join_requests'])==1
    assert len(saved['audit_events'])==2  # Team creation and one request transition.


def test_changed_key_command_and_stale_resolved_request(client,environment,subject):
    s=subject; r=request(client,s).json()['data']['id']
    assert decide(client,s,r,decision='reject').status_code==200
    assert decide(client,s,r,decision='approve').json()['error']['code']=='idempotency_mismatch'
    assert decide(client,s,r,key='new',decision='approve').json()['error']['code']=='request_resolved'
    assert environment.roster(s[1])=={s[2]}


def test_leader_page_cursor_and_private_own_status(client,environment,subject):
    s=subject
    ids=[]
    for _ in range(3):
        _,issued=environment.account()
        ids.append(request(client,s,issued=issued).json()['data']['id'])
    page=client.get(path(s)+'?limit=2',headers=headers(s[3])).json()
    assert [r['id'] for r in page['items']]==sorted(ids)[:2] and page['next_cursor']==sorted(ids)[1]
    second=client.get(path(s)+'?limit=2&cursor='+page['next_cursor'],headers=headers(s[3])).json()
    assert [r['id'] for r in second['items']]==sorted(ids)[2:] and second['next_cursor'] is None
    assert client.get(path(s)+'?cursor='+str(uuid4()),headers=headers(s[3])).status_code==422
    assert client.get(path(s)+'/mine?requester_id='+str(s[2]),headers=headers(s[5])).status_code==422


@pytest.mark.parametrize('kind',['identity','terminal','unique','scope-fk','approved-without-membership'])
def test_real_request_constraints_rollback_scoped_invalid_work(client,environment,subject,kind):
    s=subject; r=request(client,s).json()['data']['id']
    if kind=='terminal': assert decide(client,s,r,decision='reject').status_code==200
    saved=snapshot(environment,s[0])
    with pytest.raises(DBAPIError) as caught:
        with environment.connection() as c:
            if kind=='identity': sql(c,'UPDATE public.join_requests SET requester_id=:u WHERE id=:r',u=s[2],r=UUID(r))
            if kind=='terminal': sql(c,"UPDATE public.join_requests SET status='pending',resolved_at=NULL,resolved_by=NULL WHERE id=:r",r=UUID(r))
            if kind in ('unique','scope-fk'):
                sql(c,'''INSERT INTO public.join_requests(id,hackathon_id,team_id,requester_id)
                    VALUES (:id,:h,:t,:u)''',id=uuid4(),h=s[0] if kind=='unique' else uuid4(),t=s[1],u=s[4] if kind=='unique' else s[2])
            if kind=='approved-without-membership':
                sql(c,"UPDATE public.join_requests SET status='approved',resolved_at=clock_timestamp(),resolved_by=:u WHERE id=:r",u=s[2],r=UUID(r))
            c.commit()
    expected={'identity':'guard_request_identity','terminal':'guard_request_terminal','unique':'uq_requests_team_user',
        'scope-fk':'fk_requests_team_hackathon','approved-without-membership':'ct_request_admitted'}
    assert caught.value.orig.diag.constraint_name==expected[kind]
    assert snapshot(environment,s[0])==saved


@pytest.mark.parametrize('stage',['request','membership','audit','outbox','completion','deferred-commit','ambiguous-commit'])
def test_real_failure_rolls_back_or_reconciles_same_key(client,environment,subject,stage):
    s=subject; r=request(client,s).json()['data']['id']; saved=snapshot(environment,s[0]); fired=False
    target=None
    def before(c,cursor,statement,parameters,context,many):
        nonlocal fired
        token={'request':'UPDATE public.join_requests','membership':'INSERT INTO public.memberships',
            'audit':'INSERT INTO public.audit_events','outbox':'INSERT INTO public.outbox_events',
            'completion':'UPDATE public.idempotency_records'}.get(stage)
        if not fired and token and token in statement:
            fired=True
            cursor.execute('SELECT 1/0')  # Real PostgreSQL statement failure, not a Python mock.
        if stage=='deferred-commit' and 'UPDATE public.join_requests' in statement:
            # Delete just the new scoped membership; deferred request admission
            # validation must reject the complete transaction at commit.
            cursor.execute('DELETE FROM public.memberships WHERE hackathon_id=%s AND user_id=%s',(s[0],s[4]))
    def identify_decision(c,cursor,statement,parameters,context,many):
        nonlocal target
        if (stage=='ambiguous-commit' and 'UPDATE public.join_requests' in statement
                and context.compiled_parameters[0]['id']==UUID(r)):
            # Arm only after this request transition succeeded. Authentication
            # and CSRF also commit on this Engine, before the decision starts.
            target=(c,c.get_transaction())
    def lose_ack(c):
        nonlocal fired
        if (target is not None and c is target[0]
                and c.get_transaction() is target[1] and not fired):
            fired=True
            # SQLAlchemy's commit event precedes the driver COMMIT. Commit the
            # exact decision physically, then simulate losing its acknowledgement.
            c.connection.dbapi_connection.commit()
            raise psycopg.OperationalError('synthetic lost acknowledgement')
    event.listen(environment.engine,'before_cursor_execute',before)
    event.listen(environment.engine,'after_cursor_execute',identify_decision)
    event.listen(environment.engine,'commit',lose_ack)
    try: response=decide(client,s,r)
    finally:
        event.remove(environment.engine,'commit',lose_ack)
        event.remove(environment.engine,'after_cursor_execute',identify_decision)
        event.remove(environment.engine,'before_cursor_execute',before)
    if stage=='ambiguous-commit':
        assert fired
        assert response.status_code in (200,503)
        if response.status_code==503: assert response.json()['error']['code']=='outcome_uncertain'
        committed=snapshot(environment,s[0])
        resolved=next(row for row in committed['join_requests'] if row['id']==r)
        assert resolved['status']=='approved' and resolved['resolved_by']==str(s[2])
        assert sum(row['operation']=='request.decide.v1' for row in committed['idempotency_records'])==1
        replay=decide(client,s,r)
        assert replay.status_code==200
        assert replay.json()['data']['id']==r and replay.json()['data']['status']=='approved'
        if response.status_code==200: assert replay.json()==response.json()
        assert snapshot(environment,s[0])==committed
        assert environment.roster(s[1])=={s[2],s[4]}
    else:
        assert response.status_code==503 and snapshot(environment,s[0])==saved
