from __future__ import annotations

import inspect
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AnprCheckLog(Base):
    __tablename__ = "anpr_check_log"
    __table_args__ = (
        Index("ix_anpr_check_log_subject_id_created_at_desc", "subject_id", desc("created_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ana_subjects.id"),
        nullable=False,
    )
    call_type: Mapped[str] = mapped_column(String(10), nullable=False)
    id_operazione_client: Mapped[str] = mapped_column(String(100), nullable=False)
    id_operazione_anpr: Mapped[str | None] = mapped_column(String(100), nullable=True)
    esito: Mapped[str] = mapped_column(String(30), nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_decesso_anpr: Mapped[date | None] = mapped_column(Date, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subject: Mapped["AnagraficaSubject"] = relationship("AnagraficaSubject", lazy="noload")


class AnprSyncConfig(Base):
    __tablename__ = "anpr_sync_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    max_calls_per_day: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    job_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    job_cron: Mapped[str] = mapped_column(String(50), default="0 8-17 * * *", nullable=False)
    lookback_years: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retry_not_found_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id"),
        nullable=True,
    )

    @classmethod
    async def get_or_create_default(cls, session: AsyncSession) -> "AnprSyncConfig":
        config = session.get(cls, 1)
        if inspect.isawaitable(config):
            config = await config
        if config is not None:
            return config

        config = cls(id=1)
        session.add(config)
        flushed = session.flush()
        if inspect.isawaitable(flushed):
            await flushed
        return config


class AnprJobRun(Base):
    __tablename__ = "anpr_job_runs"
    __table_args__ = (
        Index("ix_anpr_job_runs_run_date_started_at_desc", "run_date", desc("started_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ruolo_year: Mapped[int] = mapped_column(Integer, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(50), nullable=False, default="job")
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False)
    hard_daily_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    configured_daily_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_calls_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_calls_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subjects_selected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subjects_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deceased_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
