"""Offline invitation ownership/atomicity/security regressions, never race proof."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4
from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.dialects import postgresql

from app.services.invitations import InvitationService, InvitationError, command
from app.services.errors import DomainError, ErrorCode
from test_admission import Connection as Parent, result
from test_team_mutations import InjectedFailure
from test_transaction_retry import database_error


class Connection(Parent):
    def __init__(self):
        super().__init__()
        self.data['invitations'] = {}
        self.now = datetime.now(timezone.utc)

    def execute(self, statement, p):
        q = str(statement)
        statement.compile(dialect=postgresql.dialect()).construct_params(p)
        if 'public.invitations' in q:
            self.sql.append((q,dict(p)))
            rows = self.data['invitations']
            if 'INSERT INTO public.invitations' in q:
                row = dict(id=p['id'],hackathon_id=p['h'],team_id=p['team'],recipient_id=p['recipient'],
                    issued_by=p['actor'],status='pending',created_at=self.now,expires_at=self.now+timedelta(hours=24),redeemed_at=None)
                rows[row['id']]=row
            elif 'UPDATE public.invitations' in q:
                row = rows[p['id']]; row.update(status='redeemed',redeemed_at=p['at'])
            elif 'SELECT CAST(:cursor' in q:
                return result(p['cursor'] is None or any(r['id']==p['cursor'] and r['hackathon_id']==p['h'] and r['recipient_id']==p['actor'] for r in rows.values()))
            elif 'JOIN public.teams' in q:
                selected = sorted((r for r in rows.values() if r['hackathon_id']==p['h'] and r['recipient_id']==p['actor'] and (p['cursor'] is None or r['id']>p['cursor'])),key=lambda r:r['id'])[:p['size']]
                data=[dict(r,available=r['status']=='pending' and r['expires_at']>self.now and self.data['teams'][r['team_id']]['leader_user_id']==r['issued_by']) for r in selected]
                return SimpleNamespace(mappings=lambda:SimpleNamespace(all=lambda:data))
            else:
                row = rows.get(p['id'])
                if row and (row['team_id']!=p['team'] or row['hackathon_id']!=p['h'] or row['recipient_id']!=p['actor']): row=None
                if 'SELECT recipient_id' in q: return result(None if row is None else row['recipient_id'])
                if 'FOR NO KEY UPDATE' in q: self.events.append('invitation-lock')
                return result(None if row is None else dict(row))
            self.events.append('invitation-write')
            if self.fail_after=='invitation': raise InjectedFailure('invitation')
            return result(dict(row))
        if q=='SELECT clock_timestamp()':
            self.sql.append((q,dict(p))); return result(self.now)
        return super().execute(statement,p)


@pytest.fixture
def db():
    c=Connection(); engine=MagicMock(spec=Engine)
    engine.connect.return_value.__enter__.return_value=c
    service=InvitationService(engine)
    h,leader,user=uuid4(),uuid4(),uuid4()
    service.create_team_idempotent(hackathon_id=h,actor_id=leader,name='Invitation fixture',key='founder')
    return SimpleNamespace(c=c,service=service,h=h,team=next(iter(c.data['teams'])),leader=leader,user=user)


def issue(d,**changes):
    return d.service.issue(**(dict(hackathon_id=d.h,team_id=d.team,actor_id=d.leader,recipient_id=d.user,key='issue')|changes))


def redeem(d,**changes):
    return d.service.redeem(**(dict(hackathon_id=d.h,team_id=d.team,actor_id=d.user,
        invitation_id=next(iter(d.c.data['invitations'])),key='redeem')|changes))


def test_issue_redeem_exact_replays_and_atomic_linked_chain(db):
    first=issue(db); before=deepcopy(db.c.data)
    assert first.http_status==201 and issue(db)==first and db.c.data==before
    reply=redeem(db); saved=deepcopy(db.c.data)
    assert reply.http_status==200 and reply.body()['data']['status']=='redeemed'
    assert redeem(db)==reply and db.c.data==saved
    assert len(saved['members'])==2
    assert len(saved['reservations'])==len(saved['audits'])==len(saved['outbox'])==3
    audit=saved['audits'][-1]
    assert audit['actor']==db.user and audit['action']=='invitation.redeem.v1'
    assert json.loads(audit['before'])['invitation']['status']=='pending'
    assert json.loads(audit['after'])['subject']=={'user_id':str(db.user),'member':True}


@pytest.mark.parametrize(('phase','fault'),[(phase,fault) for phase in ('issue','redeem')
    for fault in ('reservation','invitation','membership','version','audit','outbox','completion','commit')
    if phase=='redeem' or fault!='membership'])
def test_every_fault_rolls_back_complete_chain(db,phase,fault):
    if phase=='redeem': issue(db)
    saved=deepcopy(db.c.data)
    db.c.fail_after=None if fault=='commit' else fault; db.c.fail_commit=fault=='commit'
    with pytest.raises((InjectedFailure,DomainError)):
        issue(db) if phase=='issue' else redeem(db)
    assert db.c.data==saved


@pytest.mark.parametrize('kind',['recipient','scope','missing','full','assigned','expired','stale','used'])
def test_invalid_redemption_never_consumes_or_writes(db,kind):
    issue(db); changes={}
    if kind=='recipient': changes['actor_id']=uuid4()
    if kind=='scope': changes['hackathon_id']=uuid4()
    if kind=='missing': changes['invitation_id']=uuid4()
    if kind=='full': db.c.data['teams'][db.team]['max_team_size']=1
    if kind=='assigned': db.c.data['members'].append(dict(hackathon=db.h,team=uuid4(),actor=db.user))
    if kind=='expired': db.c.now+=timedelta(hours=24)
    if kind=='stale': db.c.data['teams'][db.team]['leader_user_id']=uuid4()
    if kind=='used': redeem(db); changes['key']='other'
    saved=deepcopy(db.c.data)
    expected={'recipient':ErrorCode.INVITATION_NOT_FOUND,'scope':ErrorCode.INVITATION_NOT_FOUND,
        'missing':ErrorCode.INVITATION_NOT_FOUND,'full':ErrorCode.TEAM_FULL,'assigned':ErrorCode.ALREADY_ASSIGNED,
        'expired':ErrorCode.INVITATION_EXPIRED,'stale':ErrorCode.INVITATION_STALE,'used':ErrorCode.INVITATION_REDEEMED}[kind]
    with pytest.raises(InvitationError) as error: redeem(db,**changes)
    assert error.value.code==expected and db.c.data==saved


@pytest.mark.parametrize('operation',['issue','redeem'])
@pytest.mark.parametrize('kind',['leader','expired'])
def test_current_authorization_precedes_replay(db,operation,kind):
    issue(db)
    if operation=='redeem': redeem(db)
    if kind=='leader': db.c.data['teams'][db.team]['leader_user_id']=uuid4()
    else: db.c.now+=timedelta(days=1)
    if operation=='issue' and kind=='expired':
        assert issue(db).http_status==201  # Leader may inspect historical issue acknowledgement.
        return
    saved=deepcopy(db.c.data)
    with pytest.raises(InvitationError) as error: issue(db) if operation=='issue' else redeem(db)
    assert error.value.code==(ErrorCode.FORBIDDEN if operation=='issue' else
        ErrorCode.INVITATION_STALE if kind=='leader' else ErrorCode.INVITATION_EXPIRED)
    assert db.c.data==saved
    if operation=='redeem':
        assert next(iter(saved['invitations'].values()))['status']=='redeemed'
        assert len(saved['members'])==2 and len(saved['audits'])==len(saved['outbox'])==3


@pytest.mark.parametrize('redeemed',[False,True])
def test_leadership_policy_uses_current_issuer_not_permanent_revocation(db,redeemed):
    issue(db)
    if redeemed: original=redeem(db)
    db.c.data['teams'][db.team]['leader_user_id']=uuid4()
    saved=deepcopy(db.c.data)
    with pytest.raises(InvitationError) as error: redeem(db)
    assert error.value.code==ErrorCode.INVITATION_STALE and db.c.data==saved
    db.c.data['teams'][db.team]['leader_user_id']=db.leader
    reply=redeem(db)
    if redeemed: assert reply==original
    assert reply.http_status==200 and len(db.c.data['members'])==2
    assert len(db.c.data['audits'])==len(db.c.data['outbox'])==3


def test_expiry_during_ambiguous_commit_reconciliation_does_not_grant_replay_proof(db):
    issue(db); original=db.c.begin; fired=False
    @contextmanager
    def begin():
        nonlocal fired
        with original(): yield
        if not fired:
            fired=True; db.c.now+=timedelta(days=1)
            raise database_error(None)
    db.c.begin=begin
    with pytest.raises(InvitationError) as error: redeem(db)
    assert error.value.code==ErrorCode.OUTCOME_UNCERTAIN and error.value.retryable
    assert len(db.c.data['members'])==2 and len(db.c.data['audits'])==3
    saved=deepcopy(db.c.data)
    with pytest.raises(InvitationError) as error: redeem(db)
    assert error.value.code==ErrorCode.INVITATION_EXPIRED and db.c.data==saved


def test_changed_command_reuse_and_cross_recipient_replay(db):
    issue(db)
    with pytest.raises(InvitationError) as error: issue(db,recipient_id=uuid4())
    assert error.value.code==ErrorCode.IDEMPOTENCY_MISMATCH
    redeem(db)
    with pytest.raises(InvitationError) as error: redeem(db,actor_id=uuid4())
    assert error.value.code==ErrorCode.INVITATION_NOT_FOUND


@pytest.mark.parametrize('authorized',[True,False])
def test_missing_recipient_is_disclosed_only_after_locked_leader_check(db,monkeypatch,authorized):
    original=db.c.execute
    def execute(statement,parameters):
        if 'FROM public.users' in str(statement) and parameters['actor']==db.user: return result(None)
        return original(statement,parameters)
    monkeypatch.setattr(db.c,'execute',execute)
    saved=deepcopy(db.c.data)
    with pytest.raises(InvitationError) as error: issue(db,actor_id=db.leader if authorized else uuid4())
    assert error.value.code==(ErrorCode.USER_NOT_FOUND if authorized else ErrorCode.FORBIDDEN)
    assert db.c.data==saved


def test_unavailable_same_key_reconciliation_keeps_committed_invitation_unambiguous_in_storage(db):
    issue(db); original=db.c.begin; engine=db.service._engine
    @contextmanager
    def begin():
        with original(): yield
        engine.connect.side_effect=database_error('08006')
        raise database_error(None)
    db.c.begin=begin
    with pytest.raises(InvitationError) as error: redeem(db)
    assert error.value.code==ErrorCode.OUTCOME_UNCERTAIN and error.value.retryable
    assert len(db.c.data['members'])==2 and len(db.c.data['audits'])==3
    assert next(iter(db.c.data['invitations'].values()))['status']=='redeemed'


def test_sorted_issue_and_recipient_only_redemption_lock_order(db):
    start=len(db.c.sql); issue(db); issuing=db.c.sql[start:]
    users=[p['actor'] for q,p in issuing if 'FROM public.users' in q]
    assert users==sorted([db.user,db.leader])
    start=len(db.c.sql); redeem(db); queries=db.c.sql[start:]
    assert [p['actor'] for q,p in queries if 'FROM public.users' in q]==[db.user]
    team=next(i for i,(q,_) in enumerate(queries) if 'FROM public.teams' in q and 'FOR NO KEY UPDATE' in q)
    invitation=next(i for i,(q,_) in enumerate(queries) if 'FROM public.invitations' in q and 'FOR NO KEY UPDATE' in q)
    assert max(i for i,(q,_) in enumerate(queries) if 'FROM public.users' in q)<team<invitation


def test_private_inbox_and_scoped_cursor_are_canonical_reads(db):
    issue(db); invitation=next(iter(db.c.data['invitations']))
    mine=lambda actor,cursor=None:db.service.mine(hackathon_id=db.h,actor_id=actor,cursor=cursor)
    assert mine(db.leader)==dict(items=[],next_cursor=None)
    assert mine(db.user)['items'][0]['available'] is True
    with pytest.raises(InvitationError): mine(db.leader,invitation)
    db.c.now+=timedelta(hours=24)
    assert mine(db.user)['items'][0]['available'] is False


@pytest.mark.parametrize('committed',[True,False])
def test_lost_commit_ack_reconciles_exact_invitation_command(db,committed):
    issue(db); original=db.c.begin; fired=False
    @contextmanager
    def begin():
        nonlocal fired
        with original():
            yield
            if not committed and not fired:
                fired=True; raise database_error(None)
        if committed and not fired:
            fired=True; raise database_error(None)
    db.c.begin=begin
    result=redeem(db)
    assert fired and result.body()['data']['status']=='redeemed'
    assert len(db.c.data['members'])==2 and len(db.c.data['audits'])==3


@pytest.mark.parametrize('phase',['issue','redeem'])
@pytest.mark.parametrize('state',['40P01','40001'])
def test_confirmed_abort_retries_complete_invitation_transaction(db,monkeypatch,phase,state):
    if phase=='redeem': issue(db)
    original=db.c.execute; fired=False
    def execute(statement,parameters):
        nonlocal fired
        result=original(statement,parameters)
        if not fired and 'INSERT INTO public.outbox_events' in str(statement):
            fired=True; raise database_error(state)
        return result
    monkeypatch.setattr(db.c,'execute',execute)
    reply=issue(db) if phase=='issue' else redeem(db)
    assert fired and reply.http_status==(201 if phase=='issue' else 200)
    assert len(db.c.data['invitations'])==1
    assert len(db.c.data['members'])==(1 if phase=='issue' else 2)


def test_frozen_additive_migration_and_named_metadata():
    from app.models import Invitation
    assert all(c.name for c in Invitation.__table__.constraints)
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0005_invitations.py'
    spec=importlib.util.spec_from_file_location('invitations_migration',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    stream=io.StringIO(); context=MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':stream})
    with Operations.context(context): m.upgrade()
    ddl=stream.getvalue()
    assert m.down_revision=='0004_admission'
    for text in ('fk_invitations_team_hackathon','guard_invitation_identity','guard_invitation_terminal',
        'BEFORE TRUNCATE','ct_invitation_admitted','DEFERRABLE INITIALLY DEFERRED','SECURITY INVOKER','SET search_path = pg_catalog, pg_temp'):
        assert text in ddl
    assert not any(text in ddl for text in ('DROP ','ALTER TABLE public.teams','GRANT ','CREATE OR REPLACE'))
    with pytest.raises(RuntimeError): m.downgrade()


@pytest.mark.parametrize('collision',range(4))
def test_migration_object_collision_refuses_before_any_ddl(monkeypatch,collision):
    path=Path(__file__).resolve().parents[1]/'alembic/versions/0005_invitations.py'
    spec=importlib.util.spec_from_file_location('invitation_collision',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    values=[None]*4; values[collision]='existing'; calls=[]
    c=SimpleNamespace(execute=lambda statement:SimpleNamespace(one=lambda:values))
    monkeypatch.setattr(m,'op',SimpleNamespace(get_context=lambda:SimpleNamespace(as_sql=False),
        get_bind=lambda:c,execute=lambda statement:calls.append(statement)))
    with pytest.raises(RuntimeError,match='no adoption'): m.upgrade()
    assert calls==[]
