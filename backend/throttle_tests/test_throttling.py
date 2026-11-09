"""PYTEST_DONT_REWRITE: independent real PostgreSQL throttle schedules, no cleanup."""
from collections import Counter
from threading import Barrier, Event
from time import monotonic
import secrets

import pytest
from sqlalchemy import event

from app.services.credential_errors import CredentialCode, CredentialError
from app.services.throttling import ThrottleExceeded, ThrottlePolicy
from test_support.races import Outcome, sql, workers

HEADERS = {'Origin': 'https://merge.example', 'X-Merge-Request': '1'}


def test_first_n_then_denied_saturates_and_commits(throttle):
    service = throttle.service(ThrottlePolicy(window_seconds=3600, register_ip=2))
    for _ in range(2): service.check(operation='register', client_ip='192.0.2.1')
    for _ in range(3):
        with pytest.raises(ThrottleExceeded) as error:
            service.check(operation='register', client_ip='192.0.2.1')
        assert 1 <= error.value.retry_after <= 3600
    assert [r.attempts for r in throttle.rows()] == [3]


def test_account_budget_shared_across_ips_and_ip_denial_skips_account(throttle):
    service = throttle.service(ThrottlePolicy(window_seconds=3600, login_account=1, login_ip=2))
    service.check(operation='login', client_ip='192.0.2.1', username='alice')
    with pytest.raises(ThrottleExceeded):
        service.check(operation='login', client_ip='192.0.2.2', username='alice')
    service.check(operation='login', client_ip='192.0.2.1', username='bob')
    with pytest.raises(ThrottleExceeded):
        service.check(operation='login', client_ip='192.0.2.1', username='carol')
    rows = throttle.rows()
    assert sorted(r.attempts for r in rows if r.scope.endswith('login_ip')) == [1, 3]
    assert sorted(r.attempts for r in rows if r.scope.endswith('login_account')) == [1, 2]


@pytest.mark.parametrize('account_scope', [False, True])
def test_concurrent_admission_exact_across_independent_connections(throttle, account_scope):
    service = throttle.service(ThrottlePolicy(window_seconds=3600, login_account=3, register_ip=3))
    other = throttle.service(ThrottlePolicy(window_seconds=3600, login_account=3, register_ip=3))
    gate = Barrier(8, timeout=8)
    pids = set()

    def overlap(c, cursor, statement, parameters, context, many):
        if 'INSERT INTO public.auth_throttle_buckets' not in statement:
            return
        expected = 'auth:v1:login_ip' if account_scope else 'auth:v1:register_ip'
        if context.compiled_parameters[0]['scope'] == expected:
            with throttle.mutex:
                pids.add(c.connection.dbapi_connection.info.backend_pid)
            gate.wait()

    def attempt(index):
        try:
            selected = service if index % 2 else other
            if account_scope:
                selected.check(operation='login', client_ip='198.51.100.'+str(index+1), username='race_account')
            else:
                selected.check(operation='register', client_ip='192.0.2.1')
        except ThrottleExceeded:
            return Outcome('denied')
        return Outcome('admitted')

    event.listen(throttle.env.engine, 'before_cursor_execute', overlap)
    try:
        results = workers([lambda index=i: attempt(index) for i in range(8)])
    finally:
        event.remove(throttle.env.engine, 'before_cursor_execute', overlap)
    assert len(pids) == 8, 'Did not observe eight independent PostgreSQL connections'
    assert Counter(r.status for r in results) == {'admitted': 3, 'denied': 5}
    rows = [r for r in throttle.rows() if r.scope.endswith('login_account' if account_scope else 'register_ip')]
    assert len(rows) == 1 and rows[0].attempts == 4


def test_window_reset_uses_database_clock_and_retains_old_bucket(throttle):
    service = throttle.service(ThrottlePolicy(window_seconds=1, register_ip=1))
    deadline = monotonic()+4
    # Start near the beginning of a real server second, leaving a bounded margin.
    with throttle.env.connection() as c:
        while monotonic() < deadline:
            now = sql(c, 'SELECT clock_timestamp()').scalar_one()
            if now.microsecond < 150000: break
            Event().wait(0.01)
        else: raise AssertionError('Database clock synchronization deadline exceeded')
    service.check(operation='register', client_ip='192.0.2.1')
    with pytest.raises(ThrottleExceeded) as error:
        service.check(operation='register', client_ip='192.0.2.1')
    assert error.value.retry_after == 1
    expiry = throttle.rows()[0].expires_at
    deadline = monotonic()+4
    with throttle.env.connection() as c:
        while monotonic() < deadline:
            if sql(c, 'SELECT clock_timestamp()>=:expiry', expiry=expiry).scalar_one(): break
            Event().wait(0.01)
        else: raise AssertionError('Window did not expire before deadline')
    service.check(operation='register', client_ip='192.0.2.1')
    assert sorted(row.attempts for row in throttle.rows()) == [1, 2]


def test_two_app_instances_share_registration_budget(throttle):
    policy = ThrottlePolicy(window_seconds=3600, register_ip=1)
    with throttle.client(policy) as first, throttle.client(policy) as second:
        body = {'username': throttle.env.username(), 'password': secrets.token_urlsafe(32)}
        assert first.post('/auth/register', headers=HEADERS, json=body).status_code == 201
        body['username'] = throttle.env.username()
        rejected = second.post('/auth/register', headers=HEADERS, json=body)
        assert rejected.status_code == 429 and rejected.json()['error']['code'] == 'rate_limited'
        assert 1 <= int(rejected.headers['retry-after']) <= 3600
    assert throttle.env.counts() == (1, 1) and throttle.env.session_count() == 0


def test_two_apps_share_login_budget_and_denial_does_no_argon_work(throttle, account, monkeypatch):
    from app.services import credentials
    policy = ThrottlePolicy(window_seconds=3600, login_account=2)
    body = {'username': account[0].username, 'password': account[1]}
    with throttle.client(policy) as first, throttle.client(policy) as second:
        assert first.post('/auth/login', headers=HEADERS, json=body).status_code == 200
        assert second.post('/auth/login', headers=HEADERS, json=body).status_code == 200
        calls = []
        original = credentials._PASSWORDS.verify

        def observe(*args):
            calls.append('verify')
            return original(*args)

        monkeypatch.setattr(credentials._PASSWORDS, 'verify', observe)
        response = first.post('/auth/login', headers=HEADERS, json=body)
        assert response.status_code == 429 and calls == []
        assert second.get('/auth/session').status_code == 200
    assert throttle.env.session_count() == 2


@pytest.mark.parametrize('known', [False, True])
def test_wrong_or_unknown_credentials_consume_account_budget(throttle, account, known):
    policy = ThrottlePolicy(window_seconds=3600, login_account=2)
    body = {'username': account[0].username if known else throttle.env.username(),
            'password': secrets.token_urlsafe(32)}
    with throttle.client(policy) as client:
        for _ in range(2):
            rejected = client.post('/auth/login', headers=HEADERS, json=body)
            assert rejected.status_code == 401 and rejected.json()['error']['code'] == 'invalid_credentials'
        assert client.post('/auth/login', headers=HEADERS, json=body).status_code == 429
    assert throttle.env.session_count() == 0
    assert [r.attempts for r in throttle.rows() if r.scope.endswith('login_account')] == [3]


def test_storage_lock_timeout_fails_closed_before_registration_hash(throttle, monkeypatch):
    from app.services import credentials
    service = throttle.service()
    service.check(operation='register', client_ip='192.0.2.1')
    row = throttle.rows()[0]
    states, calls = [], []

    def record(context):
        states.append(getattr(context.original_exception, 'sqlstate', None))

    def forbidden_hash(*args):
        calls.append('hash')
        raise AssertionError('Hash ran after storage failure')

    monkeypatch.setattr(credentials._PASSWORDS, 'hash', forbidden_hash)
    event.listen(throttle.env.engine, 'handle_error', record)
    try:
        with throttle.env.connection() as held:
            sql(held, '''SELECT attempts FROM public.auth_throttle_buckets
                WHERE scope=:scope AND key_hash=:key AND window_start=:start FOR UPDATE''',
                scope=row.scope, key=row.key_hash, start=row.window_start).one()
            with throttle.client() as client:
                response = client.post('/auth/register', headers=HEADERS,
                    json={'username': throttle.env.username(), 'password': secrets.token_urlsafe(32)})
                assert response.status_code == 503 and response.json()['error']['code'] == 'service_unavailable'
    finally:
        event.remove(throttle.env.engine, 'handle_error', record)
    assert states == ['55P03'] and calls == []
    assert throttle.env.counts() == (0, 0) and throttle.rows()[0].attempts == 1


def test_actual_autocommit_rejected_before_counter_sql(throttle):
    from app.services.throttling import ThrottleService
    engine = throttle.env.engine.execution_options(isolation_level='AUTOCOMMIT')
    service = ThrottleService(engine, secret=throttle.secret, policy=ThrottlePolicy())
    states, statements = [], []

    def state(c): states.append(c.connection.dbapi_connection.autocommit)
    def observe(c, cursor, statement, parameters, context, many):
        if 'auth_throttle_buckets' in statement or statement.startswith('SET LOCAL'):
            statements.append('unexpected-service-sql')
    event.listen(engine, 'engine_connect', state)
    event.listen(engine, 'before_cursor_execute', observe)
    try:
        with pytest.raises(CredentialError) as error:
            service.check(operation='register', client_ip='192.0.2.1')
        assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    finally:
        event.remove(engine, 'before_cursor_execute', observe)
        event.remove(engine, 'engine_connect', state)
    assert states == [True] and statements == [] and throttle.rows() == []
