"""Owner-started fixed loopback benchmark host; no production Settings fallback."""
import argparse
from getpass import getpass
import os
import secrets
from pydantic import SecretBytes
from app.auth import AuthServices,get_services
from app.main import create_app
from app.read_api import get_read_service
from app.realtime_api import get_realtime_service
from app.security.auth_policy import AuthSettings
from app.services.credentials import CredentialService
from app.services.sessions import SessionService
from app.services.team_reads import TeamReadService
from app.services.realtime import RealtimeService
from app.services.throttling import ThrottleService,ThrottlePolicy
from release_support.seed import dataset,validate_database
from release_support.seed import digest
from release_support.targets import Target,guarded_engine

ORIGIN='http://127.0.0.1:8766'


def benchmark_app(engine,hackathon,dataset_sha256):
    secret=secrets.token_bytes(32)
    app=create_app(AuthSettings(mode='development',origin=ORIGIN,throttle_secret=secret.hex()))
    allowed={'/health','/auth/session',f'/api/hackathons/{{hackathon_id}}/teams',f'/api/hackathons/{{hackathon_id}}/events'}
    app.routes[:]=[r for r in app.routes if getattr(r,'path',None) in allowed and getattr(r,'methods',set())=={'GET'}]
    # FastAPI's installed included routers are lazy containers; filter concrete
    # route inventory by flattening through the same documented app.routes surface.
    if not any(getattr(r,'path',None)=='/auth/session' for r in app.routes):
        from app.auth import router as auth_router
        from app.read_api import router as read_router
        from app.realtime_api import router as realtime_router
        app.routes[:]=[r for router in (auth_router,read_router,realtime_router) for r in router.routes if getattr(r,'path',None) in allowed]
        @app.get('/health')
        def health():return {'status':'ok'}
    @app.middleware('http')
    async def scope(request,call_next):
        from starlette.responses import JSONResponse
        if request.url.path.startswith('/api/') and request.url.path!='/api/benchmark/preflight' and not request.url.path.startswith(f'/api/hackathons/{hackathon}/'):
            return JSONResponse({'error':{'code':'forbidden','message':'Benchmark scope required.','retryable':False}},status_code=403)
        return await call_next(request)
    services=AuthServices(CredentialService(engine),SessionService(engine),ThrottleService(engine,secret=SecretBytes(secret),policy=ThrottlePolicy()))
    app.dependency_overrides.update({get_services:lambda:services,get_read_service:lambda:TeamReadService(engine),get_realtime_service:lambda:RealtimeService(engine)})
    from fastapi import Depends
    from app.auth import authenticated_session
    @app.get('/api/benchmark/preflight',dependencies=[Depends(authenticated_session)])
    def preflight():
        return dict(schema_version=1,database='merge_bench',role='merge_bench_app',revision='0006_profiles',
            hackathon_id=str(hackathon),dataset_sha256=dataset_sha256,workers=1)
    return app


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--confirm-merge-bench',action='store_true',required=True);p.add_argument('--seed',type=int,default=2026);args=p.parse_args()
    password=os.environ.get('MERGE_RELEASE_DB_PASSWORD') or getpass('Existing merge_bench_app password (hidden): ')
    with guarded_engine(Target('benchmark',True,password)) as (engine,guard):
        data=dataset(args.seed)
        with engine.connect() as c:
            c.execute(__import__('sqlalchemy').text('SET TRANSACTION READ ONLY'));validate_database(c,data)
        import uvicorn
        uvicorn.run(benchmark_app(engine,data['hackathon_id'],digest(data)),host='127.0.0.1',port=8766,proxy_headers=False,access_log=False,log_level='warning')


if __name__=='__main__':main()
