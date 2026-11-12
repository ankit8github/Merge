"""Read-only fingerprints and exact scoped journey checks. Never print snapshots."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import text

from app.services.errors import ErrorCode
from test_support.database import DiagnosticFailure
from test_support.browser_full_scope import ROLES, SUCCESS

# SQL identifiers are fixed source constants, never manifest input.
PK = {'users':'id::text', 'hackathons':'id::text', 'teams':'id::text',
      'memberships':"hackathon_id::text||'|'||user_id::text", 'idempotency_records':'id::text',
      'audit_events':'id::text', 'outbox_events':'id::text', 'account_credentials':'user_id::text',
      'auth_sessions':"encode(token_hash,'hex')",
      'auth_throttle_buckets':"scope||'|'||encode(key_hash,'hex')||'|'||window_start::text",
      'join_requests':'id::text', 'invitations':'id::text'}


def require(value):
    if not value:
        raise DiagnosticFailure('verification')


@dataclass(repr=False)
class FullSnapshot:
    hashes: dict = field(default_factory=dict, repr=False)
    rows: dict = field(default_factory=dict, repr=False)


def snapshot(c, scope):
    c.execute(text('SET TRANSACTION READ ONLY'))
    result = FullSnapshot()
    for table, key in PK.items():
        result.hashes[table] = dict(c.execute(text(
            f'SELECT {key},md5(to_jsonb(t)::text) FROM public.{table} t')).all())
    params = {'names':[a.username for a in scope.accounts], 'hs':[h.id for h in scope.hackathons]}
    credentials = c.execute(text('''SELECT user_id::text AS user_id,username,
        created_at::text AS created_at,updated_at::text AS updated_at
        FROM public.account_credentials WHERE username=ANY(:names)'''), params).mappings().all()
    result.rows['account_credentials'] = {r['user_id']:dict(r) for r in credentials}
    params['users'] = [UUID(r['user_id']) for r in credentials]
    predicates = {'users':'id=ANY(:users)', 'hackathons':'id=ANY(:hs)',
        **{t:'hackathon_id=ANY(:hs)' for t in ('teams','memberships','idempotency_records','audit_events','join_requests','invitations')},
        'outbox_events':"audit_event_id IN (SELECT id FROM public.audit_events WHERE hackathon_id=ANY(:hs))"}
    for table, where in predicates.items():
        row = "to_jsonb(t) || jsonb_build_object('request_hash',encode(request_hash,'hex'))" if table=='idempotency_records' else 'to_jsonb(t)'
        result.rows[table] = dict(c.execute(text(
            f'SELECT {PK[table]},{row} FROM public.{table} t WHERE {where}'), params).all())
    result.rows['auth_sessions'] = dict(c.execute(text('''SELECT encode(token_hash,'hex'),
        (to_jsonb(s)-'token_hash'-'csrf_token') || jsonb_build_object('immutable',md5((to_jsonb(s)-'revoked_at')::text))
        FROM public.auth_sessions s WHERE user_id=ANY(:users)'''), params).all())
    # Only digests, no raw session/CSRF/credential secret is selected.
    result.rows['auth_throttle_buckets'] = dict(c.execute(text(f'''SELECT {PK['auth_throttle_buckets']},
        (to_jsonb(t)-'key_hash') || jsonb_build_object('key',encode(key_hash,'hex'))
        FROM public.auth_throttle_buckets t''')).all())
    c.rollback()
    validate(result, scope)
    return result


def validate(s, scope):
    at = lambda v: datetime.fromisoformat(v)
    hs = {str(h.id) for h in scope.hackathons}
    teams = s.rows['teams']; members = list(s.rows['memberships'].values())
    require(len({(m['hackathon_id'],m['user_id']) for m in members}) == len(members))
    for t in teams.values():
        roster = [m for m in members if m['team_id']==t['id']]
        require(t['hackathon_id'] in hs and t['deleted_at'] is None
                and t['min_team_size']==2 and t['max_team_size']==3
                and 1 <= len(roster) <= 3 and t['leader_user_id'] in {m['user_id'] for m in roster})
    for m in members:
        require(m['team_id'] in teams and teams[m['team_id']]['hackathon_id']==m['hackathon_id'])
    for r in s.rows['join_requests'].values():
        require((r['status']=='pending') == (r['resolved_at'] is None)
                and r['status'] in ('pending','approved','rejected'))
        if r['status']=='approved':
            require(any(m['team_id']==r['team_id'] and m['user_id']==r['requester_id'] for m in members))
    for r in s.rows['invitations'].values():
        require((r['status']=='pending') == (r['redeemed_at'] is None)
                and r['status'] in ('pending','redeemed')
                and timedelta(0)<at(r['expires_at'])-at(r['created_at'])<=timedelta(hours=24))
        if r['status']=='redeemed':
            require(at(r['created_at'])<=at(r['redeemed_at'])<at(r['expires_at']))
            require(any(m['team_id']==r['team_id'] and m['user_id']==r['recipient_id'] for m in members))
    for r in s.rows['auth_sessions'].values():
        require(at(r['expires_at'])-at(r['created_at'])==timedelta(hours=8)
                and (r['revoked_at'] is None or at(r['revoked_at'])>=at(r['created_at'])))


def preflight(s, scope, *, prepared):
    # Fresh scopes only. An interrupted run is retained, never silently adopted.
    require(not s.rows['account_credentials'])
    for table in ('users','teams','memberships','join_requests','invitations','idempotency_records','audit_events','outbox_events','auth_sessions'):
        require(not s.rows[table])
    if prepared:
        require(set(s.rows['hackathons'])=={str(h.id) for h in scope.hackathons})
        for h in scope.hackathons:
            row = s.rows['hackathons'][str(h.id)]
            require(row['name']==h.name and row['min_team_size']==2 and row['max_team_size']==3)
    else:
        require(not s.rows['hackathons'])


def preserved(before, after):
    for table in PK:
        require(all(after.hashes[table].get(k)==v for k,v in before.hashes[table].items()))


def certify(before, after, ledger, throttle):
    """Nine exact successful commands plus one real full conflict; no prior row changes."""
    scope = ledger.scope
    validate(after,scope)
    preserved(before, after)
    require(not ledger.failed and set(ledger.ids)==set(ROLES))
    require(all(tag in ledger.calls and ledger.calls[tag].reply is not None for tag in SUCCESS))
    require('redeem_x' in ledger.calls and ledger.calls['redeem_x'].error==ErrorCode.TEAM_FULL)
    rows = after.rows
    ids = {r:str(u) for r,u in ledger.ids.items()}
    require({r['username']:u for u,r in rows['account_credentials'].items()}==
            {a.username:ids[a.role] for a in scope.accounts})
    require(set(rows['users'])==set(ids.values()))
    a,b = str(ledger.bindings['a']),str(ledger.bindings['b'])
    h = str(scope.hackathons[0].id)
    require(set(rows['teams'])=={a,b})
    for t,role,version,name in ((a,'l',8,scope.team_a),(b,'x',1,scope.team_b)):
        row = rows['teams'][t]
        require(row['hackathon_id']==h and row['name']==name and row['created_by']==ids[role]
                and row['leader_user_id']==ids[role] and row['version']==version)
    require({(m['hackathon_id'],m['team_id'],m['user_id']) for m in rows['memberships'].values()}==
            {(h,a,ids[r]) for r in ('l','q','r')}|{(h,b,ids['x'])})
    require(len(rows['join_requests'])==len(rows['invitations'])==2)
    for role,status in (('q','approved'),('r','rejected')):
        row = rows['join_requests'][str(ledger.bindings['request_'+role])]
        require(row['requester_id']==ids[role] and row['team_id']==a and row['status']==status)
    for role,status in (('r','redeemed'),('x','pending')):
        row = rows['invitations'][str(ledger.bindings['issue_'+role])]
        require(row['recipient_id']==ids[role] and row['issued_by']==ids['l'] and row['team_id']==a and row['status']==status)
    records, audits, events = (rows[t] for t in ('idempotency_records','audit_events','outbox_events'))
    require(len(records)==len(audits)==len(events)==9)
    require({x['idempotency_record_id'] for x in audits.values()}==set(records))
    require({x['audit_event_id'] for x in events.values()}==set(audits))
    require({x['team_version'] for x in audits.values() if x['team_id']==a}==set(range(1,9)))
    require([x['team_version'] for x in audits.values() if x['team_id']==b]==[1])
    for team in (a,b):
        history=sorted((x for x in audits.values() if x['team_id']==team),key=lambda x:x['team_version'])
        for previous,current in zip(history,history[1:]):
            require(previous['new_state']['team']==current['old_state']['team'])
        require(history[-1]['new_state']['team']['member_count']==sum(m['team_id']==team for m in rows['memberships'].values()))
    for tag in SUCCESS:
        call = ledger.calls[tag]; fp = call.fingerprint
        found = [r for r in records.values() if r['actor_id']==str(fp.actor_id) and r['operation']==fp.operation and r['key']==fp.key]
        require(len(found)==1)
        r = found[0]
        require(r['hackathon_id']==h and r['state']=='completed' and r['completed_at'] is not None
                and r['request_hash']==fp.fingerprint.digest.hex()
                and r['http_status']==call.reply.http_status and r['response_body']==call.reply.body()
                and r['response_headers']==dict(call.reply.headers))
        data=r['response_body']['data']
        require(data['hackathon_id']==h and data['team_id']==(b if tag=='create_b' else a))
        if tag.startswith('create_'):
            require(data['user_id']==r['actor_id'] and data['member_count']==data['team_version']==1)
        elif tag.startswith(('request_','approve_','reject_')):
            role='q' if tag in ('request_q','approve_q') else 'r'
            require(data['id']==str(ledger.bindings['request_'+role]) and data['requester_id']==ids[role]
                    and data['status']==('approved' if tag=='approve_q' else 'rejected' if tag=='reject_r' else 'pending'))
        else:
            role='x' if tag=='issue_x' else 'r'
            require(data['id']==str(ledger.bindings['issue_'+role]) and data['recipient_id']==ids[role]
                    and data['issued_by']==ids['l'] and data['status']==('redeemed' if tag=='redeem_r' else 'pending'))
        audit = next(x for x in audits.values() if x['idempotency_record_id']==r['id'])
        team = b if tag=='create_b' else a
        require(audit['actor_id']==r['actor_id'] and audit['action']==r['operation'] and audit['hackathon_id']==h and audit['team_id']==team)
        state=audit['new_state']; previous=audit['old_state']; version=audit['team_version']
        require(state['schema_version']==1 and state['team']['version']==version
                and state['team']['leader_user_id']==ids['x' if team==b else 'l']
                and state['team']['min_team_size']==2 and state['team']['max_team_size']==3
                and 1<=state['team']['member_count']<=3)
        require(state['team']['readiness']==('ready' if state['team']['member_count']>=2 else 'forming'))
        if tag.startswith('create_'):
            require(previous is None and version==1 and state['team']['member_count']==1
                    and state['subject']=={'user_id':r['actor_id'],'member':True})
        else:
            require(previous['team']['version']==version-1)
            admitted=tag in ('approve_q','redeem_r')
            require(state['team']['member_count']==previous['team']['member_count']+int(admitted))
            if tag.startswith(('request_','approve_','reject_')):
                target=str(ledger.bindings['request_q' if tag in ('request_q','approve_q') else 'request_r'])
                wanted='approved' if tag=='approve_q' else 'rejected' if tag=='reject_r' else 'pending'
                require(state['request']=={'id':target,'status':wanted}
                        and previous['request']==(None if tag.startswith('request_') else {'id':target,'status':'pending'}))
            else:
                target=str(ledger.bindings['issue_r' if tag in ('issue_r','redeem_r') else 'issue_x'])
                require(state['invitation']=={'id':target,'status':'redeemed' if admitted else 'pending'}
                        and previous['invitation']==({'id':target,'status':'pending'} if admitted else None))
            subject=ids['q' if tag in ('request_q','approve_q') else 'x' if tag=='issue_x' else 'r']
            require(state['subject']=={'user_id':subject,'member':admitted}
                    and previous['subject']=={'user_id':subject,'member':False})
        event = next(x for x in events.values() if x['audit_event_id']==audit['id'])
        require(event['event_type']=='team.changed.v1' and event['schema_version']==1
                and event['published_at'] is None and event['attempt_count']==0
                and event['payload']=={'hackathon_id':h,'team_id':audit['team_id'],'team_version':audit['team_version']})
    # Every added global row must be accounted for by scoped rows; unrelated rows
    # cannot hide behind legitimate counts. Old rows (even run's hackathons) immutable.
    allowed_buckets = {('auth:v1:register_ip', throttle._key('register_ip','127.0.0.1').hex()):sum(ledger.used.get((r,'register'),0) for r in ROLES),
        ('auth:v1:login_ip', throttle._key('login_ip','127.0.0.1').hex()):sum(ledger.used.get((r,'login'),0) for r in ROLES)}
    for role,account in ledger.accounts.items():
        allowed_buckets[('auth:v1:login_account',throttle._key('login_account',account.username).hex())] = ledger.used.get((role,'login'),0)
        for op in ('issue','redeem'):
            # Real check_invitation uses this domain-separated identity.
            allowed_buckets[('auth:v1:invitation_'+op,throttle._key('invitation_'+op,ids[role]).hex())] = ledger.used.get((role,'invitation_'+op),0)
    totals = {}
    new_buckets = set(after.hashes['auth_throttle_buckets'])-set(before.hashes['auth_throttle_buckets'])
    for pk in new_buckets:
        r = rows['auth_throttle_buckets'][pk]; pair = (r['scope'],r['key'])
        require(pair in allowed_buckets and 1 <= r['attempts'] <= allowed_buckets[pair])
        totals[pair] = totals.get(pair,0)+r['attempts']
    require(all(count<=allowed_buckets[pair] for pair,count in totals.items()))
    def charged(op,identifier): return totals.get(('auth:v1:'+op,throttle._key(op,identifier).hex()),0)
    require(charged('register_ip','127.0.0.1')==4)
    require(charged('invitation_issue',ids['l'])>=2 and charged('invitation_redeem',ids['r'])>=1
            and charged('invitation_redeem',ids['x'])>=1)
    for role in ROLES:
        sessions = [r for r in rows['auth_sessions'].values() if r['user_id']==ids[role]]
        require(len(sessions)<=ledger.used.get((role,'login'),0)
                and sum(r['revoked_at'] is not None for r in sessions)<=ledger.used.get((role,'logout'),0)
                and charged('login_account',ledger.accounts[role].username)>=len(sessions)
                and ledger.used.get((role,'register'),0)==1)
    require(charged('login_ip','127.0.0.1')>=len(rows['auth_sessions']))
    for table in PK:
        added = set(after.hashes[table])-set(before.hashes[table])
        expected = new_buckets if table=='auth_throttle_buckets' else set(rows[table])-set(before.rows[table])
        require(added==expected)
