"""RiordinoTask — task operativo figlio di step."""

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func


class RiordinoTask(Base):
    __tablename__ = "riordino_tasks"
    __table_args__ = (
        Index("ix_riordino_tasks_practice_id", "practice_id"),
        Index("ix_riordino_tasks_step_id", "step_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    step_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_steps.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="todo", nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=True)
    due_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    step: Mapped["RiordinoStep"] = relationship("RiordinoStep", back_populates="tasks")
