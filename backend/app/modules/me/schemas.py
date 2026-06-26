from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.modules.presenze.schemas import PresenzeDailyRecordListResponse, PresenzeDailyRecordResponse, PresenzeEventSummaryResponse


class MeCapabilitiesResponse(BaseModel):
    presenze: bool
    operazioni: bool
    network: bool


class MeModuleStatusResponse(BaseModel):
    module: str
    enabled: bool
    username: str
    capabilities: MeCapabilitiesResponse
    message: str


class MePresenzeStatusResponse(BaseModel):
    module: str
    enabled: bool
    mapped: bool
    collaborator_id: uuid.UUID | None = None
    collaborator_name: str | None = None
    employee_code: str | None = None
    message: str


class MePresenzeDailyRecordListResponse(PresenzeDailyRecordListResponse):
    pass


class MePresenzeDailyRecordResponse(PresenzeDailyRecordResponse):
    pass


class MePresenzeSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    items: list[PresenzeEventSummaryResponse]

class MeSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    ordinary_minutes: int
    extra_minutes: int
    absence_minutes: int
    worked_days: int
    anomaly_days: int
    km_from_presenze: float
    activities_count: int
    activity_minutes: int
    reports_count: int
    assigned_cases_count: int
    open_cases_count: int
    closed_cases_count: int
    vehicle_sessions_count: int
    vehicle_km: float
    assigned_devices_count: int
    active_vehicle_assignments_count: int


class MeOperazioniSummaryStatusItem(BaseModel):
    status: str
    count: int


class MeOperazioniSummaryCategoryItem(BaseModel):
    category: str
    count: int


class MeOperazioniSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    activities_count: int
    activity_minutes: int
    reports_count: int
    assigned_cases_count: int
    open_cases_count: int
    closed_cases_count: int
    vehicle_sessions_count: int
    vehicle_km: float
    distinct_vehicles_count: int
    activity_statuses: list[MeOperazioniSummaryStatusItem]
    activity_categories: list[MeOperazioniSummaryCategoryItem]


class MeOperazioniActivityItem(BaseModel):
    id: uuid.UUID
    activity_catalog_id: uuid.UUID
    activity_name: str | None = None
    activity_category: str | None = None
    vehicle_id: uuid.UUID | None = None
    vehicle_name: str | None = None
    vehicle_plate_number: str | None = None
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int | None = None
    text_note: str | None = None
    review_outcome: str | None = None
    review_note: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime


class MeOperazioniActivityListResponse(BaseModel):
    items: list[MeOperazioniActivityItem]
    total: int
    page: int
    page_size: int


class MeOperazioniReportItem(BaseModel):
    id: uuid.UUID
    report_number: str
    title: str
    description: str | None = None
    status: str
    category_name: str | None = None
    severity_name: str | None = None
    vehicle_name: str | None = None
    vehicle_plate_number: str | None = None
    created_at: datetime
    updated_at: datetime


class MeOperazioniReportListResponse(BaseModel):
    items: list[MeOperazioniReportItem]
    total: int
    page: int
    page_size: int


class MeOperazioniCaseItem(BaseModel):
    id: uuid.UUID
    case_number: str
    title: str
    status: str
    priority_rank: int | None = None
    category_name: str | None = None
    severity_name: str | None = None
    source_report_number: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class MeOperazioniCaseListResponse(BaseModel):
    items: list[MeOperazioniCaseItem]
    total: int
    page: int
    page_size: int


class MeVehicleUsageSessionItem(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    vehicle_name: str | None = None
    vehicle_plate_number: str | None = None
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    km: float
    notes: str | None = None
    operator_name: str | None = None
    created_at: datetime


class MeVehicleUsageSessionListResponse(BaseModel):
    items: list[MeVehicleUsageSessionItem]
    total: int
    page: int
    page_size: int


class MeAssignedDeviceItem(BaseModel):
    id: int
    ip_address: str
    hostname: str | None = None
    display_name: str | None = None
    resolved_label: str
    lifecycle_state: str
    status: str
    device_type: str | None = None
    operating_system: str | None = None
    asset_label: str | None = None
    location_hint: str | None = None
    last_seen_at: datetime
    updated_at: datetime


class MeAssignedDeviceListResponse(BaseModel):
    items: list[MeAssignedDeviceItem]
    total: int


class MeVehicleAssignmentItem(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    vehicle_name: str
    vehicle_plate_number: str | None = None
    vehicle_type: str
    assignment_target_type: str
    start_at: datetime
    end_at: datetime | None = None
    reason: str | None = None
    notes: str | None = None
    is_active: bool


class MeVehicleAssignmentListResponse(BaseModel):
    items: list[MeVehicleAssignmentItem]
    total: int
