from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    nas_user_id: Mapped[int] = mapped_column(ForeignKey("nas_users.id"), nullable=False)
    share_id: Mapped[int] = mapped_column(ForeignKey("shares.id"), nullable=False)
    reviewer_user_id: Mapped[int] = mapped_column(ForeignKey("application_users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
