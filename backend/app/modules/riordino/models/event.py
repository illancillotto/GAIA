"""RiordinoEvent — timeline / audit eventi."""

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func
from app.modules.riordino.models.types import RIORDINO_JSON


class RiordinoEvent(Base):
    __tablename__ = "riordino_events"
    __table_args__ = (
        Index("ix_riordino_events_practice_created", "practice_id", "created_at"),
        Index("ix_riordino_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    phase_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_phases.id"), nullable=True)
    step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_steps.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(RIORDINO_JSON, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="events")
