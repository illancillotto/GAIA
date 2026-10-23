import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RuoloTributiCalculationPolicy(Base):
    __tablename__ = "ruolo_tributi_calculation_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    only_unnotified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    year_from: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    year_to: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    bonario_due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    surcharge_rate_percent: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False, default=0)
    surcharge_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    euribor_6m_rate_percent: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False, default=0)
    euribor_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    euribor_reference_period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    euribor_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    interest_rate_percent: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False, default=0)
    interest_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    interest_start_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="fixed_date", index=True
    )
    bollettino_causale: Mapped[str | None] = mapped_column(String(3), nullable=True)
    bollettino_esercizio: Mapped[str | None] = mapped_column(String(4), nullable=True)
    print_bollettino: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    payment_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def effective_interest_rate_percent(self):
        return (self.euribor_6m_rate_percent or 0) + (self.interest_rate_percent or 0)
