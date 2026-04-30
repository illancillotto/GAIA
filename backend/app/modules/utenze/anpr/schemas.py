from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnprSyncConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_calls_per_day: int
    job_enabled: bool
    job_cron: str
    lookback_years: int
    retry_not_found_days: int
    updated_at: datetime | None


class AnprSyncConfigUpdate(BaseModel):
    max_calls_per_day: int | None = None
    job_enabled: bool | None = None
    job_cron: str | None = None
    lookback_years: int | None = None
    retry_not_found_days: int | None = None

    @field_validator("job_cron")
    @classmethod
    def validate_job_cron(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.strip().split())
        if len(normalized.split(" ")) != 5:
            raise ValueError("job_cron must contain exactly 5 cron fields")
        return normalized


class AnprCheckLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    call_type: str
    id_operazione_client: str
    id_operazione_anpr: str | None
    esito: str
    error_detail: str | None
    data_decesso_anpr: date | None
    triggered_by: str
    created_at: datetime


class AnprSyncResult(BaseModel):
    subject_id: str
    success: bool
    esito: str
    data_decesso: date | None = None
    anpr_id: str | None = None
    calls_made: int
    message: str


class AnprSubjectStatus(BaseModel):
    subject_id: str
    anpr_id: str | None
    stato_anpr: str | None
    data_decesso: date | None
    luogo_decesso_comune: str | None
    last_anpr_check_at: datetime | None
    last_c030_check_at: datetime | None


class AnprJobTriggerResult(BaseModel):
    started_at: datetime
    subjects_processed: int
    deceased_found: int
    errors: int
    calls_used: int
    message: str
