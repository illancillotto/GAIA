from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ParcelControlIndex(Base):
    __tablename__ = "ruolo_parcel_control_index"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    identity_key: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(400), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    cf_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    current_present: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    original: Mapped[dict] = mapped_column(JSON)


class ParcelControlState(Base):
    __tablename__ = "ruolo_parcel_control_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    current_year: Mapped[int] = mapped_column(Integer, default=2025)
    signatures: Mapped[dict] = mapped_column(JSON, default=dict)
    coverage: Mapped[dict] = mapped_column(JSON, default=dict)
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"))


class ParcelControlCase(Base):
    __tablename__ = "ruolo_parcel_control_cases"
    __table_args__ = (
        CheckConstraint(
            "(parcel_id IS NOT NULL AND notice_id IS NULL) OR (parcel_id IS NULL AND notice_id IS NOT NULL)",
            name="ck_parcel_control_case_origin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_parcel_control_index.id", ondelete="RESTRICT"), unique=True
    )
    notice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_avvisi.id", ondelete="RESTRICT"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    responsible_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"))
    original: Mapped[dict] = mapped_column(JSON)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    matches: Mapped[list] = mapped_column(JSON, default=list)
    parcels: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __mapper_args__ = {"version_id_col": version}


class ParcelControlProposal(Base):
    __tablename__ = "ruolo_parcel_control_proposals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    identity_key: Mapped[str] = mapped_column(String(64), unique=True)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ruolo_parcel_control_cases.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ParcelControlAudit(Base):
    __tablename__ = "ruolo_parcel_control_audit"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ruolo_parcel_control_cases.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"))
    action: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
