from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


@dataclass
class GoogleUserProfile:
    email: str
    email_verified: bool
    full_name: str | None
    given_name: str | None
    family_name: str | None
    subject: str


def ensure_google_oauth_enabled() -> None:
    if (
        not settings.google_oauth_enabled
        or not settings.google_oauth_client_id
        or not settings.google_oauth_client_secret
        or not settings.google_oauth_redirect_uri
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google login is not configured",
        )


def build_google_authorization_url(*, state: str) -> str:
    ensure_google_oauth_enabled()
    query = urlencode(
        {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": settings.google_oauth_scopes,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "select_account",
            "state": state,
        }
    )
    return f"{settings.google_oauth_authorize_url}?{query}"


async def exchange_code_for_profile(*, code: str) -> GoogleUserProfile:
    ensure_google_oauth_enabled()

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_response = await client.post(
            settings.google_oauth_token_url,
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google authorization failed during token exchange",
            )

        token_payload = token_response.json()
        access_token = str(token_payload.get("access_token") or "")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google authorization did not return an access token",
            )

        profile_response = await client.get(
            settings.google_oauth_userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google user profile lookup failed",
            )

    profile_payload = profile_response.json()
    email = str(profile_payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account does not expose an email address",
        )

    return GoogleUserProfile(
        email=email,
        email_verified=bool(profile_payload.get("email_verified")),
        full_name=profile_payload.get("name"),
        given_name=profile_payload.get("given_name"),
        family_name=profile_payload.get("family_name"),
        subject=str(profile_payload.get("sub") or ""),
    )
