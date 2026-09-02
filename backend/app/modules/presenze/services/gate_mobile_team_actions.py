from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PresenzeCollaborator,
)

PERSONNEL_AREAS = {"AGRARIO", "IMPIANTI"}
TEAM_ACTION_OPERATIONS = {
    "propose_team_create": {"create_team"},
    "propose_team_change": {"rename_team", "update_team", "upsert_team"},
    "propose_team_membership": {"update_team_memberships"},
    "propose_team_supervisor": {"update_team_supervisors"},
}


class TeamChangeApplyError(ValueError):
    pass


@dataclass(frozen=True)
class AppliedTeamChange:
    team: OrganizationTeam


def apply_presenze_team_proposal(
    db: Session,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
    action_type: str,
) -> AppliedTeamChange:
    _validate_action(payload, action_type)
    if action_type in {"propose_team_create", "propose_team_change"}:
        team = _apply_team_properties(
            db, payload, actor=actor, create=action_type == "propose_team_create"
        )
    else:
        team = _required_target_team(db, _team_payload(payload))
        if action_type == "propose_team_membership":
            _replace_memberships(db, team, payload, actor=actor)
        else:
            _replace_supervisors(db, team, payload, actor=actor)
    db.commit()
    db.refresh(team)
    return AppliedTeamChange(team=team)


def apply_presenze_team_change_proposal(
    db: Session,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
) -> AppliedTeamChange:
    action_type = (
        "propose_team_create"
        if payload.get("operation") == "create_team"
        else "propose_team_change"
    )
    return apply_presenze_team_proposal(db, payload, actor=actor, action_type=action_type)


def _validate_action(payload: dict[str, Any], action_type: str) -> None:
    allowed_operations = TEAM_ACTION_OPERATIONS.get(action_type)
    if allowed_operations is None:
        raise TeamChangeApplyError(f"Tipo pending action squadra non supportato: {action_type}")
    if payload.get("operation") not in allowed_operations:
        raise TeamChangeApplyError(f"operation non supportata per {action_type}")
    _team_payload(payload)


def _apply_team_properties(
    db: Session,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
    create: bool,
) -> OrganizationTeam:
    team_payload = _team_payload(payload)
    team = _find_target_team(db, team_payload)
    if team is None:
        if not create:
            raise TeamChangeApplyError("Squadra GAIA non trovata")
        team = OrganizationTeam(
            id=_parse_team_uuid(team_payload.get("team_id")) or uuid.uuid4(),
            gate_mobile_team_id=_external_team_id(team_payload.get("team_id")),
            name=_required_text(team_payload, "name", max_length=255),
            code=_optional_text(team_payload.get("code"), "code", max_length=64),
            scope="presenze",
            personnel_area=_personnel_area(team_payload),
            active=_optional_bool(team_payload.get("active"), default=True, field="active"),
            created_from_channel="gate_mobile",
            created_by_user_id=actor.id,
        )
        _ensure_team_code_available(db, team, team_payload)
        db.add(team)
        return team
    _ensure_matching_area(team, team_payload)
    _apply_team_update(db, team, team_payload)
    return team


def _apply_team_update(db: Session, team: OrganizationTeam, team_payload: dict[str, Any]) -> None:
    next_code = team.code
    if "code" in team_payload:
        next_code = _optional_text(team_payload.get("code"), "code", max_length=64)
    _ensure_team_code_available(db, team, team_payload, code=next_code)
    if "name" in team_payload:
        team.name = _required_text(team_payload, "name", max_length=255)
    if "code" in team_payload:
        team.code = next_code
    if "active" in team_payload:
        team.active = _optional_bool(
            team_payload.get("active"), default=team.active, field="active"
        )
    db.add(team)


def _required_target_team(db: Session, team_payload: dict[str, Any]) -> OrganizationTeam:
    team = _find_target_team(db, team_payload)
    if team is None:
        raise TeamChangeApplyError("Squadra GAIA non trovata")
    _ensure_matching_area(team, team_payload)
    return team


def _find_target_team(db: Session, team_payload: dict[str, Any]) -> OrganizationTeam | None:
    raw_team_id = team_payload.get("team_id")
    team_id = _parse_team_uuid(raw_team_id)
    if team_id is not None:
        team = db.get(OrganizationTeam, team_id)
        if team is not None:
            return team
    external_team_id = _external_team_id(raw_team_id)
    if external_team_id is not None:
        team = db.scalar(
            select(OrganizationTeam).where(OrganizationTeam.gate_mobile_team_id == external_team_id)
        )
        if team is not None:
            return team
    return None


def _ensure_matching_area(team: OrganizationTeam, team_payload: dict[str, Any]) -> None:
    if team.personnel_area != _personnel_area(team_payload):
        raise TeamChangeApplyError("personnel_area squadra incoerente")


def _ensure_team_code_available(
    db: Session,
    target: OrganizationTeam,
    team_payload: dict[str, Any],
    *,
    code: str | None = None,
) -> None:
    candidate_code = target.code if code is None else code
    if candidate_code is None:
        return
    matches = db.scalars(
        select(OrganizationTeam).where(
            OrganizationTeam.code == candidate_code,
            OrganizationTeam.personnel_area == _personnel_area(team_payload),
            OrganizationTeam.id != target.id,
        )
    ).all()
    if matches:
        raise TeamChangeApplyError(
            "code gia assegnato a un'altra squadra nella stessa personnel_area"
        )


def _replace_memberships(
    db: Session,
    team: OrganizationTeam,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
) -> None:
    requested = _requested_assignments(payload, "requested_memberships")
    desired: dict[int, tuple[PresenzeCollaborator | None, str]] = {}
    seen_user_ids: set[int] = set()
    for item in requested:
        user = _canonical_user(db, item, label="membro")
        if user.id in seen_user_ids:
            raise TeamChangeApplyError(f"gaia_user_id duplicato nelle membership: {user.id}")
        seen_user_ids.add(user.id)
        desired[user.id] = (
            _optional_canonical_collaborator(db, user.id),
            _optional_text(item.get("role"), "role", max_length=32) or "member",
        )
    existing = list(
        db.scalars(
            select(OrganizationTeamMembership).where(
                OrganizationTeamMembership.team_id == team.id,
                OrganizationTeamMembership.valid_from.is_(None),
                OrganizationTeamMembership.valid_to.is_(None),
            )
        ).all()
    )
    by_user_id: dict[int, OrganizationTeamMembership] = {}
    for membership in existing:
        if (
            membership.application_user_id not in desired
            or membership.application_user_id in by_user_id
        ):
            db.delete(membership)
            continue
        by_user_id[membership.application_user_id] = membership
    for user_id, (collaborator, role) in desired.items():
        membership = by_user_id.get(user_id)
        if membership is None:
            membership = OrganizationTeamMembership(team_id=team.id)
        membership.application_user_id = user_id
        membership.collaborator_id = collaborator.id if collaborator is not None else None
        membership.role = role
        membership.source_channel = "gate_mobile"
        membership.created_by_user_id = actor.id
        db.add(membership)


def _replace_supervisors(
    db: Session,
    team: OrganizationTeam,
    payload: dict[str, Any],
    *,
    actor: ApplicationUser,
) -> None:
    requested = _requested_assignments(payload, "requested_supervisors")
    desired: dict[int, str] = {}
    for item in requested:
        user = _canonical_user(db, item, label="responsabile")
        if user.id in desired:
            raise TeamChangeApplyError(f"gaia_user_id duplicato nei supervisor: {user.id}")
        desired[user.id] = (
            _optional_text(
                item.get("permission_scope"),
                "permission_scope",
                max_length=32,
            )
            or "team"
        )
    existing = list(
        db.scalars(
            select(OrganizationTeamSupervisorAssignment).where(
                OrganizationTeamSupervisorAssignment.team_id == team.id,
                OrganizationTeamSupervisorAssignment.valid_from.is_(None),
                OrganizationTeamSupervisorAssignment.valid_to.is_(None),
            )
        ).all()
    )
    kept_user_ids: set[int] = set()
    for assignment in existing:
        if (
            assignment.application_user_id not in desired
            or assignment.application_user_id in kept_user_ids
        ):
            db.delete(assignment)
            continue
        assignment.permission_scope = desired[assignment.application_user_id]
        assignment.source_channel = "gate_mobile"
        assignment.assigned_by_user_id = actor.id
        kept_user_ids.add(assignment.application_user_id)
        db.add(assignment)
    for user_id, permission_scope in desired.items():
        if user_id in kept_user_ids:
            continue
        db.add(
            OrganizationTeamSupervisorAssignment(
                team_id=team.id,
                application_user_id=user_id,
                permission_scope=permission_scope,
                source_channel="gate_mobile",
                assigned_by_user_id=actor.id,
            )
        )


def _canonical_user(db: Session, payload: dict[str, Any], *, label: str) -> ApplicationUser:
    user_id = canonical_gaia_user_id(payload.get("gaia_user_id"), label=label)
    user = db.get(ApplicationUser, user_id)
    if user is None:
        raise TeamChangeApplyError(f"gaia_user_id {user_id} non trovato per {label}")
    return user


def _optional_canonical_collaborator(
    db: Session,
    gaia_user_id: int,
) -> PresenzeCollaborator | None:
    matches = list(
        db.scalars(
            select(PresenzeCollaborator).where(
                PresenzeCollaborator.application_user_id == gaia_user_id
            )
        ).all()
    )
    if len(matches) > 1:
        raise TeamChangeApplyError(
            f"Relazione Presenze non univoca per gaia_user_id {gaia_user_id}"
        )
    return matches[0] if matches else None


def canonical_gaia_user_id(value: Any, *, label: str) -> int:
    if value is None or isinstance(value, bool):
        raise TeamChangeApplyError(f"gaia_user_id mancante o non valido per {label}")
    try:
        user_id = int(str(value))
    except ValueError as exc:
        raise TeamChangeApplyError(f"gaia_user_id non valido per {label}") from exc
    if user_id <= 0:
        raise TeamChangeApplyError(f"gaia_user_id non valido per {label}")
    return user_id


def pending_action_gaia_user_id(payload: dict[str, Any]) -> int:
    value = payload.get("gaia_user_id")
    if value is None:
        actor = payload.get("actor")
        value = actor.get("gaia_user_id") if isinstance(actor, dict) else None
    return canonical_gaia_user_id(value, label="autore")


def _requested_assignments(payload: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = payload.get(field)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise TeamChangeApplyError(f"{field} deve essere una lista di oggetti")
    return value


def _team_payload(payload: dict[str, Any]) -> dict[str, Any]:
    team = payload.get("team")
    if not isinstance(team, dict):
        raise TeamChangeApplyError("team mancante o non valido nella pending action")
    return team


def _personnel_area(payload: dict[str, Any]) -> str:
    value = payload.get("personnel_area")
    if value not in PERSONNEL_AREAS:
        raise TeamChangeApplyError("personnel_area deve essere AGRARIO o IMPIANTI")
    return str(value)


def _required_text(payload: dict[str, Any], field: str, *, max_length: int) -> str:
    text = _optional_text(payload.get(field), field, max_length=max_length)
    if text is None:
        raise TeamChangeApplyError(f"{field} mancante nella pending action")
    return text


def _optional_text(value: Any, field: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TeamChangeApplyError(f"{field} deve essere una stringa")
    text = value.strip()
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


def _parse_team_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _external_team_id(value: Any) -> str | None:
    if value is None or _parse_team_uuid(value) is not None:
        return None
    return _optional_text(value, "team_id", max_length=255)
