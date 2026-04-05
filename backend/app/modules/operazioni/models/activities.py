"""Activity domain models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
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


class ActivityCatalog(Base):
    __tablename__ = "activity_catalog"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    requires_vehicle: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    requires_note: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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


class OperatorActivity(Base):
    __tablename__ = "operator_activity"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    activity_catalog_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("activity_catalog.id"), nullable=False, index=True
    )
    operator_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("team.id"), nullable=True, index=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vehicle.id"), nullable=True, index=True
    )
    vehicle_usage_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vehicle_usage_session.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_minutes_declared: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    duration_minutes_calculated: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    start_latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    start_longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    end_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    end_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    gps_track_summary_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("gps_track_summary.id"), nullable=True
    )
    text_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_note_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("attachment.id"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rectified_from_activity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("operator_activity.id"), nullable=True
    )
    offline_client_uuid: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True, index=True
    )
    client_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    server_received_at: Mapped[datetime | None] = mapped_column(
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
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )


class OperatorActivityEvent(Base):
    __tablename__ = "operator_activity_event"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    operator_activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("operator_activity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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


class OperatorActivityAttachment(Base):
    __tablename__ = "operator_activity_attachment"
    __table_args__ = (
        # Unique constraint via composite index
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    operator_activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("operator_activity.id", ondelete="CASCADE"), nullable=False
    )
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("attachment.id", ondelete="CASCADE"), nullable=False
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


class ActivityApproval(Base):
    __tablename__ = "activity_approval"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    operator_activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("operator_activity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    decision_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
