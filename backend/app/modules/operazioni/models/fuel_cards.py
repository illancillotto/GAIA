"""Fuel card registry and assignment history."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FuelCard(Base):
    __tablename__ = "fuel_card"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    codice: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    sigla: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    cod: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    pan: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    card_number_emissione: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    prodotti: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    current_wc_operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("wc_operator.id"), nullable=True, index=True
    )
    current_driver_raw: Mapped[str | None] = mapped_column(String(220), nullable=True)
    ignore_driver_match: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    ignored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ignored_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True, index=True
    )
    ignored_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class FuelCardAssignmentHistory(Base):
    __tablename__ = "fuel_card_assignment_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    fuel_card_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fuel_card.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wc_operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("wc_operator.id"), nullable=True, index=True
    )
    driver_raw: Mapped[str | None] = mapped_column(String(220), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    changed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_users.id"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="excel_import")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

