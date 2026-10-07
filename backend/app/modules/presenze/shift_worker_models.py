"""Dated manual shift assignments, independent of imported daily records."""

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PresenzeShiftAssignment(Base):
    __tablename__ = "presenze_shift_assignments"
    __table_args__ = (
        CheckConstraint("date_from <= date_to", name="ck_shift_assignment_dates"),
        CheckConstraint(
            "shift_worker_type IN ('none', 'acquaiolo', 'telecontrollo', 'tecnico_turnista')",
            name="ck_shift_assignment_type",
        ),
        CheckConstraint("source IN ('gate', 'gaia')", name="ck_shift_assignment_source"),
        Index("ix_shift_assignment_person_dates", "collaborator_id", "date_from", "date_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    collaborator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presenze_collaborators.id", ondelete="CASCADE"), nullable=False
    )
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    shift_worker_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"), nullable=False)
    command_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
