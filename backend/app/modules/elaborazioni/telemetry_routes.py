from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.telemetry_schemas import (
    SisterPortalEventListResponse,
    SisterPortalHealthResponse,
)
from app.modules.elaborazioni.telemetry_service import get_portal_health, list_portal_events


router = APIRouter(prefix="/elaborazioni/portal-health", tags=["elaborazioni"])


@router.get("", response_model=SisterPortalHealthResponse)
def read_sister_portal_health(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    hours: Annotated[int, Query(ge=1, le=720)] = 24,
) -> SisterPortalHealthResponse:
    return get_portal_health(db, user_id=current_user.id, window_hours=hours)


@router.get("/events", response_model=SisterPortalEventListResponse)
def read_sister_portal_events(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    hours: Annotated[int, Query(ge=1, le=720)] = 24,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> SisterPortalEventListResponse:
    return list_portal_events(db, user_id=current_user.id, window_hours=hours, limit=limit)


__all__ = ["router"]
