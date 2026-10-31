"""Minimal Google Drive v3 client authenticated with a user OAuth refresh token."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.core.config import settings

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_SHARED_DRIVE_PARAMS = {"supportsAllDrives": "true"}
_TOKEN_EXPIRY_MARGIN_SECONDS = 60


class GoogleDriveError(RuntimeError):
    """Raised when Drive rejects a request; ``retryable`` marks transient failures."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class GoogleDriveCredentials:
    client_id: str
    client_secret: str
    refresh_token: str
    token_url: str


def drive_credentials_from_settings() -> GoogleDriveCredentials:
    credentials = GoogleDriveCredentials(
        client_id=settings.google_drive_client_id or settings.google_oauth_client_id,
        client_secret=settings.google_drive_client_secret or settings.google_oauth_client_secret,
        refresh_token=settings.google_drive_refresh_token,
        token_url=settings.google_oauth_token_url,
    )
    if not (credentials.client_id and credentials.client_secret and credentials.refresh_token):
        raise GoogleDriveError(
            "Google Drive non configurato: servono GOOGLE_DRIVE_REFRESH_TOKEN e un client OAuth.",
            retryable=False,
        )
    return credentials


def _escape_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _raise_for_drive_status(response: httpx.Response, action: str) -> None:
    if response.is_success:
        return
    retryable = response.status_code in {408, 429} or response.status_code >= 500
    raise GoogleDriveError(
        f"Google Drive {action} fallito: HTTP {response.status_code} {response.text[:300]}",
        retryable=retryable,
    )


class GoogleDriveClient:
    def __init__(self, credentials: GoogleDriveCredentials, http: httpx.AsyncClient) -> None:
        self._credentials = credentials
        self._http = http
        self._access_token = ""
        self._expires_at = 0.0

    async def _token(self) -> str:
        if self._access_token and time.monotonic() < self._expires_at:
            return self._access_token
        response = await self._http.post(
            self._credentials.token_url,
            data={
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
                "refresh_token": self._credentials.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if response.status_code in {400, 401}:
            raise GoogleDriveError(
                f"Refresh token Google Drive rifiutato: {response.text[:300]}",
                retryable=False,
            )
        _raise_for_drive_status(response, "refresh token")
        payload = response.json()
        self._access_token = str(payload["access_token"])
        lifetime = float(payload.get("expires_in", 3600)) - _TOKEN_EXPIRY_MARGIN_SECONDS
        self._expires_at = time.monotonic() + max(lifetime, 0.0)
        return self._access_token

    async def _send(self, method: str, url: str, action: str, **kwargs) -> httpx.Response:
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {await self._token()}"}
        response = await self._http.request(method, url, headers=headers, **kwargs)
        if response.status_code == 401:
            self._access_token = ""
            headers["Authorization"] = f"Bearer {await self._token()}"
            response = await self._http.request(method, url, headers=headers, **kwargs)
        _raise_for_drive_status(response, action)
        return response

    async def find_child(
        self, name: str, parent_id: str, *, mime_type: str | None = None
    ) -> str | None:
        clauses = [
            f"name = '{_escape_query_value(name)}'",
            f"'{_escape_query_value(parent_id)}' in parents",
            "trashed = false",
        ]
        if mime_type:
            clauses.append(f"mimeType = '{mime_type}'")
        response = await self._send(
            "GET",
            DRIVE_FILES_URL,
            "ricerca file",
            params={
                **_SHARED_DRIVE_PARAMS,
                "q": " and ".join(clauses),
                "fields": "files(id)",
                "includeItemsFromAllDrives": "true",
                "pageSize": "1",
            },
        )
        files = response.json().get("files") or []
        return str(files[0]["id"]) if files else None

    async def ensure_folder(self, name: str, parent_id: str) -> str:
        existing = await self.find_child(name, parent_id, mime_type=FOLDER_MIME_TYPE)
        if existing:
            return existing
        response = await self._send(
            "POST",
            DRIVE_FILES_URL,
            "creazione cartella",
            params={**_SHARED_DRIVE_PARAMS, "fields": "id"},
            json={"name": name, "parents": [parent_id], "mimeType": FOLDER_MIME_TYPE},
        )
        return str(response.json()["id"])

    async def replace_or_upload(
        self, name: str, parent_id: str, content: bytes, mime_type: str
    ) -> str:
        existing = await self.find_child(name, parent_id)
        if existing is None:
            return await self.upload_file(name, parent_id, content, mime_type)
        await self._send(
            "PATCH",
            f"{DRIVE_UPLOAD_URL}/{existing}",
            "aggiornamento file",
            params={**_SHARED_DRIVE_PARAMS, "uploadType": "media"},
            content=content,
            headers={"Content-Type": mime_type},
        )
        return existing

    async def upload_file(self, name: str, parent_id: str, content: bytes, mime_type: str) -> str:
        session = await self._send(
            "POST",
            DRIVE_UPLOAD_URL,
            "apertura upload",
            params={**_SHARED_DRIVE_PARAMS, "uploadType": "resumable", "fields": "id"},
            json={"name": name, "parents": [parent_id]},
            headers={"X-Upload-Content-Type": mime_type},
        )
        location = session.headers.get("location")
        if not location:
            raise GoogleDriveError(
                "Google Drive non ha restituito la sessione di upload.", retryable=True
            )
        response = await self._send(
            "PUT",
            location,
            "upload contenuto",
            content=content,
            headers={"Content-Type": mime_type},
        )
        return str(response.json()["id"])
