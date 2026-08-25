from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import OrganizationTeam

TEAM_CHANGE_OPERATIONS = {"create_team", "update_team", "upsert_team"}
TEAM_CHANGE_SOURCES = {"gate_admin_console", "gate_mobile", "gate"}
TEAM_SCOPES = {"presenze", "gate", "global"}


class TeamChangeApplyError(ValueError):
    pass


@dataclass(frozen=True)
class AppliedTeamChange:
    team: OrganizationTeam


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
            id=_optional_uuid(team_payload.get("team_id"), "team_id") or uuid.uuid4(),
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


def _validate_team_change_envelope(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 1:
        raise TeamChangeApplyError("schema_version non supportata per propose_team_change")
    if payload.get("source") not in TEAM_CHANGE_SOURCES:
        raise TeamChangeApplyError("source non supportata per propose_team_change")
    if payload.get("operation") not in TEAM_CHANGE_OPERATIONS:
        raise TeamChangeApplyError("operation non supportata per propose_team_change")
    if not isinstance(payload.get("team"), dict):
        raise TeamChangeApplyError("team mancante o non valido in propose_team_change")


def _resolve_target_team(db: Session, team_payload: dict[str, Any], *, operation: str) -> OrganizationTeam | None:
    team_id = _optional_uuid(team_payload.get("team_id"), "team_id")
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
    return _team_by_code_and_scope(db, team_payload)


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


def _optional_uuid(value: Any, field: str) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise TeamChangeApplyError(f"{field} non e un UUID valido") from exc
