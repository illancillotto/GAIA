import hashlib
import secrets
from datetime import datetime, timedelta
from html import escape
from typing import Annotated
from urllib.parse import quote

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.config import settings
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.core.security import create_action_token, decode_action_token, hash_password
from app.models.application_user import ApplicationUser
from app.models.application_user_password_reset import ApplicationUserPasswordResetToken
from app.modules.network.vpn_access import (
    VpnDeviceLimitExceeded,
    VpnDeviceRevoked,
    register_vpn_login_device,
)
from app.repositories.application_user import (
    get_application_user_by_email,
    get_application_user_by_login_identifier,
    record_application_user_login,
)
from app.schemas.auth import (
    ApplicationUserActivationInfo,
    ApplicationUserActivationRequest,
    ApplicationUserActivationResult,
    AuthProvidersResponse,
    CurrentUserResponse,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResult,
    PasswordResetInfo,
    PasswordResetRequest,
    PasswordResetRequestResult,
    TokenResponse,
)
from app.services.auth import authenticate_user, issue_access_token
from app.services.email import send_email
from app.services.google_oauth import (
    build_google_authorization_url,
    exchange_code_for_profile,
)

router = APIRouter(prefix="/auth", tags=["auth"])
PASSWORD_RESET_REQUEST_MESSAGE = (
    "Se l'account esiste ed e attivo, riceverai una mail con le istruzioni per reimpostare la password."
)


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


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _client_ip_from_request(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def _enforce_vpn_login_device(
    db: Session,
    *,
    user: ApplicationUser,
    client_device_id: str | None,
    device_label: str | None,
    user_agent: str | None,
    client_ip: str | None,
) -> None:
    try:
        register_vpn_login_device(
            db,
            user=user,
            client_device_id=client_device_id,
            device_label=device_label,
            user_agent=user_agent,
            client_ip=client_ip,
            max_devices=settings.network_vpn_max_active_devices_per_user,
            enforcement_enabled=settings.network_vpn_device_enforcement_enabled,
        )
    except VpnDeviceLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Limite dispositivi raggiunto: massimo {exc.max_devices} dispositivi attivi per utente. "
                "Contatta un amministratore GAIA per disattivare un dispositivo precedente."
            ),
        ) from exc
    except VpnDeviceRevoked as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispositivo non autorizzato per l'accesso GAIA. Contatta un amministratore.",
        ) from exc


def _ensure_password_reset_email_delivery_configured() -> None:
    if not settings.smtp_enabled or not settings.smtp_username or not settings.smtp_password or not settings.smtp_from_email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servizio ripristino password non configurato",
        )


def _build_password_reset_url(token: str) -> str:
    base_url = settings.frontend_public_url.rstrip("/")
    return f"{base_url}/auth/reset-password/{token}"


def _generic_password_reset_response() -> PasswordResetRequestResult:
    return PasswordResetRequestResult(message=PASSWORD_RESET_REQUEST_MESSAGE)


def _active_password_reset_tokens_query(user_id: int):
    return select(ApplicationUserPasswordResetToken).where(
        ApplicationUserPasswordResetToken.user_id == user_id,
        ApplicationUserPasswordResetToken.used_at.is_(None),
        ApplicationUserPasswordResetToken.invalidated_at.is_(None),
    )


def _invalidate_active_password_reset_tokens(db: Session, *, user_id: int, now: datetime) -> None:
    tokens = db.execute(_active_password_reset_tokens_query(user_id)).scalars().all()
    for token in tokens:
        token.invalidated_at = now
        db.add(token)


def _recent_password_reset_token_exists(db: Session, *, user_id: int, now: datetime) -> bool:
    threshold = now - timedelta(minutes=max(settings.password_reset_min_interval_minutes, 0))
    return (
        db.execute(
            _active_password_reset_tokens_query(user_id)
            .where(ApplicationUserPasswordResetToken.created_at >= threshold)
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _send_password_reset_email(*, user: ApplicationUser, reset_url: str, expires_at: datetime) -> None:
    display_name = user.full_name or user.username
    safe_display_name = escape(display_name)
    safe_reset_url = escape(reset_url, quote=True)
    safe_username = escape(user.username)
    expires_label = expires_at.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")
    send_email(
        to_email=user.email,
        subject="GAIA - Ripristino password",
        text_body=(
            f"Ciao {display_name},\n\n"
            f"abbiamo ricevuto una richiesta di ripristino password per il tuo account GAIA.\n"
            f"Username: {user.username}\n"
            f"Per impostare una nuova password usa questo link:\n{reset_url}\n\n"
            f"Il link scade il {expires_label}.\n"
            f"Se non hai richiesto tu il ripristino, ignora questa mail."
        ),
        html_body=(
            f"<p>Ciao {safe_display_name},</p>"
            f"<p>abbiamo ricevuto una richiesta di ripristino password per il tuo account <strong>GAIA</strong>.</p>"
            f"<p><strong>Username:</strong> {safe_username}</p>"
            f"<p>Per impostare una nuova password usa questo link:</p>"
            f"<p><a href=\"{safe_reset_url}\">{safe_reset_url}</a></p>"
            f"<p>Il link scade il {expires_label}.</p>"
            f"<p>Se non hai richiesto tu il ripristino, ignora questa mail.</p>"
        ),
    )


def _resolve_password_reset_token(db: Session, token: str) -> tuple[ApplicationUserPasswordResetToken, ApplicationUser]:
    token_row = db.execute(
        select(ApplicationUserPasswordResetToken).where(
            ApplicationUserPasswordResetToken.token_hash == _hash_password_reset_token(token)
        )
    ).scalar_one_or_none()
    if token_row is None:
        raise HTTPException(status_code=404, detail="Link non valido o scaduto")

    now = _now()
    if token_row.used_at is not None or token_row.invalidated_at is not None or _as_utc(token_row.expires_at) <= now:
        raise HTTPException(status_code=404, detail="Link non valido o scaduto")

    user = db.get(ApplicationUser, token_row.user_id)
    if user is None or not user.is_active or user.email != token_row.email:
        raise HTTPException(status_code=404, detail="Link non valido o scaduto")
    return token_row, user


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
    client_ip = _client_ip_from_request(request)
    _enforce_vpn_login_device(
        db,
        user=user,
        client_device_id=payload.device_id,
        device_label=payload.device_label,
        user_agent=request.headers.get("user-agent"),
        client_ip=client_ip,
    )
    user = record_application_user_login(db, user, client_ip)
    return TokenResponse(access_token=issue_access_token(user))


@router.get("/me", response_model=CurrentUserResponse, response_model_exclude_none=True, summary="Get current application user")
def me(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> CurrentUserResponse:
    return _serialize_current_user(current_user)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResult,
    summary="Request application user password reset",
)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> PasswordResetRequestResult:
    _ensure_password_reset_email_delivery_configured()
    identifier = payload.identifier.strip()
    user = get_application_user_by_login_identifier(db, identifier)
    if user is None or not user.is_active:
        return _generic_password_reset_response()

    now = _now()
    if _recent_password_reset_token_exists(db, user_id=user.id, now=now):
        return _generic_password_reset_response()

    _invalidate_active_password_reset_tokens(db, user_id=user.id, now=now)
    raw_token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=max(settings.password_reset_expire_minutes, 1))
    token_row = ApplicationUserPasswordResetToken(
        user_id=user.id,
        token_hash=_hash_password_reset_token(raw_token),
        email=user.email,
        requested_identifier=identifier[:255],
        requested_ip=_client_ip_from_request(request),
        requested_user_agent=(request.headers.get("user-agent") or "")[:512] or None,
        expires_at=expires_at,
        created_at=now,
        updated_at=now,
    )
    db.add(token_row)
    _send_password_reset_email(user=user, reset_url=_build_password_reset_url(raw_token), expires_at=expires_at)
    db.commit()
    return _generic_password_reset_response()


@router.get(
    "/password-reset/{token}",
    response_model=PasswordResetInfo,
    summary="Get password reset link info",
)
def get_password_reset_info(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> PasswordResetInfo:
    token_row, user = _resolve_password_reset_token(db, token)
    return PasswordResetInfo(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        expires_at=_as_utc(token_row.expires_at).isoformat(),
    )


@router.post(
    "/password-reset/{token}/confirm",
    response_model=PasswordResetConfirmResult,
    summary="Confirm application user password reset",
)
def confirm_password_reset(
    token: str,
    payload: PasswordResetConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PasswordResetConfirmResult:
    token_row, user = _resolve_password_reset_token(db, token)
    now = _now()
    user.password_hash = hash_password(payload.password)
    token_row.used_at = now
    token_row.invalidated_at = now
    db.add(user)
    db.add(token_row)
    _invalidate_active_password_reset_tokens(db, user_id=user.id, now=now)
    db.commit()
    return PasswordResetConfirmResult(
        username=user.username,
        message="Password aggiornata con successo. Puoi ora accedere a GAIA.",
    )


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
def start_google_login(
    device_id: str | None = Query(default=None, max_length=128),
    device_label: str | None = Query(default=None, max_length=255),
) -> RedirectResponse:
    state = create_action_token(
        "google-oauth",
        "google_oauth_state",
        expires_minutes=15,
        extra_claims={
            "device_id": device_id,
            "device_label": device_label,
        },
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
        state_payload = decode_action_token(state, expected_purpose="google_oauth_state")
        profile = await exchange_code_for_profile(code=code)
        if not profile.email_verified:
            raise HTTPException(status_code=401, detail="Google email is not verified")
        user = get_application_user_by_email(db, profile.email)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Nessun account GAIA attivo associato a questa email")
        client_ip = _client_ip_from_request(request)
        _enforce_vpn_login_device(
            db,
            user=user,
            client_device_id=state_payload.get("device_id"),
            device_label=state_payload.get("device_label") or "Google OAuth",
            user_agent=request.headers.get("user-agent"),
            client_ip=client_ip,
        )
        user = record_application_user_login(db, user, client_ip)
        token = issue_access_token(user)
        return RedirectResponse(_build_frontend_login_redirect(token=token), status_code=status.HTTP_302_FOUND)
    except HTTPException as exc:
        return RedirectResponse(_build_frontend_login_redirect(error=str(exc.detail)), status_code=status.HTTP_302_FOUND)
    except jwt.InvalidTokenError:
        return RedirectResponse(_build_frontend_login_redirect(error="Sessione Google non valida"), status_code=status.HTTP_302_FOUND)
    except Exception:  # noqa: BLE001 - OAuth failures must be collapsed into a safe redirect error.
        return RedirectResponse(_build_frontend_login_redirect(error="Errore durante accesso Google"), status_code=status.HTTP_302_FOUND)
