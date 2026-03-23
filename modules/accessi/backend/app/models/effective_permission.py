from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EffectivePermission(Base):
    __tablename__ = "effective_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    nas_user_id: Mapped[int] = mapped_column(ForeignKey("nas_users.id"), nullable=False)
    share_id: Mapped[int] = mapped_column(ForeignKey("shares.id"), nullable=False)
    can_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_write: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_denied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
