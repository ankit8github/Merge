"""Authenticated request creation/status and current-leader-only decisions."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse

from app.auth import AuthenticatedSession, AuthFailure, ErrorResponse, StrictBody, authenticated_session, error_response
from app.read_api import PageQuery
from app.team_api import creation_session, idempotency_key, team_error_handler
from app.services.admission import AdmissionError, AdmissionService
from app.services.errors import ErrorCode


class EmptyBody(StrictBody):
    pass


class DecisionBody(StrictBody):
    decision: Literal['approve', 'reject']


class RequestView(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    id: UUID
    hackathon_id: UUID
    team_id: UUID
    requester_id: UUID
    status: Literal['pending', 'approved', 'rejected']
    created_at: datetime
    resolved_at: datetime | None


class RequestReply(StrictBody):
    schema_version: Literal[1]
    data: RequestView


class OwnRequest(StrictBody):
    request: RequestView | None


class RequestPage(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    items: list[RequestView]
    next_cursor: UUID | None


def get_admission_service(request: Request,
                          auth: AuthenticatedSession = Depends(authenticated_session)) -> AdmissionService:
    with request.app.state.auth_lock:
        engine = request.app.state.auth_engine
        if engine is None:
            raise AdmissionError(ErrorCode.TRANSACTION_CONFIGURATION)
        return AdmissionService(engine)


def read_scope(request: Request):
    allowed = {'limit', 'cursor'} if request.scope['route'].name == 'pending_requests' else set()
    if (not set(request.query_params) <= allowed
            or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params)
            or 'x-user-id' in request.headers or 'x-actor-id' in request.headers):
        raise AuthFailure(422, 'invalid_request', 'Request parameters are invalid.')


router = APIRouter(prefix='/api/hackathons/{hackathon_id}/teams/{team_id}', tags=['admission'],
    responses={status: {'model': ErrorResponse} for status in (401,403,404,409,415,422,503)})


def stored(reply):
    from app.services.idempotency import _StoredReply
    if not isinstance(reply, _StoredReply):
        raise AdmissionError(ErrorCode.INTEGRITY_FAULT)
    return JSONResponse(reply.body(), status_code=reply.http_status, headers=dict(reply.headers))


@router.post('/join-requests', status_code=201, response_model=RequestReply, responses={200:{'model':RequestReply}})
def create_request(hackathon_id: UUID, team_id: UUID, body: EmptyBody,
                   auth: AuthenticatedSession = Depends(creation_session), key: str = Depends(idempotency_key),
                   service: AdmissionService = Depends(get_admission_service)):
    return stored(service.create_request(hackathon_id=hackathon_id, team_id=team_id,
        actor_id=auth.validated.principal.user_id, key=key))


@router.get('/join-requests/mine', response_model=OwnRequest, dependencies=[Depends(read_scope)])
def own_request(hackathon_id: UUID, team_id: UUID,
                auth: AuthenticatedSession = Depends(authenticated_session),
                service: AdmissionService = Depends(get_admission_service)):
    return service.own_request(hackathon_id=hackathon_id, team_id=team_id, actor_id=auth.validated.principal.user_id)


@router.get('/join-requests', response_model=RequestPage, dependencies=[Depends(read_scope)])
def pending_requests(hackathon_id: UUID, team_id: UUID, page: Annotated[PageQuery, Query()],
                     auth: AuthenticatedSession = Depends(authenticated_session),
                     service: AdmissionService = Depends(get_admission_service)):
    return service.pending_requests(hackathon_id=hackathon_id, team_id=team_id,
        actor_id=auth.validated.principal.user_id, limit=page.limit, cursor=page.cursor)


@router.post('/join-requests/{request_id}/decision', response_model=RequestReply)
def decide_request(hackathon_id: UUID, team_id: UUID, request_id: UUID, body: DecisionBody,
                   auth: AuthenticatedSession = Depends(creation_session), key: str = Depends(idempotency_key),
                   service: AdmissionService = Depends(get_admission_service)):
    return stored(service.decide_request(hackathon_id=hackathon_id, team_id=team_id,
        actor_id=auth.validated.principal.user_id, request_id=request_id, decision=body.decision, key=key))


async def admission_error_handler(request, error):
    mapped = {
        ErrorCode.FORBIDDEN: (403, 'forbidden', 'Current team leadership is required.'),
        ErrorCode.REQUEST_NOT_FOUND: (404, 'request_not_found', 'Request was not found.'),
        ErrorCode.TEAM_NOT_FOUND: (404, 'team_not_found', 'Team was not found.'),
        ErrorCode.REQUEST_RESOLVED: (409, 'request_resolved', 'Request is already resolved.'),
        ErrorCode.TEAM_FULL: (409, 'team_full', 'Team has no available seat.'),
    }
    if error.code in mapped:
        return error_response(*mapped[error.code])
    return await team_error_handler(request, error)
