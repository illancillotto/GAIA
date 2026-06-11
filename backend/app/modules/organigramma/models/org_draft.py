from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ORG_DRAFT_STATUSES = ("draft", "published", "discarded")


class OrgDraft(Base):
    __tablename__ = "org_draft"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("org_revision.id", ondelete="RESTRICT"),
        nullable=False,
    )
    working_revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("org_revision.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    published_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
