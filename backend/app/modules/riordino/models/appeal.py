"""RiordinoAppeal — ricorso con dati specifici (ricorrente, scadenza, commissione, esito)."""

import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func
from app.modules.riordino.models.types import RIORDINO_UUID


class RiordinoAppeal(Base):
    __tablename__ = "riordino_appeals"
    __table_args__ = (
        Index("ix_riordino_appeals_practice_id", "practice_id"),
        Index("ix_riordino_appeals_practice_status", "practice_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    phase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_phases.id"), nullable=False)
    step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_steps.id"), nullable=True)
    appellant_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        RIORDINO_UUID, ForeignKey("ana_subjects.id"), nullable=True
    )
    appellant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    filed_at: Mapped[Date] = mapped_column(Date, nullable=False)
    deadline_at: Mapped[Date | None] = mapped_column(Date, nullable=True)
    commission_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    commission_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="appeals")
    documents: Mapped[list["RiordinoDocument"]] = relationship(
        "RiordinoDocument", back_populates="appeal", lazy="selectin", foreign_keys="RiordinoDocument.appeal_id"
    )
