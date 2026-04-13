from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        pass

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnagraficaSubjectType(StrEnum):
    PERSON = "person"
    COMPANY = "company"
    UNKNOWN = "unknown"


class AnagraficaSubjectStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DUPLICATE = "duplicate"


class AnagraficaDocType(StrEnum):
    INGIUNZIONE = "ingiunzione"
    NOTIFICA = "notifica"
    ESTRATTO_DEBITO = "estratto_debito"
    PRATICA_INTERNA = "pratica_interna"
    VISURA = "visura"
    CORRISPONDENZA = "corrispondenza"
    CONTRATTO = "contratto"
    ALTRO = "altro"


class AnagraficaClassificationSource(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


class AnagraficaStorageType(StrEnum):
    NAS_LINK = "nas_link"
    LOCAL_UPLOAD = "local_upload"


class AnagraficaImportJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnagraficaImportJobItemStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnagraficaSubject(Base):
    __tablename__ = "ana_subjects"
    __table_args__ = (UniqueConstraint("nas_folder_path", name="uq_ana_subjects_nas_folder_path"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(
        String(32),
        default=AnagraficaSubjectType.UNKNOWN.value,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=AnagraficaSubjectStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    source_name_raw: Mapped[str] = mapped_column(String(512), nullable=False)
    nas_folder_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    nas_folder_letter: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AnagraficaPerson(Base):
    __tablename__ = "ana_persons"
    __table_args__ = (UniqueConstraint("codice_fiscale", name="uq_ana_persons_codice_fiscale"),)

    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cognome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    codice_fiscale: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    data_nascita: Mapped[date | None] = mapped_column(Date, nullable=True)
    comune_nascita: Mapped[str | None] = mapped_column(String(255), nullable=True)
    indirizzo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comune_residenza: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cap: Mapped[str | None] = mapped_column(String(16), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AnagraficaCompany(Base):
    __tablename__ = "ana_companies"
    __table_args__ = (UniqueConstraint("partita_iva", name="uq_ana_companies_partita_iva"),)

    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ragione_sociale: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    partita_iva: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    forma_giuridica: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sede_legale: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comune_sede: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cap: Mapped[str | None] = mapped_column(String(16), nullable=True)
    email_pec: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AnagraficaDocument(Base):
    __tablename__ = "ana_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[str] = mapped_column(
        String(64),
        default=AnagraficaDocType.ALTRO.value,
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    nas_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classification_source: Mapped[str] = mapped_column(
        String(32),
        default=AnagraficaClassificationSource.AUTO.value,
        nullable=False,
    )
    storage_type: Mapped[str] = mapped_column(
        String(32),
        default=AnagraficaStorageType.NAS_LINK.value,
        nullable=False,
    )
    local_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AnagraficaImportJob(Base):
    __tablename__ = "ana_import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    letter: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=AnagraficaImportJobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    total_folders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_ok: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    log_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AnagraficaImportJobItem(Base):
    __tablename__ = "ana_import_job_items"
    __table_args__ = (UniqueConstraint("job_id", "nas_folder_path", name="uq_ana_import_job_items_job_path"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ana_import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    letter: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    folder_name: Mapped[str] = mapped_column(String(512), nullable=False)
    nas_folder_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=AnagraficaImportJobItemStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    documents_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    documents_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BonificaUserStaging(Base):
    __tablename__ = "bonifica_user_staging"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    wc_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    user_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    business_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tax: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    wc_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="new", nullable=False, index=True)
    matched_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ana_subjects.id"),
        nullable=True,
        index=True,
    )
    mismatch_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("application_users.id"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AnagraficaAuditLog(Base):
    __tablename__ = "ana_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    diff_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
