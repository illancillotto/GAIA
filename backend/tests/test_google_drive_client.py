from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.services import google_drive
from app.services.google_drive import (
    DRIVE_UPLOAD_URL,
    FOLDER_MIME_TYPE,
    GoogleDriveClient,
    GoogleDriveCredentials,
    GoogleDriveError,
    drive_credentials_from_settings,
)

CREDENTIALS = GoogleDriveCredentials("client", "secret", "refresh", "https://oauth.test/token")


def make_client(handler) -> tuple[GoogleDriveClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GoogleDriveClient(CREDENTIALS, http), http


def run(coro):
    return asyncio.run(coro)


def token_response(request: httpx.Request) -> httpx.Response | None:
    if str(request.url) == CREDENTIALS.token_url:
        return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
    return None


def test_credentials_fall_back_to_oauth_client(monkeypatch):
    monkeypatch.setattr(google_drive.settings, "google_drive_client_id", "")
    monkeypatch.setattr(google_drive.settings, "google_drive_client_secret", "")
    monkeypatch.setattr(google_drive.settings, "google_oauth_client_id", "oauth-id")
    monkeypatch.setattr(google_drive.settings, "google_oauth_client_secret", "oauth-secret")
    monkeypatch.setattr(google_drive.settings, "google_drive_refresh_token", "refresh")

    credentials = drive_credentials_from_settings()

    assert (credentials.client_id, credentials.client_secret) == ("oauth-id", "oauth-secret")


def test_credentials_without_refresh_token_are_not_retryable(monkeypatch):
    monkeypatch.setattr(google_drive.settings, "google_drive_refresh_token", "")

    with pytest.raises(GoogleDriveError) as excinfo:
        drive_credentials_from_settings()

    assert excinfo.value.retryable is False


def test_ensure_folder_reuses_existing_folder_and_caches_token():
    requests: list[httpx.Request] = []

    def handler(request):
        requests.append(request)
        return token_response(request) or httpx.Response(200, json={"files": [{"id": "folder-1"}]})

    client, http = make_client(handler)

    async def scenario():
        async with http:
            first = await client.ensure_folder("inCASS", "root'x")
            second = await client.find_child("other", "root")
            return first, second

    assert run(scenario()) == ("folder-1", "folder-1")
    token_calls = [r for r in requests if str(r.url) == CREDENTIALS.token_url]
    assert len(token_calls) == 1
    query = requests[1].url.params["q"]
    assert "'root\\'x' in parents" in query
    assert f"mimeType = '{FOLDER_MIME_TYPE}'" in query
    assert requests[1].headers["Authorization"] == "Bearer tok"


def test_ensure_folder_creates_missing_folder():
    def handler(request):
        if token_response(request):
            return token_response(request)
        if request.method == "GET":
            return httpx.Response(200, json={"files": []})
        assert json.loads(request.content) == {
            "name": "2026-11-01",
            "parents": ["root"],
            "mimeType": FOLDER_MIME_TYPE,
        }
        return httpx.Response(200, json={"id": "new-folder"})

    client, http = make_client(handler)

    async def scenario():
        async with http:
            return await client.ensure_folder("2026-11-01", "root")

    assert run(scenario()) == "new-folder"


def test_upload_file_uses_resumable_session():
    seen: list[tuple[str, str]] = []

    def handler(request):
        if token_response(request):
            return token_response(request)
        seen.append((request.method, str(request.url)))
        if request.method == "POST":
            assert request.url.params["uploadType"] == "resumable"
            return httpx.Response(200, headers={"location": "https://upload.test/session"})
        assert request.content == b"xlsx"
        return httpx.Response(200, json={"id": "file-1"})

    client, http = make_client(handler)

    async def scenario():
        async with http:
            return await client.upload_file("a.xlsx", "folder", b"xlsx", "mime")

    assert run(scenario()) == "file-1"
    assert seen[0][1].startswith(DRIVE_UPLOAD_URL)
    assert seen[1] == ("PUT", "https://upload.test/session")


def test_upload_without_session_location_is_retryable():
    def handler(request):
        return token_response(request) or httpx.Response(200)

    client, http = make_client(handler)

    async def scenario():
        async with http:
            await client.upload_file("a.xlsx", "folder", b"xlsx", "mime")

    with pytest.raises(GoogleDriveError) as excinfo:
        run(scenario())
    assert excinfo.value.retryable is True


@pytest.mark.parametrize("existing", [None, "manifest-1"])
def test_replace_or_upload(existing):
    methods: list[str] = []

    def handler(request):
        if token_response(request):
            return token_response(request)
        methods.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json={"files": [{"id": existing}] if existing else []})
        if request.method == "POST":
            return httpx.Response(200, headers={"location": "https://upload.test/s"})
        if request.method == "PATCH":
            assert str(request.url).startswith(f"{DRIVE_UPLOAD_URL}/manifest-1")
            return httpx.Response(200, json={"id": "manifest-1"})
        return httpx.Response(200, json={"id": "manifest-new"})

    client, http = make_client(handler)

    async def scenario():
        async with http:
            return await client.replace_or_upload(
                "manifest.json", "folder", b"{}", "application/json"
            )

    result = run(scenario())

    assert result == (existing or "manifest-new")
    assert methods == (["GET", "PATCH"] if existing else ["GET", "POST", "PUT"])


def test_expired_access_token_is_refreshed_once():
    calls = {"token": 0, "files": 0}

    def handler(request):
        if str(request.url) == CREDENTIALS.token_url:
            calls["token"] += 1
            return httpx.Response(200, json={"access_token": f"tok{calls['token']}"})
        calls["files"] += 1
        if request.headers["Authorization"] == "Bearer tok1":
            return httpx.Response(401)
        return httpx.Response(200, json={"files": []})

    client, http = make_client(handler)

    async def scenario():
        async with http:
            return await client.find_child("x", "root")

    assert run(scenario()) is None
    assert calls == {"token": 2, "files": 2}


@pytest.mark.parametrize(
    ("status", "retryable"),
    [(400, False), (403, False), (429, True), (500, True), (503, True)],
)
def test_drive_errors_classify_retryability(status, retryable):
    def handler(request):
        return token_response(request) or httpx.Response(status, text="boom")

    client, http = make_client(handler)

    async def scenario():
        async with http:
            await client.find_child("x", "root")

    with pytest.raises(GoogleDriveError) as excinfo:
        run(scenario())
    assert excinfo.value.retryable is retryable
    assert f"HTTP {status}" in str(excinfo.value)


@pytest.mark.parametrize(("status", "retryable"), [(400, False), (401, False), (500, True)])
def test_refresh_token_failures(status, retryable):
    client, http = make_client(lambda request: httpx.Response(status, text="invalid_grant"))

    async def scenario():
        async with http:
            await client.find_child("x", "root")

    with pytest.raises(GoogleDriveError) as excinfo:
        run(scenario())
    assert excinfo.value.retryable is retryable
