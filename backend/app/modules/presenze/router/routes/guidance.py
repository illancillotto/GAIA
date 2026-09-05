from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.router.common import RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_view_all_inaz_data
from app.modules.presenze.schemas import (
    PresenzeBankHoursGuidanceConfigResponse,
    PresenzeBankHoursGuidanceConfigRevisionResponse,
    PresenzeBankHoursGuidanceConfigUpdate,
)
from app.modules.presenze.services.bank_hours_guidance_config import (
    get_bank_hours_guidance_config,
    list_bank_hours_guidance_config_revisions,
    serialize_bank_hours_guidance_config_with_user,
    serialize_bank_hours_guidance_revision,
    update_bank_hours_guidance_config,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/bank-hours/guidance-config", response_model=PresenzeBankHoursGuidanceConfigResponse)
def get_bank_hours_guidance_policy(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursGuidanceConfigResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours guidance config requires HR or admin privileges")
    return serialize_bank_hours_guidance_config_with_user(db, get_bank_hours_guidance_config(db))

@router.put("/bank-hours/guidance-config", response_model=PresenzeBankHoursGuidanceConfigResponse)
def put_bank_hours_guidance_policy(
    payload: PresenzeBankHoursGuidanceConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursGuidanceConfigResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours guidance config requires HR or admin privileges")
    config = update_bank_hours_guidance_config(db, payload, user_id=current_user.id)
    return serialize_bank_hours_guidance_config_with_user(db, config)

@router.get("/bank-hours/guidance-config/history", response_model=list[PresenzeBankHoursGuidanceConfigRevisionResponse])
def get_bank_hours_guidance_policy_history(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeBankHoursGuidanceConfigRevisionResponse]:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours guidance config requires HR or admin privileges")
    return [serialize_bank_hours_guidance_revision(db, revision) for revision in list_bank_hours_guidance_config_revisions(db)]

# fmt: on
