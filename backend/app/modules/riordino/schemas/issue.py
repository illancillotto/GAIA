"""Issue schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.riordino.schemas.base import TimestampedResponse


class IssueCreate(BaseModel):
    phase_id: uuid.UUID | None = None
    step_id: uuid.UUID | None = None
    type: str
    category: str
    severity: str
    title: str
    description: str | None = None
    assigned_to: int | None = None


class IssueCloseRequest(BaseModel):
    resolution_notes: str


class IssueResponse(TimestampedResponse):
    practice_id: uuid.UUID
    phase_id: uuid.UUID | None = None
    step_id: uuid.UUID | None = None
    type: str
    category: str
    severity: str
    status: str
    title: str
    description: str | None = None
    opened_by: int
    assigned_to: int | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    resolution_notes: str | None = None
    version: int
