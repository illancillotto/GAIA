from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.inaz.models import (
    INAZ_HOLIDAY_KIND_ORDINARY,
    INAZ_HOLIDAY_KIND_SUPPRESSED,
    INAZ_HOLIDAY_KIND_WORKING_OVERRIDE,
)

InazHolidayKind = Literal["ordinary", "suppressed", "working_override"]


def resolve_inaz_holiday_kind(
    holiday_kind: InazHolidayKind | None,
    is_workday_override: bool | None,
    *,
    current_kind: InazHolidayKind = "ordinary",
) -> InazHolidayKind:
    if holiday_kind is not None:
        if is_workday_override is not None:
            expected_override = holiday_kind != INAZ_HOLIDAY_KIND_ORDINARY
            if is_workday_override != expected_override:
                raise ValueError("holiday_kind e is_workday_override sono incoerenti")
        return holiday_kind
    if is_workday_override is None:
        return current_kind
    return INAZ_HOLIDAY_KIND_WORKING_OVERRIDE if is_workday_override else INAZ_HOLIDAY_KIND_ORDINARY


class InazModuleStatusResponse(BaseModel):
    module: str
    enabled: bool
    username: str
    message: str


class InazCollaboratorApplicationUserUpdate(BaseModel):
    application_user_id: int | None = None


InazContractKind = Literal["operaio", "impiegato", "quadro", "altro"]


class InazCollaboratorContractProfileUpdate(BaseModel):
    contract_kind: InazContractKind | None = None
    standard_daily_minutes: int | None = Field(default=None, ge=1, le=1440)


class InazHolidayCreate(BaseModel):
    holiday_date: date
    label: str = Field(min_length=1, max_length=255)
    company_code: str | None = Field(default=None, max_length=32)
    holiday_kind: InazHolidayKind | None = None
    is_workday_override: bool | None = None

    def to_model_payload(self) -> dict[str, Any]:
        return {
            "holiday_date": self.holiday_date,
            "label": self.label,
            "company_code": self.company_code,
            "holiday_kind": resolve_inaz_holiday_kind(self.holiday_kind, self.is_workday_override),
        }


class InazHolidayUpdate(BaseModel):
    holiday_date: date | None = None
    label: str | None = Field(default=None, min_length=1, max_length=255)
    company_code: str | None = Field(default=None, max_length=32)
    holiday_kind: InazHolidayKind | None = None
    is_workday_override: bool | None = None

    def to_model_payload(self, *, current_kind: InazHolidayKind) -> dict[str, Any]:
        payload = self.model_dump(exclude_unset=True)
        holiday_kind = resolve_inaz_holiday_kind(
            payload.pop("holiday_kind", None),
            payload.pop("is_workday_override", None),
            current_kind=current_kind,
        )
        payload["holiday_kind"] = holiday_kind
        return payload


class InazHolidayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    holiday_date: date
    label: str
    company_code: str | None = None
    holiday_kind: InazHolidayKind = INAZ_HOLIDAY_KIND_ORDINARY
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


class InazScheduleBootstrapRulePreview(BaseModel):
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
    applies_on_holiday: bool = False
    ordinary_label: str | None = None
    sort_order: int = 0


class InazScheduleBootstrapPresetPreview(BaseModel):
    preset_key: str
    template_code: str
    template_label: str
    template_notes: str | None = None
    source_schedule_codes: list[str] = Field(default_factory=list)
    detected_records_count: int = 0
    detected_collaborators_count: int = 0
    already_exists: bool = False
    rules: list[InazScheduleBootstrapRulePreview] = Field(default_factory=list)


class InazScheduleBootstrapCollaboratorSuggestion(BaseModel):
    collaborator_id: uuid.UUID
    employee_code: str
    collaborator_name: str
    company_code: str | None = None
    dominant_schedule_code: str | None = None
    schedule_codes: list[str] = Field(default_factory=list)
    suggested_template_code: str | None = None
    suggested_template_label: str | None = None
    suggestion_confidence: Literal["high", "medium", "low", "none"] = "none"
    suggestion_reason: str | None = None
    already_assigned: bool = False


class InazScheduleBootstrapPreviewResponse(BaseModel):
    detected_collaborators_total: int
    collaborators_with_suggestion_total: int
    collaborators_without_assignment_total: int
    presets: list[InazScheduleBootstrapPresetPreview] = Field(default_factory=list)
    collaborator_suggestions: list[InazScheduleBootstrapCollaboratorSuggestion] = Field(default_factory=list)


class InazScheduleBootstrapApplyRequest(BaseModel):
    create_missing_templates: bool = True
    assign_unassigned_collaborators: bool = True


class InazScheduleBootstrapApplyResponse(BaseModel):
    created_templates: int
    created_assignments: int
    skipped_existing_templates: int
    skipped_existing_assignments: int
    template_codes: list[str] = Field(default_factory=list)
    assigned_employee_codes: list[str] = Field(default_factory=list)


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
    contract_kind: InazContractKind | None = None
    standard_daily_minutes: int | None = None
    is_active: bool
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InazAccessContextResponse(BaseModel):
    can_view_all_data: bool
    can_view_all_credentials: bool
    can_manage_supervisors: bool
    is_supervisor: bool
    assigned_collaborators_count: int


class InazSupervisorAssignmentUpdate(BaseModel):
    supervisor_user_id: int | None = None


class InazSupervisorAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supervisor_user_id: int
    collaborator_id: uuid.UUID
    assigned_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime
    supervisor: dict[str, Any] | None = None
    collaborator: InazCollaboratorResponse | None = None


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
    trasferta_minutes: int | None = None
    trasferta_montano: bool = False
    reperibilita_unit: Literal["none", "hours", "days", "shifts"]
    reperibilita_quantity: int | None = None
    override_straordinario_minutes: int | None = None
    override_mpe_minutes: int | None = None
    manual_note: str | None = None
    request_type: str | None = None
    request_description: str | None = None
    request_status: str | None = None
    request_authorized_by: str | None = None
    resolved_absence_cause: str | None = None
    validation_status: str
    validated_by_user_id: int | None = None
    validated_at: datetime | None = None
    validation_note: str | None = None
    effective_straordinario_minutes: int | None = None
    effective_mpe_minutes: int | None = None
    effective_extra_minutes: int | None = None
    night_minutes: int = 0
    festive_minutes: int = 0
    festive_night_minutes: int = 0
    ordinary_night_minutes: int = 0
    overtime_day_minutes: int = 0
    overtime_night_minutes: int = 0
    overtime_festive_minutes: int = 0
    overtime_festive_night_minutes: int = 0
    shift_festive_day_minutes: int = 0
    shift_night_minutes: int = 0
    shift_festive_night_minutes: int = 0
    monthly_night_shift_count: int = 0
    ordinary_night_bonus_threshold_met: bool = False
    ordinary_night_bonus_rate: int | None = None
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
    holiday_kind: InazHolidayKind | None = None
    grants_recovery_day: bool = False
    recovery_day_credit: int = 0
    uses_recovery_day: bool = False
    recovery_day_debit: int = 0
    recovery_day_balance_delta: int = 0
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


class InazDashboardSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    collaborators_total: int
    mapped_collaborators_total: int
    active_collaborators_total: int
    daily_records_total: int
    ordinary_minutes_total: int
    absence_minutes_total: int
    extra_minutes_total: int
    straordinario_minutes_total: int
    maggior_presenza_minutes_total: int
    km_total: int
    trasferta_minutes_total: int
    trasferta_days_total: int
    trasferta_montano_days_total: int
    anomaly_total: int
    special_day_total: int
    recovery_days_matured_total: int
    recovery_days_used_total: int
    recovery_days_balance_total: int
    worked_days_total: int
    absence_days_total: int
    justified_days_total: int
    cause_stats: dict[str, int] = Field(default_factory=dict)
    schedule_stats: list[dict[str, int | str]] = Field(default_factory=list)


class InazDailyRecordManualUpdate(BaseModel):
    km_value: int | None = Field(default=None, ge=0, le=5000)
    trasferta_minutes: int | None = Field(default=None, ge=0, le=1440)
    trasferta_montano: bool | None = None
    reperibilita_unit: Literal["none", "hours", "days", "shifts"] | None = None
    reperibilita_quantity: int | None = Field(default=None, ge=0, le=24)
    override_straordinario_minutes: int | None = Field(default=None, ge=0, le=1440)
    override_mpe_minutes: int | None = Field(default=None, ge=0, le=1440)
    manual_note: str | None = Field(default=None, max_length=1000)
    validation_status: Literal["pending", "validated"] | None = None
    validation_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_reperibilita(self) -> "InazDailyRecordManualUpdate":
        if self.reperibilita_unit is None and self.reperibilita_quantity is None:
            return self
        unit = self.reperibilita_unit or "none"
        quantity = self.reperibilita_quantity
        if unit == "none":
            if quantity not in (None, 0):
                raise ValueError("reperibilita_quantity must be empty when reperibilita_unit is 'none'")
            self.reperibilita_quantity = None
            return self
        if quantity is None or quantity <= 0:
            raise ValueError("reperibilita_quantity must be greater than zero when reperibilita is set")
        return self


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


class InazRecoveryAdjustmentCreate(BaseModel):
    collaborator_id: uuid.UUID
    adjustment_date: date
    delta_days: int = Field(ge=-365, le=365)
    kind: Literal["credit", "debit", "correction"] = "correction"
    reason: str = Field(min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


class InazRecoveryAdjustmentUpdate(BaseModel):
    adjustment_date: date | None = None
    delta_days: int | None = Field(default=None, ge=-365, le=365)
    kind: Literal["credit", "debit", "correction"] | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


class InazRecoveryAdjustmentReview(BaseModel):
    approval_status: Literal["approved", "rejected"]
    approval_note: str | None = Field(default=None, max_length=2000)


class InazRecoveryAdjustmentResponse(BaseModel):
    id: uuid.UUID
    collaborator_id: uuid.UUID
    adjustment_date: date
    delta_days: int
    kind: Literal["credit", "debit", "correction"]
    approval_status: Literal["pending", "approved", "rejected"]
    reason: str
    note: str | None = None
    approval_note: str | None = None
    created_by_user_id: int | None = None
    updated_by_user_id: int | None = None
    reviewed_by_user_id: int | None = None
    created_by_label: str | None = None
    updated_by_label: str | None = None
    reviewed_by_label: str | None = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None


class InazRecoveryBalanceItemResponse(BaseModel):
    collaborator_id: uuid.UUID
    employee_code: str
    collaborator_name: str
    company_code: str | None = None
    application_user_id: int | None = None
    matured_days: int
    used_days: int
    manual_delta_days: int
    balance_days: int
    pending_validation_count: int
    manual_adjustment_count: int
    pending_adjustment_count: int
    last_matured_date: date | None = None
    last_used_date: date | None = None
    last_adjustment_date: date | None = None
    last_adjustment_status: Literal["pending", "approved", "rejected"] | None = None


class InazRecoveryDashboardResponse(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    collaborators_total: int
    matured_days_total: int
    used_days_total: int
    manual_delta_days_total: int
    balance_days_total: int
    pending_validation_total: int
    pending_adjustments_total: int
    negative_balance_total: int
    items: list[InazRecoveryBalanceItemResponse] = Field(default_factory=list)


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


class InazAutoSyncConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_enabled: bool
    credential_id: int | None = None
    collaborator_limit: int | None = None
    updated_at: datetime | None = None
    updated_by_user_id: int | None = None
    schedule_cron: str
    schedule_timezone: str
    schedule_times: list[str] = Field(default_factory=list)


class InazAutoSyncConfigUpdate(BaseModel):
    job_enabled: bool | None = None
    credential_id: int | None = None
    collaborator_limit: int | None = Field(default=None, ge=1, le=500)


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
