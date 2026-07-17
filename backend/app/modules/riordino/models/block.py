"""RiordinoBlock - contenitore operativo sopra le pratiche."""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.riordino.models.types import RIORDINO_JSON


class RiordinoBlock(Base):
    __tablename__ = "riordino_blocks"
    __table_args__ = (
        Index("ix_riordino_blocks_status", "status"),
        Index("ix_riordino_blocks_municipality", "municipality"),
        Index("ix_riordino_blocks_coordinator_user_id", "coordinator_user_id"),
        Index("ix_riordino_blocks_created_at", "created_at"),
        Index("ix_riordino_blocks_deleted_at", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selection_type: Mapped[str] = mapped_column(String(32), nullable=False)
    selection_json: Mapped[dict] = mapped_column(RIORDINO_JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    coordinator_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    parcel_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mismatch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignments: Mapped[list["RiordinoBlockAssignment"]] = relationship(
        "RiordinoBlockAssignment",
        back_populates="block",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    parcel_snapshots: Mapped[list["RiordinoBlockParcelSnapshot"]] = relationship(
        "RiordinoBlockParcelSnapshot",
        back_populates="block",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    practices: Mapped[list["RiordinoPractice"]] = relationship("RiordinoPractice", back_populates="block")
    events: Mapped[list["RiordinoEvent"]] = relationship(
        "RiordinoEvent",
        back_populates="block",
        lazy="selectin",
        order_by="RiordinoEvent.created_at.desc()",
    )
