"""RiordinoPartyLink — relazione pratica ↔ soggetto (modulo utenze)."""

import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func
from app.modules.riordino.models.types import RIORDINO_UUID


class RiordinoPartyLink(Base):
    __tablename__ = "riordino_party_links"
    __table_args__ = (
        Index("ix_riordino_party_links_practice_id", "practice_id"),
        UniqueConstraint("practice_id", "subject_id", name="uq_riordino_party_links_practice_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(RIORDINO_UUID, ForeignKey("ana_subjects.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="party_links")
