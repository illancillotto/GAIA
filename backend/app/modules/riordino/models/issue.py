"""RiordinoIssue — anomalia, eccezione o blocco."""

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func


class RiordinoIssue(Base):
    __tablename__ = "riordino_issues"
    __table_args__ = (
        Index("ix_riordino_issues_practice_id", "practice_id"),
        Index("ix_riordino_issues_practice_severity_status", "practice_id", "severity", "status"),
        Index("ix_riordino_issues_assigned_to_status", "assigned_to", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    phase_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_phases.id"), nullable=True)
    step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_steps.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_by: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=True)
    opened_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="issues")
    step: Mapped["RiordinoStep | None"] = relationship("RiordinoStep", back_populates="issues")
