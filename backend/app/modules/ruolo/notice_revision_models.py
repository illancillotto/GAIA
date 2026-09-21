"""Database commit revision, not a confirmation or permission to dispatch."""

from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Integer, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NoticeGenerationRevision(Base):
    __tablename__ = "ruolo_notice_generation_revision"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_notice_generation_revision_singleton"),
        CheckConstraint("revision >= 0", name="ck_notice_generation_revision_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    epoch: Mapped[UUID] = mapped_column(Uuid)
    revision: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    last_transaction_id: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
