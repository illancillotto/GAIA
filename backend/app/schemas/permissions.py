from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionEntryInput(BaseModel):
    share_name: str
    subject_type: str
    subject_name: str
    permission_level: str
    is_deny: bool = False


class PermissionUserInput(BaseModel):
    username: str
    groups: list[str] = []


class EffectivePermissionPreviewResponse(BaseModel):
    username: str
    share_name: str
    can_read: bool
    can_write: bool
    is_denied: bool
    source_summary: str


class PermissionCalculationRequest(BaseModel):
    users: list[PermissionUserInput]
    permission_entries: list[PermissionEntryInput]


class EffectivePermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_id: int | None
    nas_user_id: int
    share_id: int
    can_read: bool
    can_write: bool
    is_denied: bool
    source_summary: str


class SectionCreate(BaseModel):
    module: str
    key: str
    label: str
    description: str | None = None
    min_role: str = "admin"
    sort_order: int = 0


class SectionUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    min_role: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class SectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module: str
    key: str
    label: str
    description: str | None
    min_role: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class RolePermissionInput(BaseModel):
    role: str
    is_granted: bool


class RoleSectionPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    section_id: int
    role: str
    is_granted: bool
    updated_by_id: int | None
    updated_at: datetime


class BulkRolePermissionsRequest(BaseModel):
    permissions: list[RolePermissionInput]


class UserSectionPermissionInput(BaseModel):
    section_id: int
    is_granted: bool


class UserSectionPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    section_id: int
    is_granted: bool
    granted_by_id: int | None
    created_at: datetime
    updated_at: datetime


class BulkUserPermissionsRequest(BaseModel):
    permissions: list[UserSectionPermissionInput]


class ResolvedPermissionResponse(BaseModel):
    section_key: str
    section_label: str
    module: str
    is_granted: bool
    source: str


class MyPermissionsResponse(BaseModel):
    sections: list[ResolvedPermissionResponse]
    granted_keys: list[str]


class UserPermissionsAdminView(BaseModel):
    user_id: int
    username: str
    role: str
    resolved: list[ResolvedPermissionResponse]
    overrides: list[UserSectionPermissionResponse]
