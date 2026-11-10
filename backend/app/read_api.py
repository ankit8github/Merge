"""Authenticated GET-only discovery. Session identity never comes from the client."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.auth import AuthenticatedSession, AuthFailure, ErrorResponse, authenticated_session, error_response
from app.read_models import HackathonPage, MyTeam, TeamPage, TeamView
from app.services.team_reads import ReadError, TeamReadService


class PageQuery(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    limit: int = Field(default=20, ge=1, le=100)
    cursor: UUID | None = None


def read_request(request: Request):
    allowed = {'limit', 'cursor'} if request.scope['route'].name in ('hackathons', 'teams') else set()
    if (not set(request.query_params) <= allowed
            or any(len(request.query_params.getlist(k))>1 for k in request.query_params)
            or 'x-user-id' in request.headers or 'x-actor-id' in request.headers):
        raise AuthFailure(422, 'invalid_request', 'Request parameters are invalid.')


def get_read_service(request: Request,
                     auth: AuthenticatedSession = Depends(authenticated_session)) -> TeamReadService:
    # Session validation initializes the existing owned runtime Engine lazily.
    # Tests override this dependency and auth services together; no Settings fallback.
    with request.app.state.auth_lock:
        if request.app.state.read_service is None:
            if request.app.state.auth_engine is None:
                raise ReadError()
            request.app.state.read_service = TeamReadService(request.app.state.auth_engine)
        return request.app.state.read_service


router = APIRouter(prefix='/api', tags=['discovery'],
    dependencies=[Depends(authenticated_session), Depends(read_request)],
    responses={status: {'model': ErrorResponse} for status in (401, 403, 404, 422, 503)})


@router.get('/hackathons', response_model=HackathonPage)
def hackathons(page: Annotated[PageQuery, Query()], service: TeamReadService = Depends(get_read_service)):
    return service.hackathons(limit=page.limit, cursor=page.cursor)


@router.get('/hackathons/{hackathon_id}/teams', response_model=TeamPage)
def teams(hackathon_id: UUID, page: Annotated[PageQuery, Query()],
          service: TeamReadService = Depends(get_read_service)):
    return service.teams(hackathon_id, limit=page.limit, cursor=page.cursor)


@router.get('/hackathons/{hackathon_id}/teams/{team_id}', response_model=TeamView)
def team(hackathon_id: UUID, team_id: UUID, service: TeamReadService = Depends(get_read_service)):
    return service.team(hackathon_id, team_id)


@router.get('/hackathons/{hackathon_id}/me/team', response_model=MyTeam)
def my_team(hackathon_id: UUID, auth: AuthenticatedSession = Depends(authenticated_session),
            service: TeamReadService = Depends(get_read_service)):
    return service.my_team(hackathon_id, auth.validated.principal.user_id)


async def read_error_handler(request, error: ReadError):
    status, message = {
        'hackathon_not_found': (404, 'Hackathon was not found.'),
        'team_not_found': (404, 'Team was not found.'),
        'invalid_request': (422, 'Request parameters are invalid.'),
        'service_unavailable': (503, 'Read service unavailable.'),
    }[error.code]
    return error_response(status, error.code, message)
