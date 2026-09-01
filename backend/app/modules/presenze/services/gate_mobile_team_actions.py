from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PresenzeCollaborator,
)

TEAM_CHANGE_OPERATIONS = {"create_team", "rename_team", "update_team", "upsert_team"}
TEAM_CHANGE_SOURCES = {"gate_admin_console", "gate_console_mobile", "gate_mobile", "gate"}
TEAM_SCOPES = {"presenze", "teti", "gate", "global"}


class TeamChangeApplyError(ValueError):
    pass


@dataclass(frozen=True)
class AppliedTeamChange:
    team: OrganizationTeam


@dataclass(frozen=True)
class AppliedTeamAssignments:
    team: OrganizationTeam
    assignment_count: int


def apply_presenze_team_proposal(
    db: Session,
    action_type: str,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
) -> AppliedTeamChange | AppliedTeamAssignments:
    if action_type in {"propose_team_create", "propose_team_change"}:
        return apply_presenze_team_change_proposal(db, payload, actor=actor)
    if action_type == "propose_team_membership":
        return apply_presenze_team_membership_proposal(db, payload, actor=actor)
    if action_type == "propose_team_supervisor":
        return apply_presenze_team_supervisor_proposal(db, payload, actor=actor)
    raise TeamChangeApplyError(f"Tipo pending action squadra non supportato: {action_type}")


def apply_presenze_team_change_proposal(
    db: Session,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
) -> AppliedTeamChange:
    _validate_team_change_envelope(payload)
    operation = str(payload["operation"])
    team_payload = payload["team"]
    team = _resolve_target_team(db, team_payload, operation=operation)
    if team is None:
        team = OrganizationTeam(
            id=_optional_uuid(team_payload.get("team_id")) or uuid.uuid4(),
            name=_required_text(team_payload, "name", max_length=255),
            code=_optional_text(team_payload.get("code"), "code", max_length=64),
            scope=_team_scope(team_payload.get("scope")),
            active=_optional_bool(team_payload.get("active"), default=True, field="active"),
            created_from_channel="gate_mobile",
            created_by_user_id=actor.id,
        )
        db.add(team)
    else:
        _apply_team_update(team, team_payload)

    db.commit()
    db.refresh(team)
    return AppliedTeamChange(team=team)


def apply_presenze_team_membership_proposal(
    db: Session,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
) -> AppliedTeamAssignments:
    team, assignments = _validate_assignment_proposal(
        db, payload, operation="update_team_memberships", field="memberships"
    )
    resolved: list[tuple[PresenzeCollaborator, str]] = []
    seen_user_ids: set[int] = set()
    for assignment in assignments:
        gaia_user_id = _required_gaia_user_id(assignment)
        if gaia_user_id in seen_user_ids:
            raise TeamChangeApplyError(f"gaia_user_id duplicato nelle memberships: {gaia_user_id}")
        seen_user_ids.add(gaia_user_id)
        collaborator = db.scalar(
            select(PresenzeCollaborator).where(PresenzeCollaborator.application_user_id == gaia_user_id)
        )
        if collaborator is None:
            raise TeamChangeApplyError(f"Collaboratore Presenze non mappato a gaia_user_id={gaia_user_id}")
        resolved.append((collaborator, _assignment_text(assignment.get("role"), "role", default="member")))

    db.execute(delete(OrganizationTeamMembership).where(OrganizationTeamMembership.team_id == team.id))
    for collaborator, role in resolved:
        db.add(
            OrganizationTeamMembership(
                team_id=team.id,
                collaborator_id=collaborator.id,
                role=role,
                source_channel="gate_mobile",
                created_by_user_id=actor.id,
            )
        )
    db.commit()
    db.refresh(team)
    return AppliedTeamAssignments(team=team, assignment_count=len(resolved))


def apply_presenze_team_supervisor_proposal(
    db: Session,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
) -> AppliedTeamAssignments:
    team, assignments = _validate_assignment_proposal(
        db, payload, operation="update_team_supervisors", field="supervisors"
    )
    resolved: list[tuple[ApplicationUser, str]] = []
    seen_user_ids: set[int] = set()
    for assignment in assignments:
        gaia_user_id = _required_gaia_user_id(assignment)
        if gaia_user_id in seen_user_ids:
            raise TeamChangeApplyError(f"gaia_user_id duplicato nei supervisors: {gaia_user_id}")
        seen_user_ids.add(gaia_user_id)
        user = db.get(ApplicationUser, gaia_user_id)
        if user is None or not user.is_active:
            raise TeamChangeApplyError(f"Application user attivo non trovato per gaia_user_id={gaia_user_id}")
        resolved.append(
            (user, _assignment_text(assignment.get("permission_scope"), "permission_scope", default="view"))
        )

    db.execute(
        delete(OrganizationTeamSupervisorAssignment).where(
            OrganizationTeamSupervisorAssignment.team_id == team.id
        )
    )
    for user, permission_scope in resolved:
        db.add(
            OrganizationTeamSupervisorAssignment(
                team_id=team.id,
                application_user_id=user.id,
                permission_scope=permission_scope,
                source_channel="gate_mobile",
                assigned_by_user_id=actor.id,
            )
        )
    db.commit()
    db.refresh(team)
    return AppliedTeamAssignments(team=team, assignment_count=len(resolved))


def _validate_team_change_envelope(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") not in {None, 1}:
        raise TeamChangeApplyError("schema_version non supportata per propose_team_change")
    if (payload.get("source") or payload.get("requested_from")) not in TEAM_CHANGE_SOURCES:
        raise TeamChangeApplyError("source non supportata per propose_team_change")
    if payload.get("operation") not in TEAM_CHANGE_OPERATIONS:
        raise TeamChangeApplyError("operation non supportata per propose_team_change")
    if not isinstance(payload.get("team"), dict):
        raise TeamChangeApplyError("team mancante o non valido in propose_team_change")


def _resolve_target_team(db: Session, team_payload: dict[str, Any], *, operation: str) -> OrganizationTeam | None:
    team_id = _optional_uuid(team_payload.get("team_id"))
    if team_id is not None:
        team = db.get(OrganizationTeam, team_id)
        if team is not None:
            if operation == "create_team":
                raise TeamChangeApplyError(f"Squadra GAIA {team_id} gia esistente per create_team")
            return team
        if operation == "update_team":
            raise TeamChangeApplyError(f"Squadra GAIA {team_id} non trovata per update_team")
    if operation == "create_team":
        _ensure_team_code_available(db, team_payload, team_id=team_id)
        return None
    team = _team_by_code_and_scope(db, team_payload)
    if team is None:
        raise TeamChangeApplyError("Squadra GAIA non trovata tramite team_id o code/scope")
    return team


def _apply_team_update(team: OrganizationTeam, team_payload: dict[str, Any]) -> None:
    if "name" in team_payload:
        team.name = _required_text(team_payload, "name", max_length=255)
    if "code" in team_payload:
        team.code = _optional_text(team_payload.get("code"), "code", max_length=64)
    if "scope" in team_payload:
        team.scope = _team_scope(team_payload.get("scope"))
    if "active" in team_payload:
        team.active = _optional_bool(team_payload.get("active"), default=team.active, field="active")


def _ensure_team_code_available(db: Session, team_payload: dict[str, Any], *, team_id: uuid.UUID | None) -> None:
    existing = _team_by_code_and_scope(db, team_payload)
    if existing is not None and existing.id != team_id:
        raise TeamChangeApplyError("code gia assegnato a un'altra squadra nello stesso scope")


def _team_by_code_and_scope(db: Session, team_payload: dict[str, Any]) -> OrganizationTeam | None:
    code = _optional_text(team_payload.get("code"), "code", max_length=64)
    if code is None:
        return None
    scope = _team_scope(team_payload.get("scope"))
    return db.scalar(select(OrganizationTeam).where(OrganizationTeam.code == code, OrganizationTeam.scope == scope))


def _validate_assignment_proposal(
    db: Session,
    payload: dict[str, Any],
    *,
    operation: str,
    field: str,
) -> tuple[OrganizationTeam, list[dict[str, Any]]]:
    if payload.get("operation") != operation:
        raise TeamChangeApplyError(f"operation non supportata per {field}")
    team_payload = payload.get("team")
    if not isinstance(team_payload, dict):
        raise TeamChangeApplyError(f"team mancante o non valido per {field}")
    raw_assignments = team_payload.get(field)
    if not isinstance(raw_assignments, list) or not all(isinstance(item, dict) for item in raw_assignments):
        raise TeamChangeApplyError(f"{field} deve essere un array di oggetti")
    return _resolve_assignment_team(db, team_payload), raw_assignments


def _resolve_assignment_team(db: Session, team_payload: dict[str, Any]) -> OrganizationTeam:
    team_id = _optional_uuid(team_payload.get("team_id"))
    if team_id is not None:
        team = db.get(OrganizationTeam, team_id)
        if team is not None:
            return team
    code = _optional_text(team_payload.get("code"), "code", max_length=64)
    if code is None:
        raise TeamChangeApplyError("code squadra mancante per la riconciliazione GATE")
    candidates = db.scalars(select(OrganizationTeam).where(OrganizationTeam.code == code)).all()
    if len(candidates) != 1:
        raise TeamChangeApplyError(f"Squadra GAIA non risolta in modo univoco tramite code={code}")
    return candidates[0]


def _required_gaia_user_id(payload: dict[str, Any]) -> int:
    value = payload.get("gaia_user_id")
    if isinstance(value, bool):
        raise TeamChangeApplyError("gaia_user_id non valido")
    try:
        user_id = int(str(value))
    except (TypeError, ValueError) as exc:
        raise TeamChangeApplyError("gaia_user_id mancante o non valido") from exc
    if user_id < 1:
        raise TeamChangeApplyError("gaia_user_id mancante o non valido")
    return user_id


def _assignment_text(value: Any, field: str, *, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or len(text) > 32:
        raise TeamChangeApplyError(f"{field} non valido")
    return text


def _team_scope(value: Any) -> str:
    scope = "presenze" if value is None else str(value).strip()
    if scope not in TEAM_SCOPES:
        raise TeamChangeApplyError(f"scope squadra non supportato: {value}")
    return scope


def _required_text(payload: dict[str, Any], field: str, *, max_length: int) -> str:
    text = _optional_text(payload.get(field), field, max_length=max_length)
    if text is None:
        raise TeamChangeApplyError(f"{field} mancante in propose_team_change")
    return text


def _optional_text(value: Any, field: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise TeamChangeApplyError(f"{field} non puo essere vuoto")
    if len(text) > max_length:
        raise TeamChangeApplyError(f"{field} supera {max_length} caratteri")
    return text


def _optional_bool(value: Any, *, default: bool, field: str) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise TeamChangeApplyError(f"{field} deve essere booleano")
    return value


def _optional_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
