"""RiordinoNotification — notifiche in-app per scadenze e assegnazioni."""

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func


class RiordinoNotification(Base):
    __tablename__ = "riordino_notifications"
    __table_args__ = (
        Index("ix_riordino_notifications_user_read_created", "user_id", "is_read", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    practice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riordino_practices.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    practice: Mapped["RiordinoPractice | None"] = relationship("RiordinoPractice", back_populates="notifications")
