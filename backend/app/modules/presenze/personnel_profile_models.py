"""Dated HR attestations; independent of INAZ import and shift assignments."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PresenzePersonnelProfile(Base):
    __tablename__ = "presenze_personnel_profiles"
    __table_args__ = (
        UniqueConstraint("collaborator_id", "valid_from", name="uq_personnel_profile_start"),
        CheckConstraint(
            "valid_to IS NULL OR valid_from <= valid_to", name="ck_personnel_profile_dates"
        ),
        CheckConstraint(
            "personnel_area IN ('AGRARIO', 'IMPIANTI')", name="ck_personnel_profile_area"
        ),
        CheckConstraint(
            "employment_relationship IN ('indeterminato', 'determinato', 'avventizio')",
            name="ck_personnel_profile_employment",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    collaborator_id: Mapped[UUID] = mapped_column(
        ForeignKey("presenze_collaborators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    profile_type: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_label: Mapped[str] = mapped_column(String(120), nullable=False)
    duty: Mapped[str] = mapped_column(String(120), nullable=False)
    employment_relationship: Mapped[str] = mapped_column(String(32), nullable=False)
    personnel_area: Mapped[str] = mapped_column(String(16), nullable=False)
    supervisor_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id"), nullable=False
    )
    shift_schedule_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_document_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_note: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
