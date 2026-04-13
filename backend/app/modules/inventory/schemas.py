from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WarehouseRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wc_id: int
    wc_report_id: int | None
    field_report_id: UUID | None
    report_type: str | None
    reported_by: str | None
    requested_by: str | None
    report_date: datetime | None
    request_date: datetime | None
    archived: bool
    status_active: bool
    wc_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WarehouseRequestListResponse(BaseModel):
    items: list[WarehouseRequestResponse]
    total: int
