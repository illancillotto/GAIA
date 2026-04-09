"""RiordinoDocument — documento allegato con classificazione e soft-delete."""

import uuid

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index, func

from app.core.database import Base


class RiordinoDocument(Base):
    __tablename__ = "riordino_documents"
    __table_args__ = (
        Index("ix_riordino_documents_practice_id", "practice_id"),
        Index("ix_riordino_documents_practice_type", "practice_id", "document_type"),
        Index("ix_riordino_documents_step_id", "step_id"),
        Index("ix_riordino_documents_appeal_id", "appeal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    phase_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_phases.id"), nullable=True)
    step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_steps.id"), nullable=True)
    issue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_issues.id"), nullable=True)
    appeal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_appeals.id"), nullable=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="documents", foreign_keys=[practice_id])
    step: Mapped["RiordinoStep | None"] = relationship("RiordinoStep", back_populates="documents", foreign_keys=[step_id])
    appeal: Mapped["RiordinoAppeal | None"] = relationship("RiordinoAppeal", back_populates="documents", foreign_keys=[appeal_id])
