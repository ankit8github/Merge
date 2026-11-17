"""Own profile replacement and current-leader teammate suggestions."""
from datetime import datetime
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from app.auth import AuthenticatedSession, AuthFailure, ErrorResponse, authenticated_session, error_response
from app.profile_models import ProfileBody, ProfileView, ZONES
from app.team_api import creation_session
from app.services.profiles import ProfileError, ProfileService
from app.services.matching import MatchingService


class RankQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    limit: int = Field(default=20, ge=1, le=20)
    cursor: str | None = Field(default=None, min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')


class ProfileTimezones(BaseModel):
    items: list[str] = Field(min_length=1, max_length=2048)


class Suggestion(BaseModel):
    user_id: UUID
    display_name: str
    username: str
    skills: list[str]
    timezone: str
    new_skills: list[str]
    skill_complement: float = Field(ge=0, le=1)
    timezone_overlap: float = Field(ge=0, le=1)
    skill_points: float = Field(ge=0, le=70)
    timezone_points: float = Field(ge=0, le=30)
    score: float = Field(ge=0, le=100)


class Suggestions(BaseModel):
    hackathon_id: UUID
    team_id: UUID
    user_id: UUID
    reference_at: datetime
    team_skills: list[str]
    skill_weight: float
    timezone_weight: float
    items: list[Suggestion]
    next_cursor: str | None


def scope(request: Request):
    allowed = {'limit','cursor'} if request.scope['route'].name == 'suggestions' else set()
    if (not set(request.query_params) <= allowed
        or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params)
        or 'x-user-id' in request.headers or 'x-actor-id' in request.headers):
        raise AuthFailure(422,'invalid_request','Request parameters are invalid.')


def get_profile_service(request: Request, auth: AuthenticatedSession = Depends(authenticated_session)):
    engine = request.app.state.auth_engine
    if engine is None:
        raise ProfileError()
    return ProfileService(engine)


def get_matching_service(request: Request, auth: AuthenticatedSession = Depends(authenticated_session)):
    engine = request.app.state.auth_engine
    if engine is None:
        raise ProfileError()
    return MatchingService(engine)


router = APIRouter(prefix='/api', tags=['profiles and matching'], dependencies=[Depends(scope)],
    responses={s:{'model':ErrorResponse} for s in (401,403,404,409,415,422,503)})


@router.get('/profile/timezones', response_model=ProfileTimezones)
def profile_timezones(auth: AuthenticatedSession = Depends(authenticated_session)):
    # Same installed set and exclusions as ProfileBody, including the field bound.
    # Refuse an unexpectedly large/empty catalogue; never return a partial list.
    items = sorted(zone for zone in ZONES if len(zone) <= 64 and zone not in ('localtime', 'Factory'))
    if not 1 <= len(items) <= 2048:
        raise ProfileError()
    return ProfileTimezones(items=items)


@router.get('/me/profile',response_model=ProfileView)
def profile(auth: AuthenticatedSession = Depends(authenticated_session), service: ProfileService = Depends(get_profile_service)):
    return service.get(auth.validated.principal.user_id)


@router.post('/me/profile',response_model=ProfileView)
def update_profile(body: ProfileBody,auth: AuthenticatedSession = Depends(creation_session),
                   service: ProfileService = Depends(get_profile_service)):
    return service.update(auth.validated.principal.user_id,body)


@router.get('/hackathons/{hackathon_id}/teams/{team_id}/suggestions',response_model=Suggestions)
def suggestions(hackathon_id: UUID,team_id: UUID,page: Annotated[RankQuery,Query()],
                auth: AuthenticatedSession = Depends(authenticated_session),
                service: MatchingService = Depends(get_matching_service)):
    return service.suggestions(hackathon_id,team_id,auth.validated.principal.user_id,limit=page.limit,cursor=page.cursor)


async def profile_error_handler(request,error):
    status,message = {
        'profile_changed':(409,'Profile changed. Reload before editing again.'),
        'ranking_changed':(409,'Rankings changed. Restart from the first page.'),
        'forbidden':(403,'Current team leadership is required.'),
        'team_not_found':(404,'Team is unavailable.'),
        'invalid_request':(422,'Request parameters are invalid.'),
        'service_unavailable':(503,'Profile or matching service unavailable.'),
    }[error.code]
    return error_response(status,error.code,message)
