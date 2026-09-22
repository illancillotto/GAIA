"""Durable approval of a validated private notice generation."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, LargeBinary, String, UniqueConstraint, Uuid, func
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


class NoticeGenerationExport(Base):
    """One immutable archive per confirmation, never a dispatch instruction."""

    __tablename__ = "ruolo_notice_generation_exports"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    confirmation_id: Mapped[UUID] = mapped_column(
        ForeignKey("ruolo_notice_generation_confirmations.id", ondelete="RESTRICT"), unique=True
    )
    manifest: Mapped[dict] = mapped_column(JSON)
    artifact: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[int] = mapped_column(ForeignKey("application_users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NoticeExportClaim(Base):
    """Audit each authorized delivery attempt, including retries of the same archive."""

    __tablename__ = "ruolo_notice_export_claims"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    export_id: Mapped[UUID] = mapped_column(
        ForeignKey("ruolo_notice_generation_exports.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("application_users.id", ondelete="RESTRICT"))
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NoticeExportIdentity(Base):
    """A final notice identity belongs to one archive; corrections need an explicit workflow."""

    __tablename__ = "ruolo_notice_export_identities"

    identity_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    export_id: Mapped[UUID] = mapped_column(
        ForeignKey("ruolo_notice_generation_exports.id", ondelete="RESTRICT"), index=True
    )
