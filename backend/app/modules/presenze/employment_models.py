"""Dated employment attestations, independent of duties and shift assignments."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
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


class PresenzeEmploymentPeriod(Base):
    __tablename__ = "presenze_employment_periods"
    __table_args__ = (
        UniqueConstraint("collaborator_id", "valid_from", name="uq_employment_period_start"),
        CheckConstraint("valid_from <= valid_to", name="ck_employment_period_dates"),
        CheckConstraint(
            "employment_relationship IN ('indeterminato', 'determinato', 'avventizio')",
            name="ck_employment_period_relationship",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    collaborator_id: Mapped[UUID] = mapped_column(
        ForeignKey("presenze_collaborators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    employment_relationship: Mapped[str] = mapped_column(String(32), nullable=False)
    source_document_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_note: Mapped[str] = mapped_column(String(1000), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
