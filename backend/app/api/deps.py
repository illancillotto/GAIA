from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.services.auth import get_current_user_from_token
from app.services.permission_resolver import can_access_section

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
    def _require_module(
        current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    ) -> ApplicationUser:
        if current_user.is_super_admin:
            return current_user

        if module_name not in current_user.enabled_modules:
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


def require_admin_user(
    current_user: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
) -> ApplicationUser:
    return current_user
