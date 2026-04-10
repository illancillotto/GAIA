"""Notification schemas."""

from __future__ import annotations

import uuid

from app.modules.riordino.schemas.base import TimestampedResponse


class NotificationResponse(TimestampedResponse):
    user_id: int
    practice_id: uuid.UUID | None = None
    type: str
    message: str
    is_read: bool
