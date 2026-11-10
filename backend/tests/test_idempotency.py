"""Database-free contract tests, not evidence of PostgreSQL race correctness."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.services import idempotency as idem
from app.services.errors import DomainError, ErrorCode
from app.services.teams import _CreateTeamCommand, _JoinTeamCommand

ACTOR, HACKATHON, TEAM = (UUID(int=n) for n in (1, 2, 3))


def test_live_effect_helper_supplies_binds_and_preserves_literal_suffix():
    # Exercise the real test helper and SQLAlchemy text parsing without a DB.
    from idempotency_tests.test_idempotency import effect

    captured = []

    class CompileOnlyConnection:
        def execute(self, statement, parameters):
            compiled = statement.compile(dialect=postgresql.dialect())
            captured.append((str(compiled), compiled.construct_params(parameters)))

    effect(CompileOnlyConnection(), SimpleNamespace(actor_id=ACTOR))
    assert len(captured) == 1
    statement, parameters = captured[0]
    assert 'display_name=display_name || %(effect)s WHERE id=%(u)s' in statement
    assert parameters == {'effect': ':effect', 'u': ACTOR}


def create(name='Example', *, actor=ACTOR, hackathon=HACKATHON, team=TEAM):
    return _CreateTeamCommand(hackathon, actor, name, team)


def command(key='key'):
    return idem._command(create(), key)


def reply():
    return idem._StoredReply._from_values(201, {'schema_version': 1, 'data': {'id': str(TEAM)}},
                                         {'content-type': 'application/json', 'cache-control': 'no-store'})


def error_code(code, function, *args):
    with pytest.raises(DomainError) as found:
        function(*args)
    assert found.value.code == code and not found.value.retryable
    assert str(found.value) == code.value


@pytest.mark.parametrize('key', ['', 'x'*129, '\n', '\t', '\x00', '\x1f', '\x7f', 'é', None, 42])
def test_invalid_keys_fail_before_any_connection_or_sql(monkeypatch, key):
    monkeypatch.setattr(idem, '_query', lambda *a, **k: pytest.fail('SQL reached'))
    error_code(ErrorCode.INVALID_INPUT, idem._command, create(), key)


@pytest.mark.parametrize('key', [' ', ' '*128, 'a', 'x'*128, ''.join(chr(n) for n in range(32, 127)), ' Case '])
def test_key_contract_preserves_every_printable_ascii_character(key):
    assert idem._command(create(), key).key == key


def test_fingerprint_has_fixed_canonical_document_and_excludes_generated_outcome_and_key():
    result = idem._command(create(' A é '), 'Key')
    expected = ('{"actor_id":"00000000-0000-0000-0000-000000000001",'
                '"command":{"name":" A é "},"hackathon_id":"00000000-0000-0000-0000-000000000002",'
                '"operation":"team.create.v1","schema_version":1}')
    assert result.fingerprint.digest == sha256(expected.encode('utf-8')).digest()
    assert idem._command(create(' A é ', team=uuid4()), 'other').fingerprint == result.fingerprint
    for changed in (create('A é'), create(' A e\u0301 '), create(' A é ', actor=uuid4()),
                    create(' A é ', hackathon=uuid4())):
        assert idem._command(changed, 'Key').fingerprint != result.fingerprint
    # A literal backslash-u sequence is valid text, unlike an actual NUL.
    assert idem._command(create(r'\u0000'), 'Key')


def test_join_fingerprint_includes_target_and_operation():
    join = _JoinTeamCommand(HACKATHON, TEAM, ACTOR)
    result = idem._command(join, 'key')
    assert result.operation == 'team.join.v1'
    assert result.fingerprint != idem._command(create(), 'key').fingerprint
    assert result.fingerprint != idem._command(_JoinTeamCommand(HACKATHON, uuid4(), ACTOR), 'key').fingerprint


@pytest.mark.parametrize('value', [create(''), create(' '*3), create('x'*121), create('\x00'),
                                   create('\ud800'), create(actor='uuid'), create(hackathon=None),
                                   _JoinTeamCommand(HACKATHON, 'uuid', ACTOR), object()])
def test_invalid_meaningful_commands_fail_before_sql(value):
    error_code(ErrorCode.INVALID_INPUT, idem._command, value, 'key')


def test_private_values_are_frozen_and_sensitive_fields_are_not_represented():
    value = command('sensitive-key')
    with pytest.raises(FrozenInstanceError):
        value.key = 'replacement'
    assert 'sensitive-key' not in repr(value) and value.fingerprint.digest.hex() not in repr(value.fingerprint)
    stored = reply()
    body = stored.body()
    body['data']['id'] = 'changed'
    assert stored.body()['data']['id'] == str(TEAM)
    assert str(TEAM) not in repr(stored)


@pytest.mark.parametrize(('status', 'body', 'headers'), [
    (400, {'schema_version': 1, 'data': {}}, {}), (True, {'schema_version': 1, 'data': {}}, {}),
    (201, {'data': {}}, {}), (201, {'schema_version': 2, 'data': {}}, {}),
    (201, {'schema_version': True, 'data': {}}, {}), (201, {'schema_version': 1, 'data': []}, {}),
    (201, {'schema_version': 1, 'data': {'x': float('nan')}}, {}),
    (201, {'schema_version': 1, 'data': {'x': 1e20}}, {}),
    (201, {'schema_version': 1, 'data': {'x': '\ud800'}}, {}),
    (201, {'schema_version': 1, 'data': {'x': '\x00'}}, {}),
    (201, {'schema_version': 1, 'data': {'x': 2**64}}, {}),
    (201, {'schema_version': 1, 'data': {'x': 'a'*4097}}, {}),
    (201, {'schema_version': 1, 'data': {'x': ['a'*4096]*5}}, {}),
    (201, {'schema_version': 1, 'data': {'x': list(range(129))}}, {}),
    (201, {'schema_version': 1, 'data': {'x': object()}}, {}),
    (201, {'schema_version': 1, 'data': {}}, {'set-cookie': 'secret'}),
    (201, {'schema_version': 1, 'data': {}}, {'Content-Type': 'application/json'}),
    (201, {'schema_version': 1, 'data': {}}, {'content-type': 'text/html\r\nx: y'}),
])
def test_reply_validation_rejects_errors_unversioned_unbounded_or_unsafe_values(status, body, headers):
    error_code(ErrorCode.INTEGRITY_FAULT, idem._StoredReply._from_values, status, body, headers)


def test_reply_depth_and_cycles_are_bounded():
    cyclic = []
    cyclic.append(cyclic)
    error_code(ErrorCode.INTEGRITY_FAULT, idem._StoredReply._from_values, 200,
               {'schema_version': 1, 'data': {'cycle': cyclic}}, {})
    huge = {str(i): list(range(100)) for i in range(20)}
    error_code(ErrorCode.INTEGRITY_FAULT, idem._StoredReply._from_values, 200,
               {'schema_version': 1, 'data': huge}, {})


class Connection:
    def __init__(self):
        self.dialect = SimpleNamespace(name='postgresql', driver='psycopg', is_async=False)
        self.connection = SimpleNamespace(dbapi_connection=SimpleNamespace(autocommit=False))
        self.transaction = SimpleNamespace(is_active=True)
        self.isolation = 'READ COMMITTED'
        self.nested = False
        self.calls = []
        self.results = []

    def get_transaction(self):
        return self.transaction

    def in_transaction(self):
        return self.transaction is not None

    def in_nested_transaction(self):
        return self.nested

    def get_isolation_level(self):
        return self.isolation

    def execute(self, statement, parameters):
        self.calls.append((str(statement), parameters))
        value = self.results.pop(0)
        return SimpleNamespace(scalar_one_or_none=lambda: value,
                               mappings=lambda: SimpleNamespace(one_or_none=lambda: value))


@pytest.mark.parametrize('unsafe', ['autocommit', 'no-transaction', 'inactive', 'nested', 'isolation', 'driver', 'unreadable'])
def test_guard_rejects_unsafe_connection_before_sql(unsafe):
    c = Connection()
    if unsafe == 'autocommit':
        c.connection.dbapi_connection.autocommit = True
    elif unsafe == 'no-transaction':
        c.transaction = None
    elif unsafe == 'inactive':
        c.transaction.is_active = False
    elif unsafe == 'nested':
        c.nested = True
    elif unsafe == 'isolation':
        c.isolation = 'REPEATABLE READ'
    elif unsafe == 'driver':
        c.dialect.driver = 'other'
    else:
        c.connection = None
    error_code(ErrorCode.TRANSACTION_CONFIGURATION, idem._reserve_in_tx, c, command())
    assert c.calls == []


def test_reservation_and_completion_use_supplied_connection_and_single_active_transaction():
    c, record_id = Connection(), uuid4()
    c.results = [record_id, record_id]
    reserved = idem._reserve_in_tx(c, command())
    assert reserved.connection is c and reserved.transaction is c.transaction
    stored = reply()
    assert idem._complete_in_tx(c, reserved, stored) is stored
    assert len(c.calls) == 2
    insert, update = c.calls
    assert 'ON CONFLICT ON CONSTRAINT uq_idempotency_scope DO NOTHING RETURNING id' in insert[0]
    assert json.loads(update[1]['body']) == stored.body()
    assert update[1]['fingerprint'] == command().fingerprint.digest
    assert update[1]['id'] == record_id


def completed_row():
    cmd = command()
    return dict(actor_id=cmd.actor_id, hackathon_id=cmd.hackathon_id, operation=cmd.operation,
                key=cmd.key, request_hash=cmd.fingerprint.digest, state='completed',
                http_status=reply().http_status, response_body=reply().body(),
                response_headers=dict(reply().headers))


def test_conflict_replay_reads_in_a_separate_statement_without_second_write():
    c = Connection()
    c.results = [None, completed_row()]
    assert idem._reserve_in_tx(c, command()) == reply()
    assert len(c.calls) == 2 and c.calls[1][0].lstrip().startswith('SELECT')
    assert 'FOR UPDATE' not in c.calls[1][0]  # Completed rows are database-immutable.


@pytest.mark.parametrize(('field', 'value', 'code'), [
    ('request_hash', b'x'*32, ErrorCode.IDEMPOTENCY_MISMATCH),
    ('hackathon_id', UUID(int=8), ErrorCode.IDEMPOTENCY_MISMATCH),
    ('state', 'pending', ErrorCode.INTEGRITY_FAULT),
    ('actor_id', UUID(int=8), ErrorCode.INTEGRITY_FAULT),
    ('operation', 'other', ErrorCode.INTEGRITY_FAULT),
    ('key', 'other', ErrorCode.INTEGRITY_FAULT),
    ('request_hash', b'short', ErrorCode.INTEGRITY_FAULT),
    ('http_status', 500, ErrorCode.INTEGRITY_FAULT),
    ('response_body', {}, ErrorCode.INTEGRITY_FAULT),
    ('response_headers', {'set-cookie': 'sensitive'}, ErrorCode.INTEGRITY_FAULT),
])
def test_conflict_validation_is_fail_closed_and_sanitized(field, value, code):
    c = Connection()
    row = completed_row()
    row[field] = value
    c.results = [None, row]
    error_code(code, idem._reserve_in_tx, c, command())
    assert len(c.calls) == 2


def test_missing_conflict_row_is_an_integrity_fault_without_retry():
    c = Connection()
    c.results = [None, None]
    error_code(ErrorCode.INTEGRITY_FAULT, idem._reserve_in_tx, c, command())
    assert len(c.calls) == 2


@pytest.mark.parametrize('different', ['connection', 'transaction', 'completed'])
def test_completion_cannot_escape_original_transaction_or_repeat(different):
    c, record_id = Connection(), uuid4()
    c.results = [record_id]
    reserved = idem._reserve_in_tx(c, command())
    if different == 'connection':
        target = Connection()
    elif different == 'transaction':
        c.transaction = SimpleNamespace(is_active=True)
        target = c
    else:
        c.results = [None]
        target = c
    error_code(ErrorCode.INTEGRITY_FAULT, idem._complete_in_tx, target, reserved, reply())
    assert len(c.calls) == (2 if different == 'completed' else 1)
