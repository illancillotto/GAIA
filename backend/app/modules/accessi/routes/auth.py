import hashlib
from typing import Annotated
from urllib.parse import quote

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_action_token, decode_action_token, hash_password
from app.models.application_user import ApplicationUser
from app.repositories.application_user import get_application_user_by_email, record_application_user_login
from app.schemas.auth import (
    ApplicationUserActivationInfo,
    ApplicationUserActivationRequest,
    ApplicationUserActivationResult,
    AuthProvidersResponse,
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from app.services.auth import authenticate_user, issue_access_token
from app.services.google_oauth import build_google_authorization_url, exchange_code_for_profile

router = APIRouter(prefix="/auth", tags=["auth"])


def _serialize_current_user(user: ApplicationUser) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(user)


def _password_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def _build_frontend_login_redirect(*, token: str | None = None, error: str | None = None) -> str:
    base_url = f"{settings.frontend_public_url.rstrip('/')}/login"
    if token:
        return f"{base_url}?access_token={quote(token)}&provider=google"
    if error:
        return f"{base_url}?auth_error={quote(error)}&provider=google"
    return base_url


def _resolve_activation_token(db: Session, token: str) -> tuple[ApplicationUser, bool]:
    try:
        payload = decode_action_token(token, expected_purpose="application_user_activation")
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Link non valido") from exc

    user = db.get(ApplicationUser, user_id)
    if user is None or user.email != payload.get("email"):
        raise HTTPException(status_code=404, detail="Link non valido")

    already_activated = payload.get("pwdv") != _password_fingerprint(user.password_hash)
    return user, already_activated


@router.get("/providers", response_model=AuthProvidersResponse, summary="Get enabled authentication providers")
def auth_providers() -> AuthProvidersResponse:
    google_enabled = bool(
        settings.google_oauth_enabled
        and settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.google_oauth_redirect_uri
    )
    return AuthProvidersResponse(google=google_enabled)


@router.post("/login", response_model=TokenResponse, summary="Authenticate application user")
def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = authenticate_user(db, payload.username, payload.password)
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host if request.client else None
    user = record_application_user_login(db, user, client_ip)
    return TokenResponse(access_token=issue_access_token(user))


@router.get("/me", response_model=CurrentUserResponse, response_model_exclude_none=True, summary="Get current application user")
def me(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> CurrentUserResponse:
    return _serialize_current_user(current_user)


@router.get("/user-invite/{token}", response_model=ApplicationUserActivationInfo, summary="Get activation info for invited user")
def get_user_activation_info(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationUserActivationInfo:
    user, already_activated = _resolve_activation_token(db, token)
    return ApplicationUserActivationInfo(
        user_id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        already_activated=already_activated,
    )


@router.post(
    "/user-invite/{token}/activate",
    response_model=ApplicationUserActivationResult,
    summary="Activate invited application user",
)
def activate_invited_user(
    token: str,
    payload: ApplicationUserActivationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationUserActivationResult:
    user, already_activated = _resolve_activation_token(db, token)
    if already_activated:
        raise HTTPException(status_code=409, detail="Account già attivato")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="La password deve essere di almeno 8 caratteri")

    user.password_hash = hash_password(payload.password)
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)

    return ApplicationUserActivationResult(
        user_id=user.id,
        username=user.username,
        message="Account attivato con successo. Puoi ora accedere a GAIA.",
    )


@router.get("/google/start", summary="Start Google OAuth login")
def start_google_login() -> RedirectResponse:
    state = create_action_token(
        "google-oauth",
        "google_oauth_state",
        expires_minutes=15,
    )
    return RedirectResponse(build_google_authorization_url(state=state), status_code=status.HTTP_302_FOUND)


@router.get("/google/callback", summary="Google OAuth callback")
async def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        return RedirectResponse(_build_frontend_login_redirect(error=f"Google access denied: {error}"))
    if not code or not state:
        return RedirectResponse(_build_frontend_login_redirect(error="Risposta Google non valida"))

    try:
        decode_action_token(state, expected_purpose="google_oauth_state")
        profile = await exchange_code_for_profile(code=code)
        if not profile.email_verified:
            raise HTTPException(status_code=401, detail="Google email is not verified")
        user = get_application_user_by_email(db, profile.email)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Nessun account GAIA attivo associato a questa email")
        forwarded_for = request.headers.get("x-forwarded-for") if request else None
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host if request and request.client else None
        user = record_application_user_login(db, user, client_ip)
        token = issue_access_token(user)
        return RedirectResponse(_build_frontend_login_redirect(token=token), status_code=status.HTTP_302_FOUND)
    except HTTPException as exc:
        return RedirectResponse(_build_frontend_login_redirect(error=str(exc.detail)), status_code=status.HTTP_302_FOUND)
    except jwt.InvalidTokenError:
        return RedirectResponse(_build_frontend_login_redirect(error="Sessione Google non valida"), status_code=status.HTTP_302_FOUND)
    except Exception:
        return RedirectResponse(_build_frontend_login_redirect(error="Errore durante accesso Google"), status_code=status.HTTP_302_FOUND)
