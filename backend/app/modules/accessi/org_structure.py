from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrgStructureAssignment(Base):
    __tablename__ = "org_structure_assignment"
    __table_args__ = (
        UniqueConstraint("application_user_id", name="uq_org_structure_assignment_application_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    manager_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("application_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    area_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_wc_operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wc_operator.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_wc_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_chart_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_from_source_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
