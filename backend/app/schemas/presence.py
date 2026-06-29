from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserPresenceHeartbeatRequest(BaseModel):
    path: str = Field(min_length=1, max_length=512)
    route_label: str | None = Field(default=None, max_length=255)
    module_key: str | None = Field(default=None, max_length=64)
    visible: bool = True


class UserPresenceHeartbeatResponse(BaseModel):
    ok: bool = True
    last_seen_at: datetime


class UserPresenceSummaryItem(BaseModel):
    user_id: int
    username: str
    full_name: str | None
    role: str
    module_key: str | None
    route_label: str | None
    path: str
    visible: bool
    last_seen_at: datetime
    minutes_since_last_seen: int
    last_login_at: datetime | None


class UserPresenceModuleBucket(BaseModel):
    module_key: str
    count: int


class UserPresenceSummaryResponse(BaseModel):
    window_minutes: int
    active_users: int
    visible_users: int
    items: list[UserPresenceSummaryItem]
    by_module: list[UserPresenceModuleBucket]
