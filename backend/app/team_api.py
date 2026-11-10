"""Authenticated create-only HTTP adapter; TeamService owns the complete mutation."""
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import Field, StrictStr, field_validator
from starlette.responses import JSONResponse

from app.auth import (AuthenticatedSession, AuthFailure, AuthServices, ErrorResponse,
                      StrictBody, authenticated_session, decode_token, error_response,
                      get_services)
from app.services.errors import DomainError, ErrorCode
from app.services.idempotency import _key, _StoredReply
from app.services.teams import TeamService


class CreateTeamBody(StrictBody):
    name: StrictStr = Field(min_length=1, max_length=120)

    @field_validator('name')
    @classmethod
    def valid_name(cls, value):
        # Preserve the meaningful command exactly: no trimming/normalization.
        if not value.strip(' ') or '\x00' in value:
            raise ValueError('Invalid team name')
        value.encode('utf-8', errors='strict')
        return value


class CreatedTeamData(StrictBody):
    team_id: UUID
    hackathon_id: UUID
    user_id: UUID
    member_count: Literal[1]
    team_version: Literal[1]


class CreateTeamReply(StrictBody):
    schema_version: Literal[1]
    data: CreatedTeamData


def creation_session(request: Request,
                     auth: AuthenticatedSession = Depends(authenticated_session),
                     services: AuthServices = Depends(get_services)) -> AuthenticatedSession:
    supplied = request.headers.getlist('x-csrf-token')
    csrf = decode_token(supplied[0]) if len(supplied) == 1 else None
    if csrf is None:
        raise AuthFailure(403, 'invalid_csrf', 'A valid CSRF token is required.')
    services.sessions.verify_csrf(auth.bearer.get_secret_value(), csrf)
    if request.query_params or 'x-user-id' in request.headers or 'x-actor-id' in request.headers:
        raise AuthFailure(422, 'invalid_request', 'Request parameters are invalid.')
    return auth


def idempotency_key(request: Request, key: Annotated[str, Header(alias='Idempotency-Key',
                    description='1-128 printable ASCII characters; case and spaces are significant.')]) -> str:
    if len(request.headers.getlist('idempotency-key')) != 1:
        raise AuthFailure(422, 'invalid_request', 'A single valid Idempotency-Key is required.')
    _key(key)  # Existing exact contract, also revalidated by the composed service.
    return key


def get_team_service(request: Request,
                     auth: AuthenticatedSession = Depends(creation_session)) -> TeamService:
    # Authentication owns the lazy Engine. No Settings, fallback or second owner.
    with request.app.state.auth_lock:
        engine = request.app.state.auth_engine
        if engine is None:
            raise DomainError(ErrorCode.TRANSACTION_CONFIGURATION)
        return TeamService(engine)


router = APIRouter(prefix='/api', tags=['team creation'], responses={
    status: {'model': ErrorResponse} for status in (401, 403, 404, 409, 415, 422, 503)
})


@router.post('/hackathons/{hackathon_id}/teams', status_code=201, response_model=CreateTeamReply)
def create_team(hackathon_id: UUID, body: CreateTeamBody,
                auth: AuthenticatedSession = Depends(creation_session),
                key: str = Depends(idempotency_key),
                service: TeamService = Depends(get_team_service)):
    reply = service.create_team_idempotent(hackathon_id=hackathon_id,
        actor_id=auth.validated.principal.user_id, name=body.name, key=key)
    if not isinstance(reply, _StoredReply):
        raise DomainError(ErrorCode.INTEGRITY_FAULT)
    # Return committed/reconciled stored values, never a current-state read or a
    # regenerated DTO. _StoredReply validates its immutable body/header allowlist.
    return JSONResponse(reply.body(), status_code=reply.http_status, headers=dict(reply.headers))


async def team_error_handler(request, error: DomainError):
    if error.code == ErrorCode.OUTCOME_UNCERTAIN:
        return error_response(503, 'outcome_uncertain',
            'Outcome is unknown. Retry with the SAME Idempotency-Key and unchanged request.', True)
    mapped = {
        ErrorCode.INVALID_INPUT: (422, 'invalid_request', 'Request parameters are invalid.'),
        ErrorCode.HACKATHON_NOT_FOUND: (404, 'hackathon_not_found', 'Hackathon was not found.'),
        ErrorCode.ALREADY_ASSIGNED: (409, 'already_assigned', 'You already belong to a team in this hackathon.'),
        ErrorCode.IDEMPOTENCY_MISMATCH: (409, 'idempotency_mismatch',
                                       'Idempotency-Key was used for a different command.'),
    }
    if error.code in mapped:
        return error_response(*mapped[error.code])
    retryable = error.retryable and error.code in (
        ErrorCode.TRANSACTION_CONFLICT, ErrorCode.TRANSACTION_DEADLINE, ErrorCode.LOCK_TIMEOUT)
    return error_response(503, 'service_unavailable', 'Team service unavailable.', retryable)
