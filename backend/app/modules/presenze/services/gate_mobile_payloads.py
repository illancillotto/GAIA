from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
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
            select(PresenzeCollaborator).where(PresenzeCollaborator.application_user_id.is_not(None))
        ).all()
        if collaborator.application_user_id is not None
    }
    result: dict[str, list[dict[str, Any]]] = {}
    for supervisor, user in supervisors:
        collaborator = collaborators_by_user_id.get(supervisor.application_user_id)
        result.setdefault(str(supervisor.team_id), []).append(
            {
                "supervisor_assignment_id": str(supervisor.id),
                "application_user_id": supervisor.application_user_id,
                "username": user.username,
                "user_label": user.full_name or user.username,
                "collaborator_id": str(collaborator.id) if collaborator is not None else None,
                "employee_code": collaborator.employee_code if collaborator is not None else None,
                "collaborator_name": collaborator.name if collaborator is not None else None,
                "permission_scope": supervisor.permission_scope,
                "valid_from": json_date(supervisor.valid_from),
                "valid_to": json_date(supervisor.valid_to),
                "source_channel": gate_channel(supervisor.source_channel),
                "updated_at": json_datetime(supervisor.updated_at),
            }
        )
    return result


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
        "collaborator_name": collaborator.name if collaborator is not None else str(record.collaborator_id),
        "employee_code": collaborator.employee_code if collaborator is not None else "",
        "team_ids": [str(team_id) for team_id in team_ids],
        "work_date": json_date(record.work_date),
        "weekday": weekday_label(record.work_date),
        "status": serialized.operational_status,
        "review_status": record.validation_status,
        "severity": severity,
        "contract_kind": collaborator.contract_kind if collaborator is not None else None,
        "operai_group": collaborator.operai_group if collaborator is not None else None,
        "standard_daily_minutes": collaborator.standard_daily_minutes if collaborator is not None else None,
        "schedule_code": record.schedule_code,
        "ordinary_minutes": record.ordinary_minutes,
        "extra_minutes": serialized.effective_extra_minutes or 0,
        "missing_minutes": serialized.operational_missing_minutes,
        "absence_cause": serialized.resolved_absence_cause,
        "has_request": bool(serialized.detail_requests or record.request_type or record.request_description),
        "validated_at": json_datetime(record.validated_at) if record.validated_at is not None else None,
        "validated_by_user_id": record.validated_by_user_id,
        **_gate_record_feature_values(record),
        **_canonical_export_values(record, serialized=serialized, classification=classification),
    }


def _gate_record_feature_values(record: PresenzeDailyRecord) -> dict[str, Any]:
    return {
        "km_value": record.km_value,
        "reperibilita_unit": record.reperibilita_unit,
        "reperibilita_quantity": record.reperibilita_quantity,
    }


def _canonical_export_values(record: PresenzeDailyRecord, *, serialized: Any, classification: Any) -> dict[str, Any]:
    return {
        "trasferta_minutes": record.trasferta_minutes,
        "trasferta_montano": record.trasferta_montano,
        "absence_minutes": record.absence_minutes,
        "justified_minutes": record.justified_minutes,
        "request_description": serialized.request_description,
        "export_absence_code": resolve_export_absence_code(record),
        "export_special_day": classification.special_day,
        "export_ordinary_minutes": classification.ordinary_minutes,
        "export_extra_minutes": classification.extra_minutes,
        "export_ordinary_night_minutes": classification.ordinary_night_minutes,
        "export_overtime_day_minutes": classification.overtime_day_minutes,
        "export_overtime_night_minutes": classification.overtime_night_minutes,
        "export_overtime_festive_minutes": classification.overtime_festive_minutes,
        "export_overtime_festive_night_minutes": classification.overtime_festive_night_minutes,
        "export_shift_festive_day_minutes": classification.shift_festive_day_minutes,
        "export_shift_night_minutes": classification.shift_night_minutes,
        "export_shift_festive_night_minutes": classification.shift_festive_night_minutes,
    }


def weekday_label(value: date) -> str:
    labels = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]
    return labels[value.weekday()]


def json_datetime(value: datetime | None) -> str:
    fallback = value or datetime.now(timezone.utc)
    return fallback.isoformat().replace("+00:00", "Z")


def json_date(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def gate_channel(value: str | None) -> str:
    if value in {"gaia_web", "gaia"}:
        return "gaia"
    if value in {"gate_mobile", "gate"}:
        return "gate"
    return value or "gaia"
