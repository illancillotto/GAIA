from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PermissionEntry(Base):
    __tablename__ = "permission_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    share_id: Mapped[int] = mapped_column(ForeignKey("shares.id"), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(120), nullable=False)
    permission_level: Mapped[str] = mapped_column(String(20), nullable=False)
    is_deny: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="nas", nullable=False)
    raw_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
