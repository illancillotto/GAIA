from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, Time, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InazCredential(Base):
    __tablename__ = "inaz_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_authenticated_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InazHoliday(Base):
    __tablename__ = "inaz_holidays"
    __table_args__ = (
        UniqueConstraint("holiday_date", "company_code", "label", name="uq_inaz_holidays_date_company_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    company_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    is_workday_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InazScheduleTemplate(Base):
    __tablename__ = "inaz_schedule_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    company_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InazScheduleRule(Base):
    __tablename__ = "inaz_schedule_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("inaz_schedule_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recurrence_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="weekly")
    week_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anchor_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    season_start_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_start_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_end_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_end_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applies_on_holiday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ordinary_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InazCollaborator(Base):
    __tablename__ = "inaz_collaborators"
    __table_args__ = (
        UniqueConstraint("employee_code", "company_code", name="uq_inaz_collaborators_employee_company"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    application_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    kkint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    company_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    company_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InazCollaboratorScheduleAssignment(Base):
    __tablename__ = "inaz_collaborator_schedule_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collaborator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inaz_collaborators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("inaz_schedule_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InazImportJob(Base):
    __tablename__ = "inaz_import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    requested_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InazSyncJob(Base):
    __tablename__ = "inaz_sync_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    requested_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credential_id: Mapped[int | None] = mapped_column(
        ForeignKey("inaz_credentials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inaz_import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    collaborator_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    json_artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    worker_log_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    worker_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InazDailyRecord(Base):
    __tablename__ = "inaz_daily_records"
    __table_args__ = (
        UniqueConstraint("collaborator_id", "work_date", name="uq_inaz_daily_records_collaborator_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    collaborator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inaz_collaborators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    application_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    schedule_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    teo_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ordinary_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    absence_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    justified_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maggiorazione_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mpe_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    straordinario_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    km_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_straordinario_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_mpe_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manual_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    request_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_authorized_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_absence_cause: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    stato: Mapped[str | None] = mapped_column(String(120), nullable=True)
    evidenze: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_weekday: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inaz_import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InazDailyPunch(Base):
    __tablename__ = "inaz_daily_punches"
    __table_args__ = (
        UniqueConstraint("daily_record_id", "sequence", name="uq_inaz_daily_punches_record_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    daily_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inaz_daily_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    exit_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    terminal_label: Mapped[str | None] = mapped_column(String(255), nullable=True)


class InazEventSummary(Base):
    __tablename__ = "inaz_event_summaries"
    __table_args__ = (
        UniqueConstraint(
            "collaborator_id",
            "period_start",
            "period_end",
            "event_code",
            "description",
            name="uq_inaz_event_summaries_period_event",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    collaborator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inaz_collaborators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    application_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    spettante_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fruito_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residuo_prec_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saldo_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    autorizzato_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pianificato_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    richiesto_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saldo_totale_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unitamisura: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inaz_import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
