from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OperatorFuelCardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codice: str | None
    pan: str
    is_blocked: bool
    expires_at: date | None


class WCOperatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wc_id: int
    username: str | None
    email: str | None
    first_name: str | None
    last_name: str | None
    tax: str | None
    role: str | None
    enabled: bool
    gaia_user_id: int | None
    wc_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
    current_fuel_cards: list[OperatorFuelCardSummary] = []


class WCOperatorListResponse(BaseModel):
    items: list[WCOperatorResponse]
    total: int


class GaiaUserMin(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool


class UnlinkedOperatorItem(BaseModel):
    id: UUID
    wc_id: int
    username: str | None
    email: str | None
    first_name: str | None
    last_name: str | None
    role: str | None
    enabled: bool
    suggested_gaia_user: GaiaUserMin | None


class UnlinkedOperatorsResponse(BaseModel):
    items: list[UnlinkedOperatorItem]
    total: int


class LinkGaiaRequest(BaseModel):
    gaia_user_id: int


class AutoLinkResult(BaseModel):
    linked: int
    already_linked: int
    skipped: int


class OperatorVehicleUsageSummary(BaseModel):
    vehicle_id: UUID
    vehicle_label: str
    usage_count: int
    km_travelled: Decimal | None = None


class OperatorFuelLogSummary(BaseModel):
    id: UUID
    vehicle_id: UUID
    vehicle_label: str
    fueled_at: datetime
    liters: Decimal
    total_cost: Decimal | None
    odometer_km: Decimal | None
    station_name: str | None


class OperatorUsageSessionSummary(BaseModel):
    id: UUID
    vehicle_id: UUID
    vehicle_label: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    km_travelled: Decimal | None


class WCOperatorDetailStats(BaseModel):
    fuel_cards_count: int
    fuel_logs_count: int
    usage_sessions_count: int
    total_liters: Decimal
    total_fuel_cost: Decimal | None
    total_km_travelled: Decimal
    most_used_vehicle: OperatorVehicleUsageSummary | None = None
    last_used_vehicle_label: str | None = None


class WCOperatorDetailResponse(BaseModel):
    operator: WCOperatorResponse
    stats: WCOperatorDetailStats
    current_fuel_cards: list[OperatorFuelCardSummary]
    recent_fuel_logs: list[OperatorFuelLogSummary]
    recent_usage_sessions: list[OperatorUsageSessionSummary]
