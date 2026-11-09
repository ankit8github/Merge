from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException

from app.auth import (AuthBoundary, AuthFailure, auth_failure_handler, credential_handler,
                      http_handler, router, session_handler, validation_handler, throttle_handler)
from app.security.auth_policy import AuthSettings
from app.services.credential_errors import CredentialError
from app.services.session_errors import SessionError
from app.services.throttling import ThrottleExceeded


def create_app(policy: AuthSettings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        try:
            selected = policy if policy is not None else AuthSettings()
        except ValidationError:
            selected = None
        if selected is None:
            raise RuntimeError('Invalid authentication configuration; configure origin, mode and a shared throttle secret.')
        app.state.auth_policy = selected
        app.state.auth_services = None
        app.state.auth_engine = None
        app.state.auth_lock = Lock()
        try:
            yield
        finally:
            if app.state.auth_engine is not None:
                app.state.auth_engine.dispose()

    app = FastAPI(title='Merge', version='0.1.0', lifespan=lifespan)
    app.add_middleware(AuthBoundary)
    app.add_exception_handler(AuthFailure, auth_failure_handler)
    app.add_exception_handler(CredentialError, credential_handler)
    app.add_exception_handler(SessionError, session_handler)
    app.add_exception_handler(ThrottleExceeded, throttle_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(HTTPException, http_handler)
    app.include_router(router)

    @app.get('/health')
    def health() -> dict[str, str]:
        """Process liveness only; no database access."""
        return {'status': 'ok'}

    return app


app = create_app()
