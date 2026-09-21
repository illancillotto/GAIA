"""Immutable import snapshots and reviewable row outcomes."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NoticeImportBatch(Base):
    __tablename__ = "ruolo_notice_import_batches"
    __table_args__ = (UniqueConstraint("source", "digest", name="uq_notice_import_digest"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(40))
    digest: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(255))
    parser_version: Mapped[str] = mapped_column(String(40))
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    status: Mapped[str] = mapped_column(String(20), default="preview")
    summary: Mapped[dict] = mapped_column(JSON)
    actor_id: Mapped[int] = mapped_column(ForeignKey("application_users.id", ondelete="RESTRICT"))
    confirmed_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="RESTRICT")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NoticeImportRow(Base):
    __tablename__ = "ruolo_notice_import_rows"
    __table_args__ = (UniqueConstraint("batch_id", "row_number", name="uq_notice_import_row"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_notice_import_batches.id", ondelete="RESTRICT"), index=True
    )
    row_number: Mapped[int] = mapped_column(Integer)
    source_key: Mapped[str] = mapped_column(String(200))
    fingerprint: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    anomalies: Mapped[list] = mapped_column(JSON)
    outcome: Mapped[str] = mapped_column(String(20), default="new")
    resolution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT")
    )
