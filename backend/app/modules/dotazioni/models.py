from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DotazioneAsset(Base):
    __tablename__ = "dotazioni_assets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'maintenance', 'lost', 'damaged', 'retired')",
            name="ck_dotazioni_assets_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    asset_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    serial_number: Mapped[str | None] = mapped_column(String(200), index=True)
    imei: Mapped[str | None] = mapped_column(String(32))
    phone_number: Mapped[str | None] = mapped_column(String(64))
    mac_address: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available", index=True)
    assigned_org_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("org_unit.id", ondelete="RESTRICT"), index=True
    )
    network_device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("network_devices.id", ondelete="RESTRICT"), unique=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vehicle.id", ondelete="RESTRICT"), unique=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"))
    updated_by_user_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"))


class DotazioneCustody(Base):
    __tablename__ = "dotazioni_custodies"
    __table_args__ = (
        Index(
            "uq_dotazioni_open_custody",
            "asset_id",
            unique=True,
            postgresql_where=text("returned_at IS NULL"),
            sqlite_where=text("returned_at IS NULL"),
        ),
        CheckConstraint(
            "returned_at IS NULL OR returned_at >= taken_at", name="ck_dotazioni_custody_time"
        ),
        CheckConstraint(
            "(returned_at IS NULL AND returned_by_user_id IS NULL) OR "
            "(returned_at IS NOT NULL AND returned_by_user_id IS NOT NULL)",
            name="ck_dotazioni_custody_return_actor",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("dotazioni_assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    holder_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    handover_from_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id"))
    recorded_by_user_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"))
    returned_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("application_users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    return_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DotazioneEvent(Base):
    __tablename__ = "dotazioni_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("dotazioni_assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
