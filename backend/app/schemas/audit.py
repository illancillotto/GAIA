from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    nas_users: int
    nas_groups: int
    shares: int
    reviews: int
    snapshots: int
    sync_runs: int


class NasUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str | None
    email: str | None
    source_uid: str | None
    is_active: bool
    last_seen_snapshot_id: int | None


class NasGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    last_seen_snapshot_id: int | None


class ShareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    path: str
    parent_id: int | None
    sector: str | None
    description: str | None
    last_seen_snapshot_id: int | None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_id: int | None
    nas_user_id: int
    share_id: int
    reviewer_user_id: int
    decision: str
    note: str | None


class SyncRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_id: int | None
    mode: str
    trigger_type: str
    status: str
    attempts_used: int
    duration_ms: int | None
    initiated_by: str | None
    source_label: str | None
    error_detail: str | None
    started_at: datetime | None = None
    completed_at: datetime | None = None
