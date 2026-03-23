from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.sync_run import SyncRun


def create_sync_run(
    db: Session,
    *,
    mode: str,
    trigger_type: str,
    status: str,
    attempts_used: int,
    snapshot_id: int | None = None,
    duration_ms: int | None = None,
    initiated_by: str | None = None,
    source_label: str | None = None,
    error_detail: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> SyncRun:
    resolved_started_at = started_at or datetime.now(timezone.utc)
    resolved_completed_at = completed_at or datetime.now(timezone.utc)
    sync_run = SyncRun(
        snapshot_id=snapshot_id,
        mode=mode,
        trigger_type=trigger_type,
        status=status,
        attempts_used=attempts_used,
        duration_ms=duration_ms,
        initiated_by=initiated_by,
        source_label=source_label,
        error_detail=error_detail,
        started_at=resolved_started_at,
        completed_at=resolved_completed_at,
    )
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)
    return sync_run
