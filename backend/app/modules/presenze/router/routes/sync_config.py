from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.router.common import RequirePresenzeModule
from app.modules.presenze.schemas import (
    PresenzeAutoSyncConfigResponse,
    PresenzeAutoSyncConfigUpdate,
)
from app.modules.presenze.services.auto_sync import (
    get_auto_sync_config,
    serialize_auto_sync_config,
    update_auto_sync_config,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/sync/config", response_model=PresenzeAutoSyncConfigResponse)
def get_sync_config(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeAutoSyncConfigResponse:
    _ = current_user
    return serialize_auto_sync_config(get_auto_sync_config(db))

@router.put("/sync/config", response_model=PresenzeAutoSyncConfigResponse)
def put_sync_config(
    payload: PresenzeAutoSyncConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeAutoSyncConfigResponse:
    config = update_auto_sync_config(db, payload, user_id=current_user.id)
    return serialize_auto_sync_config(config)

# fmt: on
