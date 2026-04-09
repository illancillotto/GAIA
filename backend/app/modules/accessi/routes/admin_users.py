from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import RequireAdmin, RequireSuperAdmin, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.repositories.application_user import (
    create_application_user,
    delete_application_user,
    get_application_user_by_email,
    get_application_user_by_id,
    get_application_user_by_username,
    list_application_users,
    update_application_user,
)
from app.schemas.users import (
    ApplicationUserCreate,
    ApplicationUserListResponse,
    ApplicationUserResponse,
    ApplicationUserUpdate,
)

router = APIRouter(prefix="/admin/users", tags=["admin — users"])
RequireAccessiAdmin = Depends(require_module("accessi"))


@router.get("", response_model=ApplicationUserListResponse, dependencies=[RequireAdmin, RequireAccessiAdmin])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    is_active: bool | None = None,
) -> ApplicationUserListResponse:
    items, total = list_application_users(db, skip=skip, limit=limit, role=role, is_active=is_active)
    return ApplicationUserListResponse(items=[ApplicationUserResponse.model_validate(item) for item in items], total=total)


@router.post("", response_model=ApplicationUserResponse, dependencies=[RequireAdmin], status_code=status.HTTP_201_CREATED)
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
    return ApplicationUserResponse.model_validate(user)


@router.get("/{user_id}", response_model=ApplicationUserResponse, dependencies=[RequireAdmin, RequireAccessiAdmin])
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> ApplicationUserResponse:
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ApplicationUserResponse.model_validate(user)


@router.put("/{user_id}", response_model=ApplicationUserResponse, dependencies=[RequireAdmin])
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
    return ApplicationUserResponse.model_validate(update_application_user(db, user, payload))


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


@router.patch("/{user_id}/modules", response_model=ApplicationUserResponse, dependencies=[RequireAdmin, RequireAccessiAdmin])
def patch_user_modules(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    module_accessi: bool = Query(...),
    module_rete: bool = Query(...),
    module_inventario: bool = Query(...),
    module_catasto: bool = Query(...),
    module_utenze: bool = Query(...),
    module_operazioni: bool = Query(...),
    module_riordino: bool = Query(...),
) -> ApplicationUserResponse:
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    payload = ApplicationUserUpdate(
        module_accessi=module_accessi,
        module_rete=module_rete,
        module_inventario=module_inventario,
        module_catasto=module_catasto,
        module_utenze=module_utenze,
        module_operazioni=module_operazioni,
        module_riordino=module_riordino,
    )
    return ApplicationUserResponse.model_validate(update_application_user(db, user, payload))
