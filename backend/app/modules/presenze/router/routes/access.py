from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeSupervisorAssignment,
)
from app.modules.presenze.router.common import RequirePresenzeAdmin, RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_manage_supervisors
from app.modules.presenze.router.helpers.collaborators import _serialize_supervisor_assignment
from app.modules.presenze.router.helpers.daily_records import _get_collaborator_or_404
from app.modules.presenze.schemas import (
    PresenzeAccessContextResponse,
    PresenzeModuleStatusResponse,
    PresenzeSupervisorAssignmentResponse,
    PresenzeSupervisorAssignmentUpdate,
)
from app.modules.presenze.services.visibility_policy import (
    resolve_presenze_visibility,
)
from app.schemas.users import ApplicationUserResponse

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("", response_model=PresenzeModuleStatusResponse)
def get_module_status(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeModuleStatusResponse:
    return PresenzeModuleStatusResponse(
        module="presenze",
        enabled=True,
        username=current_user.username,
        message="GAIA Presenze collaboratori module is enabled for the current user.",
    )

@router.get("/access-context", response_model=PresenzeAccessContextResponse)
def get_presenze_access_context(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeAccessContextResponse:
    visibility = resolve_presenze_visibility(db, current_user)
    return PresenzeAccessContextResponse(
        can_view_all_data=visibility.full_access,
        can_view_all_credentials=current_user.is_super_admin,
        can_manage_supervisors=_can_manage_supervisors(current_user),
        is_supervisor=bool(visibility.approvable_user_ids or visibility.legacy_collaborator_ids),
        assigned_collaborators_count=visibility.subordinate_count,
    )

@router.get("/application-users", response_model=list[ApplicationUserResponse])
def list_inaz_application_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[ApplicationUserResponse]:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Presenze user management requires admin privileges")
    rows = db.execute(
        select(ApplicationUser)
        .where(ApplicationUser.is_active.is_(True), ApplicationUser.module_presenze.is_(True))
        .order_by(ApplicationUser.full_name.asc(), ApplicationUser.username.asc())
    ).scalars().all()
    return [ApplicationUserResponse.model_validate(row) for row in rows]

@router.get("/supervisor-assignments", response_model=list[PresenzeSupervisorAssignmentResponse])
def list_supervisor_assignments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    supervisor_user_id: int | None = Query(default=None),
) -> list[PresenzeSupervisorAssignmentResponse]:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Supervisor management requires admin privileges")
    stmt = select(PresenzeSupervisorAssignment)
    if supervisor_user_id is not None:
        stmt = stmt.where(PresenzeSupervisorAssignment.supervisor_user_id == supervisor_user_id)
    rows = db.execute(
        stmt.order_by(
            PresenzeSupervisorAssignment.supervisor_user_id.asc(),
            PresenzeSupervisorAssignment.collaborator_id.asc(),
        )
    ).scalars().all()
    return [_serialize_supervisor_assignment(db, row) for row in rows]

@router.put("/supervisor-assignments/{collaborator_id}", response_model=PresenzeSupervisorAssignmentResponse | None)
def update_supervisor_assignment(
    collaborator_id: uuid.UUID,
    payload: PresenzeSupervisorAssignmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSupervisorAssignmentResponse | None:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Supervisor management requires admin privileges")
    _get_collaborator_or_404(db, collaborator_id)
    assignment = db.execute(
        select(PresenzeSupervisorAssignment).where(PresenzeSupervisorAssignment.collaborator_id == collaborator_id)
    ).scalar_one_or_none()

    if payload.supervisor_user_id is None:
        if assignment is not None:
            db.delete(assignment)
            db.commit()
        return None

    supervisor = db.get(ApplicationUser, payload.supervisor_user_id)
    if supervisor is None or not supervisor.is_active:
        raise HTTPException(status_code=404, detail="Supervisor user not found")
    if not supervisor.module_presenze and not supervisor.is_super_admin:
        raise HTTPException(status_code=409, detail="The selected user is not enabled for the Presenze module")
    if supervisor.role == "operator":
        raise HTTPException(status_code=409, detail="Operators cannot be assigned as Presenze supervisors")

    if assignment is None:
        assignment = PresenzeSupervisorAssignment(
            supervisor_user_id=payload.supervisor_user_id,
            collaborator_id=collaborator_id,
            assigned_by_user_id=current_user.id,
        )
    else:
        assignment.supervisor_user_id = payload.supervisor_user_id
        assignment.assigned_by_user_id = current_user.id
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _serialize_supervisor_assignment(db, assignment)

# fmt: on
