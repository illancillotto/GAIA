from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WCOrgChart(Base):
    __tablename__ = "wc_org_chart"
    __table_args__ = (
        UniqueConstraint("chart_type", "wc_id", name="uq_wc_org_chart_type_wc_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    wc_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chart_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    wc_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class WCOrgChartEntry(Base):
    __tablename__ = "wc_org_chart_entry"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_chart_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("wc_org_chart.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wc_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    wc_operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wc_operator.id"),
        nullable=True,
        index=True,
    )
    wc_area_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wc_area.id"),
        nullable=True,
        index=True,
    )
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
