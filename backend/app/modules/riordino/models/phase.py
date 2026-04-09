"""RiordinoPhase — istanza fase (2 per pratica)."""

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func


class RiordinoPhase(Base):
    __tablename__ = "riordino_phases"
    __table_args__ = (
        Index("ix_riordino_phases_practice_id", "practice_id"),
        UniqueConstraint("practice_id", "phase_code", name="uq_riordino_phases_practice_phase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    phase_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="not_started", nullable=False)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Forward references resolved by SQLAlchemy
    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="phases")
    steps: Mapped[list["RiordinoStep"]] = relationship(
        "RiordinoStep", back_populates="phase", lazy="selectin"
    )
