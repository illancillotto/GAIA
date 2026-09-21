"""Private generation artifacts; not confirmed documents or dispatch intents."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NoticeDraft(Base):
    __tablename__ = "ruolo_notice_drafts"
    __table_args__ = (
        UniqueConstraint("source_system", "source_id", name="uq_notice_draft_source"),
        CheckConstraint("state = 'review_required'", name="ck_notice_draft_state"),
        CheckConstraint("length(artifact_sha256) = 64", name="ck_notice_draft_hash"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_system: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[UUID] = mapped_column(Uuid)
    batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ruolo_tributi_reminder_batches.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("application_users.id", ondelete="RESTRICT"))
    state: Mapped[str] = mapped_column(String(24), default="review_required")
    manifest: Mapped[dict] = mapped_column(JSON)
    input_basis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    artifact: Mapped[bytes] = mapped_column(LargeBinary)
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    artifact_format: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
