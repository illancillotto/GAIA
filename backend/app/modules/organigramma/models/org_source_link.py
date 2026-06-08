from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SOURCE_LINK_ENTITY_TYPES = ("org_unit", "org_assignment")


class OrgSourceLink(Base):
    """Mapping idempotente di provenienza per import/sync WhiteCompany.

    Collega un'entità canonica (org_unit | org_assignment) alla riga sorgente
    (wc_area / wc_operator / wc_org_chart_entry). Se is_manual_locked=True il sync
    NON sovrascrive l'entità canonica.
    """

    __tablename__ = "org_source_link"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "source_system",
            "external_wc_id",
            name="uq_org_source_link_entity_source_external",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("org_unit.id", ondelete="CASCADE"), nullable=True
    )
    org_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("org_assignment.id", ondelete="CASCADE"), nullable=True
    )
    source_system: Mapped[str] = mapped_column(String(30), nullable=False, default="whitecompany")
    wc_area_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("wc_area.id", ondelete="SET NULL"), nullable=True
    )
    wc_operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("wc_operator.id", ondelete="SET NULL"), nullable=True
    )
    wc_org_chart_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("wc_org_chart_entry.id", ondelete="SET NULL"), nullable=True
    )
    external_wc_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_manual_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
