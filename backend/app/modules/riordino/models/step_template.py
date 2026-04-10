"""RiordinoStepTemplate — template configurabili per generazione step."""

import uuid

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from sqlalchemy import func
from app.modules.riordino.models.types import RIORDINO_JSON, RIORDINO_UUID


class RiordinoStepTemplate(Base):
    __tablename__ = "riordino_step_templates"
    __table_args__ = (
        Index("ix_riordino_step_templates_phase_code", "phase_code"),
        Index("ix_riordino_step_templates_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(RIORDINO_UUID, primary_key=True, default=uuid.uuid4)
    phase_code: Mapped[str] = mapped_column(String(20), nullable=False)  # phase_1, phase_2
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    branch: Mapped[str | None] = mapped_column(String(50), nullable=True)  # es. anomalia
    activation_condition: Mapped[dict | None] = mapped_column(RIORDINO_JSON, nullable=True)
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_decision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    outcome_options: Mapped[list | None] = mapped_column(RIORDINO_JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
