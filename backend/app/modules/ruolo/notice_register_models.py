"""Operational notice register, independent from GAIA numbering and accounting."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NoticeDocument(Base):
    __tablename__ = "ruolo_notice_documents"
    __table_args__ = (
        UniqueConstraint("source_system", "source_key", name="uq_notice_document_source"),
        CheckConstraint("version > 0", name="ck_notice_document_version"),
        CheckConstraint("reconciled_into_id <> id", name="ck_notice_document_reconciliation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_system: Mapped[str] = mapped_column(String(40))
    source_key: Mapped[str] = mapped_column(String(200))
    document_number: Mapped[str] = mapped_column(String(100), index=True)
    tax_code: Mapped[str | None] = mapped_column(String(20), index=True)
    issued_on: Mapped[date | None] = mapped_column(Date)
    original_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    reconciled_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __mapper_args__ = {"version_id_col": version}


class NoticePosition(Base):
    __tablename__ = "ruolo_notice_positions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "source_namespace",
            "source_reference",
            "tax_year",
            name="uq_notice_position_source",
        ),
        UniqueConstraint("document_id", "avviso_id", name="uq_notice_position_avviso"),
        CheckConstraint("tax_year BETWEEN 1900 AND 9999", name="ck_notice_position_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT"), index=True
    )
    source_namespace: Mapped[str] = mapped_column(String(40))
    source_reference: Mapped[str] = mapped_column(String(100))
    tax_year: Mapped[int] = mapped_column(Integer)
    avviso_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="RESTRICT"), index=True
    )


class NoticeAttempt(Base):
    __tablename__ = "ruolo_notice_attempts"
    __table_args__ = (
        UniqueConstraint("document_id", "id", name="uq_notice_attempt_document"),
        UniqueConstraint("source_system", "source_key", name="uq_notice_attempt_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT"), index=True
    )
    source_system: Mapped[str] = mapped_column(String(40))
    source_key: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(40))
    tracking_code: Mapped[str | None] = mapped_column(String(100), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registered_mail_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_tributi_registered_mails.id", ondelete="RESTRICT"), unique=True
    )


class NoticeEvidence(Base):
    __tablename__ = "ruolo_notice_evidence"
    __table_args__ = (
        UniqueConstraint("document_id", "id", name="uq_notice_evidence_document"),
        UniqueConstraint("source_system", "source_key", name="uq_notice_evidence_source"),
        ForeignKeyConstraint(
            ["document_id", "attempt_id"],
            ["ruolo_notice_attempts.document_id", "ruolo_notice_attempts.id"],
            name="fk_notice_evidence_attempt",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT"), index=True
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    source_system: Mapped[str] = mapped_column(String(40))
    source_key: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(60))
    occurred_on: Mapped[date | None] = mapped_column(Date)
    reference: Mapped[str] = mapped_column(Text)
    original_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class NoticeNotification(Base):
    __tablename__ = "ruolo_notice_notifications"
    __table_args__ = (
        CheckConstraint(
            "state IN ('nessuna_evidenza', 'invio_in_corso', 'tentativo_senza_notifica', "
            "'perfezionata', 'da_verificare')",
            name="ck_notice_notification_state",
        ),
        CheckConstraint(
            "(state = 'perfezionata' AND notified_on IS NOT NULL AND evidence_id IS NOT NULL) "
            "OR (state <> 'perfezionata' AND notified_on IS NULL)",
            name="ck_notice_notification_proof",
        ),
        ForeignKeyConstraint(
            ["document_id", "evidence_id"],
            ["ruolo_notice_evidence.document_id", "ruolo_notice_evidence.id"],
            name="fk_notice_notification_evidence",
            ondelete="RESTRICT",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT"), primary_key=True
    )
    state: Mapped[str] = mapped_column(String(40), server_default="da_verificare")
    notified_on: Mapped[date | None] = mapped_column(Date)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class NoticeRecovery(Base):
    """Current STEP assessment per position; revisions live in the register audit."""

    __tablename__ = "ruolo_notice_recoveries"
    __table_args__ = (
        CheckConstraint(
            "state IN ('da_verificare', 'non_affidato_verificato', 'affidato', 'revocato', 'chiuso')",
            name="ck_notice_recovery_state",
        ),
        CheckConstraint(
            "state = 'da_verificare' OR (verified_on IS NOT NULL AND "
            "evidence_reference IS NOT NULL AND length(trim(evidence_reference)) > 0)",
            name="ck_notice_recovery_proof",
        ),
        CheckConstraint(
            "state NOT IN ('affidato', 'revocato', 'chiuso') OR "
            "(case_reference IS NOT NULL AND length(trim(case_reference)) > 0)",
            name="ck_notice_recovery_case",
        ),
        CheckConstraint("amount IS NULL OR amount >= 0", name="ck_notice_recovery_amount"),
    )

    position_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_notice_positions.id", ondelete="RESTRICT"), primary_key=True
    )
    state: Mapped[str] = mapped_column(String(40), server_default="da_verificare")
    case_reference: Mapped[str | None] = mapped_column(String(200))
    verified_on: Mapped[date | None] = mapped_column(Date)
    evidence_reference: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class NoticeAudit(Base):
    __tablename__ = "ruolo_notice_audit"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_notice_audit_version"),
        CheckConstraint("length(trim(reason)) > 0", name="ck_notice_audit_reason"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[int] = mapped_column(ForeignKey("application_users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(60))
    reason: Mapped[str] = mapped_column(Text)
    before_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    after_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
