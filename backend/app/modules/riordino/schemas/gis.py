"""GIS link schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.riordino.schemas.base import TimestampedResponse


class GisLinkCreate(BaseModel):
    layer_name: str
    feature_id: str | None = None
    geometry_ref: str | None = None
    notes: str | None = None


class GisLinkUpdate(BaseModel):
    layer_name: str | None = None
    feature_id: str | None = None
    geometry_ref: str | None = None
    sync_status: str | None = None
    notes: str | None = None


class GisLinkResponse(TimestampedResponse):
    practice_id: uuid.UUID
    layer_name: str
    feature_id: str | None = None
    geometry_ref: str | None = None
    sync_status: str
    last_synced_at: datetime | None = None
    notes: str | None = None
    updated_at: datetime
