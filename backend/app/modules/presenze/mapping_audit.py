from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.presenze.models import PresenzeCollaborator

MAPPING_UNIQUE_INDEX = Index(
    "uq_presenze_collaborators_application_user_id",
    PresenzeCollaborator.__table__.c.application_user_id,
    unique=True,
    postgresql_where=text("application_user_id IS NOT NULL"),
    sqlite_where=text("application_user_id IS NOT NULL"),
)


class PresenzeCollaboratorMappingAudit(Base):
    __tablename__ = "presenze_collaborator_mapping_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collaborator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presenze_collaborators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    previous_application_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_application_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    changed_by_username: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="api")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class PresenzeCollaboratorApplicationUserUpdate(BaseModel):
    application_user_id: int | None = None
    reason: str = Field(default="manual_api_update", min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must not be blank")
        return normalized


class PresenzeCollaboratorMappingAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collaborator_id: uuid.UUID
    previous_application_user_id: int | None = None
    new_application_user_id: int | None = None
    changed_by_user_id: int
    changed_by_username: str
    action: Literal["map", "remap", "unmap"]
    source: str
    reason: str
    created_at: datetime
