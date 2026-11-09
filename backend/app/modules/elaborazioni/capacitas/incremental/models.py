"""Additive PostgreSQL journal and transactional outbox (no operational writes in shadow)."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IncrementalCycle(Base):
    __tablename__ = "incass_incremental_cycles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="partial")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expected: Mapped[list] = mapped_column(JSON, default=list)
    artifacts: Mapped[dict] = mapped_column(JSON, default=dict)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    rows: Mapped[dict] = mapped_column(JSON, default=dict)


class IncrementalHead(Base):
    __tablename__ = "incass_incremental_head"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[str | None] = mapped_column(ForeignKey(IncrementalCycle.id))
    full_audit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncrementalChange(Base):
    __tablename__ = "incass_incremental_changes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    cycle_id: Mapped[str] = mapped_column(ForeignKey(IncrementalCycle.id), index=True)
    notice_key: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    old: Mapped[dict | None] = mapped_column(JSON)
    new: Mapped[dict | None] = mapped_column(JSON)
    fields: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
