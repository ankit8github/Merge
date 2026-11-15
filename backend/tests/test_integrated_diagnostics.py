"""Lifecycle doubles only: no listener, live server, driver or database."""
import json
import signal
from threading import Event
from types import SimpleNamespace

import pytest
import uvicorn

from release_support.integrated_diagnostics import HostDiagnostics, IntegratedServer
from test_support.browser import BrowserServer


@pytest.fixture(autouse=True)
def forbid_live(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Live operation reached in diagnostic regression')
    import psycopg
    import sqlalchemy
    import socket
    monkeypatch.setattr(psycopg, 'connect', forbidden)
    monkeypatch.setattr(sqlalchemy, 'create_engine', forbidden)
    monkeypatch.setattr(socket.socket, 'bind', forbidden)
    monkeypatch.setattr(IntegratedServer, 'run', forbidden)


def server():
    diagnostics = HostDiagnostics()
    return IntegratedServer(uvicorn.Config(object(), log_config=None), diagnostics), diagnostics


def finish(coroutine):
    # Parent doubles complete synchronously. Avoid even Windows asyncio's TCP
    # socketpair used for its internal wakeup pipe; the bind trap stays active.
    try:
        coroutine.send(None)
    except StopIteration:
        return
    finally:
        coroutine.close()
    pytest.fail('Lifecycle double unexpectedly required an event loop')


@pytest.mark.parametrize('outcome', ['ready', 'incomplete', 'exception'])
def test_readiness_requires_completed_uvicorn_startup(monkeypatch, capsys, outcome):
    instance, diagnostics = server()
    async def startup(self, sockets=None):
        assert diagnostics.startup_reached
        assert not diagnostics.readiness_achieved
        if outcome == 'exception':
            raise RuntimeError('synthetic-private-startup-material')
        self.started = outcome == 'ready'
    monkeypatch.setattr(uvicorn.Server, 'startup', startup)
    if outcome == 'exception':
        with pytest.raises(RuntimeError):
            finish(instance.startup())
    else:
        finish(instance.startup())
    assert diagnostics.readiness_achieved == (outcome == 'ready')
    assert ('host ready at' in capsys.readouterr().out) == (outcome == 'ready')
    assert diagnostics.lifecycle_failure == {'ready': None, 'incomplete': 'startup_incomplete',
                                             'exception': 'startup_exception'}[outcome]
    assert 'synthetic-private' not in json.dumps(diagnostics.snapshot())


def test_signal_marks_request_without_claiming_shutdown_completion():
    instance, diagnostics = server()
    instance.handle_exit(signal.SIGINT, None)
    assert instance.should_exit and diagnostics.shutdown_requested
    assert not diagnostics.shutdown_completed
    instance.handle_exit(signal.SIGINT, None)
    assert instance.force_exit and not diagnostics.shutdown_completed


@pytest.mark.parametrize('outcome', ['complete', 'undrained', 'lifespan-failed', 'lifespan-error', 'exception'])
def test_shutdown_completion_requires_real_drain_and_lifespan(monkeypatch, outcome):
    instance, diagnostics = server()
    instance.lifespan = SimpleNamespace(shutdown_failed=outcome == 'lifespan-failed',
                                       error_occurred=outcome == 'lifespan-error')
    async def shutdown(self, sockets=None):
        assert diagnostics.shutdown_requested
        if outcome == 'exception':
            raise RuntimeError('synthetic-private-shutdown-material')
        self.drain_complete = outcome != 'undrained'
    monkeypatch.setattr(BrowserServer, 'shutdown', shutdown)
    if outcome == 'exception':
        with pytest.raises(RuntimeError):
            finish(instance.shutdown())
    else:
        finish(instance.shutdown())
    assert diagnostics.shutdown_completed == (outcome == 'complete')
    assert diagnostics.lifecycle_failure == (None if outcome == 'complete' else
        'shutdown_exception' if outcome == 'exception' else 'shutdown_incomplete')
    assert 'synthetic-private' not in json.dumps(diagnostics.snapshot())


@pytest.mark.parametrize('failed', ['server_started', 'server_drained', 'guard_not_failed',
                                  'mutation_ledger_healthy', 'application_shutdown_complete', None])
def test_each_original_drain_predicate_is_named_without_weakening_it(failed):
    diagnostics = HostDiagnostics()
    guard = SimpleNamespace(failed=Event())
    if failed == 'guard_not_failed':
        guard.failed.set()
    instance = SimpleNamespace(started=failed != 'server_started', drained=lambda: failed != 'server_drained')
    ledger = SimpleNamespace(failed=failed == 'mutation_ledger_healthy')
    app = SimpleNamespace(state=SimpleNamespace(integrated_shutdown_complete=failed != 'application_shutdown_complete'))
    if failed:
        with pytest.raises(ValueError):
            diagnostics.check_drain(instance, guard, ledger, app)
    else:
        diagnostics.check_drain(instance, guard, ledger, app)
    assert diagnostics.failed_predicates == ([failed] if failed else [])


def test_aggregate_counters_never_retain_request_values():
    diagnostics = HostDiagnostics()
    diagnostics.request(dict(method='GET', path='/auth/session',
                             headers=[('cookie', 'synthetic-private-cookie')],
                             query_string=b'synthetic-private-query', body='synthetic-private-body'))
    diagnostics.request(dict(method='POST', path='/synthetic-private-path'))
    diagnostics.validation(); diagnostics.validation(success=True)
    result = diagnostics.snapshot()
    assert result['requests'] == dict(http_requests=2, get_requests=1, authentication_requests=1,
                                     session_validation_attempts=1, session_validation_successes=1)
    assert 'synthetic-private' not in json.dumps(result)
    result['requests']['http_requests'] = 999
    result['failed_predicates'].append('external-change')
    assert diagnostics.snapshot()['requests']['http_requests'] == 2
    assert diagnostics.failed_predicates == []
