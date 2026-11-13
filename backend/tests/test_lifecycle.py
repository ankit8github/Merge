"""Offline transaction regressions; these do not establish PostgreSQL race safety."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4
import json

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from app.services.lifecycle import LifecycleService, LifecycleError
from app.services.errors import ErrorCode
from test_team_mutations import Connection as BaseConnection, InjectedFailure


def result(v):
    return SimpleNamespace(scalar_one_or_none=lambda:v, one_or_none=lambda:v,
        mappings=lambda:SimpleNamespace(one_or_none=lambda:v))


class Connection(BaseConnection):
    def __init__(self):
        super().__init__()
        self.sql = []

    def execute(self, statement, p):
        q = str(statement)
        statement.compile(dialect=postgresql.dialect()).construct_params(p)
        self.sql.append((q, dict(p)))
        d = self.data
        if q=='SET TRANSACTION READ ONLY': return result(None)
        if 'AS allowed' in q:
            team=d['teams'].get(p['team']); rows=[m for m in d['members'] if m['team']==p['team']]
            selected=sorted((m for m in rows if p['cursor'] is None or m['actor']>p['cursor']),key=lambda m:m['actor'])[:p['size']]
            return result(None if team is None or team['deleted_at'] is not None else dict(
                allowed=any(m['actor']==p['actor'] for m in rows),
                cursor_ok=p['cursor'] is None or any(m['actor']==p['cursor'] for m in rows),
                items=[dict(user_id=str(m['actor']),display_name='Member',joined_at='2026-11-13T00:00:00Z') for m in selected]))
        if q.startswith('SELECT id,leader_user_id,deleted_at,min_team_size'):
            self.events.append('team-no-key-update')
            return result(deepcopy(d['teams'].get(p['team'])))
        if 'SELECT user_id FROM public.memberships' in q:
            rows = [m for m in d['members'] if m['team']==p['team']]
            if 'subject' in p: return result(next((m['actor'] for m in rows if m['actor']==p['subject']),None))
            rows.sort(key=lambda m:(m.get('joined_at',0),m['actor']))
            return result(rows[0]['actor'] if rows else None)
        if 'DELETE FROM public.memberships' in q:
            found = next((m for m in d['members'] if m['team']==p['team'] and m['actor']==p['subject']),None)
            if found: d['members'].remove(found)
            if self.fail_after=='departure': raise InjectedFailure('departure')
            return result(None if found is None else found['actor'])
        if 'SET leader_user_id=:leader' in q:
            row = d['teams'][p['team']]
            if row['version']==2**63-1: return result(None)
            row.update(version=row['version']+1,leader_user_id=p['leader'],
                deleted_at=datetime.now(timezone.utc) if p['deleted'] else None)
            if self.fail_after=='lifecycle-version': raise InjectedFailure('lifecycle-version')
            return result(deepcopy(row))
        return super().execute(statement,p)


@pytest.fixture
def db():
    c = Connection(); engine = MagicMock(spec=Engine)
    engine.connect.return_value.__enter__.return_value = c
    service = LifecycleService(engine); h, leader = uuid4(), uuid4()
    reply = service.create_team_idempotent(hackathon_id=h,actor_id=leader,name='Lifecycle',key='create')
    team = UUID(reply.body()['data']['team_id'])
    return SimpleNamespace(c=c,service=service,h=h,leader=leader,team=team)


def join(d, user):
    d.service.join_team_idempotent(hackathon_id=d.h,team_id=d.team,actor_id=user,key=str(user))


def leave(d, actor=None, key='leave'):
    return d.service.leave(hackathon_id=d.h,team_id=d.team,actor_id=actor or d.leader,key=key)


def remove(d, user, actor=None, key='remove'):
    return d.service.remove(hackathon_id=d.h,team_id=d.team,actor_id=actor or d.leader,user_id=user,key=key)


def test_final_leave_tombstone_audit_and_immutable_replay(db):
    d=db; reply=leave(d); row=reply.body()['data']
    assert row['deleted'] and row['leader_user_id'] is None and row['member_count']==0
    assert d.c.data['members']==[] and d.c.data['teams'][d.team]['deleted_at'] is not None
    before=json.loads(d.c.data['audits'][-1]['before']); after=json.loads(d.c.data['audits'][-1]['after'])
    assert before['subject']['member'] and before['team']['leader_user_id']==str(d.leader)
    assert not after['subject']['member'] and after['team']['readiness']=='deleted'
    saved=deepcopy(d.c.data)
    assert leave(d).body()==reply.body() and d.c.data==saved
    assert len(d.c.data['audits'])==len(d.c.data['outbox'])==2


def test_successor_is_oldest_then_uuid_without_late_user_lock(db):
    d=db; users=[UUID(int=3),UUID(int=2)]; [join(d,u) for u in users]
    for m in d.c.data['members']: m['joined_at']=0 if m['actor']==d.leader else 1
    d.c.sql.clear()
    assert leave(d).body()['data']['leader_user_id']==str(UUID(int=2))
    statements=[q for q,_ in d.c.sql]
    team_lock=next(i for i,q in enumerate(statements) if 'FROM public.teams' in q and 'FOR NO KEY UPDATE' in q)
    assert not any('FROM public.users' in q for q in statements[team_lock+1:])
    assert any('ORDER BY joined_at,user_id LIMIT 1' in q and 'FOR UPDATE' not in q for q in statements)


def test_regular_member_leave_preserves_leader_and_forming_state(db):
    d=db; u=uuid4(); join(d,u)
    row=leave(d,u).body()['data']
    assert row['leader_user_id']==str(d.leader) and row['member_count']==1 and not row['deleted']
    assert json.loads(d.c.data['audits'][-1]['after'])['team']['readiness']=='forming'


def test_removal_replay_and_sorted_affected_user_locks(db):
    d=db; u=uuid4(); join(d,u); d.c.sql.clear()
    reply=remove(d,u); saved=deepcopy(d.c.data)
    assert remove(d,u).body()==reply.body() and d.c.data==saved
    users=[p['actor'] for q,p in d.c.sql if 'FROM public.users' in q]
    assert users==sorted([d.leader,u])*2


def test_former_leader_cannot_replay_successful_removal(db):
    d=db; u,v=uuid4(),uuid4(); join(d,u); join(d,v); remove(d,u)
    leave(d); saved=deepcopy(d.c.data)
    with pytest.raises(LifecycleError) as error: remove(d,u)
    assert error.value.code==ErrorCode.FORBIDDEN and d.c.data==saved


@pytest.mark.parametrize('kind',['outsider','self','missing-member','wrong-team','mismatch'])
def test_rejections_have_no_effect(db,kind):
    d=db; u=uuid4(); join(d,u)
    if kind=='mismatch': remove(d,u)
    saved=deepcopy(d.c.data)
    with pytest.raises(LifecycleError) as error:
        if kind=='outsider': remove(d,u,actor=uuid4())
        elif kind=='self': remove(d,d.leader)
        elif kind=='missing-member': leave(d,uuid4())
        elif kind=='wrong-team': d.service.leave(hackathon_id=d.h,team_id=uuid4(),actor_id=d.leader,key='leave')
        else: remove(d,uuid4())
    expected={'outsider':ErrorCode.FORBIDDEN,'self':ErrorCode.USE_LEAVE,'missing-member':ErrorCode.MEMBER_NOT_FOUND,
        'wrong-team':ErrorCode.TEAM_NOT_FOUND,'mismatch':ErrorCode.IDEMPOTENCY_MISMATCH}
    assert error.value.code==expected[kind] and d.c.data==saved


@pytest.mark.parametrize('stage',['reservation','departure','lifecycle-version','audit','outbox','completion','commit'])
def test_every_write_and_deferred_commit_failure_rolls_back(db,stage):
    d=db; saved=deepcopy(d.c.data)
    d.c.fail_after=stage; d.c.fail_commit=stage=='commit'
    with pytest.raises((InjectedFailure,LifecycleError)): leave(d)
    assert d.c.data==saved and not d.c.in_transaction()


def test_leave_replay_never_deletes_a_new_membership(db):
    d=db; leave(d)
    other=d.service.create_team_idempotent(hackathon_id=d.h,actor_id=d.leader,name='New',key='new')
    saved=deepcopy(d.c.data); leave(d)
    assert d.c.data==saved and other.body()['data']['team_id']!=str(d.team)


def test_version_overflow_rolls_back_departure(db):
    d=db; d.c.data['teams'][d.team]['version']=2**63-1; saved=deepcopy(d.c.data)
    with pytest.raises(LifecycleError): leave(d)
    assert d.c.data==saved


def test_successor_prefers_join_time_before_uuid(db):
    d=db; older,newer=UUID(int=9),UUID(int=1); join(d,older); join(d,newer)
    for m in d.c.data['members']: m['joined_at']=1 if m['actor']==older else 2
    assert leave(d).body()['data']['leader_user_id']==str(older)


def test_roster_is_private_bounded_and_read_only(db):
    d=db; u=uuid4(); join(d,u); saved=deepcopy(d.c.data)
    page=d.service.members(hackathon_id=d.h,team_id=d.team,actor_id=u,limit=1)
    assert len(page['items'])==1 and page['next_cursor']==page['items'][-1]['user_id']
    assert d.c.data==saved
    for actor,cursor,code in [(uuid4(),None,ErrorCode.FORBIDDEN),(u,uuid4(),ErrorCode.INVALID_INPUT)]:
        with pytest.raises(LifecycleError) as error:
            d.service.members(hackathon_id=d.h,team_id=d.team,actor_id=actor,cursor=cursor)
        assert error.value.code==code
    assert d.c.data==saved


@pytest.mark.parametrize('removing',[False,True])
def test_lost_commit_ack_reconciles_same_lifecycle_receipt(db,monkeypatch,removing):
    d=db; u=uuid4(); join(d,u)
    original=d.service._execute; calls=[]
    def execute(operation,*,_attempt=None):
        reply=original(operation,_attempt=_attempt); calls.append(reply)
        if len(calls)==1:
            _attempt.confirmed_reply=None; _attempt.phase='commit'; _attempt.ambiguous=True
            _attempt.confirmed_failure=False
            raise OSError('synthetic-lost-ack')
        return reply
    monkeypatch.setattr(d.service,'_execute',execute)
    reply=remove(d,u) if removing else leave(d)
    assert reply.body()==calls[0].body() and len(calls)==2
    assert len(d.c.data['audits'])==3


def test_unknown_remove_commit_cannot_reconcile_after_losing_leadership(db,monkeypatch):
    d=db; u,v=uuid4(),uuid4(); join(d,u); join(d,v)
    original=d.service._execute; first=True
    def execute(operation,*,_attempt=None):
        nonlocal first
        reply=original(operation,_attempt=_attempt)
        if first:
            first=False
            leave(d,key='leader-departure')
            _attempt.confirmed_reply=None; _attempt.phase='commit'; _attempt.ambiguous=True
            _attempt.confirmed_failure=False
            raise OSError('synthetic-lost-ack')
        return reply
    monkeypatch.setattr(d.service,'_execute',execute)
    with pytest.raises(LifecycleError) as error: remove(d,u)
    assert error.value.code==ErrorCode.OUTCOME_UNCERTAIN
    assert len(d.c.data['audits'])==5 and d.c.data['teams'][d.team]['leader_user_id']==v
