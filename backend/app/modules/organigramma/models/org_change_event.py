from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ORG_CHANGE_ENTITY_TYPES = ("draft", "unit", "assignment", "override")
ORG_CHANGE_ACTIONS = (
    "draft_created",
    "published",
    "discarded",
    "create",
    "move",
    "relink",
    "detach",
    "assign",
    "unassign",
    "update",
    "delete",
)


class OrgChangeEvent(Base):
    __tablename__ = "org_change_event"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("org_draft.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    changed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
