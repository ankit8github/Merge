"""Controlled ASGI entry point: preserve the actual transport peer for auth policy."""
import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000, choices=range(1, 65536))
    parser.add_argument('--workers', type=int, default=1, choices=range(1, 33))
    args = parser.parse_args()
    uvicorn.run('app.main:app', host=args.host, port=args.port, workers=args.workers,
                proxy_headers=False, forwarded_allow_ips='', access_log=False)


if __name__ == '__main__':
    main()
