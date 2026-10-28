"""Who pays an avviso instead of its registered taxpayer (heir, buyer, office decision)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

PAYER_REASONS = ("decesso", "vendita", "ufficio")


class RuoloTributiPayerAssignment(Base):
    """One active row per avviso; a voided row stays as history."""

    __tablename__ = "ruolo_tributi_payer_assignments"
    __table_args__ = (
        CheckConstraint(
            "reason IN ('decesso', 'vendita', 'ufficio')", name="ck_ruolo_payer_assignment_reason"
        ),
        Index(
            "uq_ruolo_payer_assignment_active",
            "avviso_id",
            unique=True,
            postgresql_where=text("voided_at IS NULL"),
            sqlite_where=text("voided_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    avviso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payer_subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(String(16), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    voided_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
