from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WarehouseRequest(Base):
    __tablename__ = "warehouse_request"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    wc_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    wc_report_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    field_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("field_report.id"), nullable=True, index=True
    )
    report_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reported_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    report_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    request_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
