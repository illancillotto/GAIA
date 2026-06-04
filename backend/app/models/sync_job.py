from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requested_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("application_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile: Mapped[str] = mapped_column(String(20), nullable=False, default="quick", index=True)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default="api")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    persisted_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    persisted_groups: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    persisted_shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    persisted_permission_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    persisted_effective_permissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    share_acl_pairs_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_log_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    worker_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    source_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
