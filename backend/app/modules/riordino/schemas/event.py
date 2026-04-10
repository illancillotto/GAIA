"""Event schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.modules.riordino.schemas.base import TimestampedResponse


class EventResponse(TimestampedResponse):
    practice_id: uuid.UUID
    phase_id: uuid.UUID | None = None
    step_id: uuid.UUID | None = None
    event_type: str
    payload_json: dict | None = None
    created_by: int
