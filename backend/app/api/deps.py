from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.services.auth import get_current_user_from_token
from app.services.permission_resolver import can_access_section

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
mobile_connector_header = APIKeyHeader(name=settings.mobile_connector_header_name, auto_error=False)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> ApplicationUser:
    return get_current_user_from_token(db, token)


def require_active_user(
    current_user: Annotated[ApplicationUser, Depends(get_current_user)],
) -> ApplicationUser:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_role(*roles: str):
    def _require_role(
        current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    ) -> ApplicationUser:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return _require_role


def require_module(module_name: str):
    accepted_module_names = {module_name}
    if module_name in {"presenze", "inaz"}:
        accepted_module_names = {"presenze"}

    def _require_module(
        current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    ) -> ApplicationUser:
        if current_user.is_super_admin:
            return current_user

        if not any(module_key in current_user.enabled_modules for module_key in accepted_module_names):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module access denied")
        return current_user

    return _require_module


def require_section(section_key: str):
    def _require_section(
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    ) -> ApplicationUser:
        if not can_access_section(db, current_user, section_key):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Section access denied")
        return current_user

    return _require_section


RequireAdmin = Depends(require_role("super_admin", "admin"))
RequireSuperAdmin = Depends(require_role("super_admin"))
RequireAccessiAdmin = Depends(require_role("super_admin", "admin"))


def require_admin_user(
    current_user: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
) -> ApplicationUser:
    return current_user


def require_super_admin_user(
    current_user: Annotated[ApplicationUser, Depends(require_role("super_admin"))],
) -> ApplicationUser:
    return current_user


def require_not_operator(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> ApplicationUser:
    if current_user.role == "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operators cannot access this resource")
    return current_user


RequireNotOperator = Depends(require_not_operator)


def require_mobile_connector(
    connector_token: Annotated[str | None, Depends(mobile_connector_header)],
) -> str:
    expected_token = settings.effective_mobile_connector_token
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile connector auth not configured",
        )
    if connector_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid connector token",
        )
    return connector_token
