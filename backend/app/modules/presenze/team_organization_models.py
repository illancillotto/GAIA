"""Canonical, explicit relation between Presenze teams and organization units."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PresenzeTeamOrganization(Base):
    __tablename__ = "presenze_team_organization"

    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_teams.id", ondelete="CASCADE"), primary_key=True
    )
    org_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("org_unit.id", ondelete="CASCADE"), nullable=False, index=True
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
