"""RiordinoGisLink — link manuale a oggetti GIS."""

import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func


class RiordinoGisLink(Base):
    __tablename__ = "riordino_gis_links"
    __table_args__ = (
        Index("ix_riordino_gis_links_practice_id", "practice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("riordino_practices.id"), nullable=False)
    layer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geometry_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    last_synced_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    practice: Mapped["RiordinoPractice"] = relationship("RiordinoPractice", back_populates="gis_links")
