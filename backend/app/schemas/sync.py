from pydantic import BaseModel, ConfigDict, Field


class SyncCapabilitiesResponse(BaseModel):
    ssh_configured: bool
    host: str
    port: int
    username: str
    timeout_seconds: int
    supports_live_sync: bool
    auth_mode: str
    retry_strategy: str
    retry_max_attempts: int
    retry_base_delay_seconds: int
    retry_max_delay_seconds: int
    retry_jitter_enabled: bool
    retry_jitter_ratio: float
    live_sync_profiles: list[str]
    default_live_sync_profile: str


class SyncPreviewRequest(BaseModel):
    passwd_text: str | None = None
    group_text: str | None = None
    shares_text: str | None = None
    acl_texts: list[str] = Field(default_factory=list)


class ParsedNasUser(BaseModel):
    username: str
    source_uid: str
    full_name: str | None = None
    home_directory: str | None = None


class ParsedNasGroup(BaseModel):
    name: str
    gid: str
    members: list[str]


class ParsedShare(BaseModel):
    name: str


class ParsedAclEntry(BaseModel):
    subject: str
    permissions: str
    effect: str


class SyncPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    users: list[ParsedNasUser]
    groups: list[ParsedNasGroup]
    shares: list[ParsedShare]
    acl_entries: list[ParsedAclEntry]


class SyncApplyResponse(BaseModel):
    snapshot_id: int
    snapshot_checksum: str
    persisted_users: int
    persisted_groups: int
    persisted_shares: int
    persisted_permission_entries: int
    persisted_effective_permissions: int
    share_acl_pairs_used: int
