"""Daily edit and meal voucher contracts, re-exported by the Presenze schema facade."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.presenze.shift_worker_schemas import ShiftWorkerFields


class PresenzeDailyRecordMealVoucherFields(ShiftWorkerFields):
    meal_voucher_shift: bool = False
    meal_voucher_manual: bool = False
    meal_voucher_automatic: bool = False
    meal_voucher_count: Literal[0, 1] = 0
    meal_voucher_sources: list[Literal["automatic", "manual", "shift"]] = Field(
        default_factory=list
    )
    meal_voucher_audit: list[dict] | None = None


class PresenzeDailyRecordManualUpdate(BaseModel):
    meal_voucher_manual: bool = False
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
    def validate_reperibilita(self) -> PresenzeDailyRecordManualUpdate:
        if self.reperibilita_unit is None and self.reperibilita_quantity is None:
            return self
        unit = self.reperibilita_unit or "none"
        quantity = self.reperibilita_quantity
        if unit == "none":
            if quantity not in (None, 0):
                raise ValueError(
                    "reperibilita_quantity must be empty when reperibilita_unit is 'none'"
                )
            self.reperibilita_quantity = None
            return self
        if quantity is None or quantity <= 0:
            raise ValueError(
                "reperibilita_quantity must be greater than zero when reperibilita is set"
            )
        return self


PresenzeHolidayKind = Literal["ordinary", "suppressed", "working_override"]


class PresenzeDailyPunchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    daily_record_id: uuid.UUID
    sequence: int
    entry_time: time | None = None
    exit_time: time | None = None
    terminal_label: str | None = None


class PresenzeDetailPunchRowResponse(BaseModel):
    time: str | None = None
    direction: str | None = None
    terminal_label: str | None = None
    raw: dict[str, str] = Field(default_factory=dict)


class PresenzeDailyRecordResponse(PresenzeDailyRecordMealVoucherFields):
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
    employment_relationship: str | None = None
    employment_valid_from: date | None = None
    employment_valid_to: date | None = None
    employment_source_sha256: str | None = None
    avventizio_no_punches: bool = False
    attendance_note: str | None = None
    export_absence_code: str | None = None
    validation_status: str
    validated_by_user_id: int | None = None
    validated_at: datetime | None = None
    validation_note: str | None = None
    effective_straordinario_minutes: int | None = None
    effective_mpe_minutes: int | None = None
    effective_extra_minutes: int | None = None
    operational_status: Literal["ok", "in_analysis", "blocking", "unknown"] = "unknown"
    operational_formula_code: str | None = None
    operational_expected_minutes: int | None = None
    operational_worked_minutes: int | None = None
    operational_missing_minutes: int = 0
    operational_mpe_minutes: int = 0
    operational_notes: list[str] = Field(default_factory=list)
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
    detail_punch_rows: list[PresenzeDetailPunchRowResponse] = Field(default_factory=list)
    detail_text: str | None = None
    detail_error: str | None = None
    special_day: bool | None = None
    holiday_kind: PresenzeHolidayKind | None = None
    grants_recovery_day: bool = False
    recovery_day_credit: int = 0
    uses_recovery_day: bool = False
    recovery_day_debit: int = 0
    recovery_day_balance_delta: int = 0
    raw_payload_json: dict[str, Any] | list[Any] | None = None
    source_job_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    punches: list[PresenzeDailyPunchResponse] = Field(default_factory=list)


class PresenzeDailyRecordListResponse(BaseModel):
    items: list[PresenzeDailyRecordResponse]
    total: int
    page: int
    page_size: int
