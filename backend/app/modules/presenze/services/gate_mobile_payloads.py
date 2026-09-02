from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PresenzeCollaborator,
    PresenzeDailyRecord,
)
from app.modules.presenze.services.xlsm_export import resolve_export_absence_code


def build_presenze_supervisors_by_team(
    db: Session,
    supervisors: list[tuple[OrganizationTeamSupervisorAssignment, ApplicationUser]],
) -> dict[str, list[dict[str, Any]]]:
    collaborators_by_user_id = {
        collaborator.application_user_id: collaborator
        for collaborator in db.scalars(
            select(PresenzeCollaborator).where(
                PresenzeCollaborator.application_user_id.is_not(None)
            )
        ).all()
        if collaborator.application_user_id is not None
    }
    result: dict[str, list[dict[str, Any]]] = {}
    for supervisor, user in supervisors:
        collaborator = collaborators_by_user_id.get(supervisor.application_user_id)
        result.setdefault(str(supervisor.team_id), []).append(
            {
                "supervisor_assignment_id": str(supervisor.id),
                "gaia_user_id": str(supervisor.application_user_id),
                "username": user.username,
                "user_label": user.full_name or user.username,
                **_supervisor_collaborator_fields(collaborator),
                "permission_scope": supervisor.permission_scope,
                "valid_from": json_date(supervisor.valid_from),
                "valid_to": json_date(supervisor.valid_to),
                "source_channel": gate_channel(supervisor.source_channel),
                "updated_at": json_datetime(supervisor.updated_at),
            }
        )
    return result


def build_presenze_team_payload(
    team: OrganizationTeam,
    memberships: list[dict[str, Any]],
    supervisors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "team_id": team.gate_mobile_team_id or str(team.id),
        "name": team.name,
        "code": team.code,
        "personnel_area": required_personnel_area(
            team.personnel_area,
            entity=f"organization_team:{team.id}",
        ),
        "active": team.active,
        "created_from_channel": gate_channel(team.created_from_channel),
        "created_by_user_id": team.created_by_user_id,
        "audit": {},
        "created_at": json_datetime(team.created_at),
        "updated_at": json_datetime(team.updated_at),
        "memberships": memberships,
        "supervisors": supervisors,
    }


def build_presenze_membership_payload(
    membership: OrganizationTeamMembership,
    collaborator: PresenzeCollaborator,
) -> dict[str, Any]:
    return {
        "membership_id": str(membership.id),
        "collaborator_id": str(membership.collaborator_id),
        "gaia_user_id": json_optional_identifier(collaborator.application_user_id),
        "employee_code": collaborator.employee_code,
        "presenze_collaborator_id": str(membership.collaborator_id),
        "presenze_employee_code": collaborator.employee_code,
        "collaborator_name": collaborator.name,
        "role": membership.role,
        "valid_from": json_date(membership.valid_from),
        "valid_to": json_date(membership.valid_to),
        "source_channel": gate_channel(membership.source_channel),
        "updated_at": json_datetime(membership.updated_at),
    }


def build_presenze_mobile_record_payload(
    record: PresenzeDailyRecord,
    *,
    collaborator: PresenzeCollaborator | None,
    team_ids: list[UUID],
    serialized: Any,
    severity: str,
    classification: Any,
) -> dict[str, Any]:
    return {
        "record_id": str(record.id),
        "collaborator_id": str(record.collaborator_id),
        **_record_collaborator_values(record, collaborator),
        "team_ids": [str(team_id) for team_id in team_ids],
        "work_date": json_date(record.work_date),
        "weekday": weekday_label(record.work_date),
        "status": serialized.operational_status,
        "review_status": record.validation_status,
        "severity": severity,
        "schedule_code": record.schedule_code,
        "ordinary_minutes": record.ordinary_minutes,
        "extra_minutes": serialized.effective_extra_minutes or 0,
        "missing_minutes": serialized.operational_missing_minutes,
        "absence_cause": serialized.resolved_absence_cause,
        "has_request": bool(
            serialized.detail_requests or record.request_type or record.request_description
        ),
        "validated_at": json_datetime(record.validated_at)
        if record.validated_at is not None
        else None,
        "validated_by_user_id": record.validated_by_user_id,
        **_gate_record_feature_values(record),
        **_canonical_export_values(record, serialized, classification),
    }


def canonical_record_gaia_user_id(
    record: PresenzeDailyRecord,
    collaborator: PresenzeCollaborator | None,
) -> str | None:
    if collaborator is None or collaborator.application_user_id is None:
        return None
    if record.application_user_id not in {None, collaborator.application_user_id}:
        return None
    return str(collaborator.application_user_id)


def _record_collaborator_values(
    record: PresenzeDailyRecord, collaborator: PresenzeCollaborator | None
) -> dict[str, Any]:
    return {
        "gaia_user_id": canonical_record_gaia_user_id(record, collaborator),
        "collaborator_name": collaborator.name if collaborator else str(record.collaborator_id),
        "employee_code": collaborator.employee_code if collaborator else "",
        "contract_kind": collaborator.contract_kind if collaborator else None,
        "operai_group": collaborator.operai_group if collaborator else None,
        "standard_daily_minutes": collaborator.standard_daily_minutes if collaborator else None,
    }


def required_personnel_area(value: Any, *, entity: str) -> str:
    if value not in {"AGRARIO", "IMPIANTI"}:
        raise ValueError(f"personnel_area mancante o non valida per {entity}")
    return str(value)


def _supervisor_collaborator_fields(
    collaborator: PresenzeCollaborator | None,
) -> dict[str, str | None]:
    if collaborator is None:
        return {
            "collaborator_id": None,
            "employee_code": None,
            "presenze_collaborator_id": None,
            "presenze_employee_code": None,
            "collaborator_name": None,
        }
    collaborator_id = str(collaborator.id)
    return {
        "collaborator_id": collaborator_id,
        "employee_code": collaborator.employee_code,
        "presenze_collaborator_id": collaborator_id,
        "presenze_employee_code": collaborator.employee_code,
        "collaborator_name": collaborator.name,
    }


def _gate_record_feature_values(record: PresenzeDailyRecord) -> dict[str, Any]:
    return {
        "km_value": record.km_value,
        "reperibilita_unit": record.reperibilita_unit,
        "reperibilita_quantity": record.reperibilita_quantity,
    }


def _canonical_export_values(record: PresenzeDailyRecord, data: Any, export: Any) -> dict[str, Any]:
    return {
        "trasferta_minutes": record.trasferta_minutes,
        "trasferta_montano": record.trasferta_montano,
        "absence_minutes": record.absence_minutes,
        "justified_minutes": record.justified_minutes,
        "request_description": data.request_description,
        "export_absence_code": resolve_export_absence_code(record),
        "export_special_day": export.special_day,
        "export_ordinary_minutes": export.ordinary_minutes,
        "export_extra_minutes": export.extra_minutes,
        "export_ordinary_night_minutes": export.ordinary_night_minutes,
        "export_overtime_day_minutes": export.overtime_day_minutes,
        "export_overtime_night_minutes": export.overtime_night_minutes,
        "export_overtime_festive_minutes": export.overtime_festive_minutes,
        "export_overtime_festive_night_minutes": export.overtime_festive_night_minutes,
        "export_shift_festive_day_minutes": export.shift_festive_day_minutes,
        "export_shift_night_minutes": export.shift_night_minutes,
        "export_shift_festive_night_minutes": export.shift_festive_night_minutes,
    }


def weekday_label(value: date) -> str:
    labels = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]
    return labels[value.weekday()]


def json_datetime(value: datetime | None) -> str:
    fallback = value or datetime.now(UTC)
    return fallback.isoformat().replace("+00:00", "Z")


def json_date(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def json_optional_identifier(value: Any) -> str | None:
    return str(value) if value is not None else None


def gate_channel(value: str | None) -> str:
    if value in {"gaia_web", "gaia"}:
        return "gaia"
    if value in {"gate_mobile", "gate"}:
        return "gate"
    return value or "gaia"
