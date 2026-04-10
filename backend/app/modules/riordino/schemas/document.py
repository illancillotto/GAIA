"""Document schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.modules.riordino.schemas.base import PaginatedResponse, TimestampedResponse


class DocumentResponse(TimestampedResponse):
    practice_id: uuid.UUID
    phase_id: uuid.UUID | None = None
    step_id: uuid.UUID | None = None
    issue_id: uuid.UUID | None = None
    appeal_id: uuid.UUID | None = None
    document_type: str
    version_no: int
    storage_path: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    uploaded_by: int
    uploaded_at: datetime
    deleted_at: datetime | None = None
    notes: str | None = None


class DocumentListResponse(PaginatedResponse):
    items: list[DocumentResponse]
