from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.services.gate_mobile_sync import execute_gate_mobile_sync, get_gate_mobile_sync_status, get_running_gate_mobile_sync_run

router = APIRouter(prefix="/mobile-gateway-sync", tags=["operazioni/mobile-gateway-sync"])


class GateMobileSyncRunResponse(BaseModel):
    id: str
    trigger_source: str
    status: str
    requested_tasks_count: int
    operators_pushed: int
    duration_ms: int | None
    requested_tasks: list[dict[str, Any]]
    error_kind: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class GateMobileSyncStatusResponse(BaseModel):
    sync_enabled: bool
    gateway_base_url: str | None
    gateway_configured: bool
    token_configured: bool
    timeout_seconds: float
    outbound_scope: list[str]
    internal_connector_api: dict[str, str]
    last_run: GateMobileSyncRunResponse | None
    recent_runs: list[GateMobileSyncRunResponse]


class GateMobileSyncRunTriggerResponse(BaseModel):
    job: GateMobileSyncRunResponse


@router.get("/status", response_model=GateMobileSyncStatusResponse)
def mobile_gateway_sync_status(
    _: Annotated[object, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> GateMobileSyncStatusResponse:
    payload = get_gate_mobile_sync_status(db)
    return GateMobileSyncStatusResponse.model_validate(payload)


@router.post("/run", response_model=GateMobileSyncRunTriggerResponse)
async def mobile_gateway_sync_run(
    _: Annotated[object, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> GateMobileSyncRunTriggerResponse:
    running_run = get_running_gate_mobile_sync_run(db)
    if running_run is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Gate mobile sync già in esecuzione: run_id={running_run.id}",
        )

    result = await execute_gate_mobile_sync(
        db,
        trigger_source="manual_api",
        raise_on_error=False,
    )
    payload = get_gate_mobile_sync_status(db, recent_limit=1)
    job = payload["last_run"]
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Run gate mobile sync non trovato dopo l'esecuzione",
        )
    return GateMobileSyncRunTriggerResponse(job=GateMobileSyncRunResponse.model_validate(job))
