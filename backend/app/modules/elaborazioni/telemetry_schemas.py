from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SisterPortalTotals(BaseModel):
    events: int
    executions: int
    successes: int
    errors: int
    retries: int
    cooldowns: int
    success_rate: float
    average_duration_ms: int | None
    p95_duration_ms: int | None


class SisterPortalDownloadTotals(BaseModel):
    total: int
    by_visura_type: dict[str, int]
    by_request_type: dict[str, int]


class SisterPortalTimelinePoint(BaseModel):
    bucket: datetime
    events: int
    successes: int
    errors: int
    average_duration_ms: int | None


class SisterPortalStepMetric(BaseModel):
    step: str
    events: int
    successes: int
    errors: int
    average_duration_ms: int | None
    p95_duration_ms: int | None


class SisterPortalErrorMetric(BaseModel):
    event_type: str
    step: str
    count: int
    last_seen_at: datetime
    http_status: int | None


class SisterPortalCredentialMetric(BaseModel):
    credential_id: UUID | None
    label: str
    events: int
    successes: int
    errors: int
    success_rate: float
    last_seen_at: datetime


class SisterPortalAlert(BaseModel):
    id: str
    severity: str
    title: str
    detail: str
    active_since: datetime


class SisterPortalRecentEvent(BaseModel):
    id: UUID
    occurred_at: datetime
    event_type: str
    step: str
    outcome: str
    severity: str
    duration_ms: int | None
    http_status: int | None
    endpoint: str | None
    attempt: int | None
    cooldown_seconds: int | None
    credential_id: UUID | None
    credential_label: str | None
    batch_id: UUID | None
    request_id: UUID | None


class SisterPortalHealthResponse(BaseModel):
    generated_at: datetime
    window_hours: int
    status: str
    totals: SisterPortalTotals
    downloads: SisterPortalDownloadTotals
    timeline: list[SisterPortalTimelinePoint]
    steps: list[SisterPortalStepMetric]
    errors: list[SisterPortalErrorMetric]
    credentials: list[SisterPortalCredentialMetric]
    alerts: list[SisterPortalAlert]
    recent_events: list[SisterPortalRecentEvent]


class SisterPortalEventListResponse(BaseModel):
    total: int
    items: list[SisterPortalRecentEvent] = Field(default_factory=list)


__all__ = [
    "SisterPortalAlert",
    "SisterPortalCredentialMetric",
    "SisterPortalDownloadTotals",
    "SisterPortalErrorMetric",
    "SisterPortalEventListResponse",
    "SisterPortalHealthResponse",
    "SisterPortalRecentEvent",
    "SisterPortalStepMetric",
    "SisterPortalTimelinePoint",
    "SisterPortalTotals",
]
