"""Optional nightly STEP sync (disabled unless ``STEP_AUTOSYNC_ENABLED=true``).

Checked by the idle ``elaborazioni-worker-step`` loop, like the registry
auto import of the main worker: once per day, after the configured local
time, a ``sync`` job is queued unless another STEP job is active, a nightly
job was already queued today or no credential is enabled (a disabled account
never triggers login attempts).
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.step.credentials import has_available_credential
from app.modules.elaborazioni.step.jobs import active_job, create_job
from app.modules.elaborazioni.step.models import StepSyncJob
from app.modules.elaborazioni.step.schemas import StepSyncJobCreate

logger = logging.getLogger(__name__)


def autosync_enabled() -> bool:
    return os.getenv("STEP_AUTOSYNC_ENABLED", "false").strip().lower() == "true"


def _scheduled_start(now: datetime) -> datetime | None:
    zone = ZoneInfo(os.getenv("STEP_AUTOSYNC_TIMEZONE", "Europe/Rome"))
    local_now = now.astimezone(zone)
    at = time.fromisoformat(os.getenv("STEP_AUTOSYNC_TIME", "02:15"))
    start = datetime.combine(local_now.date(), at, tzinfo=zone)
    return start if local_now >= start else None


def queue_due_autosync(db: Session, *, now: datetime | None = None) -> int | None:
    if not autosync_enabled():
        return None
    start = _scheduled_start(now or datetime.now(UTC))
    if start is None or active_job(db) is not None:
        return None
    already_queued = db.scalar(
        select(StepSyncJob.id).where(
            StepSyncJob.mode == "sync",
            StepSyncJob.requested_by_user_id.is_(None),
            StepSyncJob.created_at >= start.astimezone(UTC),
        )
    )
    if already_queued is not None:
        return None
    if not has_available_credential(db):
        logger.warning("STEP autosync saltato: nessuna credenziale STEP attiva")
        return None
    job = create_job(db, StepSyncJobCreate(mode="sync"), requested_by_user_id=None)
    logger.info("STEP autosync: accodato job %s", job.id)
    return job.id
