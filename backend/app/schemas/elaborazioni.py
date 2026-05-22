from app.schemas.catasto import (
    CatastoBatchDetailResponse as ElaborazioneBatchDetailResponse,
    CatastoBatchResponse as ElaborazioneBatchResponse,
    CatastoCredentialCreateRequest as ElaborazioneCredentialCreateRequest,
    CatastoCaptchaSolveRequest as ElaborazioneCaptchaSolveRequest,
    CatastoCaptchaSummaryResponse as ElaborazioneCaptchaSummaryResponse,
    CatastoCredentialResponse as ElaborazioneCredentialResponse,
    CatastoCredentialStatusResponse as ElaborazioneCredentialStatusResponse,
    CatastoCredentialTestResponse as ElaborazioneCredentialTestResponse,
    CatastoCredentialTestRequest as ElaborazioneCredentialTestRequest,
    CatastoCredentialUpdateRequest as ElaborazioneCredentialUpdateRequest,
    CatastoOperationResponse as ElaborazioneOperationResponse,
    CatastoSingleVisuraCreateRequest as ElaborazioneRichiestaCreateRequest,
    CatastoVisuraRequestResponse as ElaborazioneRichiestaResponse,
)
from datetime import date, datetime

from pydantic import BaseModel, Field

__all__ = [
    "ElaborazioneBatchDetailResponse",
    "ElaborazioneBatchResponse",
    "ElaborazioneAnprErrorSubjectItemResponse",
    "ElaborazioneAnprRunRecordItemResponse",
    "ElaborazioneRuntimeDailyMetricResponse",
    "ElaborazioneRuntimeKpiBlockResponse",
    "ElaborazioneRuntimeMetricsResponse",
    "ElaborazioneRuntimeOperatingWindowResponse",
    "ElaborazioneCaptchaSolveRequest",
    "ElaborazioneCaptchaSummaryResponse",
    "ElaborazioneCredentialCreateRequest",
    "ElaborazioneCredentialResponse",
    "ElaborazioneCredentialStatusResponse",
    "ElaborazioneCredentialTestResponse",
    "ElaborazioneCredentialTestRequest",
    "ElaborazioneCredentialUpdateRequest",
    "ElaborazioneOperationResponse",
    "ElaborazioneAnprRunItemResponse",
    "ElaborazioneAnprSummaryResponse",
    "ElaborazioneRichiestaCreateRequest",
    "ElaborazioneRichiestaResponse",
]


class ElaborazioneAnprErrorSubjectItemResponse(BaseModel):
    subject_id: str
    display_name: str
    codice_fiscale: str
    data_nascita: date | None = None
    stato_anpr: str
    last_anpr_check_at: datetime | None = None
    latest_error_at: datetime | None = None
    latest_error_detail: str | None = None
    capacitas_deceduto: bool | None = None
    capacitas_last_check_at: datetime | None = None


class ElaborazioneAnprRunRecordItemResponse(BaseModel):
    id: str
    subject_id: str
    display_name: str
    codice_fiscale: str
    data_nascita: date | None = None
    last_event_at: datetime
    final_esito: str
    error_detail: str | None = None
    calls_made: int
    call_types: list[str] = Field(default_factory=list)


class ElaborazioneAnprRunItemResponse(BaseModel):
    id: str
    run_date: date
    ruolo_year: int
    status: str
    daily_calls_before: int
    daily_calls_after: int
    subjects_selected: int
    subjects_processed: int
    deceased_found: int
    errors: int
    calls_used: int
    started_at: datetime
    completed_at: datetime | None = None
    records: list[ElaborazioneAnprRunRecordItemResponse] = Field(default_factory=list)


class ElaborazioneAnprSummaryResponse(BaseModel):
    calls_today: int
    configured_daily_limit: int
    hard_daily_limit: int
    effective_daily_limit: int
    batch_size: int
    ruolo_year: int | None = None
    total_error_subjects: int = 0
    error_subjects: list[ElaborazioneAnprErrorSubjectItemResponse] = Field(default_factory=list)
    recent_runs: list[ElaborazioneAnprRunItemResponse] = Field(default_factory=list)


class ElaborazioneRuntimeOperatingWindowResponse(BaseModel):
    enabled: bool
    timezone: str
    start_hour: int
    end_hour: int
    is_within_window: bool
    state_label: str
    next_resume_at: datetime | None = None


class ElaborazioneRuntimeKpiBlockResponse(BaseModel):
    batches_total: int
    requests_total: int
    requests_completed: int
    requests_failed: int
    requests_skipped: int
    requests_not_found: int
    processed_requests: int
    success_rate: float | None = None
    throughput_per_hour: float | None = None
    average_batch_duration_minutes: float | None = None
    average_request_duration_seconds: float | None = None
    latest_processed_at: datetime | None = None


class ElaborazioneRuntimeDailyMetricResponse(BaseModel):
    date: str
    processed_requests: int
    completed: int
    failed: int
    skipped: int
    not_found: int


class ElaborazioneRuntimeMetricsResponse(BaseModel):
    operating_window: ElaborazioneRuntimeOperatingWindowResponse
    totals: ElaborazioneRuntimeKpiBlockResponse
    last_24_hours: ElaborazioneRuntimeKpiBlockResponse
    last_7_days: ElaborazioneRuntimeKpiBlockResponse
    recent_daily: list[ElaborazioneRuntimeDailyMetricResponse] = Field(default_factory=list)
