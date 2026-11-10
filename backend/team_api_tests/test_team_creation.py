"""PYTEST_DONT_REWRITE: real PostgreSQL HTTP mutations; no private dumps or cleanup."""
from datetime import timedelta
from queue import Queue
from threading import Event
from time import monotonic, sleep
from uuid import UUID, uuid4
import secrets

import psycopg
import pytest
from sqlalchemy import event

from app.auth import encode_token
from session_tests.test_sessions import seeded_session
from team_mutation_tests.test_composition import snapshot
from test_support.races import Outcome, sql, wait, workers
from team_api_tests.conftest import ORIGIN


def headers(issued, key='create'):
    return {'Origin': ORIGIN, 'Idempotency-Key': key,
            'X-CSRF-Token': encode_token(issued.csrf_token.get_secret_value())}


def create(authorized, h, key='create', name='HTTP retained team', **kwargs):
    client, issued = authorized
    return client.post(f'/api/hackathons/{h}/teams', headers=headers(issued, key),
                       json={'name': name}, **kwargs)


def private(response):
    assert response.headers['cache-control'] == 'no-store, private'
    assert response.headers['pragma'] == 'no-cache' and response.headers['expires'] == '0'
    assert 'set-cookie' not in response.headers and 'access-control-allow-origin' not in response.headers


def empty(environment, h):
    assert all(not rows for rows in snapshot(environment, h).values())


def chain(environment, h, actor):
    state = snapshot(environment, h)
    assert all(len(rows) == 1 for rows in state.values())
    team, member = state['teams'][0], state['memberships'][0]
    assert team['leader_user_id'] == team['created_by'] == member['user_id'] == str(actor)
    assert team['version'] == 1 and member['team_id'] == team['id']
    return state


def test_success_and_exact_replay_with_fresh_stored_chain(authorized, environment, subject, account):
    h, users = subject
    first = create(authorized, h)
    assert first.status_code == 201
    state = chain(environment, h, account[0].user_id)
    assert first.json() == state['idempotency_records'][0]['response_body']
    assert first.json()['data'] == dict(team_id=state['teams'][0]['id'], hackathon_id=str(h),
        user_id=str(account[0].user_id), member_count=1, team_version=1)
    replay = create(authorized, h)
    assert replay.status_code == 201 and first.content == replay.content
    assert dict(first.headers) == dict(replay.headers)
    assert snapshot(environment, h) == state
    for r in (first, replay): private(r)


def test_replay_is_original_snapshot_and_read_contracts_unchanged(authorized, environment, subject):
    h, users = subject
    client, issued = authorized
    assert client.get(f'/api/hackathons/{h}/me/team').json() == {'team': None}
    original = create(authorized, h)
    assert original.status_code == 201
    team = UUID(original.json()['data']['team_id'])
    # Trusted composed service only for a retained fixture; no HTTP join exists.
    environment.teams.join_team_idempotent(hackathon_id=h, team_id=team, actor_id=users[0], key='fixture-join')
    saved = snapshot(environment, h)
    replay = create(authorized, h)
    assert replay.status_code == 201 and replay.content == original.content
    assert replay.json()['data']['member_count'] == replay.json()['data']['team_version'] == 1
    assert snapshot(environment, h) == saved
    listing = client.get(f'/api/hackathons/{h}/teams').json()
    mine = client.get(f'/api/hackathons/{h}/me/team').json()
    assert listing['items'][0] == mine['team'] and mine['team']['member_count'] == 2
    assert 'team_version' not in mine['team'] and 'version' not in mine['team']


@pytest.mark.parametrize('kind', ['missing', 'forged', 'expired', 'revoked'])
def test_real_invalid_sessions_never_mutate(client, environment, subject, account, kind):
    h, _ = subject
    if kind == 'expired': raw, csrf, _ = seeded_session(environment, account, timedelta(hours=9))
    else:
        issued = environment.sessions.login(username=account[0].username, password=account[1])
        raw, csrf = issued.session_token.get_secret_value(), issued.csrf_token.get_secret_value()
        if kind == 'revoked': environment.sessions.revoke(raw)
        if kind == 'forged': raw = secrets.token_bytes(32)
    supplied = {'Origin': ORIGIN, 'Idempotency-Key': 'create', 'X-CSRF-Token': encode_token(csrf)}
    if kind != 'missing': supplied['Cookie'] = '__Host-merge_session=' + encode_token(raw)
    r = client.post(f'/api/hackathons/{h}/teams', headers=supplied, json={'name': 'Unauthorized'})
    assert r.status_code == 401 and r.json()['error']['code'] == 'invalid_session'
    private(r)
    empty(environment, h)


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'wrong', 'other-session'])
def test_real_csrf_never_mutates(authorized, environment, subject, account, kind):
    client, issued = authorized
    h, _ = subject
    supplied = headers(issued)
    if kind == 'missing': del supplied['X-CSRF-Token']
    elif kind == 'malformed': supplied['X-CSRF-Token'] = 'bad'
    elif kind == 'wrong': supplied['X-CSRF-Token'] = encode_token(secrets.token_bytes(32))
    else:
        other = environment.sessions.login(username=account[0].username, password=account[1])
        supplied['X-CSRF-Token'] = encode_token(other.csrf_token.get_secret_value())
    r = client.post(f'/api/hackathons/{h}/teams', headers=supplied, json={'name': 'Bad CSRF'})
    assert r.status_code == 403 and r.json()['error']['code'] == 'invalid_csrf'
    private(r)
    empty(environment, h)


@pytest.mark.parametrize('kind,status', [('origin',403), ('metadata',403), ('missing-key',422),
    ('invalid-key',422), ('json',422), ('extra',422), ('name',422), ('actor-header',422), ('uuid',422)])
def test_real_http_validation_no_record_chain(authorized, environment, subject, kind, status):
    client, issued = authorized
    h, users = subject
    supplied, body, path = headers(issued), {'name': 'Team'}, f'/api/hackathons/{h}/teams'
    if kind == 'origin': supplied['Origin'] = 'https://evil.example'
    if kind == 'metadata': supplied['Sec-Fetch-Site'] = 'same-site'
    if kind == 'missing-key': del supplied['Idempotency-Key']
    if kind == 'invalid-key': supplied['Idempotency-Key'] = 'x'*129
    if kind == 'extra': body['actor_id'] = str(users[0])
    if kind == 'name': body['name'] = ' '*3
    if kind == 'actor-header': supplied['X-Actor-ID'] = str(users[0])
    if kind == 'uuid': path = '/api/hackathons/not-a-uuid/teams'
    if kind == 'json':
        supplied['Content-Type'] = 'application/json'
        r = client.post(path, headers=supplied, content='{')
    else: r = client.post(path, headers=supplied, json=body)
    assert r.status_code == status
    private(r)
    empty(environment, h)


@pytest.mark.parametrize('change', ['name', 'hackathon', 'key'])
def test_conflicts_and_cross_hackathon_scope(authorized, environment, subject, change):
    h, _ = subject
    assert create(authorized, h).status_code == 201
    saved = snapshot(environment, h)
    other, _, _ = environment.seed(teams=0)
    r = create(authorized, other if change == 'hackathon' else h,
               key='different' if change == 'key' else 'create',
               name='Changed command' if change == 'name' else 'HTTP retained team')
    assert r.status_code == 409
    assert r.json()['error']['code'] == ('already_assigned' if change == 'key' else 'idempotency_mismatch')
    assert snapshot(environment, h) == saved
    empty(environment, other)


def test_separate_hackathon_separate_key_allowed_and_missing_scope_safe(authorized, environment, subject):
    h, _ = subject
    other, _, _ = environment.seed(teams=0)
    assert create(authorized, h).status_code == 201
    assert create(authorized, other, key='other-hackathon').status_code == 201
    # Reservation's immediate FK fires before domain existence lookup: sanitized
    # infrastructure error, never a cross-scope success or invented 404 proof.
    r = create(authorized, uuid4(), key='absent-hackathon')
    assert r.status_code == 503 and r.json()['error']['code'] == 'service_unavailable'


@pytest.mark.parametrize('matching', [True, False])
def test_concurrent_http_keys_server_wait_and_one_committed_chain(authorized, environment, subject, account, matching):
    h, _ = subject
    held, release, returned = Event(), Event(), Event()
    pids, responses = Queue(), Queue()
    before = snapshot(environment, h)
    def hold(c, cursor, statement, parameters, context, many):
        if 'UPDATE public.idempotency_records' in statement and not held.is_set():
            pids.put(('holder', sql(c, 'SELECT pg_backend_pid()').scalar_one()))
            held.set()
            wait(release)
    def identify(c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.idempotency_records' in statement and held.is_set():
            pids.put(('contender', sql(c, 'SELECT pg_backend_pid()').scalar_one()))
    def call(contender=False):
        if contender: wait(held)
        r = create(authorized, h, key='different' if contender and not matching else 'create')
        responses.put(r)
        returned.set()
        return Outcome(str(r.status_code), '' if r.status_code == 201 else r.json()['error']['code'])
    def observe():
        try:
            wait(held)
            received = dict(pids.get(timeout=8) for _ in range(2))
            assert set(received) == {'holder','contender'} and received['holder'] != received['contender']
            assert not returned.is_set() and snapshot(environment, h) == before
            with environment.connection() as c:
                sql(c, 'SET TRANSACTION READ ONLY')
                deadline = monotonic()+3
                while monotonic() < deadline:
                    if received['holder'] in sql(c, 'SELECT pg_blocking_pids(:pid)', pid=received['contender']).scalar_one():
                        return Outcome('blocking-observed')
                    sleep(0.02)
                raise AssertionError('Expected server wait missing')
        finally: release.set()
    event.listen(environment.engine, 'after_cursor_execute', hold)
    event.listen(environment.engine, 'before_cursor_execute', identify)
    try:
        results = workers([call, lambda: call(True), observe])
    finally:
        release.set()
        event.remove(environment.engine, 'after_cursor_execute', hold)
        event.remove(environment.engine, 'before_cursor_execute', identify)
    assert results == [Outcome('201'), Outcome('201') if matching else Outcome('409','already_assigned'), Outcome('blocking-observed')]
    first, second = responses.get(timeout=1), responses.get(timeout=1)
    if matching: assert first.content == second.content and dict(first.headers) == dict(second.headers)
    chain(environment, h, account[0].user_id)


@pytest.mark.parametrize('stage', ['reservation', 'membership', 'audit', 'outbox', 'completion'])
def test_http_fault_rolls_back_every_write(authorized, environment, subject, stage):
    h, _ = subject
    token = {'reservation': 'INSERT INTO public.idempotency_records', 'membership': 'INSERT INTO public.memberships',
             'audit': 'INSERT INTO public.audit_events', 'outbox': 'INSERT INTO public.outbox_events',
             'completion': 'UPDATE public.idempotency_records'}[stage]
    hits = []
    def fail(c, cursor, statement, parameters, context, many):
        if token in statement:
            hits.append(stage)
            raise RuntimeError('injected test-only failure')
    event.listen(environment.engine, 'after_cursor_execute', fail)
    try:
        r = create(authorized, h)
        assert r.status_code == 503 and hits == [stage]
    finally: event.remove(environment.engine, 'after_cursor_execute', fail)
    empty(environment, h)
    assert create(authorized, h).status_code == 201


def test_real_deferred_commit_failure_is_not_success(authorized, environment, subject):
    h, users = subject
    observed = []
    def corrupt(c, cursor, statement, parameters, context, many):
        if 'UPDATE public.idempotency_records' in statement:
            sql(c, '''UPDATE public.teams SET leader_user_id=:bad WHERE id=(SELECT team_id
                FROM public.audit_events WHERE idempotency_record_id=:r)''',
                bad=users[-1], r=context.compiled_parameters[0]['id'])
    def record(context):
        error = context.original_exception
        observed.append((getattr(error,'sqlstate',None), getattr(getattr(error,'diag',None),'constraint_name',None)))
    event.listen(environment.engine, 'after_cursor_execute', corrupt)
    event.listen(environment.engine, 'handle_error', record)
    try:
        r = create(authorized, h)
        assert r.status_code == 503 and r.json()['error']['code'] == 'service_unavailable'
        assert observed == [('23503','fk_teams_leader_member')]
    finally:
        event.remove(environment.engine, 'after_cursor_execute', corrupt)
        event.remove(environment.engine, 'handle_error', record)
    empty(environment, h)


@pytest.mark.parametrize('committed', [True, False])
@pytest.mark.parametrize('reconcile', [True, False])
def test_commit_ack_loss_reconciliation_or_explicit_uncertainty(authorized, environment, subject, account, monkeypatch, committed, reconcile):
    h, _ = subject
    original = environment.engine.dialect.do_commit
    mutation_connections, commits, attempts = set(), [], []
    def identify(c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.idempotency_records' in statement:
            attempts.append(True)
            if commits and not reconcile:
                raise RuntimeError('injected unavailable reconciliation')
            mutation_connections.add(id(c.connection.dbapi_connection))
    def lose_ack(dbapi):
        actual = getattr(dbapi, 'dbapi_connection', dbapi)
        if id(actual) in mutation_connections:
            commits.append(True)
            if len(commits) == 1:
                if committed: original(dbapi)
                raise psycopg.OperationalError('injected acknowledgement loss')
        original(dbapi)
    event.listen(environment.engine, 'before_cursor_execute', identify)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(environment.engine.dialect, 'do_commit', lose_ack)
            r = create(authorized, h)
    finally: event.remove(environment.engine, 'before_cursor_execute', identify)
    assert len(attempts) == 2
    if reconcile:
        assert r.status_code == 201 and len(commits) == 2
        saved = chain(environment, h, account[0].user_id)
    else:
        assert r.status_code == 503 and r.json()['error']['code'] == 'outcome_uncertain'
        assert r.json()['error']['retryable'] and 'SAME Idempotency-Key' in r.json()['error']['message']
        assert len(commits) == 1
        saved = snapshot(environment, h)
        if committed: chain(environment, h, account[0].user_id)
        else: empty(environment, h)
    retry = create(authorized, h)  # Explicit unchanged key, after injection removal.
    assert retry.status_code == 201
    if reconcile or committed:
        assert snapshot(environment, h) == saved
        assert retry.json() == saved['idempotency_records'][0]['response_body']
    else: chain(environment, h, account[0].user_id)
    private(r)
