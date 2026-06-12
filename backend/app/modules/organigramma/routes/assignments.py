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
    OrgAssignmentCreate,
    OrgAssignmentResponse,
    OrgAssignmentUpdate,
    StructureKindLiteral,
)
from app.modules.organigramma.services import organigramma_service as svc

router = APIRouter(prefix="/assignments", tags=["organigramma/assignments"])


@router.get("", response_model=list[OrgAssignmentResponse], dependencies=[Depends(require_organigramma_read_or_inaz())])
def list_assignments(
    db: Annotated[Session, Depends(get_db)],
    unit_id: UUID | None = Query(None),
    user_id: int | None = Query(None),
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> list[OrgAssignmentResponse]:
    return svc.list_assignment_responses(
        db,
        unit_id=unit_id,
        user_id=user_id,
        structure_kind=structure_kind,
    )


@router.post("", response_model=OrgAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: OrgAssignmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> OrgAssignmentResponse:
    if repo.get_unit(db, payload.org_unit_id, structure_kind=structure_kind) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Org unit not found")
    assignment = repo.create_assignment(
        db,
        payload,
        user_id=current_user.id,
        structure_kind=structure_kind,
    )
    for resp in svc.list_assignment_responses(
        db,
        user_id=assignment.user_id,
        unit_id=assignment.org_unit_id,
        structure_kind=structure_kind,
    ):
        if resp.id == assignment.id:
            return resp
    return OrgAssignmentResponse.model_validate(assignment)


@router.put("/{assignment_id}", response_model=OrgAssignmentResponse)
def update_assignment(
    assignment_id: UUID,
    payload: OrgAssignmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> OrgAssignmentResponse:
    assignment = repo.get_assignment(db, assignment_id, structure_kind=structure_kind)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if payload.org_unit_id is not None and repo.get_unit(db, payload.org_unit_id, structure_kind=structure_kind) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Org unit not found")
    repo.update_assignment(db, assignment, payload, user_id=current_user.id)
    matches = svc.list_assignment_responses(
        db,
        user_id=assignment.user_id,
        unit_id=assignment.org_unit_id,
        structure_kind=structure_kind,
    )
    for resp in matches:
        if resp.id == assignment_id:
            return resp
    return OrgAssignmentResponse.model_validate(assignment)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
    structure_kind: StructureKindLiteral = Query(default="organigramma"),
) -> None:
    assignment = repo.get_assignment(db, assignment_id, structure_kind=structure_kind)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    repo.delete_assignment(db, assignment)
