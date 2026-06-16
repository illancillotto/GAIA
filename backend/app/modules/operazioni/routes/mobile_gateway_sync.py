from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.services.gate_mobile_sync import get_gate_mobile_sync_status

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


@router.get("/status", response_model=GateMobileSyncStatusResponse)
def mobile_gateway_sync_status(
    _: Annotated[object, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> GateMobileSyncStatusResponse:
    payload = get_gate_mobile_sync_status(db)
    return GateMobileSyncStatusResponse.model_validate(payload)
