"""PYTEST_DONT_REWRITE: R5 HTTP/commit-hook reproduction; no PostgreSQL connection.

Real HTTP, session reads, transaction owners and admission/reconciliation code run
over the existing in-memory SQL double. SQLAlchemy events are dispatched by that
double; this cannot certify real PostgreSQL COMMIT or constraint behavior.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace

from pydantic import SecretBytes
import pytest
from sqlalchemy import create_engine, event
import psycopg

from admission_tests import test_admission as live
from app.admission_api import get_admission_service
from app.auth import AuthServices, get_services
from app.services.admission import AdmissionService
from app.services.credentials import _PASSWORDS
from app.services.sessions import SessionService
from test_admission import db
from test_auth_http import api, assert_private


@pytest.fixture
def flow(db, api, monkeypatch):
    def forbidden_connection():
        pytest.fail('Offline reproduction attempted a physical database connection')

    # This Engine supplies the real event registry only. Its creator must never run.
    engine = create_engine('postgresql+psycopg://', creator=forbidden_connection,
                           hide_parameters=True)
    c = db.c
    state = SimpleNamespace(responses=[], commits=[], injected=[], durable=None,
                            block_reconciliation=False, deliver_mutation_commit=True)
    leader = replace(api.issued, principal=replace(api.issued.principal, user_id=db.leader))
    candidate = replace(api.issued, principal=replace(api.issued.principal, user_id=db.user),
                        session_token=SecretBytes(b'u'*32))
    now = datetime.now(timezone.utc)
    encoded = _PASSWORDS.hash('synthetic offline admission passphrase')
    sessions = {sha256(issued.session_token.get_secret_value()).digest(): SimpleNamespace(
        user_id=issued.principal.user_id, username=issued.principal.username,
        password_hash=encoded, csrf_token=issued.csrf_token.get_secret_value(),
        created_at=issued.created_at, expires_at=issued.principal.expires_at,
        checked_at=now, revoked_at=None) for issued in (leader, candidate)}
    original_execute, original_begin = c.execute, c.begin
    kind = None

    def execute(statement, parameters):
        nonlocal kind
        query = str(statement)
        context = SimpleNamespace(compiled_parameters=[parameters])
        engine.dispatch.before_cursor_execute(c, None, query, parameters, context, False)
        if 'FROM public.auth_sessions s' in query:
            kind = 'authentication'
            value = SimpleNamespace(one_or_none=lambda: sessions.get(parameters['digest']))
        else:
            if 'INSERT INTO public.idempotency_records' in query:
                kind = 'admission'
                if state.block_reconciliation and state.injected:
                    raise RuntimeError('synthetic unavailable reconciliation')
            value = original_execute(statement, parameters)
        engine.dispatch.after_cursor_execute(c, None, query, parameters, context, False)
        return value

    def physical_commit():
        state.injected.append(kind)
        state.durable = deepcopy(c.data)

    @contextmanager
    def begin():
        nonlocal kind
        kind, state.durable = None, None
        try:
            with original_begin():
                yield
                state.commits.append(kind)
                if state.deliver_mutation_commit or kind != 'admission':
                    engine.dispatch.commit(c)
        except Exception:
            # A lost acknowledgement must not undo the simulated physical commit.
            if state.durable is not None:
                c.data = state.durable
            raise

    @contextmanager
    def connect():
        yield c

    monkeypatch.setattr(engine, 'connect', connect)
    monkeypatch.setattr(c, 'execute', execute)
    monkeypatch.setattr(c, 'begin', begin)
    monkeypatch.setattr(c.connection.dbapi_connection, 'commit', physical_commit, raising=False)
    service = AdmissionService(engine)
    api.app.dependency_overrides[get_services] = lambda: AuthServices(
        api.services.credentials, SessionService(engine), api.services.throttle)
    api.app.dependency_overrides[get_admission_service] = lambda: service
    env = SimpleNamespace(engine=engine, roster=lambda team: {
        m['actor'] for m in c.data['members'] if m['team'] == team})
    def snapshot(environment, hackathon):
        data = deepcopy(c.data)
        # Match the live oracle's JSONB metadata shape without a server query.
        data['join_requests'] = [dict(id=str(row['id']), status=row['status'],
            resolved_by=str(db.leader) if row['status'] != 'pending' else None)
            for row in data['requests'].values()]
        data['idempotency_records'] = list(data['reservations'].values())
        return data

    monkeypatch.setattr(live, 'snapshot', snapshot)
    original_decide = live.decide

    def decide(*args, **kwargs):
        if state.responses:
            state.block_reconciliation = False  # Explicit owner-style same-key retry.
        response = original_decide(*args, **kwargs)
        state.responses.append(response)
        return response

    monkeypatch.setattr(live, 'decide', decide)
    state.subject = (db.h, db.team, db.leader, leader, db.user, candidate)
    state.run = lambda: live.test_real_failure_rolls_back_or_reconciles_same_key(
        api.client, env, state.subject, 'ambiguous-commit')
    state.engine, state.client, state.env = engine, api.client, env
    state.db = db
    try:
        yield state
    finally:
        engine.dispose()


@pytest.mark.parametrize('reconciliation', ['available', 'unavailable'])
def test_exact_live_fault_targets_approval_after_authentication(flow, reconciliation):
    flow.block_reconciliation = reconciliation == 'unavailable'
    flow.run()
    assert flow.injected == ['admission']
    assert flow.commits[:2] == ['authentication', 'authentication']
    first, replay = flow.responses
    assert first.status_code == (200 if reconciliation == 'available' else 503)
    if reconciliation == 'available':
        assert first.json() == replay.json()
    else:
        assert first.json()['error']['code'] == 'outcome_uncertain'
        assert first.json()['error']['retryable'] is True
    for response in flow.responses:
        assert_private(response)
    data = flow.db.c.data
    assert replay.status_code == 200 and replay.json()['data']['status'] == 'approved'
    assert len(data['members']) == 2 and len(data['requests']) == 1
    assert len(data['reservations']) == len(data['audits']) == len(data['outbox']) == 3
    assert data['teams'][flow.db.team]['version'] == 3


def test_live_case_refuses_success_without_targeted_fault(flow):
    flow.deliver_mutation_commit = False
    with pytest.raises(AssertionError):
        flow.run()
    assert flow.injected == []
    assert flow.responses[0].status_code == 200


def test_unscoped_commit_fault_hits_authentication_before_admission(flow):
    request_id = live.request(flow.client, flow.subject).json()['data']['id']
    saved = deepcopy(flow.db.c.data)

    def original_unscoped_fault(c):
        c.connection.dbapi_connection.commit()
        raise psycopg.OperationalError('synthetic lost acknowledgement')

    event.listen(flow.engine, 'commit', original_unscoped_fault)
    try:
        response = live.decide(flow.client, flow.subject, request_id)
    finally:
        event.remove(flow.engine, 'commit', original_unscoped_fault)
    assert flow.injected == ['authentication']
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'service_unavailable'
    assert flow.db.c.data == saved
    assert_private(response)
