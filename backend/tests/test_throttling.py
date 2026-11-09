"""PYTEST_DONT_REWRITE: do not expose keyed identifiers in assertion locals.

Queued rows test admission decisions and transaction/error boundaries only.
They do not simulate PostgreSQL atomicity, clock selection or concurrent workers;
those properties require the separate guarded live PostgreSQL suite.
"""
from collections import deque
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
from types import SimpleNamespace
from unittest.mock import MagicMock

from pydantic import SecretBytes
import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.services.credential_errors import CredentialCode, CredentialError
from app.services.throttling import ThrottleExceeded, ThrottlePolicy, ThrottleService


NOW = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
SYNTHETIC_KEY = b'unit-only-throttle-key-material!'
CLIENT_IP = '192.0.2.73'
USERNAME = 'unit_account'


def row(attempts=1, *, seconds=300, remaining=30):
    expires = NOW + timedelta(seconds=seconds)
    return SimpleNamespace(attempts=attempts, expires_at=expires,
                           expected_expiry=expires,
                           checked_at=expires-timedelta(seconds=remaining))


class Connection:
    """Track rollback/commit around queued results without emulating SQL."""

    def __init__(self):
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.active = self.closed = self.committed = self.rolled_back = False
        self.commit_count = 0
        self.statements, self.parameters, self.charges, self.events = [], [], [], []
        self.rows = deque()
        self.fail_mutation = self.fail_commit = False
        self.sqlstate = '08006'

    def get_isolation_level(self):
        return 'READ COMMITTED'

    def in_transaction(self):
        return self.active

    def failure(self):
        original = RuntimeError('synthetic-private-driver-detail')
        original.sqlstate = self.sqlstate
        original.diag = SimpleNamespace(constraint_name='synthetic_unexpected_check')
        exception = IntegrityError if self.sqlstate.startswith('23') else DBAPIError
        raise exception('synthetic SQL', {'private': 'synthetic-private-parameter'}, original)

    @contextmanager
    def begin(self):
        before = deepcopy(self.charges)
        self.active = True
        self.events.append('begin')
        try:
            yield
            if self.fail_commit:
                self.failure()
            self.committed = True
            self.commit_count += 1
            self.events.append('commit')
        except Exception:
            self.charges = before
            self.rolled_back = True
            self.events.append('rollback')
            raise
        finally:
            self.active = False

    def execute(self, statement, parameters):
        sql = str(statement)
        self.statements.append(sql)
        self.parameters.append(parameters)
        if 'INSERT INTO public.auth_throttle_buckets' not in sql:
            return SimpleNamespace()
        assert self.active, 'Throttle query escaped the owned transaction'
        self.charges.append(deepcopy(parameters))
        self.events.append(parameters['scope'])
        if self.fail_mutation:
            self.failure()
        selected = self.rows.popleft() if self.rows else row()
        return SimpleNamespace(one=lambda: selected)


@pytest.fixture
def setup():
    connection = Connection()
    engine = MagicMock(spec=Engine)
    engine.hide_parameters, engine.echo = True, False

    @contextmanager
    def connect():
        connection.closed = False
        try:
            yield connection
        finally:
            connection.closed = True
            connection.events.append('close')

    engine.connect.side_effect = connect
    policy = ThrottlePolicy()
    service = ThrottleService(engine, secret=SecretBytes(SYNTHETIC_KEY), policy=policy)
    return service, connection, engine


def login(service, *, client_ip=CLIENT_IP, username=USERNAME):
    service.check(operation='login', client_ip=client_ip, username=username)


def test_default_policy_is_modest_immutable_and_exact():
    policy = ThrottlePolicy()
    assert (policy.window_seconds, policy.login_account, policy.login_ip,
            policy.register_ip) == (300, 5, 30, 5)
    with pytest.raises(FrozenInstanceError):
        policy.login_account = 100


@pytest.mark.parametrize('field,value', [
    ('window_seconds', 0), ('window_seconds', 3601), ('window_seconds', True),
    ('window_seconds', 1.0), ('login_account', 0), ('login_account', 101),
    ('login_account', '5'), ('login_ip', 0), ('login_ip', 501),
    ('register_ip', 0), ('register_ip', 51), ('register_ip', None),
])
def test_policy_rejects_outside_bounded_integer_limits(field, value):
    with pytest.raises(CredentialError) as error:
        ThrottlePolicy(**{field: value})
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    assert error.value.args == ('transaction_configuration',)


@pytest.mark.parametrize('values', [
    {'window_seconds': 1, 'login_account': 1, 'login_ip': 1, 'register_ip': 1},
    {'window_seconds': 3600, 'login_account': 100, 'login_ip': 500, 'register_ip': 50},
])
def test_policy_accepts_documented_boundary_limits(values):
    policy = ThrottlePolicy(**values)
    assert all(getattr(policy, field) == value for field, value in values.items())


@pytest.mark.parametrize('secret', [None, SYNTHETIC_KEY, SecretBytes(b'x'*31), SecretBytes(b'x'*33)])
def test_service_requires_exact_secret_material_before_connections(setup, secret):
    _, _, engine = setup
    with pytest.raises(CredentialError) as error:
        ThrottleService(engine, secret=secret, policy=ThrottlePolicy())
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    engine.connect.assert_not_called()


def test_service_rejects_untyped_policy_before_connections(setup):
    _, _, engine = setup
    with pytest.raises(CredentialError) as error:
        ThrottleService(engine, secret=SecretBytes(SYNTHETIC_KEY), policy={})
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    engine.connect.assert_not_called()


@pytest.mark.parametrize('arguments', [
    {'operation': 'logout', 'client_ip': CLIENT_IP},
    {'operation': None, 'client_ip': CLIENT_IP},
    {'operation': 'register', 'client_ip': None},
    {'operation': 'register', 'client_ip': 123},
    {'operation': 'register', 'client_ip': ''},
    {'operation': 'register', 'client_ip': 'localhost'},
    {'operation': 'register', 'client_ip': '192.0.2.73:80'},
    {'operation': 'register', 'client_ip': '192.000.2.73'},
    {'operation': 'register', 'client_ip': 'fe80::1%12'},
    {'operation': 'login', 'client_ip': CLIENT_IP, 'username': None},
    {'operation': 'login', 'client_ip': CLIENT_IP, 'username': 'UNIT_ACCOUNT'},
    {'operation': 'login', 'client_ip': CLIENT_IP, 'username': 'unit_account '},
    {'operation': 'login', 'client_ip': CLIENT_IP, 'username': 'ab'},
    {'operation': 'login', 'client_ip': CLIENT_IP, 'username': 'unit\u00e9_account'},
])
def test_invalid_inputs_fail_closed_before_opening_database(setup, arguments):
    service, connection, engine = setup
    with pytest.raises(CredentialError) as error:
        service.check(**arguments)
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    assert not connection.statements
    engine.connect.assert_not_called()


def test_first_n_returned_attempts_permitted_then_denial_commits(setup):
    service, connection, _ = setup
    # These rows exercise the decision threshold only, not counter atomicity.
    for attempt in range(1, 6):
        connection.rows.extend([row(attempt), row(attempt)])
        login(service)
    connection.rows.extend([row(6), row(6)])
    with pytest.raises(ThrottleExceeded) as error:
        login(service)
    assert error.value.retry_after == 30
    assert error.value.args == ('rate_limited',)
    assert connection.commit_count == 6
    assert connection.closed and not connection.active and not connection.rolled_back
    assert connection.events[-2:] == ['commit', 'close']
    assert len(connection.charges) == 12


def test_ip_denial_commits_and_never_queries_account_bucket(setup):
    service, connection, _ = setup
    connection.rows.append(row(31))
    with pytest.raises(ThrottleExceeded):
        login(service)
    assert connection.committed and connection.closed and len(connection.charges) == 1
    assert connection.charges[0]['scope'] == 'auth:v1:login_ip'
    assert 'auth:v1:login_account' not in connection.events


def test_account_denial_commits_the_ip_charge_in_same_transaction(setup):
    service, connection, _ = setup
    connection.rows.extend([row(2), row(6)])
    with pytest.raises(ThrottleExceeded):
        login(service)
    assert connection.commit_count == 1 and not connection.rolled_back
    assert [charge['scope'] for charge in connection.charges] == [
        'auth:v1:login_ip', 'auth:v1:login_account']
    assert connection.events[-2:] == ['commit', 'close']


def test_register_only_charges_registration_ip_bucket(setup):
    service, connection, _ = setup
    service.check(operation='register', client_ip=CLIENT_IP)
    assert len(connection.charges) == 1 and connection.commit_count == 1
    charge = connection.charges[0]
    assert charge['scope'] == 'auth:v1:register_ip' and charge['maximum'] == 5


def test_sql_uses_one_atomic_upsert_and_saturates_attempts(setup):
    service, connection, _ = setup
    login(service)
    sql = [statement for statement in connection.statements
           if 'INSERT INTO public.auth_throttle_buckets' in statement]
    assert len(sql) == 2
    for statement in sql:
        assert 'ON CONFLICT (scope,key_hash,window_start) DO UPDATE' in statement
        assert 'SET attempts=LEAST(bucket.attempts,:maximum)+1' in statement
        assert 'clock_timestamp()' in statement and 'date_bin(' in statement
        assert 'stamp AS MATERIALIZED' in statement and 'bounds AS MATERIALIZED' in statement
        assert 'RETURNING attempts,expires_at' in statement
        assert ':scope' in statement and ':key' in statement
    assert connection.statements[:4] == [
        "SET LOCAL lock_timeout='5s'", "SET LOCAL statement_timeout='15s'",
        "SET LOCAL lock_timeout='1s'", "SET LOCAL statement_timeout='2s'"]


def test_scope_separation_hmac_and_parameter_privacy(setup, caplog):
    service, connection, _ = setup
    login(service)
    service.check(operation='register', client_ip=CLIENT_IP)
    expected = [
        ('login_ip', CLIENT_IP), ('login_account', USERNAME), ('register_ip', CLIENT_IP)]
    for charge, (scope, identifier) in zip(connection.charges, expected, strict=True):
        assert charge['key'] == hmac.digest(SYNTHETIC_KEY, (scope+'\0'+identifier).encode('ascii'), sha256)
        assert isinstance(charge['key'], bytes) and len(charge['key']) == 32
        assert set(charge) == {'scope', 'key', 'seconds', 'maximum'}
    assert len({charge['key'] for charge in connection.charges}) == 3
    rendered = repr(connection.parameters) + repr(connection.statements) + caplog.text + repr(service)
    assert CLIENT_IP not in rendered and USERNAME not in rendered
    assert repr(SYNTHETIC_KEY) not in rendered


def test_different_account_and_ip_inputs_create_distinct_key_scopes(setup):
    service, connection, _ = setup
    login(service)
    login(service, client_ip='192.0.2.74', username='other_account')
    first_ip, first_account, second_ip, second_account = connection.charges
    assert first_ip['key'] != second_ip['key']
    assert first_account['key'] != second_account['key']


def test_ipv6_and_ipv4_mapped_aliases_share_their_canonical_ip_key(setup):
    service, connection, _ = setup
    for supplied in ('2001:0db8:0000:0000:0000:0000:0000:0001', '2001:db8::1',
                     '::ffff:192.0.2.73', CLIENT_IP):
        service.check(operation='register', client_ip=supplied)
    first, second, mapped, ipv4 = connection.charges
    assert first['key'] == second['key'] and mapped['key'] == ipv4['key']


@pytest.mark.parametrize('remaining,expected', [(29.001, 30), (0.001, 1), (0, 1), (-5, 1), (999, 300)])
def test_retry_after_uses_returned_database_clock_ceil_and_policy_clamp(setup, remaining, expected):
    service, connection, _ = setup
    connection.rows.append(row(31, remaining=remaining))
    with pytest.raises(ThrottleExceeded) as error:
        login(service)
    assert type(error.value.retry_after) is int and error.value.retry_after == expected
    assert connection.committed


@pytest.mark.parametrize('change', [
    {'attempts': 0}, {'attempts': 32}, {'attempts': True}, {'attempts': 1.0},
    {'attempts': '1'}, {'expires_at': NOW},
    {'checked_at': NOW.replace(tzinfo=None)}, {'checked_at': None},
    {'expires_at': None, 'expected_expiry': None},
    {'expires_at': NOW.replace(tzinfo=None), 'expected_expiry': NOW.replace(tzinfo=None)},
])
def test_corrupt_database_rows_fail_closed_as_integrity_fault_and_rollback(setup, change):
    service, connection, _ = setup
    selected = row()
    for field, value in change.items():
        setattr(selected, field, value)
    connection.rows.append(selected)
    with pytest.raises(CredentialError) as error:
        login(service)
    assert error.value.code == CredentialCode.INTEGRITY_FAULT
    assert error.value.args == ('integrity_fault',)
    assert connection.rolled_back and not connection.charges and not connection.committed


@pytest.mark.parametrize('phase', ['mutation', 'commit'])
@pytest.mark.parametrize('sqlstate,code', [
    ('08006', CredentialCode.DATABASE_FAILURE), ('23514', CredentialCode.INTEGRITY_FAULT),
    ('57014', CredentialCode.STATEMENT_TIMEOUT), ('55P03', CredentialCode.LOCK_TIMEOUT),
    ('40001', CredentialCode.TRANSACTION_CONFLICT), ('XX999', CredentialCode.DATABASE_FAILURE),
])
def test_database_faults_rollback_and_are_not_success_or_rate_limits(setup, phase, sqlstate, code, caplog):
    service, connection, _ = setup
    connection.fail_mutation = phase == 'mutation'
    connection.fail_commit = phase == 'commit'
    connection.sqlstate = sqlstate
    with pytest.raises(CredentialError) as error:
        login(service)
    assert error.value.code == code
    assert error.value.__context__ is None and error.value.__cause__ is None
    assert error.value.args == (code.value,)
    assert connection.rolled_back and not connection.charges and connection.closed
    assert not connection.committed
    rendered = repr(error.value) + str(error.value) + caplog.text
    assert 'synthetic-private' not in rendered and 'synthetic SQL' not in rendered


def test_failed_commit_cannot_be_reported_as_intended_denial(setup):
    service, connection, _ = setup
    connection.rows.append(row(31))
    connection.fail_commit = True
    with pytest.raises(CredentialError) as error:
        login(service)
    assert error.value.code == CredentialCode.DATABASE_FAILURE
    assert connection.rolled_back and not connection.charges


@pytest.mark.parametrize('state', [True, None, 0, 1, 'False'])
def test_actual_or_ambiguous_dbapi_autocommit_rejected_before_service_sql(setup, state):
    service, connection, _ = setup
    connection.connection.dbapi_connection.autocommit = state
    connection.get_isolation_level = lambda: pytest.fail('Isolation read before DBAPI guard')
    with pytest.raises(CredentialError) as error:
        login(service)
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    assert connection.closed and not connection.statements and not connection.charges


@pytest.mark.parametrize('isolation', ['AUTOCOMMIT', 'REPEATABLE READ', 'SERIALIZABLE', None])
def test_non_read_committed_isolation_rejected_before_service_sql(setup, isolation):
    service, connection, _ = setup
    connection.get_isolation_level = lambda: isolation
    with pytest.raises(CredentialError) as error:
        login(service)
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    assert connection.closed and not connection.statements and not connection.charges


def test_existing_transaction_rejected_before_service_sql(setup):
    service, connection, _ = setup
    connection.active = True
    with pytest.raises(CredentialError) as error:
        login(service)
    assert error.value.code == CredentialCode.TRANSACTION_CONFIGURATION
    assert not connection.statements
