from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RuoloImportJob(Base):
    __tablename__ = "ruolo_import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    anno_tributario: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_partite: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_imported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_skipped: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_errors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id"), nullable=True
    )
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuoloAvviso(Base):
    __tablename__ = "ruolo_avvisi"
    __table_args__ = (
        UniqueConstraint("codice_cnc", "anno_tributario", name="uq_ruolo_avvisi_cnc_anno"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    import_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_import_jobs.id", ondelete="CASCADE"), nullable=False
    )
    codice_cnc: Mapped[str] = mapped_column(String(50), nullable=False)
    anno_tributario: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    codice_fiscale_raw: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    nominativo_raw: Mapped[str | None] = mapped_column(String(300), nullable=True)
    domicilio_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    residenza_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    n2_extra_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codice_utenza: Mapped[str | None] = mapped_column(String(30), nullable=True)
    importo_totale_0648: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    importo_totale_0985: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    importo_totale_0668: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    importo_totale_euro: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    importo_totale_lire: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    n4_campo_sconosciuto: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RuoloPartita(Base):
    __tablename__ = "ruolo_partite"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    avviso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="CASCADE"), nullable=False, index=True
    )
    codice_partita: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    comune_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    comune_codice: Mapped[str | None] = mapped_column(String(10), nullable=True)
    contribuente_cf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    co_intestati_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    importo_0648: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    importo_0985: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    importo_0668: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuoloParticella(Base):
    __tablename__ = "ruolo_particelle"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    partita_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_partite.id", ondelete="CASCADE"), nullable=False, index=True
    )
    anno_tributario: Mapped[int] = mapped_column(Integer, nullable=False)
    domanda_irrigua: Mapped[str | None] = mapped_column(String(10), nullable=True)
    distretto: Mapped[str | None] = mapped_column(String(10), nullable=True)
    foglio: Mapped[str] = mapped_column(String(10), nullable=False)
    particella: Mapped[str] = mapped_column(String(20), nullable=False)
    subalterno: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sup_catastale_are: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    sup_catastale_ha: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    sup_irrigata_ha: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    coltura: Mapped[str | None] = mapped_column(String(50), nullable=True)
    importo_manut: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    importo_irrig: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    importo_ist: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    catasto_parcel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catasto_parcels.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cat_particella_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_particelle.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cat_particella_match_status: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    cat_particella_match_confidence: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    cat_particella_match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ade_scan_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    ade_scan_classification: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    ade_scan_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ade_scan_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catasto_visure_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ade_scan_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catasto_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ade_scan_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    ade_scan_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuoloTributiPaymentImportJob(Base):
    __tablename__ = "ruolo_tributi_payment_import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="capacitas_excel", index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_imported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_matched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_unmatched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_errors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    mapping_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    triggered_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuoloTributiPayment(Base):
    __tablename__ = "ruolo_tributi_payments"
    __table_args__ = (
        UniqueConstraint("source", "payment_reference", name="uq_ruolo_tributi_payment_source_reference"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    avviso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="CASCADE"), nullable=False, index=True
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_tributi_payment_import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    codice_cnc_raw: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    codice_utenza_raw: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    anno_tributario: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    payment_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual", index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="valid", index=True)
    raw_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RuoloTributiAvvisoStatus(Base):
    __tablename__ = "ruolo_tributi_avviso_status"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    avviso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    payment_status: Mapped[str] = mapped_column(String(24), nullable=False, default="unpaid", index=True)
    workflow_status: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    saldo_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    last_payment_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capacitas_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacitas_avviso_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RuoloTributiNote(Base):
    __tablename__ = "ruolo_tributi_notes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    avviso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(24), nullable=False, default="internal", index=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RuoloTributiTemplate(Base):
    __tablename__ = "ruolo_tributi_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    template_path: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False, default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuoloTributiYearManager(Base):
    __tablename__ = "ruolo_tributi_year_managers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    manager_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    manager_label: Mapped[str] = mapped_column(String(160), nullable=False)
    year_from: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    year_to: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    calculation_policy: Mapped[str] = mapped_column(String(40), nullable=False, default="external")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RuoloTributiReminder(Base):
    __tablename__ = "ruolo_tributi_reminders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    avviso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_tributi_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", index=True)
    generated_document_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuoloTributiReminderBatch(Base):
    __tablename__ = "ruolo_tributi_reminder_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", index=True)
    template_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    items_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RuoloTributiReminderBatchItem(Base):
    __tablename__ = "ruolo_tributi_reminder_batch_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_tributi_reminder_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    codice_fiscale: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    comune_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    years_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    avviso_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    due_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    paid_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    saldo_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    nas_folder_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_document_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RuoloTributiPostaOnlineImportJob(Base):
    __tablename__ = "ruolo_tributi_posta_online_import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="posta_online", index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_imported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_matched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_ambiguous: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_unmatched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_errors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annualita_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    anomalies_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuoloTributiRegisteredMail(Base):
    __tablename__ = "ruolo_tributi_registered_mails"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "source_shipment_id",
            "recipient_index",
            name="uq_ruolo_tributi_registered_mail_source_recipient",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_tributi_posta_online_import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    avviso_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_system: Mapped[str] = mapped_column(String(40), nullable=False, default="posta_online", index=True)
    source_shipment_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    recipient_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shipment_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    service: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status_label: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    recipient_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    recipient_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipient_city: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    recipient_province: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recipient_zipcode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    annualita_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    match_status: Mapped[str] = mapped_column(String(24), nullable=False, default="unmatched", index=True)
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    anomaly_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    recovery_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    recovered_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_tributi_payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
