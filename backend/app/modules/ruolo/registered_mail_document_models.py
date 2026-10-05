import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RegisteredMailDocument(Base):
    __tablename__ = "ruolo_registered_mail_documents"
    __table_args__ = (
        UniqueConstraint("mail_id", "sha256", name="uq_registered_mail_document_hash"),
        UniqueConstraint("document_id", name="uq_registered_mail_document_document"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mail_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_tributi_registered_mails.id", ondelete="RESTRICT"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ana_documents.id", ondelete="RESTRICT")
    )
    tracking_number: Mapped[str] = mapped_column(String(12))
    sha256: Mapped[str] = mapped_column(String(64))
    scanned_on: Mapped[date] = mapped_column(Date)
    source_reference: Mapped[str | None] = mapped_column(String(1024))
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
