from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.organigramma.deps import require_organigramma_manage_or_inaz
from app.modules.organigramma import repositories as repo
from app.modules.organigramma.schemas import (
    OrgVisibilityOverrideCreate,
    OrgVisibilityOverrideResponse,
    OrgVisibilityOverrideUpdate,
    StructureKindLiteral,
)
from app.modules.organigramma.services import organigramma_service as svc

# Le eccezioni di visibilità sono area sensibile: gestione riservata a gestione organigramma/presenze.
MANAGE = Depends(require_organigramma_manage_or_inaz())

router = APIRouter(prefix="/overrides", tags=["organigramma/overrides"])


@router.get("", response_model=list[OrgVisibilityOverrideResponse], dependencies=[MANAGE])
def list_overrides(
    db: Annotated[Session, Depends(get_db)],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> list[OrgVisibilityOverrideResponse]:
    return svc.list_override_responses(db, structure_kind=structure_kind)


@router.post("", response_model=OrgVisibilityOverrideResponse, status_code=status.HTTP_201_CREATED)
def create_override(
    payload: OrgVisibilityOverrideCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> OrgVisibilityOverrideResponse:
    if payload.target_type == "org_unit" and repo.get_unit(db, payload.target_org_unit_id, structure_kind=structure_kind) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target org unit not found")
    override = repo.create_override(db, payload, user_id=current_user.id, structure_kind=structure_kind)
    return svc.override_response(db, override, structure_kind=structure_kind)


@router.put("/{override_id}", response_model=OrgVisibilityOverrideResponse)
def update_override(
    override_id: UUID,
    payload: OrgVisibilityOverrideUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> OrgVisibilityOverrideResponse:
    override = repo.get_override(db, override_id, structure_kind=structure_kind)
    if override is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    override = repo.update_override(db, override, payload, user_id=current_user.id)
    return svc.override_response(db, override, structure_kind=structure_kind)


@router.delete("/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_override(
    override_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> None:
    override = repo.get_override(db, override_id, structure_kind=structure_kind)
    if override is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    repo.delete_override(db, override)
