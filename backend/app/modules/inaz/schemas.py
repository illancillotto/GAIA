from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InazModuleStatusResponse(BaseModel):
    module: str
    enabled: bool
    username: str
    message: str


class InazCollaboratorApplicationUserUpdate(BaseModel):
    application_user_id: int | None = None


class InazHolidayCreate(BaseModel):
    holiday_date: date
    label: str = Field(min_length=1, max_length=255)
    company_code: str | None = Field(default=None, max_length=32)
    is_workday_override: bool = False


class InazHolidayUpdate(BaseModel):
    holiday_date: date | None = None
    label: str | None = Field(default=None, min_length=1, max_length=255)
    company_code: str | None = Field(default=None, max_length=32)
    is_workday_override: bool | None = None


class InazHolidayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    holiday_date: date
    label: str
    company_code: str | None = None
    is_workday_override: bool
    created_at: datetime
    updated_at: datetime


class InazHolidayBootstrapResponse(BaseModel):
    year: int
    created: int
    items: list[InazHolidayResponse]


class InazScheduleTemplateCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    company_code: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    valid_from: date | None = None
    valid_to: date | None = None
    notes: str | None = None


class InazScheduleTemplateUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    label: str | None = Field(default=None, min_length=1, max_length=255)
    company_code: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    notes: str | None = None


class InazScheduleRuleCreate(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    weekday: int | None = Field(default=None, ge=0, le=6)
    recurrence_kind: str = Field(default="weekly", min_length=1, max_length=32)
    week_of_month: int | None = Field(default=None, ge=1, le=5)
    interval_weeks: int | None = Field(default=None, ge=1, le=8)
    anchor_date: date | None = None
    start_time: time
    end_time: time
    season_start_month: int | None = Field(default=None, ge=1, le=12)
    season_start_day: int | None = Field(default=None, ge=1, le=31)
    season_end_month: int | None = Field(default=None, ge=1, le=12)
    season_end_day: int | None = Field(default=None, ge=1, le=31)
    applies_on_holiday: bool = False
    ordinary_label: str | None = Field(default=None, max_length=64)
    sort_order: int = 0


class InazScheduleRuleUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    weekday: int | None = Field(default=None, ge=0, le=6)
    recurrence_kind: str | None = Field(default=None, min_length=1, max_length=32)
    week_of_month: int | None = Field(default=None, ge=1, le=5)
    interval_weeks: int | None = Field(default=None, ge=1, le=8)
    anchor_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    season_start_month: int | None = Field(default=None, ge=1, le=12)
    season_start_day: int | None = Field(default=None, ge=1, le=31)
    season_end_month: int | None = Field(default=None, ge=1, le=12)
    season_end_day: int | None = Field(default=None, ge=1, le=31)
    applies_on_holiday: bool | None = None
    ordinary_label: str | None = Field(default=None, max_length=64)
    sort_order: int | None = None


class InazScheduleRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    label: str | None = None
    weekday: int | None = None
    recurrence_kind: str
    week_of_month: int | None = None
    interval_weeks: int | None = None
    anchor_date: date | None = None
    start_time: time
    end_time: time
    season_start_month: int | None = None
    season_start_day: int | None = None
    season_end_month: int | None = None
    season_end_day: int | None = None
    applies_on_holiday: bool
    ordinary_label: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class InazScheduleTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    company_code: str | None = None
    is_active: bool
    valid_from: date | None = None
    valid_to: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    rules: list[InazScheduleRuleResponse] = Field(default_factory=list)


class InazCollaboratorScheduleAssignmentCreate(BaseModel):
    template_id: int
    valid_from: date | None = None
    valid_to: date | None = None
    notes: str | None = None


class InazCollaboratorScheduleAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collaborator_id: uuid.UUID
    template_id: int
    valid_from: date | None = None
    valid_to: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    template: InazScheduleTemplateResponse | None = None


class InazDailyPunchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    daily_record_id: uuid.UUID
    sequence: int
    entry_time: time | None = None
    exit_time: time | None = None
    terminal_label: str | None = None


class InazCollaboratorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_user_id: int | None = None
    application_user_id: int | None = None
    kint: str | None = None
    kkint: str | None = None
    employee_code: str
    company_code: str | None = None
    company_label: str | None = None
    name: str
    birth_date: date | None = None
    is_active: bool
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InazCollaboratorListResponse(BaseModel):
    items: list[InazCollaboratorResponse]
    total: int
    page: int
    page_size: int


class InazDailyRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    collaborator_id: uuid.UUID
    owner_user_id: int | None = None
    application_user_id: int | None = None
    work_date: date
    schedule_code: str | None = None
    teo_minutes: int | None = None
    ordinary_minutes: int | None = None
    absence_minutes: int | None = None
    justified_minutes: int | None = None
    maggiorazione_minutes: int | None = None
    mpe_minutes: int | None = None
    straordinario_minutes: int | None = None
    km_value: int | None = None
    override_straordinario_minutes: int | None = None
    override_mpe_minutes: int | None = None
    manual_note: str | None = None
    request_type: str | None = None
    request_description: str | None = None
    request_status: str | None = None
    request_authorized_by: str | None = None
    resolved_absence_cause: str | None = None
    effective_straordinario_minutes: int | None = None
    effective_mpe_minutes: int | None = None
    effective_extra_minutes: int | None = None
    stato: str | None = None
    evidenze: str | None = None
    raw_weekday: str | None = None
    detail_title: str | None = None
    detail_status: str | None = None
    detail_programmed_schedule: str | None = None
    detail_effective_schedule: str | None = None
    detail_time_slots: str | None = None
    detail_schedule_type: str | None = None
    detail_theoretical_hours: str | None = None
    detail_absence_hours: str | None = None
    detail_day_summary: dict[str, str] = Field(default_factory=dict)
    detail_day_totals: dict[str, str] = Field(default_factory=dict)
    detail_requests: list[dict[str, str]] = Field(default_factory=list)
    detail_anomalies: list[dict[str, str]] = Field(default_factory=list)
    detail_text: str | None = None
    detail_error: str | None = None
    special_day: bool | None = None
    raw_payload_json: dict[str, Any] | list[Any] | None = None
    source_job_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    punches: list[InazDailyPunchResponse] = Field(default_factory=list)


class InazDailyRecordListResponse(BaseModel):
    items: list[InazDailyRecordResponse]
    total: int
    page: int
    page_size: int


class InazDailyRecordManualUpdate(BaseModel):
    km_value: int | None = Field(default=None, ge=0, le=5000)
    override_straordinario_minutes: int | None = Field(default=None, ge=0, le=1440)
    override_mpe_minutes: int | None = Field(default=None, ge=0, le=1440)
    manual_note: str | None = Field(default=None, max_length=1000)


class InazEventSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    collaborator_id: uuid.UUID
    owner_user_id: int | None = None
    application_user_id: int | None = None
    period_start: date
    period_end: date
    event_code: str | None = None
    description: str
    valid_from: date | None = None
    valid_to: date | None = None
    spettante_minutes: int | None = None
    fruito_minutes: int | None = None
    residuo_prec_minutes: int | None = None
    saldo_minutes: int | None = None
    autorizzato_minutes: int | None = None
    pianificato_minutes: int | None = None
    richiesto_minutes: int | None = None
    saldo_totale_minutes: int | None = None
    unitamisura: str | None = None
    raw_payload_json: dict[str, Any] | list[Any] | None = None
    source_job_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class InazImportPreviewCollaborator(BaseModel):
    employee_code: str
    company_code: str | None = None
    name: str
    application_user_id: int | None = None
    total_daily_rows: int
    total_summary_rows: int
    period_start: date
    period_end: date


class InazImportPreviewResponse(BaseModel):
    total_collaborators: int
    total_daily_rows: int
    total_summary_rows: int
    collaborators: list[InazImportPreviewCollaborator]
    errors: list[str]


class InazImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    filename: str | None = None
    requested_by_user_id: int
    target_user_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    total_records: int
    records_imported: int
    records_skipped: int
    records_errors: int
    error_detail: str | None = None
    params_json: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class InazImportJobListResponse(BaseModel):
    items: list[InazImportJobResponse]
    total: int


class InazCredentialCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)
    active: bool = True


class InazCredentialUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=1)
    active: bool | None = None


class InazCredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_user_id: int
    label: str
    username: str
    active: bool
    last_used_at: datetime | None = None
    last_authenticated_url: str | None = None
    last_error: str | None = None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime


class InazCredentialTestResult(BaseModel):
    ok: bool
    authenticated_url: str | None = None
    cookies: str | None = None
    error: str | None = None


class InazSyncJobCreateRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    credential_id: int
    collaborator_limit: int | None = Field(default=None, ge=1, le=500)


class InazSyncJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    requested_by_user_id: int
    credential_id: int | None = None
    import_job_id: uuid.UUID | None = None
    period_start: date
    period_end: date
    collaborator_limit: int | None = None
    records_imported: int
    records_skipped: int
    records_errors: int
    json_artifact_path: str | None = None
    worker_log_path: str | None = None
    worker_pid: int | None = None
    attempt_count: int
    max_attempts: int
    error_detail: str | None = None
    params_json: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class InazSyncJobListResponse(BaseModel):
    items: list[InazSyncJobResponse]
    total: int


class InazImportJsonResponse(BaseModel):
    job: InazImportJobResponse
    preview: InazImportPreviewResponse


class InazCollaboratorCalendarResponse(BaseModel):
    collaborator: InazCollaboratorResponse
    date_from: date
    date_to: date
    items: list[InazDailyRecordResponse]


class InazCollaboratorSummaryResponse(BaseModel):
    collaborator: InazCollaboratorResponse
    period_start: date
    period_end: date
    items: list[InazEventSummaryResponse]


class InazExportRequestParams(BaseModel):
    collaborator_ids: list[uuid.UUID] | None = None
    period_start: date
    employee_kind: str = "AVVENTIZI"
    template_path: str | None = None
