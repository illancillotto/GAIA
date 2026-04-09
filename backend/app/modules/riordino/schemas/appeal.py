"""Appeal schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.modules.riordino.schemas.base import TimestampedResponse


class AppealCreate(BaseModel):
    appellant_subject_id: uuid.UUID | None = None
    appellant_name: str
    filed_at: date
    deadline_at: date | None = None
    commission_name: str | None = None
    commission_date: date | None = None


class AppealUpdate(BaseModel):
    appellant_subject_id: uuid.UUID | None = None
    appellant_name: str | None = None
    filed_at: date | None = None
    deadline_at: date | None = None
    commission_name: str | None = None
    commission_date: date | None = None
    status: str | None = None


class AppealResolveRequest(BaseModel):
    status: str
    resolution_notes: str | None = None


class AppealResponse(TimestampedResponse):
    practice_id: uuid.UUID
    phase_id: uuid.UUID
    step_id: uuid.UUID | None = None
    appellant_subject_id: uuid.UUID | None = None
    appellant_name: str
    filed_at: date
    deadline_at: date | None = None
    commission_name: str | None = None
    commission_date: date | None = None
    status: str
    resolution_notes: str | None = None
    resolved_at: datetime | None = None
    created_by: int
