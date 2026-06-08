from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.organigramma import repositories as repo
from app.modules.organigramma.schemas import (
    OrgVisibilityOverrideCreate,
    OrgVisibilityOverrideResponse,
    OrgVisibilityOverrideUpdate,
)
from app.modules.organigramma.services import organigramma_service as svc

# Le eccezioni di visibilità sono area sensibile: gestione riservata a organigramma.manage.
MANAGE = Depends(require_section("organigramma.manage"))

router = APIRouter(prefix="/overrides", tags=["organigramma/overrides"])


@router.get("", response_model=list[OrgVisibilityOverrideResponse], dependencies=[MANAGE])
def list_overrides(db: Annotated[Session, Depends(get_db)]) -> list[OrgVisibilityOverrideResponse]:
    return svc.list_override_responses(db)


@router.post("", response_model=OrgVisibilityOverrideResponse, status_code=status.HTTP_201_CREATED)
def create_override(
    payload: OrgVisibilityOverrideCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_section("organigramma.manage"))],
) -> OrgVisibilityOverrideResponse:
    if payload.target_type == "org_unit" and repo.get_unit(db, payload.target_org_unit_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target org unit not found")
    override = repo.create_override(db, payload, user_id=current_user.id)
    return svc.override_response(db, override)


@router.put("/{override_id}", response_model=OrgVisibilityOverrideResponse)
def update_override(
    override_id: UUID,
    payload: OrgVisibilityOverrideUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_section("organigramma.manage"))],
) -> OrgVisibilityOverrideResponse:
    override = repo.get_override(db, override_id)
    if override is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    override = repo.update_override(db, override, payload, user_id=current_user.id)
    return svc.override_response(db, override)


@router.delete("/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_override(
    override_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_section("organigramma.manage"))],
) -> None:
    override = repo.get_override(db, override_id)
    if override is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    repo.delete_override(db, override)
