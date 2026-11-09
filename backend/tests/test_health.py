from fastapi.testclient import TestClient

from app.main import create_app
from app.security.auth_policy import AuthSettings


def test_health():
    with TestClient(create_app(AuthSettings(mode='development', origin='http://127.0.0.1:5173', throttle_secret='a'*64))) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
