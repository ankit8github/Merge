"""Bounded SSE leases; all synchronous DB work closes before yield/sleep."""
import asyncio
from collections import Counter
from contextlib import contextmanager
import json
import re
from threading import Lock
from time import monotonic
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect
from starlette.responses import StreamingResponse

from app.auth import AuthenticatedSession, AuthFailure, AuthServices, ErrorResponse, authenticated_session, get_services
from app.services.realtime import RealtimeService
from app.services.team_reads import ReadError
from app.services.session_errors import SessionError, SessionCode

POLL_SECONDS = 2
LEASE_SECONDS = 60
SEND_TIMEOUT_SECONDS = 10


class Subscribers:
    """Per-process resource bound, never domain authority or an event queue."""
    def __init__(self):
        self.lock = Lock()
        self.accounts = Counter()

    @contextmanager
    def claim(self, actor):
        with self.lock:
            if sum(self.accounts.values()) >= 64 or self.accounts[actor] >= 2:
                raise AuthFailure(429, 'stream_limit', 'Too many realtime subscriptions.', True)
            self.accounts[actor] += 1
        try:
            yield
        finally:
            with self.lock:
                self.accounts[actor] -= 1
                if not self.accounts[actor]: del self.accounts[actor]


def get_realtime_service(request: Request, auth: AuthenticatedSession = Depends(authenticated_session)):
    engine = request.app.state.auth_engine
    if engine is None: raise ReadError()
    return RealtimeService(engine)


def stream_request(request: Request):
    ids = request.headers.getlist('last-event-id')
    if (request.query_params or 'x-user-id' in request.headers or 'x-actor-id' in request.headers
            or len(ids) > 1 or (ids and not re.fullmatch(r'[0-9a-f]{64}', ids[0]))):
        raise AuthFailure(422, 'invalid_request', 'Stream parameters are invalid.')


def frame(kind, h, actor, revision=None):
    data = json.dumps(dict(schema_version=1, hackathon_id=str(h), user_id=str(actor)), separators=(',', ':'))
    return (f'id: {revision}\n' if revision is not None else '') + f'event: {kind}\ndata: {data}\n\n'


async def changes(request, h, actor, raw, services, service, initial):
    previous = initial
    started = monotonic()
    yield 'retry: 2000\n\n' + frame('reset', h, actor, initial)
    while monotonic() - started < LEASE_SECONDS:
        await asyncio.sleep(POLL_SECONDS)
        if await request.is_disconnected(): return
        try:
            def sample():
                principal = services.sessions.validate(raw)
                if principal.user_id != actor:
                    raise SessionError(SessionCode.INVALID_SESSION)
                return service.revision(h, actor)
            current = await run_in_threadpool(sample)
        except SessionError as error:
            yield frame('expired' if error.code == SessionCode.INVALID_SESSION else 'unavailable', h, actor)
            return
        except Exception:
            yield frame('unavailable', h, actor)
            return
        if await request.is_disconnected(): return
        if current != previous:
            previous = current
            yield frame('invalidate', h, actor, current)
        else:
            yield ': keepalive\n\n'


router = APIRouter(prefix='/api/hackathons/{hackathon_id}', tags=['realtime'],
    responses={status: {'model': ErrorResponse} for status in (401,403,404,422,429,503)})


class EventStream(StreamingResponse):
    def __init__(self, body, claim):
        super().__init__(body, media_type='text/event-stream',
            headers={'Cache-Control':'no-store', 'X-Accel-Buffering':'no'})
        self.claim = claim

    async def __call__(self, scope, receive, send):
        async def bounded_send(message):
            # A stalled socket must not retain a subscriber slot indefinitely.
            await asyncio.wait_for(send(message), SEND_TIMEOUT_SECONDS)
        try:
            await super().__call__(scope, receive, bounded_send)
        except (TimeoutError, ClientDisconnect):
            pass  # Transport is no longer useful; no error payload after headers.
        finally:
            # Includes cancellation/failure while sending headers, before body starts.
            try:
                await self.body_iterator.aclose()
            finally:
                self.claim.__exit__(None, None, None)


@router.get('/events', dependencies=[Depends(stream_request)], response_class=StreamingResponse,
            responses={200: {'content': {'text/event-stream': {}}}})
async def events(hackathon_id: UUID, request: Request,
                 auth: AuthenticatedSession = Depends(authenticated_session),
                 services: AuthServices = Depends(get_services),
                 service: RealtimeService = Depends(get_realtime_service)):
    actor = auth.validated.principal.user_id
    # Claim before DB sampling/headers; release even if sampling fails.
    claim = request.app.state.realtime_subscribers.claim(actor)
    try:
        claim.__enter__()
    except AuthFailure:
        from app.auth import error_response
        response = error_response(429, 'stream_limit', 'Too many realtime subscriptions.', True)
        response.headers['Retry-After'] = '5'
        return response
    try:
        initial = await run_in_threadpool(service.revision, hackathon_id, actor)
    except BaseException:
        claim.__exit__(None, None, None)
        raise
    return EventStream(changes(request, hackathon_id, actor, auth.bearer.get_secret_value(),
        services, service, initial), claim)
