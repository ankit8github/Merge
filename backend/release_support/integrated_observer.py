"""Independent fixed-target read-only observer. Private input only via stdin.

Snapshots/fingerprints stay in memory/private IPC. Output is counts and fixed
markers only. No credentials, tokens, raw snapshots or exceptions are printed.
"""
from datetime import datetime, timedelta
import json
import os
import sys
from uuid import UUID
from sqlalchemy import text
from release_support.integrated_ledger import require,DENIALS
from release_support.integrated_plan import validate_plan, COMMANDS, PROFILE_POSTS
from release_support.integrated_host import profile_engine
from release_support.targets import Target

PK = {'users':'id::text','hackathons':'id::text','teams':'id::text',
    'memberships':"hackathon_id::text||'|'||user_id::text",'idempotency_records':'id::text',
    'audit_events':'id::text','outbox_events':'id::text','account_credentials':'user_id::text',
    'auth_sessions':"encode(token_hash,'hex')",
    'auth_throttle_buckets':"scope||'|'||encode(key_hash,'hex')||'|'||window_start::text",
    'join_requests':'id::text','invitations':'id::text','participant_profiles':'user_id::text'}


def snapshot(c, plan):
    """One owned consistent read-only snapshot, after connection guard's RC probe."""
    validate_plan(plan); result=dict(hashes={},rows={})
    require(not c.in_transaction())
    with c.begin():
        c.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        for table,key in PK.items():
            result['hashes'][table]=dict(c.execute(text(f'SELECT {key},md5(to_jsonb(t)::text) FROM public.{table} t')).all())
        params=dict(names=[a['username'] for a in plan['accounts']],hs=[UUID(h['id']) for h in plan['hackathons']])
        creds=c.execute(text('SELECT user_id::text,username,created_at::text,updated_at::text FROM public.account_credentials WHERE username=ANY(:names)'),params).mappings().all()
        result['rows']['account_credentials']={r['user_id']:dict(r) for r in creds}
        params['ids']=[UUID(r['user_id']) for r in creds]
        where={'users':'id=ANY(:ids)','hackathons':'id=ANY(:hs)',
            **{t:'hackathon_id=ANY(:hs)' for t in ('teams','memberships','idempotency_records','audit_events','join_requests','invitations')},
            'participant_profiles':'user_id=ANY(:ids)',
            'outbox_events':'audit_event_id IN (SELECT id FROM public.audit_events WHERE hackathon_id=ANY(:hs))'}
        for table,predicate in where.items():
            row="to_jsonb(t)||jsonb_build_object('request_hash',encode(request_hash,'hex'))" if table=='idempotency_records' else 'to_jsonb(t)'
            result['rows'][table]=dict(c.execute(text(f'SELECT {PK[table]},{row} FROM public.{table} t WHERE {predicate}'),params).all())
        result['rows']['auth_sessions']=dict(c.execute(text("SELECT encode(token_hash,'hex'),to_jsonb(t)-'token_hash'-'csrf_token' FROM public.auth_sessions t WHERE user_id=ANY(:ids)"),params).all())
        result['rows']['auth_throttle_buckets']=dict(c.execute(text(f"SELECT {PK['auth_throttle_buckets']},(to_jsonb(t)-'key_hash')||jsonb_build_object('key',encode(key_hash,'hex')) FROM public.auth_throttle_buckets t")).all())
    return result


def preserved(before,after):
    require(set(before['hashes'])==set(PK)==set(after['hashes']))
    for table in PK:
        require(all(after['hashes'][table].get(k)==v for k,v in before['hashes'][table].items()))


def preflight(s,plan,prepared):
    for table in PK:
        if table not in ('hackathons','auth_throttle_buckets'):require(not s['rows'][table])
    hs=s['rows']['hackathons']
    require(set(hs)==({h['id'] for h in plan['hackathons']} if prepared else set()))
    for h in plan['hackathons']:
        if prepared:
            row=hs[h['id']]
            require(row['name']==h['name'] and row['min_team_size']==2 and row['max_team_size']==3)


def preparation_delta(before,after,plan):
    preserved(before,after);preflight(after,plan,True)
    for table in PK:
        require(set(after['hashes'][table])-set(before['hashes'][table])==({h['id'] for h in plan['hackathons']} if table=='hackathons' else set()))


def prepare(engine,plan):
    """Only two additive hackathon INSERTs, owned transaction, no reuse/reset."""
    with engine.connect() as c:
        before=snapshot(c,plan);preflight(before,plan,False)
        with c.begin():
            for h in plan['hackathons']:
                c.execute(text('INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:id,:name,2,3)'),h)
            for table,key in PK.items():
                current=dict(c.execute(text(f'SELECT {key},md5(to_jsonb(t)::text) FROM public.{table} t')).all())
                require(all(current.get(k)==v for k,v in before['hashes'][table].items()))
                require(set(current)-set(before['hashes'][table])==({h['id'] for h in plan['hackathons']} if table=='hackathons' else set()))
    return before


def verify_final(before,after,plan,ledger,charges):
    """Full fresh scope AND DB-wide prior-row/addition checks; never infer from counts alone."""
    validate_plan(plan);preserved(before,after)
    ids,b=ledger['ids'],ledger['bindings'];rows=after['rows']
    require(set(ids)=={'l','q','r','x'} and len(set(ids.values()))==4)
    require(set(b)=={'a','b','request_q','request_r','issue_q','issue_r'} and len(set(b.values()))==6)
    require(ledger['total']==38)
    require(ledger['denials']==DENIALS)
    expected_status={**{f'register_{r}':[201] for r in ids},**{f'login_{r}':[200,200] if r=='l' else [200] for r in ids},
        'logout_x':[204],**{t:[s] for t,r,s in PROFILE_POSTS},**{t:[s]*n for t,r,n,e,s in COMMANDS},
        'missing_session':[401],'missing_csrf':[403],'foreign_origin':[403]}
    require(ledger['statuses']==expected_status)
    require({r['username']:u for u,r in rows['account_credentials'].items()}=={a['username']:ids[a['role']] for a in plan['accounts']})
    require(set(rows['users'])==set(ids.values()))
    for r in ids:
        p=rows['participant_profiles'][ids[r]]
        require({k:p[k] for k in ('skills','timezone','discoverable')}=={k:v for k,v in plan['profile_values'][r].items() if k!='version'})
        require(p['version']==(2 if r=='l' else 1))
    require(set(rows['participant_profiles'])==set(ids.values()))
    a,other=rows['teams'][b['a']],rows['teams'][b['b']]
    require(set(rows['teams'])=={b['a'],b['b']})
    h1,h2=[h['id'] for h in plan['hackathons']]
    for team,h,name,creator,version in ((a,h1,plan['teams']['a'],ids['l'],13),(other,h2,plan['teams']['b'],ids['q'],1)):
        require(team['hackathon_id']==h and team['name']==name and team['created_by']==creator and team['version']==version)
        require(team['min_team_size']==2 and team['max_team_size']==3)
    require(a['deleted_at'] is not None and a['leader_user_id'] is None)
    require(other['deleted_at'] is None and other['leader_user_id']==ids['q'])
    require([(r['hackathon_id'],r['team_id'],r['user_id']) for r in rows['memberships'].values()]==[(h2,b['b'],ids['q'])])
    require(set(rows['join_requests'])=={b['request_q'],b['request_r']})
    for role,status in (('q','approved'),('r','rejected')):
        r=rows['join_requests'][b['request_'+role]]
        require(r['hackathon_id']==h1 and r['team_id']==b['a'] and r['requester_id']==ids[role] and r['status']==status and r['resolved_at'] is not None)
    require(set(rows['invitations'])=={b['issue_q'],b['issue_r']})
    for role in ('q','r'):
        r=rows['invitations'][b['issue_'+role]]
        require(r['hackathon_id']==h1 and r['team_id']==b['a'] and r['recipient_id']==ids[role] and r['issued_by']==ids['l'] and r['status']=='redeemed')
        created,redeemed,expires=[datetime.fromisoformat(r[k]) for k in ('created_at','redeemed_at','expires_at')]
        require(created<=redeemed<expires and timedelta(0)<expires-created<=timedelta(hours=24))
    sessions=list(rows['auth_sessions'].values())
    require(len(sessions)==5)
    for role,count in (('l',2),('q',1),('r',1),('x',1)):
        found=[r for r in sessions if r['user_id']==ids[role]];require(len(found)==count)
        for r in found:
            require(datetime.fromisoformat(r['expires_at'])-datetime.fromisoformat(r['created_at'])==timedelta(hours=8))
            require((r['revoked_at'] is not None)==(role=='x'))
    records,audits,events=[rows[k] for k in ('idempotency_records','audit_events','outbox_events')]
    require(len(records)==len(audits)==len(events)==14)
    require({a['idempotency_record_id'] for a in audits.values()}==set(records))
    require({e['audit_event_id'] for e in events.values()}==set(audits))
    versions={'create_a':1,'create_b':1,'request_q':2,'request_r':3,'reject_r':4,'approve_q':5,
        'issue_r':6,'redeem_r':7,'remove_r':8,'leave_q':9,'issue_q':10,'redeem_q':11,'leave_l':12,'final_q':13}
    require(set(ledger['calls'])=={c[0] for c in COMMANDS})
    for tag,r,n,e,s in COMMANDS:
        c=ledger['calls'][tag]
        found=[v for v in records.values() if (v['actor_id'],v['operation'],v['key'])==(c['actor'],c['operation'],c['key'])]
        if not e:require(not found and c['reply'] is None);continue
        require(len(found)==1);record=found[0]
        require(record['state']=='completed' and record['completed_at'] is not None and record['request_hash']==c['request_hash'])
        require(record['hackathon_id']==c['hackathon'] and record['response_body']==c['reply'] and record['http_status']==c['status']==s and record['response_headers']==c['headers'])
        audit=next(v for v in audits.values() if v['idempotency_record_id']==record['id'])
        team=b['b' if tag=='create_b' else 'a'];version=versions[tag]
        require(audit['team_id']==team and audit['hackathon_id']==c['hackathon'] and audit['actor_id']==c['actor'] and audit['action']==c['operation'] and audit['team_version']==version)
        state=audit['new_state'];old=audit['old_state'];t=state['team']
        require(state['schema_version']==1 and t['version']==version and t['min_team_size']==2 and t['max_team_size']==3)
        leader=ids['q'] if tag in ('create_b','leave_l') else None if tag=='final_q' else ids['l']
        require(t['leader_user_id']==leader and t.get('deleted',False)==(tag=='final_q'))
        count=t['member_count'];require(0<=count<=3 and t['readiness']==('deleted' if count==0 else 'forming' if count==1 else 'ready'))
        if tag.startswith('create_'):require(old is None and count==1)
        else:
            delta=1 if tag in ('approve_q','redeem_r','redeem_q') else -1 if tag in ('remove_r','leave_q','leave_l','final_q') else 0
            require(old['team']['version']==version-1 and count==old['team']['member_count']+delta)
        data=c['reply']['data']
        subject=c['actor'] if tag.startswith('create_') or tag in ('leave_q','leave_l','final_q') else ids['q' if tag in ('request_q','approve_q','issue_q','redeem_q') else 'r']
        joined=tag.startswith('create_') or tag in ('approve_q','redeem_r','redeem_q')
        leaving=tag in ('remove_r','leave_q','leave_l','final_q')
        require(state['subject']==dict(user_id=subject,member=joined))
        if old is not None:require(old['subject']==dict(user_id=subject,member=leaving))
        require(data['hackathon_id']==c['hackathon'] and data['team_id']==team)
        if tag.startswith(('request_','approve_','reject_')):
            role='q' if tag in ('request_q','approve_q') else 'r';target=b['request_'+role]
            status='pending' if tag.startswith('request_') else 'approved' if tag=='approve_q' else 'rejected'
            require(data['id']==target and data['requester_id']==subject and data['status']==status)
            require(state['request']==dict(id=target,status=status) and old['request']==(None if tag.startswith('request_') else dict(id=target,status='pending')))
        elif tag.startswith(('issue_','redeem_')):
            target=b['issue_q' if tag in ('issue_q','redeem_q') else 'issue_r'];redeemed=tag.startswith('redeem_')
            status='redeemed' if redeemed else 'pending'
            require(data['id']==target and data['recipient_id']==subject and data['issued_by']==ids['l'] and data['status']==status)
            require(state['invitation']==dict(id=target,status=status) and old['invitation']==(dict(id=target,status='pending') if redeemed else None))
        else:
            require(data['user_id']==subject and data['member_count']==count and data['team_version']==version)
            if leaving:require(data['leader_user_id']==leader and data['deleted']==(count==0))
        event=next(v for v in events.values() if v['audit_event_id']==audit['id'])
        require(event['event_type']=='team.changed.v1' and event['schema_version']==1 and event['published_at'] is None and event['attempt_count']==0)
        require(event['payload']==dict(hackathon_id=c['hackathon'],team_id=team,team_version=version))
    for team in (b['a'],b['b']):
        chain=sorted((v for v in audits.values() if v['team_id']==team),key=lambda v:v['team_version'])
        require([v['team_version'] for v in chain]==list(range(1,len(chain)+1)))
        def normalized(t):return dict(t,deleted=t.get('deleted',False))
        for first,second in zip(chain,chain[1:]):require(normalized(first['new_state']['team'])==normalized(second['old_state']['team']))
    # Private HMAC keys can be compared in-memory, never printed/persisted.
    allowances={(v['scope'],v['key']):v['count'] for v in charges};totals={}
    require(sum(allowances.values())==19 and len(allowances)==10)
    for pk in set(after['hashes']['auth_throttle_buckets'])-set(before['hashes']['auth_throttle_buckets']):
        row=rows['auth_throttle_buckets'][pk];pair=(row['scope'],row['key'])
        require(pair in allowances and type(row['attempts']) is int and 1<=row['attempts']<=allowances[pair])
        totals[pair]=totals.get(pair,0)+row['attempts']
    require(totals==allowances)
    for table in PK:
        added=set(after['hashes'][table])-set(before['hashes'][table])
        expected=set(rows[table])-set(before['rows'][table])
        require(added==expected)
    return dict(auth_posts=10,profile_posts=7,security_posts=3,total_posts=38,users=4,credentials=4,sessions=5,
        revoked_sessions=1,profiles=4,hackathons=2,teams=2,memberships=1,requests=2,invitations=2,
        tombstones=1,idempotency=14,audit=14,outbox=14,team_a_version=13,team_b_version=1)


def main():
    code=1;report={'status':'failed','invariants':'not_certified'}
    try:
        require(sys.argv[1:]==['--private-worker'])
        raw=sys.stdin.buffer.read(8_000_001);require(len(raw)<=8_000_000)
        payload=json.loads(raw);password=os.environ.pop('MERGE_INTEGRATED_CHILD_PASSWORD','');require(bool(password))
        plan=validate_plan(payload['plan'])
        with profile_engine(Target('profiles',True,password)) as (engine,_):
            with engine.connect() as c:after=snapshot(c,plan)
        counts=verify_final(payload['before'],after,plan,payload['ledger'],payload['charges'])
        report=dict(status='passed',invariants='fresh_scope_and_prior_rows_verified',totals=counts);code=0
    except BaseException:pass
    print(json.dumps(report));return code


if __name__=='__main__':raise SystemExit(main())
