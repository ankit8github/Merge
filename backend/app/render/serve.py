"""Render process owner: normal startup has no setup or migration import."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from threading import Event
from app.railway.serve import wait_for_api, stop_children
from app.render import config
from app.render.check import caddy

TEMPLATE = Path('/srv/merge/render/caddy.template.json')


def supervise(filename, stopped, caddy_env):
    children = []
    try:
        worker = subprocess.Popen([sys.executable, '-m', 'app.render.api'])
        children.append(worker)
        if not wait_for_api(worker, stopped, timeout=180): return 0 if stopped.is_set() else 1
        if stopped.is_set(): return 0
        edge = subprocess.Popen(['caddy', 'run', '--config', filename], env=caddy_env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        children.append(edge)
        while not stopped.wait(.2):
            if any(child.poll() is not None for child in children): return 1
        return 0
    finally: stop_children(children)


def main():
    if len(sys.argv) != 1: raise SystemExit('Render supervisor accepts no overrides')
    stopped, filename, previous, code = Event(), None, {}, 1
    try:
        selected = config.load()
        generated = caddy(selected, config.port(os.environ), json.loads(TEMPLATE.read_text()))
        edge_env = {'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
                    'XDG_CONFIG_HOME': '/tmp/merge-caddy', 'XDG_DATA_HOME': '/tmp/merge-caddy',
                    'GOMEMLIMIT': '64MiB', 'GOMAXPROCS': '1'}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', prefix='merge-render-', encoding='utf-8', delete=False) as output:
            filename = output.name
            json.dump(generated, output)
        result = subprocess.run(['caddy', 'validate', '--config', filename], env=edge_env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        if result.returncode: raise ValueError('Caddy config rejected')
        for sig in (signal.SIGTERM, signal.SIGINT): previous[sig] = signal.signal(sig, lambda *_: stopped.set())
        code = supervise(filename, stopped, edge_env)
    except Exception: pass
    finally:
        for sig, handler in previous.items(): signal.signal(sig, handler)
        if filename:
            try: Path(filename).unlink()
            except OSError: pass
    print('Merge Render supervisor stopped; exit=' + str(code))
    raise SystemExit(code)


if __name__ == '__main__': main()
