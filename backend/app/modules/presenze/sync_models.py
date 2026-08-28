from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import ClassVar

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PresenzeSyncJob(Base):
    __tablename__ = "presenze_sync_jobs"
    __table_args__ = (
        Index(
            "ix_presenze_sync_jobs_claim",
            "status",
            "priority",
            "retry_not_before",
            "created_at",
        ),
        Index("ix_presenze_sync_jobs_lease_expiry", "status", "lease_expires_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    requested_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credential_id: Mapped[int | None] = mapped_column(
        ForeignKey("presenze_credentials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("presenze_import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
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
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    lease_token: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    lease_generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __mapper_args__: ClassVar[dict[str, object]] = {
        "version_id_col": lease_generation,
        "version_id_generator": False,
    }
