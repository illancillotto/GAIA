"""RiordinoChecklistItem — checklist per step."""

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func


class RiordinoChecklistItem(Base):
    __tablename__ = "riordino_checklist_items"
    __table_args__ = (
        Index("ix_riordino_checklist_items_step_id", "step_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    step_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_steps.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    checked_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=True)
    checked_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    step: Mapped["RiordinoStep"] = relationship("RiordinoStep", back_populates="checklist_items")
