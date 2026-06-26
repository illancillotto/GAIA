from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.services.permission_resolver import can_access_section


def require_organigramma_or_inaz_module(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> ApplicationUser:
    if current_user.is_super_admin:
        return current_user
    if current_user.module_organigramma or current_user.module_presenze:
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Module access denied")


def require_organigramma_read_or_inaz():
    def _require_access(
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[ApplicationUser, Depends(require_organigramma_or_inaz_module)],
    ) -> ApplicationUser:
        if can_access_section(db, current_user, "organigramma.read"):
            return current_user
        if current_user.module_presenze and current_user.role in {"admin", "super_admin", "hr_manager"}:
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Section access denied")

    return _require_access


def require_organigramma_manage_or_inaz():
    def _require_access(
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[ApplicationUser, Depends(require_organigramma_or_inaz_module)],
    ) -> ApplicationUser:
        if current_user.is_super_admin:
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Section access denied")

    return _require_access
