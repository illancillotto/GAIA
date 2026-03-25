from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        pass

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CatastoBatchStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CatastoVisuraRequestStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_CAPTCHA = "awaiting_captcha"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CatastoConnectionTestStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CatastoCredential(Base):
    __tablename__ = "catasto_credentials"
    __table_args__ = (UniqueConstraint("user_id", name="uq_catasto_credentials_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sister_username: Mapped[str] = mapped_column(String(128), nullable=False)
    sister_password_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    convenzione: Mapped[str | None] = mapped_column(Text, nullable=True)
    codice_richiesta: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ufficio_provinciale: Mapped[str] = mapped_column(
        String(255),
        default="ORISTANO Territorio",
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CatastoConnectionTest(Base):
    __tablename__ = "catasto_connection_tests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catasto_credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    sister_username: Mapped[str] = mapped_column(String(128), nullable=False)
    sister_password_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ufficio_provinciale: Mapped[str] = mapped_column(
        String(255),
        default="ORISTANO Territorio",
        nullable=False,
    )
    persist_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=CatastoConnectionTestStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reachable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    authenticated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CatastoBatch(Base):
    __tablename__ = "catasto_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=CatastoBatchStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_operation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CatastoDocument(Base):
    __tablename__ = "catasto_documents"
    __table_args__ = (UniqueConstraint("request_id", name="uq_catasto_documents_request_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    comune: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    foglio: Mapped[str] = mapped_column(String(64), nullable=False)
    particella: Mapped[str] = mapped_column(String(64), nullable=False)
    subalterno: Mapped[str | None] = mapped_column(String(64), nullable=True)
    catasto: Mapped[str] = mapped_column(String(64), nullable=False)
    tipo_visura: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CatastoVisuraRequest(Base):
    __tablename__ = "catasto_visure_requests"
    __table_args__ = (UniqueConstraint("batch_id", "row_index", name="uq_catasto_visure_requests_batch_row"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catasto_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    comune: Mapped[str] = mapped_column(String(255), nullable=False)
    comune_codice: Mapped[str | None] = mapped_column(String(255), nullable=True)
    catasto: Mapped[str] = mapped_column(String(64), nullable=False)
    sezione: Mapped[str | None] = mapped_column(String(64), nullable=True)
    foglio: Mapped[str] = mapped_column(String(64), nullable=False)
    particella: Mapped[str] = mapped_column(String(64), nullable=False)
    subalterno: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tipo_visura: Mapped[str] = mapped_column(String(64), nullable=False, default="Sintetica")
    status: Mapped[str] = mapped_column(
        String(32),
        default=CatastoVisuraRequestStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    current_operation: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    captcha_image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    captcha_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captcha_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captcha_manual_solution: Mapped[str | None] = mapped_column(String(64), nullable=True)
    captcha_skip_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catasto_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CatastoCaptchaLog(Base):
    __tablename__ = "catasto_captcha_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catasto_visure_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    ocr_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manual_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CatastoComune(Base):
    __tablename__ = "catasto_comuni"
    __table_args__ = (UniqueConstraint("nome", "ufficio", name="uq_catasto_comuni_nome_ufficio"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    codice_sister: Mapped[str] = mapped_column(String(255), nullable=False)
    ufficio: Mapped[str] = mapped_column(String(255), default="ORISTANO Territorio", nullable=False)
