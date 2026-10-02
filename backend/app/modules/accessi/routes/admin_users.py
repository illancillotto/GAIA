import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import RequireAdmin, RequireSuperAdmin, require_module
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_action_token
from app.models.application_user import ApplicationUser
from app.modules.accessi.user_management_policy import (
    RequireUserManager,
    check_managed_user,
    check_user_payload,
)
from app.modules.gis import qgis_desktop_access
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
    ApplicationUserModulesUpdate,
    ApplicationUserResponse,
    ApplicationUserUpdate,
    QgisDesktopAccessStatusResponse,
    QgisDesktopCredentialsResponse,
)
from app.services.email import send_email

router = APIRouter(prefix="/admin/users", tags=["admin — users"])
RequireAccessiAdmin = Depends(require_module("accessi"))


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


def _get_existing_user(db: Session, user_id: int) -> ApplicationUser:
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _get_managed_user(
    user_id: int,
    current_user: Annotated[ApplicationUser, RequireUserManager],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationUser:
    user = _get_existing_user(db, user_id)
    check_managed_user(current_user, user)
    return user


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


@router.get("", response_model=ApplicationUserListResponse, response_model_exclude_none=True, dependencies=[RequireUserManager])
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


@router.post("", response_model=ApplicationUserResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: ApplicationUserCreate,
    current_user: Annotated[ApplicationUser, RequireUserManager],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationUserResponse:
    check_user_payload(current_user, payload.model_dump())
    if get_application_user_by_username(db, payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    if get_application_user_by_email(db, str(payload.email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = create_application_user(db, payload)
    return _serialize_application_user(user)


@router.post(
    "/{user_id}/send-invite",
    response_model=ApplicationUserInviteResponse,
    dependencies=[RequireUserManager],
)
def send_user_invite(
    user: Annotated[ApplicationUser, Depends(_get_managed_user)],
    request: Request,
) -> ApplicationUserInviteResponse:
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


@router.get("/{user_id}", response_model=ApplicationUserResponse, response_model_exclude_none=True, dependencies=[RequireUserManager])
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> ApplicationUserResponse:
    user = _get_existing_user(db, user_id)
    gate_mobile_console = _build_gate_mobile_console_map(db, user_ids=[user.id]).get(user.id)
    return _serialize_application_user(user, gate_mobile_console=gate_mobile_console)


@router.put("/{user_id}", response_model=ApplicationUserResponse, response_model_exclude_none=True)
def update_user(
    user_id: int,
    payload: ApplicationUserUpdate,
    current_user: Annotated[ApplicationUser, RequireUserManager],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationUserResponse:
    user = _get_existing_user(db, user_id)
    check_user_payload(current_user, payload.model_dump(exclude_unset=True), user)
    return _serialize_application_user(_update_user_and_revoke_qgis_if_needed(db, user, payload))


def _update_user_and_revoke_qgis_if_needed(
    db: Session, user: ApplicationUser, payload: ApplicationUserUpdate
) -> ApplicationUser:
    if payload.module_gis is False or payload.is_active is False:
        qgis_desktop_access.disable_access(db, user, commit=False)
    return update_application_user(db, user, payload)


@router.get(
    "/{user_id}/qgis-desktop-access",
    response_model=QgisDesktopAccessStatusResponse,
    dependencies=[RequireAdmin, RequireAccessiAdmin],
)
def get_qgis_desktop_access(
    user_id: int, db: Annotated[Session, Depends(get_db)]
) -> QgisDesktopAccessStatusResponse:
    user = _get_existing_user(db, user_id)
    return QgisDesktopAccessStatusResponse.model_validate(
        qgis_desktop_access.access_status(db, user)
    )


@router.post(
    "/{user_id}/qgis-desktop-access",
    response_model=QgisDesktopCredentialsResponse,
    dependencies=[RequireAdmin, RequireAccessiAdmin],
)
def provision_qgis_desktop_access(
    user_id: int, db: Annotated[Session, Depends(get_db)]
) -> QgisDesktopCredentialsResponse:
    user = _get_existing_user(db, user_id)
    return QgisDesktopCredentialsResponse.model_validate(
        qgis_desktop_access.provision_access(db, user)
    )


@router.delete(
    "/{user_id}/qgis-desktop-access",
    response_model=QgisDesktopAccessStatusResponse,
    dependencies=[RequireAdmin, RequireAccessiAdmin],
)
def revoke_qgis_desktop_access(
    user_id: int, db: Annotated[Session, Depends(get_db)]
) -> QgisDesktopAccessStatusResponse:
    user = _get_existing_user(db, user_id)
    qgis_desktop_access.disable_access(db, user)
    return QgisDesktopAccessStatusResponse.model_validate(
        qgis_desktop_access.access_status(db, user)
    )


@router.delete("/{user_id}", dependencies=[RequireSuperAdmin, RequireAccessiAdmin], status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: Annotated[ApplicationUser, RequireAccessiAdmin],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete own account")
    user = _get_existing_user(db, user_id)
    qgis_desktop_access.disable_access(db, user, commit=False)
    delete_application_user(db, user)


@router.patch("/{user_id}/modules", response_model=ApplicationUserResponse, response_model_exclude_none=True)
def patch_user_modules(
    user: Annotated[ApplicationUser, Depends(_get_managed_user)],
    db: Annotated[Session, Depends(get_db)],
    modules: Annotated[ApplicationUserModulesUpdate, Query()],
    current_user: Annotated[ApplicationUser, RequireUserManager],
) -> ApplicationUserResponse:
    payload = ApplicationUserUpdate(**modules.model_dump())
    check_user_payload(current_user, payload.model_dump(exclude_unset=True), user)
    if not modules.module_gis:
        qgis_desktop_access.disable_access(db, user, commit=False)
    return _serialize_application_user(update_application_user(db, user, payload))
