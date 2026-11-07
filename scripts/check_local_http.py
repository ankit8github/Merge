"""Verify real local API/Vite proxy success, outage and recovery; no database access.

Run with backend/.venv/Scripts/python.exe scripts/check_local_http.py.
Requires frontend npm ci. Starts and stops only its own child processes.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def get(path: str, timeout: float = 2) -> tuple[int, bytes]:
    try:
        with urlopen(path, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, b""


def wait_for(path: str) -> bytes:
    for _ in range(50):
        try:
            status, body = get(path)
            if status == 200:
                return body
        except (URLError, TimeoutError):
            pass
        time.sleep(0.2)
    raise RuntimeError("Local server did not become ready")


def start(command: list[str], directory: Path) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def stop(process: subprocess.Popen | None) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> None:
    # Refuse occupied ports so we never inspect or terminate someone else's app.
    for port in (8000, 5173):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"Port {port} is occupied; stop your dev server manually first")
    api = frontend = None
    api_command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
    try:
        api = start(api_command, ROOT / "backend")
        frontend = start(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1"], ROOT / "frontend")
        assert json.loads(wait_for("http://127.0.0.1:8000/health")) == {"status": "ok"}
        assert b"<title>Merge" in wait_for("http://127.0.0.1:5173/")
        assert json.loads(wait_for("http://127.0.0.1:5173/health")) == {"status": "ok"}
        print("PASS: API health, frontend HTML and Vite proxy")
        stop(api)
        # Allow the proxy to finish detecting the stopped upstream on Windows.
        # Still require an actual HTTP failure; a client timeout is not a pass.
        status, _ = get("http://127.0.0.1:5173/health", timeout=10)
        assert status >= 500, "Proxy should fail when the API is unavailable"
        print("PASS: proxy returns an error during API outage")
        api = start(api_command, ROOT / "backend")
        assert json.loads(wait_for("http://127.0.0.1:5173/health")) == {"status": "ok"}
        print("PASS: proxy recovers after API restart")
    finally:
        stop(frontend)
        stop(api)


if __name__ == "__main__":
    main()
