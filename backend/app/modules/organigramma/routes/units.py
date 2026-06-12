from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.organigramma.deps import (
    require_organigramma_manage_or_inaz,
    require_organigramma_read_or_inaz,
)
from app.modules.organigramma import repositories as repo
from app.modules.organigramma.schemas import (
    OrgUnitCreate,
    OrgUnitResponse,
    OrgUnitTreeNode,
    OrgUnitUpdate,
    StructureKindLiteral,
    UnitDetailResponse,
)
from app.modules.organigramma.services import organigramma_service as svc

READ = Depends(require_organigramma_read_or_inaz())

router = APIRouter(prefix="/units", tags=["organigramma/units"])


@router.get("/tree", response_model=list[OrgUnitTreeNode], dependencies=[READ])
def get_tree(
    db: Annotated[Session, Depends(get_db)],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> list[OrgUnitTreeNode]:
    return svc.build_tree(db, structure_kind=structure_kind)


@router.get("", response_model=list[OrgUnitResponse], dependencies=[READ])
def list_units(
    db: Annotated[Session, Depends(get_db)],
    parent_id: UUID | None = Query(None),
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> list[OrgUnitResponse]:
    units = repo.list_units(db, structure_kind=structure_kind)
    if parent_id is not None:
        units = [u for u in units if u.parent_id == parent_id]
    return [OrgUnitResponse.model_validate(u) for u in units]


@router.get("/{unit_id}", response_model=UnitDetailResponse, dependencies=[READ])
def get_unit_detail(
    unit_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> UnitDetailResponse:
    detail = svc.get_unit_detail(db, unit_id, structure_kind=structure_kind)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return detail


@router.post("", response_model=OrgUnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: OrgUnitCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> OrgUnitResponse:
    if payload.parent_id is not None and repo.get_unit(db, payload.parent_id, structure_kind=structure_kind) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent unit not found")
    unit = repo.create_unit(db, payload, user_id=current_user.id, structure_kind=structure_kind)
    return OrgUnitResponse.model_validate(unit)


@router.put("/{unit_id}", response_model=OrgUnitResponse)
def update_unit(
    unit_id: UUID,
    payload: OrgUnitUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> OrgUnitResponse:
    unit = repo.get_unit(db, unit_id, structure_kind=structure_kind)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    if payload.parent_id is not None:
        if payload.parent_id == unit_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit cannot be its own parent")
        if repo.get_unit(db, payload.parent_id, structure_kind=structure_kind) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent unit not found")
    unit = repo.update_unit(db, unit, payload, user_id=current_user.id)
    return OrgUnitResponse.model_validate(unit)


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> None:
    unit = repo.get_unit(db, unit_id, structure_kind=structure_kind)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    if repo.unit_has_children(db, unit_id, structure_kind=structure_kind):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit has sub-units")
    if repo.unit_has_assignments(db, unit_id, structure_kind=structure_kind):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit has assignments")
    repo.delete_unit(db, unit)
