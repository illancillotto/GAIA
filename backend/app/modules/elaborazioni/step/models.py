"""STEP read-only archive.

Rows mirror what the STEP portal shows for each contribuente. Original records
are kept verbatim in ``raw_json``; every change observed by a sync is appended
to ``step_observations`` so the history stays reconstructible. Nothing here is
a GAIA payment or a register decision: links to ``ruolo_avvisi`` are exact
identifier matches with an explicit status.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

DEFAULT_STEP_PORTAL_URL = "https://prunesenti-step.servizienti.it/PrunesEntiPp/?c=0044"


class StepCredential(Base):
    __tablename__ = "step_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    portal_url: Mapped[str] = mapped_column(
        String(500), nullable=False, default=DEFAULT_STEP_PORTAL_URL
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    min_delay_ms: Mapped[int] = mapped_column(Integer, default=600, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StepSyncJob(Base):
    __tablename__ = "step_sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    credential_id: Mapped[int | None] = mapped_column(
        ForeignKey("step_credentials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), default="sync", nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StepContribuente(Base):
    __tablename__ = "step_contribuenti"
    __table_args__ = (
        UniqueConstraint("cod_ent", "codice_fiscale", name="uq_step_contribuente_ente_cf"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cod_ent: Mapped[str] = mapped_column(String(20), nullable=False)
    codice_fiscale: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tipo_anagrafica: Mapped[str | None] = mapped_column(String(8), nullable=True)
    denominazione: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    numero_documenti: Mapped[int | None] = mapped_column(Integer, nullable=True)
    importo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    pagato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    residuo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    importo_aggiornato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    stato_documenti: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    anagrafica_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    situazione_contabile_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sections_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary_raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    detail_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_reconciliation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_seen_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("step_sync_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detail_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StepDocumento(Base):
    __tablename__ = "step_documenti"
    __table_args__ = (
        UniqueConstraint(
            "contribuente_id", "num_doc", "prg_coo", name="uq_step_documento_contribuente_doc"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contribuente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("step_contribuenti.id", ondelete="CASCADE"), nullable=False, index=True
    )
    num_doc: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    prg_coo: Mapped[str] = mapped_column(String(10), nullable=False)
    section: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tipo_lista: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cod_trib: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    des_trib: Mapped[str | None] = mapped_column(String(300), nullable=True)
    des_doc: Mapped[str | None] = mapped_column(String(300), nullable=True)
    anno_rif: Mapped[str | None] = mapped_column(String(60), nullable=True)
    data_notifica: Mapped[date | None] = mapped_column(Date, nullable=True)
    tot_dovuto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    imp_carico: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    imp_discaricato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tot_pagato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    residuo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    num_tributi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_status: Mapped[str] = mapped_column(String(20), nullable=False, default="missing")
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pdf_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pdf_original_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    pdf_unavailable_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StepTributo(Base):
    __tablename__ = "step_tributi"
    __table_args__ = (
        UniqueConstraint("documento_id", "position", name="uq_step_tributo_documento_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("step_documenti.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    partita: Mapped[str | None] = mapped_column(String(40), nullable=True)
    prg: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cod_tributo: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    des_tributo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tipo_tributo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    anno_rif: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    imp_carico: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    imp_carico_pagato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    imp_discaricato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    avviso_reference_raw: Mapped[str | None] = mapped_column(String(300), nullable=True)
    codice_cnc: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class StepPagamento(Base):
    __tablename__ = "step_pagamenti"
    __table_args__ = (
        UniqueConstraint(
            "contribuente_id", "position", name="uq_step_pagamento_contribuente_position"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contribuente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("step_contribuenti.id", ondelete="CASCADE"), nullable=False, index=True
    )
    documento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("step_documenti.id", ondelete="SET NULL"), nullable=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    num_quietanza: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    num_doc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    data_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_accredito: Mapped[date | None] = mapped_column(Date, nullable=True)
    modalita: Mapped[str | None] = mapped_column(String(80), nullable=True)
    importo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    importo_pagato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    annullato: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stato: Mapped[str | None] = mapped_column(String(60), nullable=True)
    riferimento: Mapped[str | None] = mapped_column(String(300), nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class StepObservation(Base):
    """Append-only history: one row each time a sync sees a new version of a scheda."""

    __tablename__ = "step_observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contribuente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("step_contribuenti.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("step_sync_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StepRuoloLink(Base):
    """Exact link between a STEP document reference and a ``ruolo_avvisi`` row.

    ``status`` is one of ``linked``, ``not_found``, ``ambiguous`` or
    ``unrecognized``; only ``linked`` rows carry ``ruolo_avviso_id``.
    """

    __tablename__ = "step_ruolo_links"
    __table_args__ = (
        UniqueConstraint(
            "documento_id", "reference_key", name="uq_step_ruolo_link_documento_reference"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("step_documenti.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reference_key: Mapped[str] = mapped_column(String(300), nullable=False)
    codice_cnc: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    anno_rif: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    ruolo_avviso_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_avviso_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tributi_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imp_carico: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    imp_carico_pagato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    imp_discaricato: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
