"""Vehicle domain models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicle"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    plate_number: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True
    )
    asset_tag: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_of_manufacture: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="available", index=True
    )
    ownership_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    gps_provider_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    has_gps_device: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )


class VehicleAssignment(Base):
    __tablename__ = "vehicle_assignment"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    operator_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("team.id"), nullable=True, index=True
    )
    assigned_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VehicleOdometerReading(Base):
    __tablename__ = "vehicle_odometer_reading"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reading_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    odometer_km: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    usage_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vehicle_usage_session.id"), nullable=True
    )
    recorded_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VehicleUsageSession(Base):
    __tablename__ = "vehicle_usage_session"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=False, index=True
    )
    actual_driver_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("team.id"), nullable=True, index=True
    )
    related_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vehicle_assignment.id"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    start_odometer_km: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    end_odometer_km: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True
    )
    start_latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    start_longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    end_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    end_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    gps_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    route_distance_km: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True
    )
    engine_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="open", index=True
    )
    validated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VehicleFuelLog(Base):
    __tablename__ = "vehicle_fuel_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usage_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vehicle_usage_session.id"), nullable=True
    )
    recorded_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=False
    )
    fueled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    liters: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    station_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    receipt_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("attachment.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VehicleMaintenanceType(Base):
    __tablename__ = "vehicle_maintenance_type"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VehicleMaintenance(Base):
    __tablename__ = "vehicle_maintenance"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maintenance_type_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vehicle_maintenance_type.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="planned", index=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )


class VehicleDocument(Base):
    __tablename__ = "vehicle_document"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("attachment.id"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
