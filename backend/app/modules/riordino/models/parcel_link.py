"""RiordinoParcelLink — particella catastale nel lotto."""

import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func
from app.modules.riordino.models.types import RIORDINO_UUID


class RiordinoParcelLink(Base):
    __tablename__ = "riordino_parcel_links"
    __table_args__ = (
        Index("ix_riordino_parcel_links_practice_id", "practice_id"),
        Index("ix_riordino_parcel_links_practice_foglio_particella", "practice_id", "foglio", "particella"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    foglio: Mapped[str] = mapped_column(String(20), nullable=False)
    particella: Mapped[str] = mapped_column(String(20), nullable=False)
    subalterno: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title_holder_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title_holder_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        RIORDINO_UUID, ForeignKey("ana_subjects.id"), nullable=True
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="parcel_links")
