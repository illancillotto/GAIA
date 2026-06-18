from app.models.catasto import (
    CatastoBatch as ElaborazioneBatch,
    CatastoBatchKind as ElaborazioneBatchKind,
    CatastoBatchStatus as ElaborazioneBatchStatus,
    CatastoConnectionTest as ElaborazioneConnectionTest,
    CatastoConnectionTestStatus as ElaborazioneConnectionTestStatus,
    CatastoCredential as ElaborazioneCredential,
    CatastoVisuraRequest as ElaborazioneRichiesta,
    CatastoVisuraRequestStatus as ElaborazioneRichiestaStatus,
)
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ElaborazioneAutoJobConfig(Base):
    __tablename__ = "elaborazione_auto_job_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

__all__ = [
    "ElaborazioneAutoJobConfig",
    "ElaborazioneBatch",
    "ElaborazioneBatchKind",
    "ElaborazioneBatchStatus",
    "ElaborazioneConnectionTest",
    "ElaborazioneConnectionTestStatus",
    "ElaborazioneCredential",
    "ElaborazioneRichiesta",
    "ElaborazioneRichiestaStatus",
]
