from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrgAssignment(Base):
    """Perimetro organizzativo della persona, separato dalla persona stessa.

    Lega user -> org_unit con un responsabile diretto (manager_user_id) e un ruolo
    operativo libero (title, es. "Caposettore", "Operatore", "Autista"). NON è un
    ruolo RBAC.
    """

    __tablename__ = "org_assignment"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    structure_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="organigramma", index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("org_unit.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    manager_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("application_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manuale")
    wc_operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("wc_operator.id", ondelete="SET NULL"),
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
