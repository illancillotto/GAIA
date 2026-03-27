from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_section
from app.core.database import get_db
from app.jobs.sync import run_live_sync_job
from app.models.application_user import ApplicationUser
from app.schemas.sync import (
    SyncApplyResponse,
    SyncCapabilitiesResponse,
    SyncPreviewRequest,
    SyncPreviewResponse,
)
from app.services.nas_connector import NasConnectorError, get_sync_capabilities
from app.services.sync import apply_sync_payload, build_sync_preview
from app.services.sync_runs import create_sync_run

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/capabilities", response_model=SyncCapabilitiesResponse)
def sync_capabilities(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> SyncCapabilitiesResponse:
    return get_sync_capabilities()


@router.post("/preview", response_model=SyncPreviewResponse)
def sync_preview(
    payload: SyncPreviewRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> SyncPreviewResponse:
    return build_sync_preview(payload)


@router.post("/apply", response_model=SyncApplyResponse)
def sync_apply(
    payload: SyncPreviewRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SyncApplyResponse:
    started_at = datetime.now(timezone.utc)
    result = apply_sync_payload(db, payload)
    create_sync_run(
        db,
        mode="payload",
        trigger_type="api",
        status="succeeded",
        attempts_used=1,
        snapshot_id=result.snapshot_id,
        initiated_by=current_user.username,
        source_label="api:payload",
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )
    return result


@router.post("/live-apply", response_model=SyncApplyResponse)
def sync_live_apply(
    current_user: Annotated[ApplicationUser, Depends(require_section("accessi.sync"))],
    db: Annotated[Session, Depends(get_db)],
    profile: Literal["quick", "full"] = "quick",
) -> SyncApplyResponse:
    from app.api.routes import sync as sync_bridge

    try:
        return sync_bridge.run_live_sync_job(
            db,
            trigger_type="api",
            initiated_by=current_user.username,
            source_label=f"api:ssh:{profile}",
            profile=profile,
        ).sync_result
    except NasConnectorError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
