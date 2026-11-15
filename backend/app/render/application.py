"""Production services on Render; lifecycle owns only runtime readiness, no DDL."""
from contextlib import asynccontextmanager
from fastapi import Request
from pydantic import SecretBytes
from starlette.responses import JSONResponse
from app.main import create_app
from app.auth import AuthServices, get_services
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.throttling import ThrottleService, ThrottlePolicy
from app.render import config, database


def create_render_app():
    try:
        selected = config.load()
        policy = selected.auth()
    except Exception:
        raise RuntimeError('Invalid Render configuration; private details suppressed') from None
    app = create_app(policy)
    ordinary_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        async with ordinary_lifespan(app):
            resource = None
            try:
                resource = database.engine(selected)
                database.ready(resource)
                app.state.auth_engine = resource
                app.state.auth_services = AuthServices(CredentialService(resource), SessionService(resource),
                    ThrottleService(resource, secret=SecretBytes(bytes.fromhex(policy.throttle_secret.get_secret_value())), policy=ThrottlePolicy()))
                yield
            except Exception:
                raise RuntimeError('Render runtime failed; private details suppressed') from None
            finally:
                if resource is not None and app.state.auth_engine is None: resource.dispose()
    app.router.lifespan_context = lifespan

    def services(request: Request):
        if request.app.state.auth_services is None: raise RuntimeError('Render services unavailable')
        return request.app.state.auth_services
    app.dependency_overrides[get_services] = services

    @app.get('/ready')
    def readiness():
        try: database.ready(app.state.auth_engine)
        except Exception: return JSONResponse({'status': 'unavailable'}, status_code=503)
        return {'status': 'ready'}
    app.routes[:] = [r for r in app.routes if getattr(r, 'path', None) not in
                    ('/docs', '/docs/oauth2-redirect', '/redoc', '/openapi.json')]
    return app
