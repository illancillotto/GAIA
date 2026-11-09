"""Explicit association editor; no matching by names or team membership."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_role
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import OrganizationTeam
from app.modules.presenze.services.team_organization import (
    build_team_organization_directory,
    require_team_org_unit,
)
from app.modules.presenze.team_organization_models import PresenzeTeamOrganization

router = APIRouter(prefix="/gate/presenze", tags=["gate-presenze"])
Access = Depends(require_role("super_admin", "admin", "hr_manager"))
Module = Depends(require_module("presenze"))


class TeamOrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_unit_id: UUID | None
    expected_org_unit_id: UUID | None


@router.get("/team-organizations")
def list_team_organizations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Access],
    __: Annotated[ApplicationUser, Module],
) -> dict:
    links = db.scalars(select(PresenzeTeamOrganization)).all()
    return {
        "teams": [
            {"team_id": str(link.team_id), "org_unit_id": str(link.org_unit_id)} for link in links
        ],
        "units": list(build_team_organization_directory(db).values()),
    }


@router.put("/teams/{team_id}/organization")
def update_team_organization(
    team_id: UUID,
    payload: TeamOrganizationUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[ApplicationUser, Access],
    _: Annotated[ApplicationUser, Module],
) -> dict:
    team = db.scalar(
        select(OrganizationTeam).where(OrganizationTeam.id == team_id).with_for_update()
    )
    if team is None:
        raise HTTPException(status_code=404, detail="Presenze team not found")
    unit_id = require_team_org_unit(db, payload.org_unit_id)
    link = db.get(PresenzeTeamOrganization, team_id)
    previous = link.org_unit_id if link else None
    if previous != payload.expected_org_unit_id:
        raise HTTPException(
            status_code=409, detail="Organization link changed; reload before saving"
        )
    if unit_id is None:
        if link is not None:
            db.delete(link)
    elif link is None:
        db.add(
            PresenzeTeamOrganization(
                team_id=team_id, org_unit_id=unit_id, updated_by_user_id=user.id
            )
        )
    else:
        link.org_unit_id, link.updated_by_user_id = unit_id, user.id
    db.commit()
    return {"team_id": str(team_id), "org_unit_id": str(unit_id) if unit_id else None}
