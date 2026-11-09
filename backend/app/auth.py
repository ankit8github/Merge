"""HTTP identity adapter. Services own all database transactions; never log inputs."""
from base64 import b64decode, urlsafe_b64encode
from dataclasses import dataclass, field
from datetime import datetime
import re
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, SecretBytes, SecretStr, StrictStr, field_validator
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.security.auth_policy import AuthSettings
from app.security.passwords import valid_password
from app.services.credentials import CredentialService, valid_username
from app.services.credential_errors import CredentialCode, CredentialError
from app.services.sessions import SessionService, ValidatedSession
from app.services.session_errors import SessionCode, SessionError


class AuthFailure(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        self.status, self.code, self.message, self.retryable = status, code, message, retryable
        super().__init__(code)


def error_response(status, code, message, retryable=False):
    return JSONResponse({'error': {'code': code, 'message': message, 'retryable': retryable}},
                        status_code=status)


def encode_token(raw: bytes) -> str:
    return urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def decode_token(value: str | None) -> bytes | None:
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
        return None
    raw = b64decode(value + '=', altchars=b'-_', validate=True)
    return raw if len(raw) == 32 and encode_token(raw) == value else None


class AuthBoundary:
    """Before body parsing: browser policy. On all auth responses: no caching.

    Pure ASGI middleware also sanitizes unexpected failures without logging their
    exception, request headers, body or local variables. Hosting/APM remains trusted.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not (scope['path'] == '/auth' or scope['path'].startswith('/auth/')):
            return await self.app(scope, receive, send)
        request = Request(scope)
        policy = request.app.state.auth_policy
        started = False

        async def private_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
                headers = [(k, v) for k, v in message.get('headers', [])
                           if k.lower() not in (b'cache-control', b'pragma', b'expires')]
                message = {**message, 'headers': headers + [
                    (b'cache-control', b'no-store, private'), (b'pragma', b'no-cache'),
                    (b'expires', b'0'), (b'x-content-type-options', b'nosniff')]}
            await send(message)

        try:
            if policy.secure and scope.get('scheme') != 'https':
                raise AuthFailure(403, 'https_required', 'HTTPS is required.')
            origins = request.headers.getlist('origin')
            sites = request.headers.getlist('sec-fetch-site')
            if (len(origins) > 1 or (origins and origins != [policy.origin])
                    or len(sites) > 1 or (sites and sites[0] not in ('same-origin', 'none'))):
                raise AuthFailure(403, 'origin_rejected', 'Request origin is not allowed.')
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                content = request.headers.getlist('content-type')
                if len(content) != 1 or content[0].split(';', 1)[0].strip().lower() != 'application/json':
                    raise AuthFailure(415, 'unsupported_media_type', 'Use application/json.')
                if origins != [policy.origin]:
                    raise AuthFailure(403, 'origin_rejected', 'Request origin is not allowed.')
                if scope['path'] in ('/auth/register', '/auth/login'):
                    if request.headers.getlist('x-merge-request') != ['1']:
                        raise AuthFailure(403, 'request_header_required', 'Required request header is missing or invalid.')
            await self.app(scope, receive, private_send)
        except AuthFailure as error:
            await error_response(error.status, error.code, error.message, error.retryable)(scope, receive, private_send)
        except Exception:
            if started:
                raise
            await error_response(503, 'service_unavailable', 'Authentication service unavailable.')(scope, receive, private_send)


class StrictBody(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', hide_input_in_errors=True)


class LoginBody(StrictBody):
    username: StrictStr
    password: SecretStr = Field(repr=False)

    @field_validator('username')
    @classmethod
    def username_policy(cls, value):
        if not valid_username(value):
            raise ValueError('Invalid username')
        return value

    @field_validator('password', mode='before')
    @classmethod
    def password_policy(cls, value):
        if not valid_password(value):
            raise ValueError('Invalid password')
        return value


class RegisterBody(LoginBody):
    display_name: StrictStr | None = Field(default=None, min_length=1, max_length=80)

    @field_validator('display_name')
    @classmethod
    def display_policy(cls, value):
        if value is not None:
            if not value.strip(' ') or '\x00' in value:
                raise ValueError('Invalid display name')
            value.encode('utf-8', errors='strict')
        return value


class AccountResponse(BaseModel):
    user_id: UUID
    username: str


class SessionResponse(BaseModel):
    identity: AccountResponse
    expires_at: datetime
    csrf_token: str = Field(repr=False)


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail


@dataclass(frozen=True, repr=False)
class AuthServices:
    credentials: CredentialService
    sessions: SessionService


def get_services(request: Request) -> AuthServices:
    # Lazy runtime-only construction: /health and database-free tests never load
    # database settings or open connections. Tests override this dependency.
    with request.app.state.auth_lock:
        if request.app.state.auth_services is None:
            from app.core.config import Settings
            from app.db.session import build_engine
            engine = build_engine(Settings())
            request.app.state.auth_engine = engine
            request.app.state.auth_services = AuthServices(CredentialService(engine), SessionService(engine))
        return request.app.state.auth_services


def session_cookie(request: Request) -> bytes:
    name = request.app.state.auth_policy.cookie_name
    values = [value for header in request.headers.getlist('cookie')
              for part in header.split(';')
              for key, separator, value in [part.strip().partition('=')]
              if separator and key == name]
    raw = decode_token(values[0]) if len(values) == 1 else None
    if raw is None:
        raise AuthFailure(401, 'invalid_session', 'A valid session is required.')
    return raw


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    validated: ValidatedSession
    bearer: SecretBytes = field(repr=False)


def authenticated_session(raw: bytes = Depends(session_cookie),
                          services: AuthServices = Depends(get_services)) -> AuthenticatedSession:
    return AuthenticatedSession(services.sessions.validate_with_csrf(raw), SecretBytes(raw))


def public_session(validated) -> SessionResponse:
    principal = validated.principal
    return SessionResponse(identity=AccountResponse(user_id=principal.user_id, username=principal.username),
                           expires_at=principal.expires_at,
                           csrf_token=encode_token(validated.csrf_token.get_secret_value()))


router = APIRouter(prefix='/auth', tags=['authentication'], responses={
    status: {'model': ErrorResponse} for status in (401, 403, 409, 415, 422, 503)
})


@router.post('/register', status_code=201, response_model=AccountResponse)
def register(body: RegisterBody, services: AuthServices = Depends(get_services)):
    identity = services.credentials.register(username=body.username, password=body.password.get_secret_value(),
                                             display_name=body.display_name)
    return AccountResponse(user_id=identity.user_id, username=identity.username)


@router.post('/login', response_model=SessionResponse)
def login(body: LoginBody, request: Request, response: Response, services: AuthServices = Depends(get_services)):
    issued = services.sessions.login(username=body.username, password=body.password.get_secret_value())
    policy = request.app.state.auth_policy
    response.set_cookie(policy.cookie_name, encode_token(issued.session_token.get_secret_value()),
                        max_age=8*60*60, expires=issued.principal.expires_at,
                        secure=policy.secure, httponly=True, samesite='lax', path='/')
    return public_session(issued)


@router.get('/session', response_model=SessionResponse)
def current_session(auth: AuthenticatedSession = Depends(authenticated_session)):
    return public_session(auth.validated)


@router.post('/logout', status_code=204)
def logout(body: StrictBody, request: Request, auth: AuthenticatedSession = Depends(authenticated_session),
           services: AuthServices = Depends(get_services)):
    supplied = request.headers.getlist('x-csrf-token')
    raw_csrf = decode_token(supplied[0]) if len(supplied) == 1 else None
    if raw_csrf is None:
        raise AuthFailure(403, 'invalid_csrf', 'A valid CSRF token is required.')
    raw = auth.bearer.get_secret_value()
    services.sessions.verify_csrf(raw, raw_csrf)
    services.sessions.revoke(raw)
    policy = request.app.state.auth_policy
    response = Response(status_code=204)
    response.delete_cookie(policy.cookie_name, path='/', secure=policy.secure, httponly=True, samesite='lax')
    return response


async def auth_failure_handler(request, error):
    return error_response(error.status, error.code, error.message, error.retryable)


async def validation_handler(request, error: RequestValidationError):
    # Pydantic errors include submitted inputs; never serialize .errors() or body.
    return error_response(422, 'invalid_request', 'Request body is invalid.')


async def credential_handler(request, error: CredentialError):
    if error.code == CredentialCode.INVALID_CREDENTIALS:
        return error_response(401, 'invalid_credentials', 'Invalid username or password.')
    if error.code == CredentialCode.USERNAME_UNAVAILABLE:
        return error_response(409, 'username_unavailable', 'Username is unavailable.')
    if error.code == CredentialCode.INVALID_INPUT:
        return error_response(422, 'invalid_request', 'Request body is invalid.')
    retryable = error.code in (CredentialCode.HASHING_BUSY, CredentialCode.TRANSACTION_CONFLICT, CredentialCode.LOCK_TIMEOUT)
    return error_response(503, 'service_unavailable', 'Authentication service unavailable.', retryable)


async def session_handler(request, error: SessionError):
    if error.code == SessionCode.INVALID_CSRF:
        return error_response(403, 'invalid_csrf', 'A valid CSRF token is required.')
    if error.code == SessionCode.INVALID_SESSION:
        return error_response(401, 'invalid_session', 'A valid session is required.')
    if error.code == SessionCode.AUTHENTICATION_CHANGED:
        return error_response(401, 'invalid_credentials', 'Invalid username or password.')
    return error_response(503, 'service_unavailable', 'Authentication service unavailable.')


async def http_handler(request, error: HTTPException):
    return error_response(error.status_code, 'http_error', 'Request could not be handled.')
