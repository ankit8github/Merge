"""Explicit local merge_test browser host. Never a production ASGI entry point."""
import argparse
from contextlib import asynccontextmanager, contextmanager
from getpass import GetPassWarning, getpass
import json
import logging
from pathlib import Path
import secrets
import socket
import sys
from threading import Event, Lock
import warnings

from fastapi import Request
from fastapi.routing import APIRoute, iter_route_contexts
from pydantic import SecretBytes, ValidationError
from sqlalchemy import event, text
import uvicorn

from app import auth, read_api
from app.main import create_app
from app.security.auth_policy import AuthSettings
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.team_reads import TeamReadService
from app.services.throttling import ThrottlePolicy, ThrottleService
from test_support.database import (DiagnosticFailure, TestDatabaseSettings,
                                   assert_test_identity, safe_failure_message,
                                   test_connection)
from test_support.browser_state import RunScope, compare, snapshot

HOST, PORT, ORIGIN = '127.0.0.1', 8000, 'http://127.0.0.1:5173'
REVISION = '0003_auth'


class BrowserPolicy(AuthSettings):
    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings,
                                   dotenv_settings, file_secret_settings):
        return (init_settings,)


def local_policy():
    # Supply EVERY field: MERGE_AUTH_* and dotenv cannot select test policy.
    return BrowserPolicy(mode='development', origin=ORIGIN, throttle_secret=secrets.token_hex(32),
                        trusted_proxies=(), throttle_window_seconds=300,
                        login_account_limit=5, login_ip_limit=30, register_ip_limit=5)


def validate_policy(policy, host):
    if (host != HOST or policy.mode != 'development' or policy.origin != ORIGIN
            or policy.secure or policy.cookie_name != 'merge_session_dev'
            or policy.trusted_proxies != () or policy.throttle_window_seconds != 300
            or (policy.login_account_limit, policy.login_ip_limit, policy.register_ip_limit) != (5, 30, 5)):
        raise DiagnosticFailure('verification')


class ConnectionGuard:
    """Every logical Engine connection, including pool reuse, before service SQL.

    A failure latches this host closed. Independent final observers still verify
    through a fresh guarded engine; they never reuse a suspect pooled connection.
    """
    def __init__(self):
        self.failed = Event()

    def __call__(self, connection):
        try:
            if self.failed.is_set():
                raise DiagnosticFailure('identity')
            dialect = connection.dialect
            if (dialect.name != 'postgresql' or dialect.driver != 'psycopg'
                    or dialect.is_async is not False or connection.in_transaction()
                    or connection.connection.dbapi_connection.autocommit is not False
                    or connection.get_execution_options().get('isolation_level') == 'AUTOCOMMIT'):
                raise DiagnosticFailure('driver-configuration')
            connection.execute(text('SET TRANSACTION READ ONLY'))
            assert_test_identity(connection)
            settings = tuple(connection.execute(text('''SELECT
                current_setting('transaction_isolation'), current_setting('default_transaction_isolation'),
                current_setting('transaction_read_only'), current_setting('lock_timeout'),
                current_setting('statement_timeout')''')).one())
            if settings != ('read committed', 'read committed', 'on', '5s', '15s'):
                raise DiagnosticFailure('identity')
            if connection.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() != [REVISION]:
                raise DiagnosticFailure('migration-state')
            connection.rollback()
        except Exception as error:
            self.failed.set()
            try:
                connection.invalidate()
            except Exception:
                pass
            # Retain no driver error/SQL/parameters in the raised diagnostic.
            category = error.category if isinstance(error, DiagnosticFailure) else 'verification'
            raise DiagnosticFailure(category) from None


@contextmanager
def guarded_engine(settings):
    settings.url()  # Fail before constructing an engine or connecting.
    if not settings.password:
        raise DiagnosticFailure('authentication')
    guard = ConnectionGuard()
    with test_connection(settings) as anchor:
        engine = anchor.engine
        guard(anchor)
        event.listen(engine, 'engine_connect', guard)
        try:
            yield engine, guard
        finally:
            event.remove(engine, 'engine_connect', guard)


class Budget:
    def __init__(self, scope):
        self.accounts = {a.username: a for a in scope.accounts}
        self.used = {}
        self.lock = Lock()

    def principal(self, principal):
        account = self.accounts.get(principal.username)
        if account is None or account.user_id != principal.user_id:
            raise auth.AuthFailure(403, 'browser_scope_rejected', 'Request is outside the approved browser scope.')
        return account

    def charge(self, username, operation):
        with self.lock:
            account = self.accounts.get(username)
            key = (username, operation)
            if account is None or self.used.get(key, 0) >= getattr(account, operation + '_attempts'):
                raise auth.AuthFailure(403, 'browser_scope_rejected', 'Request is outside the approved browser scope.')
            self.used[key] = self.used.get(key, 0) + 1


class ScopedSessions:
    """Real session validation and CSRF remain authoritative; UUIDs only narrow scope."""
    def __init__(self, real, budget):
        self.real, self.budget = real, budget

    def login(self, **values):
        issued = self.real.login(**values)
        self.budget.principal(issued.principal)
        return issued

    def validate_with_csrf(self, token):
        validated = self.real.validate_with_csrf(token)
        self.budget.principal(validated.principal)
        return validated

    def verify_csrf(self, token, csrf):
        principal = self.real.verify_csrf(token, csrf)
        self.budget.principal(principal)
        return principal

    def revoke(self, token):
        principal = self.real.validate(token)
        account = self.budget.principal(principal)
        self.budget.charge(account.username, 'logout')
        self.real.revoke(token)


# Exact closed route/dependency inventory, not names or prefix-based guesses.
ENDPOINTS = {
    ('/auth/register', 'POST'): auth.register, ('/auth/login', 'POST'): auth.login,
    ('/auth/session', 'GET'): auth.current_session, ('/auth/logout', 'POST'): auth.logout,
    ('/api/hackathons', 'GET'): read_api.hackathons,
    ('/api/hackathons/{hackathon_id}/teams', 'GET'): read_api.teams,
    ('/api/hackathons/{hackathon_id}/teams/{team_id}', 'GET'): read_api.team,
    ('/api/hackathons/{hackathon_id}/me/team', 'GET'): read_api.my_team,
}
DEPENDENCIES = {auth.get_services, read_api.get_read_service, auth.authenticated_session,
                auth.session_cookie, read_api.read_request}


def audit_wiring(app, overrides, health_endpoint):
    if (dict(app.dependency_overrides) != overrides or app.state.auth_engine is not None
            or app.state.auth_services is not None or app.state.read_service is not None):
        raise DiagnosticFailure('verification')
    found = {}
    health_count = 0
    def walk(dependency):
        calls = set()
        for child in dependency.dependencies:
            if child.call not in DEPENDENCIES:
                raise DiagnosticFailure('verification')
            calls.add(child.call)
            calls.update(walk(child))
        return calls
    for route in iter_route_contexts(app.routes):
        if not isinstance(route.original_route, APIRoute):
            raise DiagnosticFailure('verification')
        if route.path == '/health' and route.methods == {'GET'}:
            health_count += 1
            if route.endpoint is not health_endpoint or route.dependant.dependencies:
                raise DiagnosticFailure('verification')
            continue
        for method in route.methods:
            if (route.path, method) in found:
                raise DiagnosticFailure('verification')
            found[(route.path, method)] = route.endpoint
        calls = walk(route.dependant)
        expected = {auth.get_services}
        if route.path not in ('/auth/register', '/auth/login'):
            expected.update({auth.authenticated_session, auth.session_cookie})
        if route.path.startswith('/api/'):
            expected.update({read_api.get_read_service, read_api.read_request})
        if calls != expected:
            raise DiagnosticFailure('verification')
    if found != ENDPOINTS or health_count != 1:
        raise DiagnosticFailure('verification')


def browser_app(engine, guard, scope, policy, *, allow_writes=False, host=HOST):
    validate_policy(policy, host)
    if allow_writes is not True:
        raise DiagnosticFailure('verification')
    app = create_app(policy)
    # No new routes, including framework docs/schema endpoints, in this harness.
    app.routes[:] = [r for r in app.routes if getattr(r, 'path', None) not in
                     ('/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc')]
    app.openapi_url = app.docs_url = app.redoc_url = None
    budget = Budget(scope)
    throttle = ThrottleService(engine, secret=SecretBytes(bytes.fromhex(policy.throttle_secret.get_secret_value())),
                               policy=ThrottlePolicy())
    services = auth.AuthServices(CredentialService(engine),
                                ScopedSessions(SessionService(engine), budget), throttle)
    reads = TeamReadService(engine)

    async def scoped_auth(request: Request):
        # AuthBoundary has already checked Origin/media/Fetch Metadata/peer/custom
        # headers. Parse only the existing strict model; never echo invalid input.
        if request.method == 'POST':
            if request.url.path == '/auth/register':
                raise auth.AuthFailure(403, 'browser_scope_rejected', 'Registration is outside the approved browser scope.')
            if request.url.path == '/auth/login':
                try:
                    body = auth.LoginBody.model_validate(await request.json())
                except (ValueError, ValidationError):
                    raise auth.AuthFailure(422, 'invalid_request', 'Request body is invalid.') from None
                if request.state.auth_client_ip != HOST:
                    raise auth.AuthFailure(403, 'browser_scope_rejected', 'Request is outside the approved browser scope.')
                budget.charge(body.username, 'login')
        return services

    def scoped_reads():
        return reads

    overrides = {auth.get_services: scoped_auth, read_api.get_read_service: scoped_reads}
    app.dependency_overrides.update(overrides)
    health_endpoint = next(r.endpoint for r in iter_route_contexts(app.routes) if r.path == '/health')
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with original_lifespan(application):
            audit_wiring(application, overrides, health_endpoint)
            if guard.failed.is_set():
                raise DiagnosticFailure('identity')
            print('Browser host ready; guarded loopback only.', flush=True)
            yield
            audit_wiring(application, overrides, health_endpoint)
            application.state.browser_shutdown_complete = True

    app.router.lifespan_context = lifespan

    # Wrap the complete ASGI app: re-audit BEFORE FastAPI resolves dependencies on
    # every request. Removing an override cannot reach ordinary Settings even once.
    class ClosedHost:
        async def __call__(self, scope, receive, send):
            if scope['type'] == 'http':
                try:
                    audit_wiring(app, overrides, health_endpoint)
                    if guard.failed.is_set():
                        raise DiagnosticFailure('identity')
                except Exception:
                    guard.failed.set()
                    response = auth.error_response(503, 'service_unavailable', 'Browser host guard failed.')
                    response.headers.update({'Cache-Control': 'no-store, private',
                                             'Pragma': 'no-cache', 'Expires': '0',
                                             'X-Content-Type-Options': 'nosniff'})
                    return await response(scope, receive, send)
            try:
                return await app(scope, receive, send)
            except BaseException:
                # Cancellation/drain timeout is inconclusive: a sync worker may
                # still finish. Block later checkouts and never report success.
                guard.failed.set()
                raise

    return ClosedHost(), app, throttle


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes unknown arguments (which could contain secrets).
        self.exit(2, 'Browser host arguments rejected. Use --help; never supply secrets as arguments.\n')


def arguments(argv):
    parser = SafeParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'serve', 'verify'))
    parser.add_argument('--confirm-merge-test', action='store_true', required=True)
    parser.add_argument('--revision', choices=(REVISION,), required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--allow-scoped-auth-writes', action='store_true')
    args = parser.parse_args(argv)
    if args.action == 'serve' and not args.allow_scoped_auth_writes:
        parser.error('Explicit scoped-write opt-in required')
    if args.action != 'serve' and args.allow_scoped_auth_writes:
        parser.error('Read-only command')
    if not __debug__:
        parser.error('Python optimization is forbidden')
    return args


def read_scope(path):
    # Reject duplicate keys, extra fields and accidental credential-bearing files.
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DiagnosticFailure('verification')
            result[key] = value
        return result
    content = path.read_bytes()
    if len(content) > 8192:
        raise DiagnosticFailure('verification')
    parsed = json.loads(content, object_pairs_hook=unique)
    return RunScope.model_validate_json(json.dumps(parsed))


def hidden_password():
    if not sys.stdin.isatty():
        raise DiagnosticFailure('authentication')
    with warnings.catch_warnings():
        warnings.simplefilter('error', GetPassWarning)
        password = getpass('Existing merge_app password (hidden): ')
    if not password:
        raise DiagnosticFailure('authentication')
    return password


@contextmanager
def quiet_logs():
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(previous)


@contextmanager
def reserved_socket(host=HOST):
    if host != HOST:
        raise DiagnosticFailure('verification')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as backend:
        # No SO_REUSEADDR: do not share or take over another listener.
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            backend.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        backend.bind((HOST, PORT))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as frontend:
            frontend.bind((HOST, 5173))
        yield backend


class BrowserServer(uvicorn.Server):
    """Record the drain Uvicorn's shutdown() otherwise swallows on timeout.

    Uvicorn 0.54.0 wait_for cancels _wait_tasks_to_complete on timeout; a zero
    deadline can cancel it before entry. Require positive completion as well as
    a sticky failure bit and empty protocol/task sets. Cancellation is not proof
    that a synchronous request worker or its database transaction has stopped.
    """
    def __init__(self, config):
        super().__init__(config)
        self.drain_complete = False
        self.drain_failed = False

    def drained(self):
        return (self.drain_complete and not self.drain_failed and not self.force_exit
                and not self.server_state.connections and not self.server_state.tasks)

    async def _wait_tasks_to_complete(self):
        try:
            await super()._wait_tasks_to_complete()
        except BaseException:
            self.drain_failed = True
            raise
        self.drain_complete = not (self.force_exit or self.server_state.connections
                                   or self.server_state.tasks)
        if not self.drain_complete:
            self.drain_failed = True

    async def shutdown(self, sockets=None):
        try:
            await super().shutdown(sockets=sockets)
        except BaseException:
            self.drain_failed = True
            raise
        finally:
            if not self.drained():
                self.drain_failed = True


def serve(settings, scope, sock):
    with guarded_engine(settings) as (engine, guard):
        with engine.connect() as connection:
            before = snapshot(connection, scope)
        policy = local_policy()
        host, app, throttle = browser_app(engine, guard, scope, policy, allow_writes=True)
        config = uvicorn.Config(host, host=HOST, port=PORT, workers=1, reload=False,
                                proxy_headers=False, forwarded_allow_ips='', access_log=False,
                                log_config=None, log_level='critical', timeout_graceful_shutdown=25)
        server = BrowserServer(config)
        try:
            print('Browser host preflight verified; awaiting ASGI startup.', flush=True)
            try:
                server.run(sockets=[sock])
            except KeyboardInterrupt:
                pass  # Uvicorn re-raises its first handled signal after graceful shutdown.
        finally:
            if not server.drained():
                server.drain_failed = True
            # The observer is diagnostic after an incomplete drain: workers may
            # still finish. Its result cannot clear the server drain failure.
            with guarded_engine(settings) as (observer, _):
                with observer.connect() as connection:
                    after = snapshot(connection, scope)
            compare(before, after, scope, throttle)
        if (not server.started or not server.drained() or guard.failed.is_set()
                or app.state.auth_engine is not None
                or not getattr(app.state, 'browser_shutdown_complete', False)):
            raise DiagnosticFailure('verification')


def main(argv=None):
    args = arguments(argv)
    try:
        with quiet_logs():
            scope = read_scope(args.manifest)
            if args.action == 'serve':
                with reserved_socket() as sock:
                    settings = TestDatabaseSettings(confirmed=True, password=hidden_password())
                    serve(settings, scope, sock)
                # Only after observer comparison, Engine disposal and socket close.
                print('Browser host final invariants verified; fixtures retained.', flush=True)
            else:
                settings = TestDatabaseSettings(confirmed=True, password=hidden_password())
                with guarded_engine(settings) as (engine, _):
                    with engine.connect() as connection:
                        snapshot(connection, scope)
                print('Browser host read-only scope and invariants verified; no server started.')
    except (Exception, KeyboardInterrupt) as error:
        print(safe_failure_message(error, 'verification'))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
