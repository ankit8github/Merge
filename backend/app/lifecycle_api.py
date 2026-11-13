"""Session-actor lifecycle endpoints; no route owns a transaction."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, model_validator
from app.auth import AuthenticatedSession, AuthFailure, ErrorResponse, authenticated_session, error_response
from app.admission_api import EmptyBody, stored
from app.read_api import PageQuery
from app.team_api import creation_session, idempotency_key
from app.services.errors import ErrorCode
from app.services.lifecycle import LifecycleError, LifecycleService


class LifecycleData(BaseModel):
    hackathon_id: UUID
    team_id: UUID
    user_id: UUID
    member_count: int = Field(ge=0)
    team_version: int = Field(ge=2)
    leader_user_id: UUID | None
    deleted: bool

    @model_validator(mode='after')
    def consistent(self):
        if self.deleted != (self.member_count == 0) or self.deleted != (self.leader_user_id is None):
            raise ValueError('Invalid lifecycle receipt')
        return self


class LifecycleReply(BaseModel):
    schema_version: Literal[1]
    data: LifecycleData


class Member(BaseModel):
    user_id: UUID
    display_name: str = Field(min_length=1, max_length=80)
    joined_at: datetime


class Roster(BaseModel):
    items: list[Member]
    next_cursor: UUID | None


def get_lifecycle_service(request: Request, auth: AuthenticatedSession = Depends(authenticated_session)):
    engine = request.app.state.auth_engine
    if engine is None: raise LifecycleError(ErrorCode.TRANSACTION_CONFIGURATION)
    return LifecycleService(engine)


def roster_scope(request: Request):
    if (not set(request.query_params) <= {'limit','cursor'}
            or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params)
            or 'x-user-id' in request.headers or 'x-actor-id' in request.headers):
        raise AuthFailure(422,'invalid_request','Request parameters are invalid.')


router = APIRouter(prefix='/api/hackathons/{hackathon_id}/teams/{team_id}', tags=['team lifecycle'],
    responses={status: {'model': ErrorResponse} for status in (401,403,404,409,415,422,503)})


@router.post('/leave', response_model=LifecycleReply)
def leave(hackathon_id: UUID, team_id: UUID, body: EmptyBody,
          auth: AuthenticatedSession = Depends(creation_session), key: str = Depends(idempotency_key),
          service: LifecycleService = Depends(get_lifecycle_service)):
    return stored(service.leave(hackathon_id=hackathon_id, team_id=team_id,
        actor_id=auth.validated.principal.user_id, key=key))


@router.post('/members/{user_id}/remove', response_model=LifecycleReply)
def remove(hackathon_id: UUID, team_id: UUID, user_id: UUID, body: EmptyBody,
           auth: AuthenticatedSession = Depends(creation_session), key: str = Depends(idempotency_key),
           service: LifecycleService = Depends(get_lifecycle_service)):
    return stored(service.remove(hackathon_id=hackathon_id, team_id=team_id,
        actor_id=auth.validated.principal.user_id, user_id=user_id, key=key))


@router.get('/members', response_model=Roster, dependencies=[Depends(roster_scope)])
def members(hackathon_id: UUID, team_id: UUID, page: Annotated[PageQuery, Query()],
            auth: AuthenticatedSession = Depends(authenticated_session), service: LifecycleService = Depends(get_lifecycle_service)):
    return service.members(hackathon_id=hackathon_id, team_id=team_id,
        actor_id=auth.validated.principal.user_id, limit=page.limit, cursor=page.cursor)


async def lifecycle_error_handler(request, error):
    mapped = {
        ErrorCode.FORBIDDEN: (403,'forbidden','Current team permission is required.'),
        ErrorCode.HACKATHON_NOT_FOUND: (404,'team_not_found','Team is unavailable.'),
        ErrorCode.TEAM_NOT_FOUND: (404,'team_not_found','Team is unavailable.'),
        ErrorCode.MEMBER_NOT_FOUND: (409,'member_not_found','The participant is not currently on this team.'),
        ErrorCode.USE_LEAVE: (422,'use_leave','Use leave for your own membership.'),
        ErrorCode.INVALID_INPUT: (422,'invalid_request','Request is invalid.'),
        ErrorCode.IDEMPOTENCY_MISMATCH: (409,'idempotency_mismatch','The original command differs.'),
        ErrorCode.OUTCOME_UNCERTAIN: (503,'outcome_uncertain','The original outcome is not confirmed.'),
    }
    status,code,message = mapped.get(error.code, (503,'service_unavailable','Team service unavailable.'))
    return error_response(status,code,message,error.retryable)
