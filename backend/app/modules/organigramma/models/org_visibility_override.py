from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

OVERRIDE_TARGET_TYPES = ("user", "org_unit")
OVERRIDE_SCOPES = ("read", "approve", "full")


class OrgVisibilityOverride(Base):
    """Eccezione esplicita di visibilità, tenuta SEPARATA dall'albero canonico.

    Casi come "HR vede tutto" o "caposettore sostituto" sono modellati qui come
    regole esplicite (rule-based), NON come ruoli RBAC.
    """

    __tablename__ = "org_visibility_override"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    viewer_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_org_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("org_unit.id", ondelete="CASCADE"),
        nullable=True,
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
