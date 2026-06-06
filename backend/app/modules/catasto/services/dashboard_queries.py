from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatImportBatch


def active_capacitas_batch_id(db: Session, anno: int | None) -> UUID | None:
    """Restituisce il batch Capacitas attivo per anno, se disponibile."""
    if anno is None:
        return None

    return db.scalars(
        select(CatImportBatch.id)
        .where(
            CatImportBatch.tipo == "capacitas_ruolo",
            CatImportBatch.status == "completed",
            CatImportBatch.anno_campagna == anno,
        )
        .order_by(desc(CatImportBatch.completed_at), desc(CatImportBatch.created_at))
        .limit(1)
    ).first()
