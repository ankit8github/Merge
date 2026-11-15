"""Own two child processes; exit on either failure; no migrations or shell."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from threading import Event
import time
from urllib.request import build_opener, ProxyHandler
from app.railway import config
from app.railway.check import caddy

TEMPLATE = Path('/srv/merge/railway/caddy.template.json')


def api_ready():
    # Never let inherited HTTP_PROXY route loopback health checks elsewhere.
    opener = build_opener(ProxyHandler({}))
    with opener.open('http://127.0.0.1:8000/ready', timeout=2) as response:
        return response.status == 200


def wait_for_api(process, stopped, *, timeout=60):
    deadline = time.monotonic() + timeout
    while not stopped.is_set() and time.monotonic() < deadline:
        if process.poll() is not None: return False
        try:
            if api_ready(): return True
        except Exception: pass
        stopped.wait(.2)
    return False


def stop_children(children, *, timeout=30):
    # Caddy stops ingress first; both children get their own graceful drain.
    for child in reversed(children):
        if child.poll() is None:
            try: child.terminate()
            except ProcessLookupError: pass
    deadline = time.monotonic() + timeout
    for child in reversed(children):
        try: child.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def supervise(filename, stopped, caddy_env):
    children = []
    try:
        api = subprocess.Popen([sys.executable, '-m', 'app.railway.api'])
        children.append(api)
        if not wait_for_api(api, stopped): return 0 if stopped.is_set() else 1
        if stopped.is_set(): return 0
        edge = subprocess.Popen(['caddy', 'run', '--config', filename], env=caddy_env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        children.append(edge)
        while not stopped.wait(.2):
            if any(child.poll() is not None for child in children): return 1
        return 0
    finally:
        stop_children(children)


def main():
    if len(sys.argv) != 1: raise SystemExit('Railway supervisor accepts no overrides')
    filename = None
    stopped = Event()
    previous = {}
    code = 1
    try:
        selected = config.load()
        generated = caddy(selected, config.port(os.environ), json.loads(TEMPLATE.read_text()))
        # Caddy receives public configuration only; it never receives DB secrets.
        edge_env = {'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
                    'XDG_CONFIG_HOME': '/tmp/merge-caddy', 'XDG_DATA_HOME': '/tmp/merge-caddy'}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', prefix='merge-caddy-',
                                         encoding='utf-8', delete=False) as output:
            filename = output.name
            json.dump(generated, output)
        result = subprocess.run(['caddy', 'validate', '--config', filename], env=edge_env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if result.returncode: raise ValueError('Caddy configuration rejected')
        for name in (signal.SIGTERM, signal.SIGINT):
            previous[name] = signal.signal(name, lambda *_: stopped.set())
        code = supervise(filename, stopped, edge_env)
    except Exception: pass
    finally:
        for name, handler in previous.items(): signal.signal(name, handler)
        if filename:
            try: Path(filename).unlink()  # Only our new temporary public config.
            except OSError: pass
    print('Merge Railway supervisor stopped; exit=' + str(code))
    raise SystemExit(code)


if __name__ == '__main__': main()
