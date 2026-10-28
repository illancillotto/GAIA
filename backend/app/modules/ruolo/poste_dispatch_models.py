"""Posta Online outbox: GAIA prepares drafts, an operator presses INVIA on Poste.

Nothing here authorizes a shipment. GAIA never calls the Poste INVIA endpoint;
the archive reconciliation records what the operator actually sent.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PosteDispatchLot(Base):
    __tablename__ = "ruolo_poste_dispatch_lots"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    postal_options: Mapped[dict] = mapped_column(JSON)
    portal_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("application_users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PosteDispatchItem(Base):
    __tablename__ = "ruolo_poste_dispatch_items"
    __table_args__ = (
        UniqueConstraint("active_key", name="uq_poste_dispatch_item_active_key"),
        UniqueConstraint("active_source_key", name="uq_poste_dispatch_item_active_source"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    lot_id: Mapped[UUID] = mapped_column(
        ForeignKey("ruolo_poste_dispatch_lots.id", ondelete="RESTRICT"), index=True
    )
    batch_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("ruolo_tributi_reminder_batch_items.id", ondelete="RESTRICT"), index=True
    )
    notice_number: Mapped[str] = mapped_column(String(40))
    shipment_name: Mapped[str] = mapped_column(String(40), index=True)
    # Cleared on cancellation so the same notice can be prepared again later.
    active_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    active_source_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="address_pending", index=True)
    recipient: Mapped[dict] = mapped_column(JSON)
    poste_address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    address_review: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    artifact: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    artifact_size: Mapped[int] = mapped_column(Integer)
    poste_draft_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    poste_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    draft_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    registered_mail_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ruolo_tributi_registered_mails.id", ondelete="SET NULL"), nullable=True
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PosteDispatchEvent(Base):
    """Append-only trail of operator commands and portal observations."""

    __tablename__ = "ruolo_poste_dispatch_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    lot_id: Mapped[UUID] = mapped_column(
        ForeignKey("ruolo_poste_dispatch_lots.id", ondelete="RESTRICT"), index=True
    )
    item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ruolo_poste_dispatch_items.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Python clock: events written in one transaction keep their order.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
