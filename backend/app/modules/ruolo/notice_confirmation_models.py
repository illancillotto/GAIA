"""Durable approval of a validated private notice generation."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NoticeGenerationConfirmation(Base):
    __tablename__ = "ruolo_notice_generation_confirmations"
    __table_args__ = (
        UniqueConstraint(
            "generation_id", "generation_kind", name="uq_notice_generation_confirmation_source"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    generation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    generation_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    review_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    input_basis: Mapped[dict] = mapped_column(JSON, nullable=False)
    identity_keys: Mapped[list] = mapped_column(JSON, nullable=False)
    notice_numbers: Mapped[list] = mapped_column(JSON, nullable=False)
    confirmed_by: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="RESTRICT"), nullable=False
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
