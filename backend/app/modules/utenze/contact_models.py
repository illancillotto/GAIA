"""Typed electronic contacts shared by all GAIA domains, owned by Utenze."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnagraficaElectronicContact(Base):
    __tablename__ = "ana_electronic_contacts"
    __table_args__ = (
        UniqueConstraint("subject_id", "address", name="uq_ana_econtact_address"),
        CheckConstraint(
            "channel IN ('pec','email','unclassified')", name="ck_ana_econtact_channel"
        ),
        CheckConstraint("state IN ('active','review','revoked')", name="ck_ana_econtact_state"),
        CheckConstraint(
            "channel <> 'unclassified' OR state <> 'active'", name="ck_ana_econtact_classified"
        ),
        CheckConstraint("version > 0", name="ck_ana_econtact_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("ana_subjects.id", ondelete="CASCADE"), index=True
    )
    address: Mapped[str] = mapped_column(String(254))
    channel: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(12))
    source: Mapped[str] = mapped_column(String(80))
    evidence_reference: Mapped[str] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, default=1)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("application_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
