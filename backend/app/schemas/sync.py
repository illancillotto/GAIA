from pydantic import BaseModel, ConfigDict


class SyncCapabilitiesResponse(BaseModel):
    ssh_configured: bool
    host: str
    port: int
    username: str
    timeout_seconds: int
    supports_live_sync: bool


class SyncPreviewRequest(BaseModel):
    passwd_text: str | None = None
    group_text: str | None = None
    shares_text: str | None = None
    acl_texts: list[str] = []


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
