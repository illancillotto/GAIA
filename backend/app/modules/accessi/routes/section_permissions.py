from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import RequireAdmin, RequireSuperAdmin, require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.repositories.application_user import get_application_user_by_id
from app.repositories.section_permission import (
    bulk_update_role_permissions,
    bulk_update_user_permissions,
    create_section,
    deactivate_section,
    delete_user_override,
    get_role_permissions_for_section,
    get_section_by_id,
    get_section_by_key,
    get_user_overrides,
    list_sections,
    update_section,
)
from app.schemas.permissions import (
    BulkRolePermissionsRequest,
    BulkUserPermissionsRequest,
    MyPermissionsResponse,
    ResolvedPermissionResponse,
    RoleSectionPermissionResponse,
    SectionCreate,
    SectionResponse,
    SectionUpdate,
    UserPermissionsAdminView,
    UserSectionPermissionResponse,
)
from app.services.permission_resolver import resolve_user_permissions

auth_permissions_router = APIRouter(tags=["auth"])
sections_router = APIRouter(prefix="/sections", tags=["sections"])
admin_permissions_router = APIRouter(prefix="/admin/users", tags=["admin — permissions"])


@auth_permissions_router.get("/auth/my-permissions", response_model=MyPermissionsResponse)
def my_permissions(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MyPermissionsResponse:
    resolved = resolve_user_permissions(db, current_user)
    sections = [ResolvedPermissionResponse(**item.__dict__) for item in resolved]
    granted_keys = [item.section_key for item in resolved if item.is_granted]
    return MyPermissionsResponse(sections=sections, granted_keys=granted_keys)


@sections_router.get("", response_model=list[SectionResponse], dependencies=[RequireAdmin])
def get_sections(db: Annotated[Session, Depends(get_db)], module: str | None = None, active_only: bool = False):
    return [SectionResponse.model_validate(s) for s in list_sections(db, module=module, active_only=active_only)]


@sections_router.post("", response_model=SectionResponse, dependencies=[RequireSuperAdmin], status_code=201)
def create_sections(payload: SectionCreate, db: Annotated[Session, Depends(get_db)], current_user: Annotated[ApplicationUser, Depends(require_active_user)]):
    if get_section_by_key(db, payload.key):
        raise HTTPException(status_code=409, detail="Section key already exists")
    section = create_section(db, payload, updated_by_id=current_user.id)
    return SectionResponse.model_validate(section)


@sections_router.get("/{section_id}", response_model=SectionResponse, dependencies=[RequireAdmin])
def get_section(section_id: int, db: Annotated[Session, Depends(get_db)]):
    section = get_section_by_id(db, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return SectionResponse.model_validate(section)


@sections_router.put("/{section_id}", response_model=SectionResponse, dependencies=[RequireSuperAdmin])
def put_section(section_id: int, payload: SectionUpdate, db: Annotated[Session, Depends(get_db)]):
    section = get_section_by_id(db, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return SectionResponse.model_validate(update_section(db, section, payload))


@sections_router.delete("/{section_id}", response_model=SectionResponse, dependencies=[RequireSuperAdmin])
def delete_section(section_id: int, db: Annotated[Session, Depends(get_db)]):
    section = get_section_by_id(db, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return SectionResponse.model_validate(deactivate_section(db, section))


@sections_router.get("/{section_id}/role-permissions", response_model=list[RoleSectionPermissionResponse], dependencies=[RequireAdmin])
def get_section_role_permissions(section_id: int, db: Annotated[Session, Depends(get_db)]):
    return [RoleSectionPermissionResponse.model_validate(item) for item in get_role_permissions_for_section(db, section_id)]


@sections_router.put("/{section_id}/role-permissions", response_model=list[RoleSectionPermissionResponse], dependencies=[RequireSuperAdmin])
def put_section_role_permissions(
    section_id: int,
    payload: BulkRolePermissionsRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    updated = bulk_update_role_permissions(db, section_id, payload, current_user.id)
    return [RoleSectionPermissionResponse.model_validate(item) for item in updated]


@admin_permissions_router.get("/{user_id}/permissions", response_model=UserPermissionsAdminView, dependencies=[RequireAdmin])
def get_user_permissions(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user = get_application_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    resolved = [ResolvedPermissionResponse(**item.__dict__) for item in resolve_user_permissions(db, user)]
    overrides = [UserSectionPermissionResponse.model_validate(item) for item in get_user_overrides(db, user_id)]
    return UserPermissionsAdminView(user_id=user.id, username=user.username, role=user.role, resolved=resolved, overrides=overrides)


@admin_permissions_router.put("/{user_id}/permissions", response_model=list[UserSectionPermissionResponse], dependencies=[RequireAdmin])
def put_user_permissions(
    user_id: int,
    payload: BulkUserPermissionsRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    target = get_application_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not current_user.is_super_admin and target.role in {"super_admin", "admin"}:
        raise HTTPException(status_code=403, detail="Forbidden for admin")
    updated = bulk_update_user_permissions(db, user_id, payload, current_user.id)
    return [UserSectionPermissionResponse.model_validate(item) for item in updated]


@admin_permissions_router.delete("/{user_id}/permissions/{section_id}", dependencies=[RequireAdmin], status_code=204)
def remove_user_permissions(user_id: int, section_id: int, db: Annotated[Session, Depends(get_db)]):
    delete_user_override(db, user_id, section_id)
