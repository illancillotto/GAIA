"""Assegnazioni operative dei blocchi di riordino."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RiordinoBlockAssignment(Base):
    __tablename__ = "riordino_block_assignments"
    __table_args__ = (
        UniqueConstraint("block_id", "user_id", "assignment_role", name="uq_riordino_block_assignments_user_role"),
        Index("ix_riordino_block_assignments_block_id", "block_id"),
        Index("ix_riordino_block_assignments_user_id", "user_id"),
        Index("ix_riordino_block_assignments_role", "assignment_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_blocks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    assignment_role: Mapped[str] = mapped_column(String(24), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_by: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    assigned_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    block: Mapped["RiordinoBlock"] = relationship("RiordinoBlock", back_populates="assignments")
