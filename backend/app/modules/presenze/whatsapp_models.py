from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

PRESENZE_WHATSAPP_KIND_PUNCH_REMINDER = "punch_reminder"


class PresenzeWhatsAppMessage(Base):
    __tablename__ = "presenze_whatsapp_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default=PRESENZE_WHATSAPP_KIND_PUNCH_REMINDER
    )
    collaborator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presenze_collaborators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    text_body: Mapped[str] = mapped_column(Text, nullable=False)
    days_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PresenzeWhatsAppNotifiedDay(Base):
    __tablename__ = "presenze_whatsapp_notified_days"
    __table_args__ = (
        UniqueConstraint(
            "kind", "collaborator_id", "work_date", name="uq_presenze_whatsapp_notified_day"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default=PRESENZE_WHATSAPP_KIND_PUNCH_REMINDER
    )
    collaborator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presenze_collaborators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    problem: Mapped[str] = mapped_column(String(32), nullable=False)
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presenze_whatsapp_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PresenzeWhatsAppOptOut(Base):
    __tablename__ = "presenze_whatsapp_opt_outs"

    application_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_users.id", ondelete="CASCADE"), primary_key=True
    )
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PresenzeWhatsAppPendingDay(Base):
    __tablename__ = "presenze_whatsapp_pending_days"

    collaborator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presenze_collaborators.id", ondelete="CASCADE"), primary_key=True
    )
    work_date: Mapped[date] = mapped_column(Date, primary_key=True)
    last_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("presenze_whatsapp_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PresenzeWhatsAppReceipt(Base):
    __tablename__ = "presenze_whatsapp_receipts"

    provider_message_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
