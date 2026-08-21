from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SisterPortalEvent(Base):
    __tablename__ = "sister_portal_events"
    __table_args__ = (
        Index("ix_sister_portal_events_user_occurred", "user_id", "occurred_at"),
        Index("ix_sister_portal_events_credential_occurred", "credential_id", "occurred_at"),
        Index("ix_sister_portal_events_type_occurred", "event_type", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=True,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("catasto_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("catasto_visure_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    credential_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("catasto_credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cooldown_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


__all__ = ["SisterPortalEvent"]
