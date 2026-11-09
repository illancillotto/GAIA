"""Explicit Presenze team links to the canonical GAIA organization chart."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.organigramma.models.org_assignment import OrgAssignment
from app.modules.organigramma.models.org_unit import OrgUnit
from app.modules.presenze.models import OrganizationTeam
from app.modules.presenze.team_organization_models import PresenzeTeamOrganization


def attach_team_organization(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    directory = build_team_organization_directory(db)
    rows = db.execute(
        select(OrganizationTeam, PresenzeTeamOrganization).join(
            PresenzeTeamOrganization, PresenzeTeamOrganization.team_id == OrganizationTeam.id
        )
    ).all()
    links = {
        team.gate_mobile_team_id or str(team.id): directory.get(link.org_unit_id)
        for team, link in rows
    }
    payload["teams"] = [
        {**team, "organization": links.get(team["team_id"])} for team in payload["teams"]
    ]
    return payload


def require_team_org_unit(db: Session, unit_id: UUID | None) -> UUID | None:
    if unit_id is None:
        return None
    unit = db.get(OrgUnit, unit_id)
    if unit is None or not unit.is_active or unit.structure_kind != "organigramma":
        raise HTTPException(status_code=422, detail="Active organization chart unit required")
    return unit.id


def build_team_organization_directory(db: Session) -> dict[UUID, dict[str, Any]]:
    units = {
        unit.id: unit
        for unit in db.scalars(
            select(OrgUnit).where(OrgUnit.structure_kind == "organigramma", OrgUnit.is_active)
        ).all()
    }
    leaders: dict[UUID, list[dict[str, Any]]] = {}
    rows = db.execute(
        select(OrgAssignment, ApplicationUser)
        .join(ApplicationUser, ApplicationUser.id == OrgAssignment.user_id)
        .where(
            OrgAssignment.structure_kind == "organigramma",
            OrgAssignment.active,
            OrgAssignment.position_code.in_(["capo_settore", "capo_reparto"]),
            ApplicationUser.is_active,
        )
        .order_by(OrgAssignment.id)
    ).all()
    for assignment, user in rows:
        leaders.setdefault(assignment.org_unit_id, []).append(
            {
                "gaia_user_id": str(user.id),
                "user_label": user.full_name or user.username,
                "position_code": assignment.position_code,
                "valid_from": _assignment_datetime(assignment.valid_from),
                "valid_to": _assignment_datetime(assignment.valid_to),
            }
        )
    result = {}
    for unit_id in units:
        path = _unit_path(unit_id, units, leaders)
        if path:
            result[unit_id] = {"unit_id": str(unit_id), "path": path}
    return result


def _unit_path(unit_id: UUID, units: dict, leaders: dict) -> list[dict[str, Any]]:
    path = []
    seen = set()
    while unit_id is not None:
        if unit_id in seen or unit_id not in units:
            return []
        seen.add(unit_id)
        unit = units[unit_id]
        path.append(
            {
                "id": str(unit.id),
                "name": unit.nome,
                "kind": unit.tipo,
                "leaders": leaders.get(unit.id, []),
            }
        )
        unit_id = unit.parent_id
    return list(reversed(path))


def _assignment_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
