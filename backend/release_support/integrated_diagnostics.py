"""Fixed lifecycle flags and aggregate counters; never retain request material."""
from threading import Lock

from test_support.browser import BrowserServer


class HostDiagnostics:
    def __init__(self):
        self.startup_reached = False
        self.readiness_achieved = False
        self.shutdown_requested = False
        self.shutdown_completed = False
        self.run_returned = False
        self.interrupted = False
        self.drain_failure_latched_guard = False
        self.lifecycle_failure = None
        self.failed_predicates = []
        self._lock = Lock()
        self._counts = dict(http_requests=0, get_requests=0, authentication_requests=0,
                            session_validation_attempts=0, session_validation_successes=0)

    def request(self, scope):
        # Read only the method and fixed route classification. Store neither.
        with self._lock:
            self._counts['http_requests'] += 1
            self._counts['get_requests'] += int(scope['method'] == 'GET')
            self._counts['authentication_requests'] += int(scope['path'] in
                ('/auth/register', '/auth/login', '/auth/logout', '/auth/session'))

    def validation(self, *, success=False):
        with self._lock:
            key = 'session_validation_successes' if success else 'session_validation_attempts'
            self._counts[key] += 1

    def snapshot(self):
        with self._lock:
            counts = self._counts.copy()
        return dict(startup_reached=self.startup_reached, readiness_achieved=self.readiness_achieved,
                    shutdown_requested=self.shutdown_requested, shutdown_completed=self.shutdown_completed,
                    run_returned=self.run_returned, interrupted=self.interrupted,
                    drain_failure_latched_guard=self.drain_failure_latched_guard,
                    lifecycle_failure=self.lifecycle_failure, failed_predicates=list(self.failed_predicates),
                    requests=counts)

    def check_drain(self, server, guard, ledger, app):
        checks = dict(server_started=server.started, server_drained=server.drained(),
                      guard_not_failed=not guard.failed.is_set(), mutation_ledger_healthy=not ledger.failed,
                      application_shutdown_complete=getattr(app.state, 'integrated_shutdown_complete', False))
        self.failed_predicates = [name for name, passed in checks.items() if not passed]
        if self.failed_predicates:
            raise ValueError('Integrated shutdown checks failed; retain state')


class IntegratedServer(BrowserServer):
    """Observe the existing Uvicorn lifecycle; do not replace its drain protocol."""
    def __init__(self, config, diagnostics):
        super().__init__(config)
        self.diagnostics = diagnostics

    async def startup(self, sockets=None):
        self.diagnostics.startup_reached = True
        try:
            await super().startup(sockets=sockets)
        except BaseException:
            self.diagnostics.lifecycle_failure = 'startup_exception'
            raise
        if self.started:
            self.diagnostics.readiness_achieved = True
            print('Integrated host ready at http://127.0.0.1:8000; campaign not certified.', flush=True)
        else:
            self.diagnostics.lifecycle_failure = 'startup_incomplete'

    def handle_exit(self, sig, frame):
        self.diagnostics.shutdown_requested = True
        super().handle_exit(sig, frame)

    async def shutdown(self, sockets=None):
        self.diagnostics.shutdown_requested = True
        try:
            await super().shutdown(sockets=sockets)
        except BaseException:
            self.diagnostics.lifecycle_failure = 'shutdown_exception'
            raise
        self.diagnostics.shutdown_completed = (self.drained() and not self.lifespan.shutdown_failed
                                               and not self.lifespan.error_occurred)
        if not self.diagnostics.shutdown_completed:
            self.diagnostics.lifecycle_failure = 'shutdown_incomplete'
