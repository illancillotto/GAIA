"""Persistent outbox. Binary artifacts are private, bounded database snapshots."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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


class CommunicationAccount(Base):
    __tablename__ = "communication_accounts"
    __table_args__ = (
        CheckConstraint("channel IN ('pec','email')", name="ck_comm_account_channel"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    channel: Mapped[str] = mapped_column(String(10), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    sender: Mapped[str] = mapped_column(String(254))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    smtp_host: Mapped[str] = mapped_column(String(253))
    smtp_port: Mapped[int] = mapped_column(Integer)
    smtp_encryption: Mapped[str] = mapped_column(String(12))
    imap_host: Mapped[str] = mapped_column(String(253))
    imap_port: Mapped[int] = mapped_column(Integer)
    imap_encryption: Mapped[str] = mapped_column(String(12))
    auth_method: Mapped[str] = mapped_column(String(16), default="password")
    username: Mapped[str] = mapped_column(String(254))
    secret_ref: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    paused: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_modules: Mapped[list] = mapped_column(JSON, default=lambda: ["ruolo"])
    allowed_user_ids: Mapped[list] = mapped_column(JSON, default=list)
    default_modules: Mapped[list] = mapped_column(JSON, default=list)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    max_bytes: Mapped[int] = mapped_column(Integer, default=16 * 1024 * 1024)
    hourly_limit: Mapped[int] = mapped_column(Integer, default=30)
    health: Mapped[str] = mapped_column(String(40), default="untested")
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imap_uidvalidity: Mapped[str | None] = mapped_column(String(40))
    imap_last_uid: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CommunicationTemplate(Base):
    __tablename__ = "communication_templates"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_comm_template_version"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    channel: Mapped[str] = mapped_column(String(10))
    module: Mapped[str] = mapped_column(String(40))
    subject: Mapped[str] = mapped_column(String(250))
    body: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("application_users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationMessage(Base):
    __tablename__ = "communication_messages"
    __table_args__ = (
        UniqueConstraint("active_key", name="uq_comm_active_notice"),
        CheckConstraint("version > 0", name="ck_comm_message_version"),
        CheckConstraint("channel IN ('pec','email')", name="ck_comm_message_channel"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_module: Mapped[str] = mapped_column(String(40), default="ruolo")
    source_entity_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("ruolo_notice_documents.id"), index=True)
    notice_number: Mapped[str] = mapped_column(String(100), index=True)
    active_key: Mapped[str | None] = mapped_column(String(100))
    channel: Mapped[str] = mapped_column(String(10), index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("communication_accounts.id"), index=True)
    account_digest: Mapped[str] = mapped_column(String(64))
    sender: Mapped[str] = mapped_column(String(254))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(250))
    body: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(String(30), default="courtesy")
    template_id: Mapped[UUID | None] = mapped_column(ForeignKey("communication_templates.id"))
    source_digest: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[int] = mapped_column(ForeignKey("application_users.id"))
    technical_id: Mapped[str | None] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CommunicationAttachment(Base):
    __tablename__ = "communication_attachments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(ForeignKey("communication_messages.id"), index=True)
    filename: Mapped[str] = mapped_column(String(160))
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    primary_document: Mapped[bool] = mapped_column(Boolean, default=False)
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    pages: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationReview(Base):
    __tablename__ = "communication_reviews"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    attachment_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_attachments.id"), index=True
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"))
    message_version: Mapped[int] = mapped_column(Integer)
    rendered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationAuthorization(Base):
    __tablename__ = "communication_authorizations"
    __table_args__ = (UniqueConstraint("message_id", "version", name="uq_comm_authorization"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(ForeignKey("communication_messages.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    digest: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"))
    checklist: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationJob(Base):
    __tablename__ = "communication_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("communication_messages.id"), index=True
    )
    account_id: Mapped[UUID] = mapped_column(ForeignKey("communication_accounts.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    state: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[UUID | None] = mapped_column(Uuid)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    error_code: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationAttempt(Base):
    __tablename__ = "communication_attempts"
    __table_args__ = (UniqueConstraint("job_id", "number", name="uq_comm_attempt_number"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(ForeignKey("communication_messages.id"), index=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("communication_jobs.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    technical_id: Mapped[str] = mapped_column(String(200), unique=True)
    state: Mapped[str] = mapped_column(String(24))
    error_code: Mapped[str | None] = mapped_column(String(60))
    mime_sha256: Mapped[str] = mapped_column(String(64))
    mime_content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationEvent(Base):
    __tablename__ = "communication_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    kind: Mapped[str] = mapped_column(String(60))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id"))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationReceipt(Base):
    __tablename__ = "communication_receipts"
    __table_args__ = (UniqueConstraint("account_id", "sha256", name="uq_comm_receipt_hash"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("communication_messages.id"), index=True
    )
    account_id: Mapped[UUID] = mapped_column(ForeignKey("communication_accounts.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    provider_id: Mapped[str | None] = mapped_column(String(200))
    correlated_id: Mapped[str | None] = mapped_column(String(200), index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sha256: Mapped[str] = mapped_column(String(64))
    classification: Mapped[str] = mapped_column(String(30))
    original: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunicationControl(Base):
    __tablename__ = "communication_controls"
    __table_args__ = (CheckConstraint("id = 1", name="ck_comm_control_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    paused: Mapped[bool] = mapped_column(Boolean, default=True)
    worker_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
