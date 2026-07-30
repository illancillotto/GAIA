from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CatDomandaIrrigua(Base):
    __tablename__ = "cat_domande_irrigue"
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_cat_domande_irrigue_external_id"),
        Index("ix_cat_domande_irrigue_context", "cco", "com", "pvc", "fra", "ccs"),
        Index("ix_cat_domande_irrigue_anno_numero", "anno", "domanda_numero"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anno: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    domanda_numero: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    cco: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    com: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    pvc: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fra: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ccs: Mapped[str | None] = mapped_column(String(20), nullable=True)
    idxana: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_row_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_denominazione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_patrimonio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    patrimonio_has_domanda_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    comune: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    utenza_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_utenze_irrigue.id", ondelete="SET NULL"), nullable=True, index=True
    )
    occupancy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_consorzio_occupancies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stato: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    stato_codice: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    tipo: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tipo_codice: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tipo_scheda_codice: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tipo_scheda: Mapped[str | None] = mapped_column(String(100), nullable=True)
    autorinnovo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ruolo_irr: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tot_sup_cat_mq: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tot_sup_irr_mq: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tot_sup_servita_mq: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tot_sup_richiesta_mq: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tot_sup_malus_mq: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tot_sup_bonus_mq: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    data_ins: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    data_agg: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_rett: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_sosp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_chius: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    particelle: Mapped[list["CatDomandaIrriguaParticella"]] = relationship(
        back_populates="domanda", cascade="all, delete-orphan"
    )


class CatDomandaIrriguaParticella(Base):
    __tablename__ = "cat_domanda_irrigua_particelle"
    __table_args__ = (
        UniqueConstraint("domanda_id", "external_id", name="uq_cat_domanda_irrigua_part_domanda_external"),
        Index("ix_cat_domanda_irrigua_part_key", "part_com", "foglio", "particella", "sub"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    domanda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cat_domande_irrigue.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_consorzio_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_consorzio_unit_segments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    particella_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_particelle.id", ondelete="SET NULL"), nullable=True, index=True
    )
    utenza_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_utenze_irrigue.id", ondelete="SET NULL"), nullable=True, index=True
    )
    occupancy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cat_consorzio_occupancies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    localita: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comizio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    foglio: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    particella: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    sub: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sup_cat_mq: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    sup_irr_mq: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    coltura: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    part_pvc: Mapped[str | None] = mapped_column(String(10), nullable=True)
    part_com: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    part_cco: Mapped[str | None] = mapped_column(String(20), nullable=True)
    part_fra: Mapped[str | None] = mapped_column(String(20), nullable=True)
    part_ccs: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ruolo_bon: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    ruolo_irr: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    ruolo_var: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    domanda: Mapped[CatDomandaIrrigua] = relationship(back_populates="particelle")


__all__ = ["CatDomandaIrrigua", "CatDomandaIrriguaParticella"]
