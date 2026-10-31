"""Obtain the Google Drive refresh token used by the ruoli export workers.

Usage (from backend/): python scripts/google_drive_authorize.py
Open the printed URL with the Google account that owns the Drive folder, accept,
then paste the full address the browser lands on (http://localhost/?code=...).
Store the printed token in GOOGLE_DRIVE_REFRESH_TOKEN.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:  # pragma: no cover - direct script bootstrap
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx  # noqa: E402 - after the direct-run sys.path bootstrap

from app.core.config import settings  # noqa: E402 - after the direct-run sys.path bootstrap

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
REDIRECT_URI = "http://localhost"


def client_credentials() -> tuple[str, str]:
    client_id = settings.google_drive_client_id or settings.google_oauth_client_id
    client_secret = settings.google_drive_client_secret or settings.google_oauth_client_secret
    if not (client_id and client_secret):
        raise SystemExit(
            "Configurare GOOGLE_DRIVE_CLIENT_ID/SECRET (o GOOGLE_OAUTH_CLIENT_ID/SECRET)."
        )
    return client_id, client_secret


def authorization_url(client_id: str) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": DRIVE_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return f"{settings.google_oauth_authorize_url}?{query}"


def code_from_redirect(redirected: str) -> str:
    codes = parse_qs(urlparse(redirected.strip()).query).get("code")
    if not codes:
        raise SystemExit("Nessun parametro code nell'indirizzo incollato.")
    return codes[0]


def exchange_code(
    client_id: str, client_secret: str, code: str, post: Callable = httpx.post
) -> str:
    response = post(
        settings.google_oauth_token_url,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    response.raise_for_status()
    refresh_token = response.json().get("refresh_token")
    if not refresh_token:
        raise SystemExit(
            "Google non ha restituito un refresh token: revocare l'accesso e ripetere."
        )
    return refresh_token


def main(read_line: Callable[[str], str] = input, post: Callable = httpx.post) -> int:
    client_id, client_secret = client_credentials()
    print("Apri questo indirizzo e autorizza l'accesso a Google Drive:\n")
    print(authorization_url(client_id))
    code = code_from_redirect(
        read_line("\nIncolla l'indirizzo di ritorno (http://localhost/?code=...): ")
    )
    print("\nGOOGLE_DRIVE_REFRESH_TOKEN=" + exchange_code(client_id, client_secret, code, post))
    return 0


if __name__ == "__main__":
    sys.exit(main())
