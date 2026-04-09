"""RiordinoPractice — pratica principale del riordino catastale."""

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from sqlalchemy import Index, func


class RiordinoPractice(Base):
    __tablename__ = "riordino_practices"
    __table_args__ = (
        Index("ix_riordino_practices_status", "status"),
        Index("ix_riordino_practices_municipality", "municipality"),
        Index("ix_riordino_practices_owner_user_id", "owner_user_id"),
        Index("ix_riordino_practices_current_phase", "current_phase"),
        Index("ix_riordino_practices_deleted_at", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    municipality: Mapped[str] = mapped_column(String(100), nullable=False)
    grid_code: Mapped[str] = mapped_column(String(50), nullable=False)
    lot_code: Mapped[str] = mapped_column(String(50), nullable=False)
    current_phase: Mapped[str] = mapped_column(String(20), default="phase_1", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    opened_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("application_users.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    phases: Mapped[list["RiordinoPhase"]] = relationship(
        "RiordinoPhase", back_populates="practice", lazy="selectin", order_by="RiordinoPhase.phase_code"
    )
    steps: Mapped[list["RiordinoStep"]] = relationship(
        "RiordinoStep", back_populates="practice", lazy="selectin", foreign_keys="RiordinoStep.practice_id"
    )
    appeals: Mapped[list["RiordinoAppeal"]] = relationship(
        "RiordinoAppeal", back_populates="practice", lazy="selectin"
    )
    issues: Mapped[list["RiordinoIssue"]] = relationship(
        "RiordinoIssue", back_populates="practice", lazy="selectin"
    )
    events: Mapped[list["RiordinoEvent"]] = relationship(
        "RiordinoEvent", back_populates="practice", lazy="selectin",
        order_by="RiordinoEvent.created_at.desc()"
    )
    documents: Mapped[list["RiordinoDocument"]] = relationship(
        "RiordinoDocument", back_populates="practice", lazy="selectin", foreign_keys="RiordinoDocument.practice_id"
    )
    parcel_links: Mapped[list["RiordinoParcelLink"]] = relationship(
        "RiordinoParcelLink", back_populates="practice", lazy="selectin"
    )
    party_links: Mapped[list["RiordinoPartyLink"]] = relationship(
        "RiordinoPartyLink", back_populates="practice", lazy="selectin"
    )
    gis_links: Mapped[list["RiordinoGisLink"]] = relationship(
        "RiordinoGisLink", back_populates="practice", lazy="selectin"
    )
    notifications: Mapped[list["RiordinoNotification"]] = relationship(
        "RiordinoNotification", back_populates="practice", lazy="selectin"
    )
