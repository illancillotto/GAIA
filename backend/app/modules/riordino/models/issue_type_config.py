"""Configurazione persistente delle tipologie issue del modulo Riordino."""

import uuid

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.riordino.models.types import RIORDINO_UUID


class RiordinoIssueTypeConfig(Base):
    __tablename__ = "riordino_issue_type_configs"
    __table_args__ = (
        Index("ix_riordino_issue_type_configs_code", "code", unique=True),
        Index("ix_riordino_issue_type_configs_category", "category"),
        Index("ix_riordino_issue_type_configs_is_active", "is_active"),
        Index("ix_riordino_issue_type_configs_sort_order", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(RIORDINO_UUID, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    default_severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
