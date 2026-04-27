from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnagraficaModuleStatusResponse(BaseModel):
    module: str
    enabled: bool
    message: str
    username: str


class AnagraficaImportPreviewRequest(BaseModel):
    letter: str | None = Field(default=None, min_length=1, max_length=1)

    @field_validator("letter")
    @classmethod
    def validate_letter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) != 1 or not normalized.isalpha():
            raise ValueError("letter must be a single alphabetical character")
        return normalized


class AnagraficaImportWarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    message: str
    path: str | None = None


class AnagraficaCsvImportErrorResponse(BaseModel):
    row_number: int
    message: str
    codice_fiscale: str | None = None


class AnagraficaCsvImportResponse(BaseModel):
    total_rows: int
    created_subjects: int
    updated_subjects: int
    skipped_rows: int
    errors: list[AnagraficaCsvImportErrorResponse] = Field(default_factory=list)


class AnagraficaPreviewDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    filename: str
    relative_path: str
    nas_path: str
    extension: str | None
    is_pdf: bool
    doc_type: str
    classification_source: str
    warnings: list[str] = Field(default_factory=list)


class AnagraficaPreviewSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    folder_name: str
    letter: str
    nas_folder_path: str
    source_name_raw: str
    subject_type: str
    requires_review: bool
    confidence: float
    cognome: str | None = None
    nome: str | None = None
    codice_fiscale: str | None = None
    ragione_sociale: str | None = None
    partita_iva: str | None = None
    warnings: list[str] = Field(default_factory=list)
    documents: list[AnagraficaPreviewDocumentResponse] = Field(default_factory=list)


class AnagraficaImportPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    letter: str
    archive_root: str
    generated_at: datetime
    total_folders: int
    parsed_subjects: int
    subjects_requiring_review: int
    total_documents: int
    non_pdf_documents: int
    warnings: list[AnagraficaImportWarningResponse] = Field(default_factory=list)
    errors: list[AnagraficaImportWarningResponse] = Field(default_factory=list)
    subjects: list[AnagraficaPreviewSubjectResponse] = Field(default_factory=list)


class AnagraficaImportRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    letter: str
    status: str
    total_folders: int
    imported_ok: int
    imported_errors: int
    warning_count: int
    pending_items: int = 0
    running_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    created_subjects: int = 0
    updated_subjects: int = 0
    created_documents: int = 0
    updated_documents: int = 0
    generated_at: datetime
    completed_at: datetime | None
    log_json: dict | list | None = None


class AnagraficaSubjectImportResponse(BaseModel):
    subject_id: str
    matched_folder_path: str
    matched_folder_name: str
    warning_count: int
    created_documents: int
    updated_documents: int
    imported_at: datetime


class AnagraficaResetRequest(BaseModel):
    confirm: str


class AnagraficaResetResponse(BaseModel):
    cleared_subject_links: int
    deleted_documents: int
    deleted_audit_logs: int
    deleted_import_jobs: int
    deleted_import_job_items: int
    deleted_storage_files: int


class AnagraficaNasFolderCandidateResponse(BaseModel):
    folder_name: str
    letter: str | None = None
    nas_folder_path: str
    score: int
    subject_type: str
    confidence: float
    requires_review: bool
    codice_fiscale: str | None = None
    partita_iva: str | None = None
    ragione_sociale: str | None = None
    cognome: str | None = None
    nome: str | None = None


class AnagraficaSubjectNasImportStatusResponse(BaseModel):
    can_import_from_nas: bool
    missing_in_nas: bool
    matched_folder_path: str | None = None
    matched_folder_name: str | None = None
    total_files_in_nas: int
    pending_files_in_nas: int
    message: str


class AnagraficaImportJobItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str | None = None
    letter: str | None = None
    folder_name: str
    nas_folder_path: str
    status: str
    attempt_count: int
    warning_count: int
    documents_created: int
    documents_updated: int
    payload_json: dict | list | None = None
    last_error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AnagraficaImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    requested_by_user_id: int | None
    letter: str | None
    status: str
    total_folders: int
    imported_ok: int
    imported_errors: int
    warning_count: int
    pending_items: int = 0
    running_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    items: list[AnagraficaImportJobItemResponse] = Field(default_factory=list)
    log_json: dict | list | None = None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class AnagraficaPersonPayload(BaseModel):
    cognome: str
    nome: str
    codice_fiscale: str
    data_nascita: date | None = None
    comune_nascita: str | None = None
    indirizzo: str | None = None
    comune_residenza: str | None = None
    cap: str | None = None
    email: str | None = None
    telefono: str | None = None
    note: str | None = None


class AnagraficaCompanyPayload(BaseModel):
    ragione_sociale: str
    partita_iva: str
    codice_fiscale: str | None = None
    forma_giuridica: str | None = None
    sede_legale: str | None = None
    comune_sede: str | None = None
    cap: str | None = None
    email_pec: str | None = None
    telefono: str | None = None
    note: str | None = None


class AnagraficaPersonResponse(AnagraficaPersonPayload):
    model_config = ConfigDict(from_attributes=True)

    subject_id: str
    created_at: datetime
    updated_at: datetime


class AnagraficaPersonSnapshotResponse(AnagraficaPersonPayload):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    is_capacitas_history: bool = False
    source_system: str
    source_ref: str | None = None
    valid_from: datetime | None
    collected_at: datetime


class AnagraficaCompanyResponse(AnagraficaCompanyPayload):
    model_config = ConfigDict(from_attributes=True)

    subject_id: str
    created_at: datetime
    updated_at: datetime


class AnagraficaAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    changed_by_user_id: int | None
    action: str
    diff_json: dict[str, Any] | list[Any] | None = None
    changed_at: datetime


class AnagraficaCatastoDocumentResponse(BaseModel):
    id: str
    request_id: str | None = None
    comune: str
    foglio: str
    particella: str
    subalterno: str | None = None
    catasto: str
    tipo_visura: str
    filename: str
    codice_fiscale: str | None = None
    created_at: datetime


class AnagraficaSubjectCreateRequest(BaseModel):
    subject_type: Literal["person", "company", "unknown"]
    source_name_raw: str
    nas_folder_path: str | None = None
    nas_folder_letter: str | None = None
    requires_review: bool = False
    person: AnagraficaPersonPayload | None = None
    company: AnagraficaCompanyPayload | None = None


class AnagraficaSubjectUpdateRequest(BaseModel):
    source_name_raw: str | None = None
    status: Literal["active", "inactive", "duplicate"] | None = None
    nas_folder_path: str | None = None
    nas_folder_letter: str | None = None
    requires_review: bool | None = None
    person: AnagraficaPersonPayload | None = None
    company: AnagraficaCompanyPayload | None = None


class AnagraficaSubjectListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_type: str
    status: str
    source_system: str
    source_external_id: str | None = None
    source_name_raw: str
    display_name: str
    codice_fiscale: str | None = None
    partita_iva: str | None = None
    nas_folder_path: str | None = None
    nas_folder_letter: str | None = None
    requires_review: bool
    imported_at: datetime | None
    document_count: int
    created_at: datetime
    updated_at: datetime


class AnagraficaSubjectListResponse(BaseModel):
    items: list[AnagraficaSubjectListItemResponse]
    total: int
    page: int
    page_size: int


class AnagraficaSubjectDetailResponse(BaseModel):
    id: str
    subject_type: str
    status: str
    source_system: str
    source_external_id: str | None = None
    source_name_raw: str
    nas_folder_path: str | None = None
    nas_folder_letter: str | None = None
    requires_review: bool
    imported_at: datetime | None
    created_at: datetime
    updated_at: datetime
    person: AnagraficaPersonResponse | None = None
    person_snapshots: list[AnagraficaPersonSnapshotResponse] = Field(default_factory=list)
    company: AnagraficaCompanyResponse | None = None
    documents: list[AnagraficaPreviewDocumentResponse] = Field(default_factory=list)
    audit_log: list[AnagraficaAuditLogResponse] = Field(default_factory=list)
    catasto_documents: list[AnagraficaCatastoDocumentResponse] = Field(default_factory=list)


class AnagraficaDocumentUpdateRequest(BaseModel):
    doc_type: str | None = None
    notes: str | None = None


class AnagraficaStatsResponse(BaseModel):
    total_subjects: int
    total_persons: int
    total_companies: int
    total_unknown: int
    total_documents: int
    requires_review: int
    active_subjects: int
    inactive_subjects: int
    documents_unclassified: int
    by_letter: dict[str, int] = Field(default_factory=dict)


class AnagraficaDocumentSummaryBucketResponse(BaseModel):
    doc_type: str
    count: int


class AnagraficaDocumentSummaryItemResponse(BaseModel):
    document_id: str
    subject_id: str
    subject_display_name: str
    filename: str
    doc_type: str
    classification_source: str
    created_at: datetime


class AnagraficaDocumentSummaryResponse(BaseModel):
    total_documents: int
    documents_unclassified: int
    classified_documents: int
    by_doc_type: list[AnagraficaDocumentSummaryBucketResponse] = Field(default_factory=list)
    recent_unclassified: list[AnagraficaDocumentSummaryItemResponse] = Field(default_factory=list)


class AnagraficaSearchResultResponse(BaseModel):
    items: list[AnagraficaSubjectListItemResponse]
    total: int


class BonificaUserStagingResponse(BaseModel):
    id: str
    wc_id: int
    username: str | None = None
    email: str | None = None
    user_type: str | None = None
    business_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    tax: str | None = None
    phone: str | None = None
    mobile: str | None = None
    role: str | None = None
    enabled: bool
    wc_synced_at: datetime | None = None
    review_status: str
    matched_subject_id: str | None = None
    matched_subject_display_name: str | None = None
    mismatch_fields: dict[str, Any] | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class BonificaUserStagingListResponse(BaseModel):
    items: list[BonificaUserStagingResponse]
    total: int
    page: int
    page_size: int


class BonificaUserStagingBulkApproveRequest(BaseModel):
    ids: list[str]


class BonificaUserStagingBulkApproveResponse(BaseModel):
    approved: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class XlsxImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requested_by_user_id: int | None
    filename: str
    status: str
    total_rows: int
    processed_rows: int
    inserted: int
    updated: int
    unchanged: int
    anomalies: int
    errors: int
    error_log: list[Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class XlsxImportStartResponse(BaseModel):
    batch_id: str
    status: str
    message: str
