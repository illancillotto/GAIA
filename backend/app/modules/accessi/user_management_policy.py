from typing import Annotated

from fastapi import Depends, HTTPException

from app.api.deps import require_active_user
from app.models.application_user import ApplicationUser, ApplicationUserRole

STANDARD_ROLES = frozenset({"viewer", "reviewer", "hr_manager", "operator"})
CED_MODULES = frozenset(
    {
        "inventario",
        "dotazioni",
        "gis",
        "catasto",
        "utenze",
        "operazioni",
        "riordino",
        "ruolo",
        "presenze",
        "organigramma",
    }
)


def require_user_manager(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> ApplicationUser:
    if current_user.role == "ced":
        return current_user
    if current_user.role in {"admin", "super_admin"} and "accessi" in current_user.enabled_modules:
        return current_user
    raise HTTPException(status_code=403, detail="User management access denied")


RequireUserManager = Depends(require_user_manager)


def require_not_ced(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> ApplicationUser:
    if current_user.role == "ced":
        raise HTTPException(status_code=403, detail="Module unavailable to CED")
    return current_user


def check_managed_user(actor: ApplicationUser, target: ApplicationUser) -> None:
    if actor.role == "ced" and (target.id == actor.id or target.role not in STANDARD_ROLES):
        raise HTTPException(status_code=403, detail="CED can only manage standard users")
    if target.is_super_admin and not actor.is_super_admin:
        raise HTTPException(status_code=403, detail="Cannot modify super_admin")


def check_user_payload(
    actor: ApplicationUser,
    data: dict,
    target: ApplicationUser | None = None,
) -> None:
    if target is not None:
        check_managed_user(actor, target)
    role = data.get("role")
    if "role" in data and role not in {item.value for item in ApplicationUserRole}:
        raise HTTPException(status_code=422, detail="Unknown application role")
    if role == "super_admin" and not actor.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super_admin can assign super_admin")
    if actor.role != "ced":
        return
    if role is not None and role not in STANDARD_ROLES:
        raise HTTPException(status_code=403, detail="CED can only assign standard roles")
    check_delegated_modules(data, target)


def check_delegated_modules(data: dict, target: ApplicationUser | None) -> None:
    for field, value in data.items():
        if field.startswith("module_") and field[7:] not in CED_MODULES:
            previous = getattr(target, field, False) if target is not None else False
            if value != previous:
                raise HTTPException(status_code=403, detail="Module cannot be delegated by CED")
