from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, Uuid, func
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
