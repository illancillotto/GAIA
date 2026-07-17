"""Snapshot immutabile delle particelle AdE in un blocco di riordino."""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.riordino.models.types import RIORDINO_JSON, RIORDINO_UUID


class RiordinoBlockParcelSnapshot(Base):
    __tablename__ = "riordino_block_parcel_snapshots"
    __table_args__ = (
        UniqueConstraint("block_id", "national_cadastral_reference", name="uq_riordino_block_snapshot_ref"),
        Index("ix_riordino_block_parcel_snapshots_block_id", "block_id"),
        Index("ix_riordino_block_parcel_snapshots_ade_id", "ade_particella_id"),
        Index("ix_riordino_block_parcel_snapshots_match_status", "cat_particella_match_status"),
        Index("ix_riordino_block_parcel_snapshots_foglio_particella", "foglio", "particella"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_blocks.id", ondelete="CASCADE"), nullable=False)
    ade_particella_id: Mapped[uuid.UUID | None] = mapped_column(
        RIORDINO_UUID, ForeignKey("cat_ade_particelle.id", ondelete="SET NULL"), nullable=True
    )
    national_cadastral_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    administrative_unit: Mapped[str | None] = mapped_column(String(4), nullable=True)
    codice_catastale: Mapped[str | None] = mapped_column(String(4), nullable=True)
    sezione_catastale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    foglio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    particella: Mapped[str | None] = mapped_column(String(20), nullable=True)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ade_payload_json: Mapped[dict | None] = mapped_column(RIORDINO_JSON, nullable=True)
    cat_particella_id: Mapped[uuid.UUID | None] = mapped_column(
        RIORDINO_UUID, ForeignKey("cat_particelle.id", ondelete="SET NULL"), nullable=True
    )
    cat_particella_match_status: Mapped[str] = mapped_column(String(24), nullable=False)
    cat_particella_match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacitas_payload_json: Mapped[dict | None] = mapped_column(RIORDINO_JSON, nullable=True)
    operator_review_status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    operator_review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=True)
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sister_visura_status: Mapped[str] = mapped_column(String(24), default="not_requested", nullable=False)
    sister_visura_request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sister_visura_document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sister_visura_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sister_visura_requested_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=True)
    sister_visura_requested_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sister_visura_completed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=True)
    sister_visura_completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    block: Mapped["RiordinoBlock"] = relationship("RiordinoBlock", back_populates="parcel_snapshots")
