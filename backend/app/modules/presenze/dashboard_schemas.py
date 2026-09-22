from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.presenze.schemas import PresenzeDashboardSummaryResponse, PresenzeSyncJobResponse


class PresenzeDashboardReviewCaseResponse(BaseModel):
    record_id: uuid.UUID
    collaborator_id: uuid.UUID
    collaborator_name: str
    work_date: date
    schedule_label: str | None = None
    kind: Literal["anomaly", "analysis"]
    reason: str
    missing_minutes: int = 0
    extra_minutes: int = 0
    request_description: str | None = None


class PresenzeDashboardCollaboratorResponse(BaseModel):
    id: uuid.UUID
    application_user_id: int | None = None
    employee_code: str
    company_code: str | None = None
    company_label: str | None = None
    name: str
    birth_date: date | None = None


class PresenzeDashboardSnapshotMetaResponse(BaseModel):
    cached: bool
    stale: bool
    generated_at: datetime
    source_sync_job_id: uuid.UUID | None = None


class PresenzeDashboardWorkspaceResponse(BaseModel):
    summary: PresenzeDashboardSummaryResponse
    review_cases: list[PresenzeDashboardReviewCaseResponse] = Field(default_factory=list)
    recent_collaborators: list[PresenzeDashboardCollaboratorResponse] = Field(default_factory=list)
    sync_jobs: list[PresenzeSyncJobResponse] = Field(default_factory=list)
    snapshot: PresenzeDashboardSnapshotMetaResponse
