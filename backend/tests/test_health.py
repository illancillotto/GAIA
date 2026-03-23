from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthcheck_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "backend",
        "environment": "development",
    }


def test_options_preflight_returns_cors_headers() -> None:
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"
