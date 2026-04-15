from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FuelCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codice: str | None
    driver: str | None = None
    sigla: str | None
    is_blocked: bool
    pan: str
    card_number_emissione: str | None
    expires_at: date | None
    prodotti: str | None
    cod: str | None
    current_wc_operator_id: UUID | None
    created_at: datetime
    updated_at: datetime


class FuelCardAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fuel_card_id: UUID
    wc_operator_id: UUID | None
    driver_raw: str | None
    start_at: datetime
    end_at: datetime | None
    changed_by_user_id: int | None
    source: str
    note: str | None
    created_at: datetime
    updated_at: datetime


class FuelCardListResponse(BaseModel):
    items: list[FuelCardResponse]
    total: int


class FuelCardImportResult(BaseModel):
    imported: int
    updated: int
    skipped: int
    assignments_created: int
    assignments_closed: int
    rows_read: int
    unmatched_drivers: int
    errors: list[str]


class FuelCardAssignRequest(BaseModel):
    wc_operator_id: UUID
    driver_raw: str | None = None
    note: str | None = None

