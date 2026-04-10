"""RiordinoStep — step operativo generato da template."""

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func


class RiordinoStep(Base):
    __tablename__ = "riordino_steps"
    __table_args__ = (
        Index("ix_riordino_steps_practice_phase", "practice_id", "phase_id"),
        Index("ix_riordino_steps_practice_status", "practice_id", "status"),
        UniqueConstraint("practice_id", "code", name="uq_riordino_steps_practice_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    phase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_phases.id"), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_step_templates.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="todo", nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    branch: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_decision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    outcome_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=True)
    due_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="steps", foreign_keys=[practice_id])
    phase: Mapped["RiordinoPhase"] = relationship("RiordinoPhase", back_populates="steps")
    template: Mapped["RiordinoStepTemplate"] = relationship("RiordinoStepTemplate", lazy="selectin")
    tasks: Mapped[list["RiordinoTask"]] = relationship("RiordinoTask", back_populates="step", lazy="selectin")
    issues: Mapped[list["RiordinoIssue"]] = relationship(
        "RiordinoIssue", back_populates="step", lazy="selectin"
    )
    documents: Mapped[list["RiordinoDocument"]] = relationship(
        "RiordinoDocument", back_populates="step", lazy="selectin", foreign_keys="RiordinoDocument.step_id"
    )
    checklist_items: Mapped[list["RiordinoChecklistItem"]] = relationship(
        "RiordinoChecklistItem", back_populates="step", lazy="selectin"
    )
