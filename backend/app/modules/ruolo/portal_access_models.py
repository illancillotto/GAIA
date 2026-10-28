"""inCatasto access supplied by the Consorzio, keyed by the source account code."""

from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RuoloTaxpayerPortalAccess(Base):
    __tablename__ = "ruolo_taxpayer_portal_access"

    account_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    tax_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    pin_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
