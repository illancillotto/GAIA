from datetime import datetime, timedelta, timezone
import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import RequireAdmin, RequireSuperAdmin, require_module
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_action_token
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.wc_operator import WCOperator
from app.repositories.application_user import (
    create_application_user,
    delete_application_user,
    get_application_user_by_email,
    get_application_user_by_id,
    get_application_user_by_username,
    list_application_users,
    update_application_user,
)
from app.schemas.auth import ApplicationUserInviteResponse
from app.schemas.users import (
    ApplicationUserCreate,
    ApplicationUserListResponse,
    ApplicationUserResponse,
    ApplicationUserUpdate,
)
from app.services.email import send_email

router = APIRouter(prefix="/admin/users", tags=["admin — users"])
RequireAccessiAdmin = Depends(require_module("accessi"))
UTC = timezone.utc


def _build_gate_mobile_console_map(
    db: Session,
    *,
    user_ids: list[int],
) -> dict[int, ApplicationUserResponse.GateMobileConsoleSummary]:
    if not user_ids:
        return {}
    operators = db.execute(
        select(WCOperator).where(WCOperator.gaia_user_id.in_(user_ids))
    ).scalars().all()
    return {
        operator.gaia_user_id: ApplicationUserResponse.GateMobileConsoleSummary(
            operator_id=str(operator.id),
            enabled=operator.gate_mobile_console_enabled,
            role=operator.gate_mobile_console_role,
        )
        for operator in operators
        if operator.gaia_user_id is not None
    }


def _serialize_application_user(
    user: ApplicationUser,
    *,
    gate_mobile_console: ApplicationUserResponse.GateMobileConsoleSummary | None = None,
) -> ApplicationUserResponse:
    payload = ApplicationUserResponse.model_validate(user).model_dump()
    payload["gate_mobile_console"] = gate_mobile_console
    return ApplicationUserResponse.model_validate(payload)


def _password_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def _frontend_base_url_from_request(request: Request) -> str:
    # Invitation emails must always use the configured public frontend URL.
    # Request-derived Origin/Referer values are unreliable behind proxies or
    # when admins access GAIA through internal hostnames not reachable by users.
    return settings.frontend_public_url.rstrip("/")


def _build_activation_payload(user: ApplicationUser, request: Request) -> tuple[str, datetime, str, str]:
    expires_at = datetime.now(UTC) + timedelta(hours=settings.user_invite_expire_hours)
    token = create_action_token(
        str(user.id),
        "application_user_activation",
        expires_minutes=settings.user_invite_expire_hours * 60,
        extra_claims={
            "email": user.email,
            "pwdv": _password_fingerprint(user.password_hash),
        },
    )
    activation_url_path = f"/auth/attiva-account/{token}"
    activation_url = f"{_frontend_base_url_from_request(request)}{activation_url_path}"
    return token, expires_at, activation_url_path, activation_url


@router.get("", response_model=ApplicationUserListResponse, response_model_exclude_none=True, dependencies=[RequireAdmin, RequireAccessiAdmin])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    is_active: bool | None = None,
) -> ApplicationUserListResponse:
    items, total = list_application_users(db, skip=skip, limit=limit, role=role, is_active=is_active)
    gate_mobile_console_by_user_id = _build_gate_mobile_console_map(db, user_ids=[item.id for item in items])
    return ApplicationUserListResponse(
        items=[
            _serialize_application_user(
                item,
                gate_mobile_console=gate_mobile_console_by_user_id.get(item.id),
            )
            for item in items
        ],
        total=total,
    )


@router.post("", response_model=ApplicationUserResponse, response_model_exclude_none=True, dependencies=[RequireAdmin], status_code=status.HTTP_201_CREATED)
def create_user(
    payload: ApplicationUserCreate,
    current_user: Annotated[ApplicationUser, RequireAccessiAdmin],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationUserResponse:
    if payload.role == ApplicationUserRole.SUPER_ADMIN.value and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super_admin can create super_admin users")
    if get_application_user_by_username(db, payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    if get_application_user_by_email(db, str(payload.email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = create_application_user(db, payload)
    return _serialize_application_user(user)


@router.post(
    "/{user_id}/send-invite",
    response_model=ApplicationUserInviteResponse,
    dependencies=[RequireAdmin, RequireAccessiAdmin],
)
def send_user_invite(
    user_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationUserInviteResponse:
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    _, expires_at, activation_url_path, activation_url = _build_activation_payload(user, request)
    full_name = user.full_name or user.username
    send_email(
        to_email=user.email,
        subject="GAIA - Attiva il tuo accesso",
        text_body=(
            f"Ciao {full_name},\n\n"
            f"il tuo account GAIA è pronto.\n"
            f"Username: {user.username}\n"
            f"Per impostare la password usa questo link:\n{activation_url}\n\n"
            f"Il link scade il {expires_at.astimezone(UTC).strftime('%d/%m/%Y %H:%M UTC')}."
        ),
        html_body=(
            f"<p>Ciao {full_name},</p>"
            f"<p>il tuo account <strong>GAIA</strong> è pronto.</p>"
            f"<p><strong>Username:</strong> {user.username}</p>"
            f"<p>Per impostare la password usa questo link:</p>"
            f"<p><a href=\"{activation_url}\">{activation_url}</a></p>"
            f"<p>Il link scade il {expires_at.astimezone(UTC).strftime('%d/%m/%Y %H:%M UTC')}.</p>"
        ),
    )
    return ApplicationUserInviteResponse(
        user_id=user.id,
        email=user.email,
        expires_at=expires_at.isoformat(),
        activation_url=activation_url,
        activation_url_path=activation_url_path,
        email_sent=True,
    )


@router.get("/{user_id}", response_model=ApplicationUserResponse, response_model_exclude_none=True, dependencies=[RequireAdmin, RequireAccessiAdmin])
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> ApplicationUserResponse:
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    gate_mobile_console = _build_gate_mobile_console_map(db, user_ids=[user.id]).get(user.id)
    return _serialize_application_user(user, gate_mobile_console=gate_mobile_console)


@router.put("/{user_id}", response_model=ApplicationUserResponse, response_model_exclude_none=True, dependencies=[RequireAdmin])
def update_user(
    user_id: int,
    payload: ApplicationUserUpdate,
    current_user: Annotated[ApplicationUser, RequireAccessiAdmin],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationUserResponse:
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_super_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Cannot modify super_admin")
    return _serialize_application_user(update_application_user(db, user, payload))


@router.delete("/{user_id}", dependencies=[RequireSuperAdmin, RequireAccessiAdmin], status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: Annotated[ApplicationUser, RequireAccessiAdmin],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete own account")
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    delete_application_user(db, user)


@router.patch("/{user_id}/modules", response_model=ApplicationUserResponse, response_model_exclude_none=True, dependencies=[RequireAdmin, RequireAccessiAdmin])
def patch_user_modules(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    module_accessi: bool = Query(...),
    module_rete: bool = Query(...),
    module_inventario: bool = Query(...),
    module_gis: bool = Query(False),
    module_catasto: bool = Query(...),
    module_utenze: bool = Query(...),
    module_operazioni: bool = Query(...),
    module_riordino: bool = Query(...),
    module_ruolo: bool = Query(...),
    module_presenze: bool = Query(...),
    module_organigramma: bool = Query(False),
) -> ApplicationUserResponse:
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    payload = ApplicationUserUpdate(
        module_accessi=module_accessi,
        module_rete=module_rete,
        module_inventario=module_inventario,
        module_gis=module_gis,
        module_catasto=module_catasto,
        module_utenze=module_utenze,
        module_operazioni=module_operazioni,
        module_riordino=module_riordino,
        module_ruolo=module_ruolo,
        module_presenze=module_presenze,
        module_organigramma=module_organigramma,
    )
    return _serialize_application_user(update_application_user(db, user, payload))
