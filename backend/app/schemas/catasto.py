from __future__ import annotations

import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_CF_PF_RE = re.compile(r"^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$")
_PIVA_RE = re.compile(r"^\d{11}$")
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class CatastoCredentialAvailabilityWindow(BaseModel):
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def validate_time(cls, value: str) -> str:
        if not _TIME_RE.fullmatch(value):
            raise ValueError("Time must use HH:MM in the 00:00-23:59 range")
        return value


class CatastoCredentialAvailabilitySchedule(BaseModel):
    timezone: str = "Europe/Rome"
    weekly: dict[str, list[CatastoCredentialAvailabilityWindow]] = Field(default_factory=dict)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        if value != "Europe/Rome":
            raise ValueError("Only Europe/Rome is supported")
        return value

    @field_validator("weekly")
    @classmethod
    def validate_weekly(cls, value: dict[str, list[CatastoCredentialAvailabilityWindow]]) -> dict[str, list[CatastoCredentialAvailabilityWindow]]:
        if any(day not in {str(index) for index in range(7)} for day in value):
            raise ValueError("Weekly schedule keys must be weekdays from 0 (Monday) to 6 (Sunday)")
        if any(len(windows) > 4 for windows in value.values()):
            raise ValueError("A maximum of four availability windows per day is supported")
        return value


class CatastoCredentialCreateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    sister_username: str = Field(min_length=1, max_length=128)
    sister_password: str = Field(min_length=1)
    convenzione: str | None = None
    codice_richiesta: str | None = None
    ufficio_provinciale: str = "ORISTANO Territorio"
    active: bool = True
    is_default: bool = False
    schedule_enabled: bool = False
    availability_schedule: CatastoCredentialAvailabilitySchedule | None = None

    @model_validator(mode="after")
    def validate_schedule(self) -> CatastoCredentialCreateRequest:
        if self.schedule_enabled and self.availability_schedule is None:
            raise ValueError("Availability schedule is required when scheduling is enabled")
        return self


class CatastoCredentialUpdateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    sister_username: str | None = Field(default=None, min_length=1, max_length=128)
    sister_password: str | None = Field(default=None, min_length=1)
    convenzione: str | None = None
    codice_richiesta: str | None = None
    ufficio_provinciale: str | None = None
    active: bool | None = None
    is_default: bool | None = None
    schedule_enabled: bool | None = None
    availability_schedule: CatastoCredentialAvailabilitySchedule | None = None


class CatastoCredentialTestRequest(BaseModel):
    credential_id: UUID | None = None
    sister_username: str | None = Field(default=None, min_length=1, max_length=128)
    sister_password: str | None = Field(default=None, min_length=1)
    convenzione: str | None = None
    codice_richiesta: str | None = None
    ufficio_provinciale: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> CatastoCredentialTestRequest:
        has_transient_credentials = bool(self.sister_username and self.sister_password)
        if self.credential_id is None and not has_transient_credentials:
            return self
        if self.credential_id is not None and has_transient_credentials:
            raise ValueError("Provide either credential_id or transient SISTER credentials, not both")
        if (self.sister_username is None) != (self.sister_password is None):
            raise ValueError("Both sister_username and sister_password are required for transient test")
        return self


class CatastoCredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    label: str
    sister_username: str
    convenzione: str | None
    codice_richiesta: str | None
    ufficio_provinciale: str
    active: bool
    is_default: bool
    schedule_enabled: bool
    availability_schedule: CatastoCredentialAvailabilitySchedule | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CatastoCredentialStatusResponse(BaseModel):
    configured: bool
    credentials: list[CatastoCredentialResponse]
    default_credential: CatastoCredentialResponse | None
    credential: CatastoCredentialResponse | None


class CatastoCredentialTestResponse(BaseModel):
    id: UUID
    credential_id: UUID | None = None
    status: str
    success: bool | None
    mode: str | None
    reachable: bool | None
    authenticated: bool | None
    message: str | None
    verified_at: datetime | None = None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CatastoComuneUpsertRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    codice_sister: str = Field(min_length=1, max_length=255)
    ufficio: str = "ORISTANO Territorio"


class CatastoComuneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    codice_sister: str
    ufficio: str


class CatastoSingleVisuraCreateRequest(BaseModel):
    search_mode: str = Field(default="immobile", min_length=1)
    comune: str | None = None
    catasto: str | None = None
    sezione: str | None = None
    foglio: str | None = None
    particella: str | None = None
    subalterno: str | None = None
    tipo_visura: str = Field(default="Sintetica", min_length=1)
    subject_kind: str | None = None
    subject_id: str | None = None
    request_type: str | None = None
    intestazione: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> CatastoSingleVisuraCreateRequest:
        mode = self.search_mode.strip().lower()
        if mode == "soggetto":
            if not self.subject_id or not self.subject_id.strip():
                raise ValueError("subject_id is required for search_mode='soggetto'")
            self.subject_id = self.subject_id.strip().upper()
            if not self.subject_kind:
                self.subject_kind = "PNF" if _PIVA_RE.match(self.subject_id) else "PF"
            if self.subject_kind == "PF" and not _CF_PF_RE.match(self.subject_id):
                raise ValueError(
                    f"Codice fiscale non valido: '{self.subject_id}'. "
                    "Formato atteso: 6 lettere + 2 cifre + lettera + 2 cifre + lettera + 3 cifre + lettera."
                )
            if self.subject_kind == "PNF" and not _PIVA_RE.match(self.subject_id):
                raise ValueError(
                    f"Partita IVA non valida: '{self.subject_id}'. Formato atteso: 11 cifre."
                )
            return self

        if mode != "immobile":
            raise ValueError("search_mode must be either 'immobile' o 'soggetto'")

        missing = [
            field_name
            for field_name in ("comune", "catasto", "foglio", "particella")
            if not getattr(self, field_name) or not str(getattr(self, field_name)).strip()
        ]
        if missing:
            raise ValueError(f"Missing required fields for search_mode='immobile': {', '.join(missing)}")
        return self


class CatastoCaptchaSolveRequest(BaseModel):
    text: str = Field(min_length=1, max_length=64)


class CatastoCaptchaSummaryResponse(BaseModel):
    processed: int
    correct: int
    wrong: int


class CatastoVisuraRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    user_id: int
    row_index: int
    purpose: str
    target_ruolo_particella_id: UUID | None
    search_mode: str
    comune: str | None
    comune_codice: str | None
    catasto: str | None
    sezione: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    tipo_visura: str
    subject_kind: str | None
    subject_id: str | None
    request_type: str | None
    intestazione: str | None
    status: str
    current_operation: str | None
    error_message: str | None
    attempts: int
    sister_credential_id: UUID | None
    sister_remote_request_id: str | None
    sister_remote_state: str | None
    retry_not_before: datetime | None
    last_error_code: str | None
    captcha_image_path: str | None
    captcha_requested_at: datetime | None
    captcha_expires_at: datetime | None
    captcha_skip_requested: bool
    artifact_dir: str | None
    document_id: UUID | None
    created_at: datetime
    processed_at: datetime | None


class CatastoDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    request_id: UUID | None
    batch_id: UUID | None = None
    search_mode: str
    comune: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    catasto: str | None
    tipo_visura: str
    subject_kind: str | None
    subject_id: str | None
    request_type: str | None
    intestazione: str | None
    filename: str
    file_size: int | None
    sha256: str | None
    codice_fiscale: str | None
    content_request_type: str | None
    parcel_classification: str | None
    parcel_suppressed_at: date | None
    content_metadata_json: dict | None
    created_at: datetime


class CatastoDocumentBulkDownloadRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=1)


class CatastoBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    credential_id: UUID | None
    credential_ids: list[UUID] | None
    name: str | None
    batch_kind: str
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    skipped_items: int
    not_found_items: int
    source_filename: str | None
    current_operation: str | None
    report_json_path: str | None
    report_md_path: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CatastoBatchCredentialUsageResponse(BaseModel):
    credential_id: UUID
    label: str
    sister_username: str | None
    request_count: int
    execution_count: int


class CatastoBatchStatisticsResponse(BaseModel):
    duration_seconds: int
    processed_items: int
    remaining_items: int
    progress_percent: float
    success_rate_percent: float | None
    completed_per_hour: float | None
    processed_per_hour: float | None
    estimated_remaining_seconds: int | None
    total_attempts: int
    average_attempts: float
    credentials_used: list[CatastoBatchCredentialUsageResponse]


class CatastoBatchDetailResponse(CatastoBatchResponse):
    requests: list[CatastoVisuraRequestResponse]
    statistics: CatastoBatchStatisticsResponse | None = None


class CatastoOperationResponse(BaseModel):
    success: bool = True
    message: str


class CatastoRuoloAutoSyncConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    credential_id: UUID | None = None
    credential_ids: list[UUID] | None = None
    primary_enabled: bool | None = None
    secondary_enabled: bool | None = None
    role_parcel_refresh_hours: int | None = Field(default=None, ge=1, le=8760)
    role_subject_refresh_hours: int | None = Field(default=None, ge=1, le=8760)
    consortium_parcel_refresh_hours: int | None = Field(default=None, ge=1, le=8760)
    registry_subject_refresh_hours: int | None = Field(default=None, ge=1, le=8760)
    batch_size: int | None = Field(default=None, ge=1, le=100)


class CatastoRuoloAutoSyncConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    credential_id: UUID | None
    credential_ids: list[str] | None
    primary_enabled: bool
    secondary_enabled: bool
    role_parcel_refresh_hours: int
    role_subject_refresh_hours: int
    consortium_parcel_refresh_hours: int
    registry_subject_refresh_hours: int
    batch_size: int
    source_watermarks: dict | None
    last_planner_at: datetime | None
    last_source_refresh_at: datetime | None
    last_batch_started_at: datetime | None
    last_error_message: str | None
    updated_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class CatastoRuoloAutoSyncItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    ruolo_particella_id: UUID
    cat_particella_id: UUID | None
    comune: str | None
    comune_codice: str | None
    catasto: str
    foglio: str | None
    particella: str | None
    subalterno: str | None
    tipo_visura: str
    status: str
    last_error_message: str | None
    attempt_count: int
    linked_batch_id: UUID | None
    linked_request_id: UUID | None
    retry_after: datetime | None
    last_enqueued_at: datetime | None
    last_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CatastoRuoloAutoSyncStatusCountsResponse(BaseModel):
    total: int = 0
    pending: int = 0
    queued: int = 0
    processing: int = 0
    completed: int = 0
    blocked_source: int = 0
    blocked_runtime: int = 0


class CatastoPerpetualSyncItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: str
    target_key: str
    priority: int
    search_mode: str
    comune: str | None
    foglio: str | None
    particella: str | None
    subalterno: str | None
    subject_kind: str | None
    subject_identifier: str | None
    intestazione: str | None
    status: str
    attempt_count: int
    linked_batch_id: UUID | None
    linked_request_id: UUID | None
    last_error_message: str | None
    retry_after: datetime | None
    next_due_at: datetime
    last_enqueued_at: datetime | None
    last_completed_at: datetime | None
    source_updated_at: datetime | None
    updated_at: datetime


class CatastoAutoSyncDashboardSummaryResponse(BaseModel):
    period_hours: int = 24
    batches_total: int = 0
    batches_active: int = 0
    batches_completed: int = 0
    batches_failed: int = 0
    requests_total: int = 0
    requests_completed: int = 0
    requests_failed: int = 0
    requests_blocked: int = 0
    documents_downloaded: int = 0
    completed_per_hour: float = 0
    average_batch_duration_seconds: int | None = None
    last_activity_at: datetime | None = None


class CatastoAutoSyncHourlyResponse(BaseModel):
    hour: datetime
    completed: int = 0
    failed: int = 0
    documents_downloaded: int = 0


class CatastoAutoSyncEventResponse(BaseModel):
    timestamp: datetime
    level: str
    title: str
    detail: str | None = None
    batch_id: UUID
    request_id: UUID | None = None


class CatastoAutoSyncDashboardResponse(BaseModel):
    summary: CatastoAutoSyncDashboardSummaryResponse
    hourly: list[CatastoAutoSyncHourlyResponse] = Field(default_factory=list)
    recent_batches: list[CatastoBatchResponse] = Field(default_factory=list)
    events: list[CatastoAutoSyncEventResponse] = Field(default_factory=list)


class CatastoRuoloAutoSyncStatusResponse(BaseModel):
    config: CatastoRuoloAutoSyncConfigResponse
    counts: CatastoRuoloAutoSyncStatusCountsResponse
    running_batch: CatastoBatchResponse | None = None
    last_batch: CatastoBatchResponse | None = None
    error_items: list[CatastoRuoloAutoSyncItemResponse] = Field(default_factory=list)
    recent_items: list[CatastoRuoloAutoSyncItemResponse] = Field(default_factory=list)
    scope_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    available_credential_ids: list[UUID] = Field(default_factory=list)
    perpetual_error_items: list[CatastoPerpetualSyncItemResponse] = Field(default_factory=list)
    perpetual_recent_items: list[CatastoPerpetualSyncItemResponse] = Field(default_factory=list)
    dashboard: CatastoAutoSyncDashboardResponse
