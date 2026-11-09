"""Single team snapshot builder shared by LAN pull and outbound push."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.gate_router import RULES_VERSION
from app.modules.presenze.models import OrganizationTeam, OrganizationTeamSupervisorAssignment
from app.modules.presenze.services.gate_mobile_payloads import (
    build_presenze_memberships_by_team,
    build_presenze_supervisors_by_team,
    build_presenze_team_payload,
)
from app.modules.presenze.services.team_organization import attach_team_organization


def build_presenze_teams_push_payload(
    db: Session, *, now: datetime | None = None
) -> dict[str, Any]:
    return attach_team_organization(
        db,
        {
            "schema_version": 1,
            "source": "gaia",
            "rules_version": RULES_VERSION,
            "synced_from_gaia_at": (now or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
            "teams": _team_snapshot_items(db),
        },
    )


def _team_snapshot_items(db: Session) -> list[dict[str, Any]]:
    teams = db.scalars(select(OrganizationTeam).order_by(OrganizationTeam.name.asc())).all()
    memberships = build_presenze_memberships_by_team(db)
    assignments = db.execute(
        select(OrganizationTeamSupervisorAssignment, ApplicationUser)
        .join(
            ApplicationUser,
            ApplicationUser.id == OrganizationTeamSupervisorAssignment.application_user_id,
        )
        .order_by(
            OrganizationTeamSupervisorAssignment.team_id.asc(), ApplicationUser.username.asc()
        )
    ).all()
    supervisors = build_presenze_supervisors_by_team(db, assignments)
    return [
        build_presenze_team_payload(
            team, memberships.get(str(team.id), []), supervisors.get(str(team.id), [])
        )
        for team in teams
    ]
