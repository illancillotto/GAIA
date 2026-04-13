from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WCAreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wc_id: int
    name: str
    color: str | None
    is_district: bool
    description: str | None
    lat: Decimal | None
    lng: Decimal | None
    polygon: str | None
    wc_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WCAreaListResponse(BaseModel):
    items: list[WCAreaResponse]
    total: int
