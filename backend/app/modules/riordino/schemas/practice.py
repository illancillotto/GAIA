"""Practice schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.riordino.schemas.base import PaginatedResponse, TimestampedResponse
from app.modules.riordino.schemas.document import DocumentResponse


class ChecklistItemResponse(TimestampedResponse):
    step_id: uuid.UUID
    label: str
    is_checked: bool
    is_blocking: bool
    checked_by: int | None = None
    checked_at: datetime | None = None
    sequence_no: int


class StepResponse(TimestampedResponse):
    practice_id: uuid.UUID
    phase_id: uuid.UUID
    template_id: uuid.UUID | None = None
    code: str
    title: str
    sequence_no: int
    status: str
    is_required: bool
    branch: str | None = None
    is_decision: bool
    outcome_code: str | None = None
    outcome_notes: str | None = None
    skip_reason: str | None = None
    requires_document: bool
    owner_user_id: int | None = None
    due_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    version: int
    updated_at: datetime
    checklist_items: list[ChecklistItemResponse] = []
    documents: list[DocumentResponse] = []


class PhaseResponse(TimestampedResponse):
    practice_id: uuid.UUID
    phase_code: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    approved_by: int | None = None
    notes: str | None = None
    updated_at: datetime
    steps: list[StepResponse] = []


class PracticeCreate(BaseModel):
    title: str
    municipality: str
    grid_code: str
    lot_code: str
    owner_user_id: int
    description: str | None = None


class PracticeUpdate(BaseModel):
    title: str | None = None
    municipality: str | None = None
    grid_code: str | None = None
    lot_code: str | None = None
    owner_user_id: int | None = None
    description: str | None = None
    version: int


class PracticeResponse(TimestampedResponse):
    code: str
    title: str
    description: str | None = None
    municipality: str
    grid_code: str
    lot_code: str
    current_phase: str
    status: str
    owner_user_id: int
    opened_at: datetime | None = None
    completed_at: datetime | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    version: int
    created_by: int
    updated_at: datetime


class PracticeListResponse(PaginatedResponse):
    items: list[PracticeResponse]


class PracticeDetailResponse(PracticeResponse):
    phases: list[PhaseResponse]
    issues_count: int = 0
    appeals_count: int = 0
    documents_count: int = 0
