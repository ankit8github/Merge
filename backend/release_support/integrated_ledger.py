"""Closed campaign ledger; narrows real services, never owns domain transactions.

Only one POST is admitted at a time. A mismatch, interruption or unknown outcome
latches the run closed. Secrets, cookies and authentication bodies are not kept.
"""
from copy import deepcopy
from threading import RLock
from uuid import UUID

from app.auth import AuthFailure
from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import _StoredReply, _key, _canonical
from release_support.integrated_plan import validate_plan, COMMANDS, PROFILE_POSTS


def require(value):
    if not value:
        raise ValueError('Integrated acceptance contract rejected; preserve state and stop')


ORDER = ('create_b', 'create_a', 'create_a', 'request_q', 'request_r',
         'deny_decision', 'reject_r', 'approve_q', 'issue_r', 'deny_redeem',
         'redeem_r', 'deny_remove', 'remove_r', 'leave_q', 'issue_q',
         'redeem_q', 'leave_l', 'final_q')
DENIALS = dict(deny_decision='forbidden',deny_remove='forbidden',deny_redeem='invitation_not_found',
    profile_invalid='invalid_request',profile_stale='profile_changed',missing_session='invalid_session',
    missing_csrf='invalid_csrf',foreign_origin='origin_rejected')


def command_spec(plan, tag, ids, bindings, key):
    """Exact route, body and service values from SERVER-bound identities."""
    row = next(c for c in plan['commands'] if c['tag'] == tag)
    actor = ids[row['actor']]
    h = UUID(plan['hackathons'][1 if tag == 'create_b' else 0]['id'])
    values = dict(hackathon_id=h, actor_id=actor, key=key)
    path = f'/api/hackathons/{h}/teams'
    body = {}
    if tag.startswith('create_'):
        method = 'create_team_idempotent'
        values['name'] = plan['teams']['b' if tag == 'create_b' else 'a']
        body = dict(name=values['name'])
    else:
        values['team_id'] = bindings['a']; path += f"/{bindings['a']}"
        if tag.startswith('request_'):
            method = 'create_request'; path += '/join-requests'
        elif tag in ('deny_decision', 'reject_r', 'approve_q'):
            method = 'decide_request'
            values['request_id'] = bindings['request_q' if tag == 'approve_q' else 'request_r']
            values['decision'] = 'reject' if tag == 'reject_r' else 'approve'
            path += f"/join-requests/{values['request_id']}/decision"
            body = dict(decision=values['decision'])
        elif tag.startswith('issue_'):
            method = 'issue'; values['recipient_id'] = ids['q' if tag == 'issue_q' else 'r']
            path += '/invitations'; body = dict(recipient_id=str(values['recipient_id']))
        elif tag in ('deny_redeem', 'redeem_r', 'redeem_q'):
            method = 'redeem'; values['invitation_id'] = bindings['issue_q' if tag == 'redeem_q' else 'issue_r']
            path += f"/invitations/{values['invitation_id']}/redeem"
        elif tag in ('deny_remove', 'remove_r'):
            method = 'remove'; values['user_id'] = ids['r']; path += f"/members/{ids['r']}/remove"
        else:
            method = 'leave'; path += '/leave'
    return path, body, method, values


def fingerprint(method, v):
    from app.services.idempotency import _command
    from app.services.teams import _CreateTeamRequest
    from app.services.admission import _command as admission
    from app.services.invitations import command as invitation
    from app.services.lifecycle import command as lifecycle
    h,a,k = v['hackathon_id'],v['actor_id'],v['key']
    if method == 'create_team_idempotent': return _command(_CreateTeamRequest(h,a,v['name']),k)
    t = v['team_id']
    if method == 'create_request': return admission(h,t,a,k)
    if method == 'decide_request': return admission(h,t,a,k,v['request_id'],v['decision'])
    if method == 'issue': return invitation(h,t,a,k,recipient=v['recipient_id'])
    if method == 'redeem': return invitation(h,t,a,k,invitation=v['invitation_id'])
    return lifecycle(h,t,a,k,v.get('user_id'))


class Ledger:
    def __init__(self, plan):
        self.plan = deepcopy(validate_plan(plan)); self.lock = RLock()
        self.ids, self.bindings, self.calls, self.statuses = {}, {}, {}, {}
        self.auth_used, self.invitation_used = {}, {}
        self.denials = {}
        self.total = 0; self.domain_index = 0; self.active = None; self.failed = False

    def stop(self):
        self.failed = True
        raise AuthFailure(403, 'browser_scope_rejected', 'Campaign scope rejected; stop.')

    def actor(self, user):
        with self.lock:
            role = next((r for r,u in self.ids.items() if u == user),None)
            if role is None: self.stop()
            return role

    def principal(self, principal):
        role = self.actor(principal.user_id)
        if principal.username != next(a['username'] for a in self.plan['accounts'] if a['role'] == role): self.stop()
        return role

    def bind_account(self, identity):
        with self.lock:
            tag = self.active and self.active['tag']
            require(tag and tag.startswith('register_'))
            role = tag.removeprefix('register_')
            account = next(a for a in self.plan['accounts'] if a['role'] == role)
            if identity.username != account['username'] or role in self.ids or identity.user_id in self.ids.values(): self.stop()
            self.ids[role] = identity.user_id

    def begin(self):
        with self.lock:
            if self.failed or self.active is not None or self.total >= 38: self.stop()
            self.total += 1
            self.active = {'tag':None, 'expected':None, 'invoked':False}

    def claim(self, path, body, role=None, key=None, probe=None):
        """Called after begin and real read-only session validation, before writes."""
        with self.lock:
            if self.failed or self.active is None or self.active['tag'] is not None: self.stop()
            if probe:
                expected = {'missing_session':401,'missing_csrf':403,'foreign_origin':403}
                if (probe not in expected or probe in self.statuses or path != '/api/me/profile'
                        or body != dict(self.plan['profile_values']['l'], version=2)
                        or (probe != 'missing_session' and role != 'l')): self.stop()
                tag,status = probe,expected[probe]
            elif path in ('/auth/register','/auth/login','/auth/logout'):
                op = path.rsplit('/',1)[1]
                if op != 'logout':
                    role = next((a['role'] for a in self.plan['accounts'] if a['username'] == body.get('username')),None)
                if role not in ('l','q','r','x'): self.stop()
                account = next(a for a in self.plan['accounts'] if a['role'] == role)
                used = self.auth_used.get((role,op),0)
                if (used >= account[op+'_attempts'] or (op == 'login' and role not in self.ids)
                        or (op == 'login' and used == 1 and self.statuses.get('logout_x') != [204])
                        or (op == 'logout' and body != {})): self.stop()
                tag,status = f'{op}_{role}',201 if op == 'register' else 204 if op == 'logout' else 200
                self.auth_used[(role,op)] = used + 1
            elif path == '/api/me/profile':
                tag = 'profile_'+str(role)
                initial = self.plan['profile_values'].get(role)
                if tag in self.statuses:
                    if role != 'l' or any('profile_'+r not in self.statuses for r in ('l','q','r','x')): self.stop()
                    tag = next((t for t in ('profile_invalid','profile_edit','profile_stale') if t not in self.statuses),None)
                    initial = dict(initial,version=1)
                    if tag == 'profile_invalid': initial['timezone'] = 'Mars/Base'
                if not tag or body != initial: self.stop()
                status = next(s for t,r,s in PROFILE_POSTS if t == tag)
            else:
                if self.domain_index >= len(ORDER) or 'profile_stale' not in self.statuses: self.stop()
                tag = ORDER[self.domain_index]
                row = next(c for c in self.plan['commands'] if c['tag'] == tag)
                if role != row['actor']: self.stop()
                try:
                    _key(key)
                    route,payload,method,values = command_spec(self.plan,tag,self.ids,self.bindings,key)
                except (ValueError, KeyError, DomainError): self.stop()
                if path != route or body != payload: self.stop()
                fp = fingerprint(method, values)
                old = self.calls.get(tag)
                if old:
                    # Only an already KNOWN successful creation can replay.
                    if tag != 'create_a' or old['values'] != values or old.get('reply') is None: self.stop()
                elif any(c['values']['actor_id'] == values['actor_id'] and c['values']['key'] == key for c in self.calls.values()):
                    self.stop()
                else:
                    self.calls[tag] = dict(method=method,values=values,fp=fp,reply=None)
                self.active.update(method=method,values=values)
                status = row['status']
            self.active.update(tag=tag,expected=status)
            return tag

    def invoke(self, real, method, values):
        with self.lock:
            active = self.active
            if (self.failed or not active or active.get('method') != method
                    or active.get('values') != values or active['invoked']): self.stop()
            active['invoked'] = True; tag = active['tag']; call = self.calls[tag]
        try:
            reply = getattr(real,method)(**values)
        except DomainError as error:
            expected = {'deny_decision':ErrorCode.FORBIDDEN,'deny_remove':ErrorCode.FORBIDDEN,
                        'deny_redeem':ErrorCode.INVITATION_NOT_FOUND}
            if error.code != expected.get(tag): self.failed = True
            raise
        except BaseException:
            self.failed = True; raise
        with self.lock:
            if not isinstance(reply,_StoredReply) or active['expected'] >= 400: self.stop()
            old = call.get('reply')
            if old and (old.body() != reply.body() or old.http_status != reply.http_status or old.headers != reply.headers): self.stop()
            call['reply'] = reply
            binding = 'a' if tag == 'create_a' else 'b' if tag == 'create_b' else tag if tag.startswith(('request_','issue_')) else None
            if binding:
                value = UUID(reply.body()['data']['team_id' if binding in ('a','b') else 'id'])
                if binding in self.bindings and self.bindings[binding] != value: self.stop()
                self.bindings[binding] = value
        return reply

    def invitation_charge(self, actor, op):
        with self.lock:
            if not self.active or self.active.get('method') != ('issue' if op == 'issue' else 'redeem') or self.active['values']['actor_id'] != actor: self.stop()
            pair = (self.actor(actor),op)
            self.invitation_used[pair] = self.invitation_used.get(pair,0)+1

    def finish(self, status, completed=True, error_code=None):
        with self.lock:
            active = self.active
            if (not completed or self.failed or not active or active['tag'] is None
                    or status != active['expected']
                    or (active['tag'] in DENIALS and error_code != DENIALS[active['tag']])
                    or ('method' in active and not active['invoked'])):
                self.failed = True; self.active = None
                raise ValueError('Incomplete or unexpected POST; run closed')
            tag = active['tag']; self.statuses.setdefault(tag,[]).append(status)
            if tag in DENIALS:self.denials[tag]=error_code
            if tag in ORDER: self.domain_index += 1
            self.active = None

    def read(self, h=None, t=None, actor=None):
        if self.failed: self.stop()
        if h is not None and h not in {UUID(v['id']) for v in self.plan['hackathons']}: self.stop()
        if t is not None and t not in (self.bindings.get('a'),self.bindings.get('b')): self.stop()
        if actor is not None: self.actor(actor)

    def complete(self):
        require(not self.failed and self.active is None and self.total == 38 and self.domain_index == 18)
        require(self.denials==DENIALS)
        require(self.statuses == {
            **{f'register_{r}':[201] for r in ('l','q','r','x')},
            **{f'login_{r}':[200,200] if r == 'l' else [200] for r in ('l','q','r','x')},
            'logout_x':[204], **{t:[s] for t,r,s in PROFILE_POSTS},
            **{t:[s]*n for t,r,n,e,s in COMMANDS},
            'missing_session':[401],'missing_csrf':[403],'foreign_origin':[403]})

    def observer_input(self):
        self.complete()
        return dict(ids={r:str(u) for r,u in self.ids.items()},bindings={k:str(v) for k,v in self.bindings.items()},
            statuses=self.statuses,denials=self.denials,total=self.total,
            calls={t:dict(actor=str(c['fp'].actor_id),hackathon=str(c['fp'].hackathon_id),
                         operation=c['fp'].operation,key=c['fp'].key,request_hash=c['fp'].fingerprint.digest.hex(),
                         reply=None if c['reply'] is None else c['reply'].body(),
                         status=None if c['reply'] is None else c['reply'].http_status,
                         headers=None if c['reply'] is None else dict(c['reply'].headers)) for t,c in self.calls.items()})

    def diagnostics(self):
        """Bounded public counters/tags only, including on an incomplete run."""
        with self.lock:
            return dict(attempted_posts=self.total,completed_posts=sum(len(v) for v in self.statuses.values()),
                domain_attempts_completed=self.domain_index,active_tag=self.active.get('tag') if self.active else None,
                closed=self.failed,statuses=deepcopy(self.statuses),denial_codes=dict(self.denials))
