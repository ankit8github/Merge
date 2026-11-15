"""Private ASGI worker. The public listener belongs only to Caddy."""
import sys
import uvicorn
from app.production.serve import LOGGING
from app.railway.config import load


def main():
    if len(sys.argv) != 1: raise SystemExit('Railway worker accepts no overrides')
    try:
        load()
        uvicorn.run('app.railway.application:create_railway_app', factory=True,
            host='127.0.0.1', port=8000, workers=1, proxy_headers=False,
            forwarded_allow_ips='', access_log=False, log_config=LOGGING,
            timeout_graceful_shutdown=20, timeout_keep_alive=5, limit_concurrency=256)
    except Exception:
        raise SystemExit('Railway worker failed; private details suppressed') from None


if __name__ == '__main__': main()
