from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PresenzeDashboardSnapshot(Base):
    __tablename__ = "presenze_dashboard_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "period_start", "period_end", name="uq_presenze_dashboard_snapshots_period"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_sync_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("presenze_sync_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
