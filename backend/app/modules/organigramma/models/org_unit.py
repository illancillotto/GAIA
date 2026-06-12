from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Valori validati app-side (vedi schemas). Tenuti come costanti per riuso nei test.
ORG_UNIT_TYPES = ("direzione", "distretto", "settore", "squadra")
ORG_SOURCES = ("manuale", "whitecompany", "bridge_team")


class OrgUnit(Base):
    """Nodo canonico della gerarchia organizzativa (verità principale in GAIA)."""

    __tablename__ = "org_unit"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    structure_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="organigramma", index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("org_unit.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    canvas_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    canvas_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manuale")
    wc_area_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wc_area.id", ondelete="SET NULL"),
        nullable=True,
    )
    legacy_team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("team.id", ondelete="SET NULL"),
        nullable=True,
    )
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
