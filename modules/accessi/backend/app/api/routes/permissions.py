from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.schemas.permissions import (
    EffectivePermissionPreviewResponse,
    EffectivePermissionResponse,
    PermissionCalculationRequest,
)
from app.services.permissions import calculate_effective_permissions, get_effective_permissions

router = APIRouter(tags=["permissions"])


@router.post("/permissions/calculate-preview", response_model=list[EffectivePermissionPreviewResponse])
def calculate_preview(
    payload: PermissionCalculationRequest,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
) -> list[EffectivePermissionPreviewResponse]:
    return calculate_effective_permissions(payload)


@router.get("/effective-permissions", response_model=list[EffectivePermissionResponse])
def effective_permissions(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[EffectivePermissionResponse]:
    return [
        EffectivePermissionResponse.model_validate(item)
        for item in get_effective_permissions(db)
    ]
