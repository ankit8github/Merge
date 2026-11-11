"""Cookie-actor invitation inbox, leader issuance and recipient redemption."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator
from app.auth import (AuthenticatedSession, AuthServices, ErrorResponse, StrictBody,
    authenticated_session, get_services, error_response)
from app.admission_api import EmptyBody, stored
from app.read_api import PageQuery
from app.team_api import creation_session, idempotency_key, team_error_handler
from app.services.invitations import InvitationService, InvitationError
from app.services.errors import ErrorCode


class IssueBody(StrictBody):
    recipient_id: StrictStr = Field(min_length=36,max_length=36)

    @field_validator('recipient_id')
    @classmethod
    def valid_recipient(cls, value):
        canonical = str(UUID(value))
        if canonical != value.lower(): raise ValueError('Invalid recipient')
        return canonical


class InvitationView(BaseModel):
    model_config = ConfigDict(extra='forbid',hide_input_in_errors=True)
    id: UUID
    hackathon_id: UUID
    team_id: UUID
    recipient_id: UUID
    issued_by: UUID
    status: Literal['pending','redeemed']
    created_at: datetime
    expires_at: datetime
    redeemed_at: datetime | None


class InvitationReply(StrictBody):
    schema_version: Literal[1]
    data: InvitationView


class InboxItem(InvitationView):
    available: bool


class Inbox(BaseModel):
    model_config = ConfigDict(extra='forbid',hide_input_in_errors=True)
    items: list[InboxItem]
    next_cursor: UUID | None


def get_invitation_service(request: Request,
                           auth: AuthenticatedSession = Depends(authenticated_session)):
    with request.app.state.auth_lock:
        engine = request.app.state.auth_engine
        if engine is None: raise InvitationError(ErrorCode.TRANSACTION_CONFIGURATION)
        return InvitationService(engine)


def mutation_session(request: Request, auth: AuthenticatedSession = Depends(creation_session),
                     services: AuthServices = Depends(get_services)):
    operation = 'issue' if request.scope['route'].name == 'issue_invitation' else 'redeem'
    services.throttle.check_invitation(actor_id=auth.validated.principal.user_id, operation=operation)
    return auth


def inbox_scope(request: Request):
    from app.auth import AuthFailure
    if (not set(request.query_params) <= {'limit','cursor'}
            or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params)
            or 'x-user-id' in request.headers or 'x-actor-id' in request.headers):
        raise AuthFailure(422,'invalid_request','Request parameters are invalid.')


router = APIRouter(prefix='/api/hackathons/{hackathon_id}', tags=['invitations'],
    responses={status:{'model':ErrorResponse} for status in (401,403,404,409,415,422,429,503)})


@router.post('/teams/{team_id}/invitations',status_code=201,response_model=InvitationReply)
def issue_invitation(hackathon_id: UUID,team_id: UUID,body: IssueBody,
                     auth: AuthenticatedSession = Depends(mutation_session),key: str = Depends(idempotency_key),
                     service: InvitationService = Depends(get_invitation_service)):
    return stored(service.issue(hackathon_id=hackathon_id,team_id=team_id,
        actor_id=auth.validated.principal.user_id,recipient_id=UUID(body.recipient_id),key=key))


@router.post('/teams/{team_id}/invitations/{invitation_id}/redeem',response_model=InvitationReply)
def redeem_invitation(hackathon_id: UUID,team_id: UUID,invitation_id: UUID,body: EmptyBody,
                      auth: AuthenticatedSession = Depends(mutation_session),key: str = Depends(idempotency_key),
                      service: InvitationService = Depends(get_invitation_service)):
    return stored(service.redeem(hackathon_id=hackathon_id,team_id=team_id,
        actor_id=auth.validated.principal.user_id,invitation_id=invitation_id,key=key))


@router.get('/invitations/mine',response_model=Inbox,dependencies=[Depends(inbox_scope)])
def own_invitations(hackathon_id: UUID,page: Annotated[PageQuery,Query()],
                    auth: AuthenticatedSession = Depends(authenticated_session),
                    service: InvitationService = Depends(get_invitation_service)):
    return service.mine(hackathon_id=hackathon_id,actor_id=auth.validated.principal.user_id,
        limit=page.limit,cursor=page.cursor)


async def invitation_error_handler(request,error):
    mapped = {
        ErrorCode.FORBIDDEN:(403,'forbidden','Current leadership is required.'),
        ErrorCode.USER_NOT_FOUND:(404,'recipient_not_found','Recipient was not found.'),
        ErrorCode.TEAM_NOT_FOUND:(404,'team_not_found','Team was not found.'),
        ErrorCode.INVITATION_NOT_FOUND:(404,'invitation_not_found','Invitation was not found.'),
        ErrorCode.INVITATION_EXPIRED:(409,'invitation_expired','Invitation has expired.'),
        ErrorCode.INVITATION_STALE:(409,'invitation_stale','The issuing leader is no longer current.'),
        ErrorCode.INVITATION_REDEEMED:(409,'invitation_redeemed','Invitation was already redeemed.'),
        ErrorCode.TEAM_FULL:(409,'team_full','Team has no available seat.'),
    }
    if error.code in mapped: return error_response(*mapped[error.code])
    return await team_error_handler(request,error)
