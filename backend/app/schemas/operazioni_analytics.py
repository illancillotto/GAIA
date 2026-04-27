"""Schemas for the Operazioni Analytics module."""

from __future__ import annotations

from pydantic import BaseModel


# --- Shared ---

class TimeSeriesPoint(BaseModel):
    period: str          # "2024-01", "2024-W03", "2024-01-15"
    value: float


# --- Summary KPIs ---

class AnalyticsSummary(BaseModel):
    period_label: str            # e.g. "Ultimi 30 giorni"
    total_km: float
    total_liters: float
    total_fuel_cost: float
    total_work_hours: float
    work_hours_source: str = "activity"  # "activity" | "session"
    active_sessions: int
    anomaly_count: int
    avg_consumption_l_per_100km: float | None


# --- Fuel Analytics ---

class FuelStationUsageItem(BaseModel):
    station_name: str
    refuel_count: int
    total_liters: float
    total_cost: float


class FuelRelatedUsageItem(BaseModel):
    id: str
    label: str
    refuel_count: int
    total_liters: float
    total_cost: float
    avg_price_per_liter: float | None = None
    avg_refuel_cost: float | None = None
    avg_liters_per_refuel: float | None = None


class FuelTopItem(BaseModel):
    id: str
    label: str           # vehicle plate or operator name
    total_liters: float
    total_cost: float
    refuel_count: int
    total_km: float | None = None
    avg_consumption_l_per_100km: float | None = None
    consumption_coefficient: float | None = None
    consumption_judgement: str | None = None
    avg_price_per_liter: float | None = None
    avg_refuel_cost: float | None = None
    avg_liters_per_refuel: float | None = None
    top_stations: list[FuelStationUsageItem] = []
    related: list[FuelRelatedUsageItem] = []


class FuelAnalytics(BaseModel):
    time_series: list[TimeSeriesPoint]         # liters per period
    cost_series: list[TimeSeriesPoint]         # cost per period
    top_vehicles: list[FuelTopItem]
    top_operators: list[FuelTopItem]
    total_liters: float
    total_cost: float
    avg_liters_per_refuel: float
    storno_count: int = 0
    storno_liters: float = 0.0
    storno_cost: float = 0.0


# --- Km Analytics ---

class KmTopItem(BaseModel):
    id: str
    label: str
    total_km: float
    session_count: int
    avg_km_per_session: float | None = None


class KmSessionExtremeItem(BaseModel):
    session_id: str
    vehicle_label: str
    operator_label: str | None = None
    started_at: str
    ended_at: str
    duration_minutes: int
    km: float


class KmAnalytics(BaseModel):
    time_series: list[TimeSeriesPoint]         # km per period
    top_vehicles: list[KmTopItem]
    top_operators: list[KmTopItem]
    total_km: float
    avg_km_per_session: float
    longest_session: KmSessionExtremeItem | None = None
    shortest_session: KmSessionExtremeItem | None = None


# --- Work Hours Analytics ---

class WorkHoursOperatorItem(BaseModel):
    operator_id: str
    operator_name: str
    total_hours: float
    activity_count: int


class WorkHoursTeamItem(BaseModel):
    team_id: str
    team_name: str
    total_hours: float
    operator_count: int


class WorkHoursCategoryItem(BaseModel):
    category: str
    total_hours: float
    activity_count: int


class WorkHoursAnalytics(BaseModel):
    time_series: list[TimeSeriesPoint]         # hours per period
    top_operators: list[WorkHoursOperatorItem]
    by_team: list[WorkHoursTeamItem]
    by_category: list[WorkHoursCategoryItem]
    total_hours: float
    avg_hours_per_operator: float


# --- Anomalies ---

class AnomalyItem(BaseModel):
    id: str
    type: str            # "driver_mismatch" | "excessive_fuel" | "hours_discrepancy" | "orphan_session" | "unmatched_refuel"
    severity: str        # "low" | "medium" | "high"
    description: str
    entity_id: str | None
    entity_label: str | None
    detected_at: str     # ISO date string
    details: dict


class AnomaliesResponse(BaseModel):
    items: list[AnomalyItem]
    total: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
