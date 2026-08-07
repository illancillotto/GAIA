from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services import google_oauth


def test_ensure_google_oauth_enabled_rejects_missing_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_enabled", False)

    with pytest.raises(HTTPException) as exc:
        google_oauth.ensure_google_oauth_enabled()

    assert exc.value.status_code == 503
    assert "not configured" in exc.value.detail


def test_build_google_authorization_url_includes_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_enabled", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "client-id")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "client-secret")
    monkeypatch.setattr(settings, "google_oauth_redirect_uri", "https://gaia.example/oauth/callback")
    monkeypatch.setattr(settings, "google_oauth_scopes", "openid email profile")
    monkeypatch.setattr(settings, "google_oauth_authorize_url", "https://accounts.google.com/o/oauth2/v2/auth")

    url = google_oauth.build_google_authorization_url(state="csrf-token")

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=client-id" in url
    assert "state=csrf-token" in url
    assert "response_type=code" in url


@pytest.mark.anyio
async def test_exchange_code_for_profile_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_enabled", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "client-id")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "client-secret")
    monkeypatch.setattr(settings, "google_oauth_redirect_uri", "https://gaia.example/oauth/callback")
    monkeypatch.setattr(settings, "google_oauth_token_url", "https://oauth2.googleapis.com/token")
    monkeypatch.setattr(settings, "google_oauth_userinfo_url", "https://openidconnect.googleapis.com/v1/userinfo")

    class FakeResponse:
        def __init__(self, status_code: int, payload: dict) -> None:
            self.status_code = status_code
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.calls: list[tuple[str, str]] = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, data: dict):
            self.calls.append(("POST", url))
            assert data["code"] == "auth-code"
            return FakeResponse(200, {"access_token": "access-token"})

        async def get(self, url: str, headers: dict):
            self.calls.append(("GET", url))
            assert headers["Authorization"] == "Bearer access-token"
            return FakeResponse(
                200,
                {
                    "email": "User@Example.com",
                    "email_verified": True,
                    "name": "User Example",
                    "given_name": "User",
                    "family_name": "Example",
                    "sub": "google-subject",
                },
            )

    monkeypatch.setattr(google_oauth.httpx, "AsyncClient", FakeAsyncClient)

    profile = await google_oauth.exchange_code_for_profile(code="auth-code")

    assert profile.email == "user@example.com"
    assert profile.email_verified is True
    assert profile.full_name == "User Example"
    assert profile.subject == "google-subject"


@pytest.mark.anyio
async def test_exchange_code_for_profile_maps_token_and_profile_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_enabled", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "client-id")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "client-secret")
    monkeypatch.setattr(settings, "google_oauth_redirect_uri", "https://gaia.example/oauth/callback")
    monkeypatch.setattr(settings, "google_oauth_token_url", "https://oauth2.googleapis.com/token")
    monkeypatch.setattr(settings, "google_oauth_userinfo_url", "https://openidconnect.googleapis.com/v1/userinfo")

    class FakeResponse:
        def __init__(self, status_code: int, payload: dict | None = None) -> None:
            self.status_code = status_code
            self._payload = payload or {}

        def json(self) -> dict:
            return self._payload

    class TokenErrorClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, data: dict):
            return FakeResponse(400)

    monkeypatch.setattr(google_oauth.httpx, "AsyncClient", TokenErrorClient)

    with pytest.raises(HTTPException) as token_exc:
        await google_oauth.exchange_code_for_profile(code="bad-code")
    assert token_exc.value.status_code == 401
    assert "token exchange" in token_exc.value.detail

    class MissingAccessTokenClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, data: dict):
            return FakeResponse(200, {})

    monkeypatch.setattr(google_oauth.httpx, "AsyncClient", MissingAccessTokenClient)

    with pytest.raises(HTTPException) as missing_token_exc:
        await google_oauth.exchange_code_for_profile(code="auth-code")
    assert "access token" in missing_token_exc.value.detail

    class ProfileErrorClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, data: dict):
            return FakeResponse(200, {"access_token": "access-token"})

        async def get(self, url: str, headers: dict):
            return FakeResponse(403)

    monkeypatch.setattr(google_oauth.httpx, "AsyncClient", ProfileErrorClient)

    with pytest.raises(HTTPException) as profile_exc:
        await google_oauth.exchange_code_for_profile(code="auth-code")
    assert "profile lookup failed" in profile_exc.value.detail

    class MissingEmailClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, data: dict):
            return FakeResponse(200, {"access_token": "access-token"})

        async def get(self, url: str, headers: dict):
            return FakeResponse(200, {"sub": "google-subject"})

    monkeypatch.setattr(google_oauth.httpx, "AsyncClient", MissingEmailClient)

    with pytest.raises(HTTPException) as email_exc:
        await google_oauth.exchange_code_for_profile(code="auth-code")
    assert "email address" in email_exc.value.detail
