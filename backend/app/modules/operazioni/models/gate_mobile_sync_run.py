from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GateMobileSyncRun(Base):
    __tablename__ = "gate_mobile_sync_run"

    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)
    trigger_source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual_cli", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requested_tasks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    operators_pushed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_tasks_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    error_kind: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
