"""Private ASGI worker. The public listener belongs only to Caddy."""
import sys
import uvicorn
from app.production.serve import LOGGING
from app.render.config import load


def main():
    if len(sys.argv) != 1: raise SystemExit('Render worker accepts no overrides')
    try:
        load()
        uvicorn.run('app.render.application:create_render_app', factory=True,
            host='127.0.0.1', port=8000, workers=1, proxy_headers=False,
            forwarded_allow_ips='', access_log=False, log_config=LOGGING,
            timeout_graceful_shutdown=20, timeout_keep_alive=5, limit_concurrency=64)
    except Exception:
        raise SystemExit('Render worker failed; private details suppressed') from None


if __name__ == '__main__': main()
