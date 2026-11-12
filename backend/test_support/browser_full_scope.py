"""Public approval scope and memory-only command ledger; no I/O or authentication."""
from dataclasses import dataclass, field
from threading import RLock
from typing import Literal
from uuid import UUID
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.auth import AuthFailure
from app.services.credentials import valid_username
from app.services.idempotency import _StoredReply, _command as create_command
from app.services.teams import _CreateTeamRequest
from app.services.admission import _command as request_command
from app.services.invitations import command as invitation_command
from app.services.errors import DomainError, ErrorCode
from test_support.database import DiagnosticFailure

ROLES = ('l', 'q', 'r', 'x')
COMMANDS = ('create_a', 'create_b', 'request_q', 'request_r', 'approve_q', 'reject_r',
            'issue_r', 'issue_x', 'redeem_r', 'redeem_x', 'deny_issue_q', 'deny_decide_q', 'deny_redeem_x')
SUCCESS = COMMANDS[:9]


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True, hide_input_in_errors=True)


class Account(Strict):
    role: Literal['l', 'q', 'r', 'x']
    username: str
    register_attempts: int = Field(ge=0, le=1)
    login_attempts: int = Field(ge=0, le=4)
    logout_attempts: int = Field(ge=0, le=4)


class Hackathon(Strict):
    id: UUID
    name: str = Field(min_length=1, max_length=120)


class CommandBudget(Strict):
    command: Literal[*COMMANDS]
    attempts: int = Field(ge=0, le=3)


class FullScope(Strict):
    run_id: UUID
    accounts: tuple[Account, ...] = Field(min_length=4, max_length=4)
    hackathons: tuple[Hackathon, ...] = Field(min_length=2, max_length=2)
    team_a: str = Field(min_length=1, max_length=120)
    team_b: str = Field(min_length=1, max_length=120)
    commands: tuple[CommandBudget, ...] = Field(min_length=len(COMMANDS), max_length=len(COMMANDS))

    @model_validator(mode='after')
    def bounded(self):
        prefix = 'm015b_' + self.run_id.hex[:8] + '_'
        if ({a.role for a in self.accounts} != set(ROLES)
                or self.run_id.version!=4 or any(h.id.version!=4 for h in self.hackathons)
                or any(a.username != prefix+a.role or not valid_username(a.username) for a in self.accounts)
                or len({h.id for h in self.hackathons}) != 2
                or len({h.name for h in self.hackathons})!=2 or self.team_a==self.team_b
                or {c.command for c in self.commands} != set(COMMANDS)):
            raise ValueError('Invalid approval scope')
        for value in (*[h.name for h in self.hackathons], self.team_a, self.team_b):
            if not value.strip(' ') or '\0' in value or not value.startswith(prefix):
                raise ValueError('Invalid fixture label')
            value.encode('utf-8')
        return self


def read_scope(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DiagnosticFailure('verification')
            result[key] = value
        return result
    content = path.read_bytes()
    if len(content) > 16384:
        raise DiagnosticFailure('verification')
    return FullScope.model_validate_json(json.dumps(json.loads(content, object_pairs_hook=unique)))


def rejected():
    raise AuthFailure(403, 'browser_scope_rejected', 'Request is outside the approved browser scope.')


@dataclass(repr=False)
class Attempt:
    method: str
    values: dict = field(repr=False)
    fingerprint: object = field(repr=False)
    reply: object = field(default=None, repr=False)
    error: object = None


class Ledger:
    """Narrow the real services, never substitute an actor or transaction owner."""
    def __init__(self, scope):
        self.scope, self.lock = scope, RLock()
        self.accounts = {a.role: a for a in scope.accounts}
        self.ids, self.bindings, self.used, self.calls = {}, {}, {}, {}
        self.failed = False

    def auth_charge(self, username, operation):
        with self.lock:
            account = next((a for a in self.accounts.values() if a.username == username), None)
            if account is None:
                rejected()
            if operation=='login' and account.role not in self.ids:
                rejected()  # Never adopt a preexisting/unknown registration outcome.
            self.charge((account.role, operation), getattr(account, operation+'_attempts'))

    def charge(self, key, limit):
        if self.used.get(key, 0) >= limit:
            rejected()
        self.used[key] = self.used.get(key, 0) + 1

    def bind_account(self, identity):
        with self.lock:
            role = next((r for r,a in self.accounts.items() if a.username == identity.username), None)
            if (role is None or role in self.ids or identity.user_id in self.ids.values()):
                self.failed = True
                raise DiagnosticFailure('verification')
            self.ids[role] = identity.user_id

    def principal(self, principal):
        role = self.actor(principal.user_id)
        if principal.username != self.accounts[role].username:
            rejected()
        return role

    def actor(self, actor):
        with self.lock:
            role = next((r for r,u in self.ids.items() if u == actor), None)
            if role is None:
                rejected()
            return role

    def read(self, h, t=None, actor=None):
        if h not in {h.id for h in self.scope.hackathons}:
            rejected()
        if t is not None and t not in {self.bindings.get('a'), self.bindings.get('b')}:
            rejected()
        if actor is not None:
            self.actor(actor)

    def resolve(self, method, v):
        """Match a concrete immutable command to the approved journey."""
        role = self.actor(v['actor_id'])
        if v['hackathon_id'] != self.scope.hackathons[0].id:
            rejected()
        a = self.bindings.get('a')
        if method == 'create_team_idempotent':
            tag = 'create_a' if role == 'l' and v['name'] == self.scope.team_a else 'create_b' if role == 'x' and v['name'] == self.scope.team_b else None
            fp = create_command(_CreateTeamRequest(v['hackathon_id'], v['actor_id'], v['name']), v['key'])
        else:
            if a is None or v['team_id'] != a:
                rejected()
            if method == 'create_request':
                tag = 'request_'+role if role in ('q','r') else None
                fp = request_command(v['hackathon_id'], a, v['actor_id'], v['key'])
            elif method == 'decide_request':
                q, r = self.bindings.get('request_q'), self.bindings.get('request_r')
                tag = ('approve_q' if role == 'l' and q is not None and v['request_id'] == q and v['decision'] == 'approve'
                       else 'reject_r' if role == 'l' and r is not None and v['request_id'] == r and v['decision'] == 'reject'
                       else 'deny_decide_q' if role == 'q' and q is not None and v['request_id'] == q and v['decision'] == 'approve' else None)
                fp = request_command(v['hackathon_id'], a, v['actor_id'], v['key'], v['request_id'], v['decision'])
            elif method == 'issue':
                recipient = next((r for r,u in self.ids.items() if u == v['recipient_id']), None)
                tag = 'issue_'+recipient if role == 'l' and recipient in ('r','x') else 'deny_issue_q' if role == 'q' and recipient == 'r' else None
                fp = invitation_command(v['hackathon_id'], a, v['actor_id'], v['key'], recipient=v['recipient_id'])
            elif method == 'redeem':
                grant = next((r for r in ('r','x') if self.bindings.get('issue_'+r) == v['invitation_id']), None)
                tag = 'redeem_'+role if role in ('r','x') and grant == role else 'deny_redeem_x' if role == 'x' and grant == 'r' else None
                fp = invitation_command(v['hackathon_id'], a, v['actor_id'], v['key'], invitation=v['invitation_id'])
            else:
                rejected()
        if tag is None:
            rejected()
        if tag=='redeem_x' and not all(n in self.calls and self.calls[n].reply is not None for n in ('approve_q','redeem_r')):
            rejected()  # This grant is approved only for a genuine full-team denial.
        if tag=='create_b' and ('redeem_x' not in self.calls or self.calls['redeem_x'].error!=ErrorCode.TEAM_FULL):
            rejected()
        return tag, fp

    def reserve(self, method, values):
        with self.lock:
            tag, fp = self.resolve(method, values)
            old = self.calls.get(tag)
            if old and old.values != values:
                rejected()  # Exact original key/body/scope; no new command by accident.
            limit = next(c.attempts for c in self.scope.commands if c.command == tag)
            self.charge(tag, limit)
            if old is None:
                self.calls[tag] = Attempt(method, dict(values), fp)
            return tag

    def invoke(self, real, method, values, *, reserved=None):
        tag = reserved if reserved is not None else self.reserve(method, values)
        call = self.calls[tag]
        if call.values != values or call.method != method:
            rejected()
        try:
            reply = getattr(real, method)(**values)
        except DomainError as error:
            with self.lock:
                call.error = error.code
                if error.code in (ErrorCode.INTEGRITY_FAULT,ErrorCode.DATABASE_FAILURE,ErrorCode.TRANSACTION_CONFIGURATION):
                    self.failed = True
            raise
        except BaseException:
            self.failed = True
            raise
        with self.lock:
            if not isinstance(reply, _StoredReply) or tag.startswith('deny_') or tag == 'redeem_x':
                self.failed = True
                raise DiagnosticFailure('verification')
            if call.reply is not None and (call.reply.body() != reply.body() or call.reply.http_status != reply.http_status or call.reply.headers != reply.headers):
                self.failed = True
                raise DiagnosticFailure('verification')
            call.reply, call.error = reply, None
            data = reply.body()['data']
            binding = 'a' if tag == 'create_a' else 'b' if tag == 'create_b' else tag if tag.startswith(('request_', 'issue_')) else None
            if binding:
                value = UUID(data['team_id'] if binding in ('a','b') else data['id'])
                if binding in self.bindings and self.bindings[binding] != value:
                    self.failed = True
                    raise DiagnosticFailure('verification')
                self.bindings[binding] = value
        return reply
