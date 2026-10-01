"""Serialize manual starts with the existing automatic INAZ scheduler lock."""

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.presenze.models import PresenzeSyncJob
from app.modules.presenze.services.sync_runtime import reconcile_stale_sync_jobs

# Same transaction lock already used by auto_sync._try_acquire_auto_sync_lock.
PRESENZE_SYNC_START_LOCK_KEY = 760031001


def ensure_sync_start_available(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        acquired = db.scalar(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": PRESENZE_SYNC_START_LOCK_KEY}
        )
        if not acquired:
            raise HTTPException(
                status_code=409, detail="Sincronizzazione INAZ in avvio; riprovare tra poco"
            )
    reconcile_stale_sync_jobs(db, commit=False)
    existing = db.scalar(
        select(PresenzeSyncJob.id)
        .where(PresenzeSyncJob.status.in_(("pending", "running")))
        .limit(1)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="Another Presenze sync job is already pending or running"
        )
