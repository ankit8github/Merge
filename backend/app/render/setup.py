"""Owner-selected one-time setup process; status HTTP cannot execute commands."""
import json
import os
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Lock, Thread
from app.render import config
from app.render.initialization import initialize


class Status:
    def __init__(self):
        self.lock = Lock()
        self.value = dict(initialized=False, state='initializing')

    def set(self, value):
        with self.lock: self.value = dict(value)

    def body(self):
        with self.lock: return json.dumps(self.value).encode()


def handler(status):
    class Handler(BaseHTTPRequestHandler):
        timeout = 5
        def log_message(self, *args): pass
        def do_GET(self):
            if self.path != '/ready':
                self.send_error(404); return
            # Liveness of the SETUP STATUS process, never product readiness.
            # 200 prevents Render from repeatedly restarting a failed setup.
            body = status.body()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if self.command != 'HEAD': self.wfile.write(body)
        do_HEAD = do_GET
        def do_POST(self): self.send_error(405)
    return Handler


def main():
    p = config.SafeParser(description=__doc__)
    p.add_argument('--confirm-new-render-production', required=True, action='store_true')
    p.parse_args()
    # Validate every input before DNS, SQL or even a status listener.
    try: selected = config.load_setup()
    except Exception: p.exit(1, 'Render setup inputs rejected; details suppressed.\n')
    stopped, status = Event(), Status()
    def stop(*args): stopped.set()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server = HTTPServer(('0.0.0.0', config.port(os.environ)), handler(status))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            result = initialize(selected)
            status.set(dict(state='complete', **result))
        except Exception:
            status.set(dict(initialized=False, state='failed', source_commit=selected.commit,
                            attempt=str(selected.attempt)))
        print(status.body().decode(), flush=True)
        stopped.wait()  # Owner switches Docker command after inspecting JSON.
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=6)


if __name__ == '__main__': main()
