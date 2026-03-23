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
