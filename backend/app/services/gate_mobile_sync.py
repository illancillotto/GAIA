from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from typing import Any
from uuid import UUID
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.application_user import ApplicationUser
from app.schemas.users import normalize_email
from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileSyncRun
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.routes.mobile_sync import get_mobile_catalogs, get_mobile_worksets
from app.modules.presenze.gate_router import (
    EXPORT_RULES_VERSION,
    RULES_VERSION,
    _append_gate_audit,
    _build_rules_response,
    _collaborator_map,
    _gate_record_analysis,
    _gate_record_analysis_from_serialized,
    _gate_record_snapshot,
    _get_gate_record_or_404,
    _month_period,
    _serialize_gate_record_item,
    _team_ids_by_collaborator,
    _weekday_label,
)
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PRESENZE_CONTRACT_KIND_IMPIEGATO,
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.router import (
    _build_classification_map,
    _build_operational_quality_map,
    _serialize_daily_record_matrix,
)
from app.modules.presenze.schemas import GatePresenzeDailyRecordPatchRequest, GatePresenzeDailyRecordValidateRequest, GatePresenzeResolveAnomalyRequest
from app.modules.presenze.services.operai_rules import load_operai_rule_configs
from app.modules.presenze.services.xlsm_export import resolve_export_absence_code

OPERATOR_UPDATE_ACTION_TYPE = "propose_operator_update"
OPERATOR_UPDATE_OPERATIONS = {"create_operator", "update_operator", "update_operator_domains"}
GATE_MOBILE_CONSOLE_ROLES = {"console_admin", "device_manager", "team_manager", "viewer"}
OPERATOR_ACTIVE_STATUSES = {"ACTIVE"}
OPERATOR_DISABLED_STATUSES = {"DISABLED", "INACTIVE"}


@dataclass(frozen=True)
class GateMobileSyncReport:
    requested_tasks: list[dict[str, Any]]
    catalogs_pushed: int
    operators_pushed: int
    worksets_pushed: int
    presenze_teams_pushed: int = 0
    presenze_rules_pushed: int = 0
    presenze_months_pushed: int = 0
    presenze_giornaliere_pushed: int = 0
    presenze_anomalie_pushed: int = 0
    presenze_pending_actions_acknowledged: int = 0
    presenze_pending_actions_failed: int = 0


@dataclass(frozen=True)
class GateMobileSyncExecutionResult:
    status: str
    run_id: UUID
    report: GateMobileSyncReport | None
    error_kind: str | None = None
    error_message: str | None = None


class PendingActionApplyError(ValueError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class GateMobileConsoleEnableItem:
    operator_id: UUID
    gaia_user_id: int
    username: str
    display_name: str
    email: str
    collaborator_id: UUID
    collaborator_name: str
    contract_kind: str
    previous_role: str | None


@dataclass(frozen=True)
class GateMobileConsoleEnableResult:
    candidates_total: int
    enabled_total: int
    dry_run: bool
    role: str
    items: list[GateMobileConsoleEnableItem]


def build_mobile_operator_push_payload(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    synced_at = now or datetime.now(timezone.utc)
    rows = db.execute(
        select(WCOperator, ApplicationUser, OperatorProfile)
        .join(ApplicationUser, ApplicationUser.id == WCOperator.gaia_user_id)
        .join(OperatorProfile, OperatorProfile.user_id == ApplicationUser.id, isouter=True)
        .where(WCOperator.email.is_not(None))
        .order_by(WCOperator.last_name.asc(), WCOperator.first_name.asc(), WCOperator.email.asc())
    ).all()

    return {
        "synced_from_gaia_at": synced_at.isoformat().replace("+00:00", "Z"),
        "operators": [
            {
                "operator_id": str(operator.id),
                "gaia_user_id": str(user.id),
                "gaia_operator_profile_id": str(profile.id) if profile else None,
                "gaia_username": user.username,
                "display_name": _operator_display_name(operator, user),
                "email": operator.email or user.email,
                "phone": profile.phone if profile else user.phone_extension,
                "status": "ACTIVE" if operator.enabled and user.is_active else "DISABLED",
                "domains": operator.domains,
                "gate_mobile_console_enabled": operator.gate_mobile_console_enabled,
                "gate_mobile_console_role": operator.gate_mobile_console_role,
                "gate_mobile_console_pages": operator.gate_mobile_console_pages,
            }
            for operator, user, profile in rows
        ],
    }


def enable_gate_mobile_console_for_giornaliere_workers(
    db: Session,
    *,
    limit: int | None = 1,
    role: str = "viewer",
    dry_run: bool = True,
) -> GateMobileConsoleEnableResult:
    """Enable Gate console for WC operators linked to operai/impiegati found in giornaliere."""

    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero or None")

    rows = db.execute(
        select(WCOperator, ApplicationUser, PresenzeCollaborator)
        .join(ApplicationUser, ApplicationUser.id == WCOperator.gaia_user_id)
        .join(PresenzeCollaborator, PresenzeCollaborator.application_user_id == ApplicationUser.id)
        .join(PresenzeDailyRecord, PresenzeDailyRecord.collaborator_id == PresenzeCollaborator.id)
        .where(
            PresenzeCollaborator.contract_kind.in_(
                [PRESENZE_CONTRACT_KIND_OPERAIO, PRESENZE_CONTRACT_KIND_IMPIEGATO]
            ),
            WCOperator.email.is_not(None),
            WCOperator.enabled.is_(True),
            WCOperator.gate_mobile_console_enabled.is_(False),
            ApplicationUser.is_active.is_(True),
        )
        .order_by(PresenzeCollaborator.name.asc(), WCOperator.last_name.asc(), WCOperator.first_name.asc())
    ).all()

    candidates: list[tuple[WCOperator, ApplicationUser, PresenzeCollaborator]] = []
    seen_operator_ids: set[UUID] = set()
    for operator, user, collaborator in rows:
        if operator.id in seen_operator_ids:
            continue
        seen_operator_ids.add(operator.id)
        candidates.append((operator, user, collaborator))

    selected = candidates[:limit] if limit is not None else candidates
    items = [
        GateMobileConsoleEnableItem(
            operator_id=operator.id,
            gaia_user_id=user.id,
            username=user.username,
            display_name=_operator_display_name(operator, user),
            email=operator.email or user.email,
            collaborator_id=collaborator.id,
            collaborator_name=collaborator.name,
            contract_kind=collaborator.contract_kind or "",
            previous_role=operator.gate_mobile_console_role,
        )
        for operator, user, collaborator in selected
    ]

    if not dry_run:
        for operator, _, _ in selected:
            operator.gate_mobile_console_enabled = True
            operator.gate_mobile_console_role = role
            db.add(operator)
        db.commit()

    return GateMobileConsoleEnableResult(
        candidates_total=len(candidates),
        enabled_total=len(selected),
        dry_run=dry_run,
        role=role,
        items=items,
    )


def build_mobile_catalog_push_payloads(db: Session) -> list[dict[str, Any]]:
    response = get_mobile_catalogs(db)
    return [
        {
            "catalog_type": item.catalog_type,
            "version": item.version,
            "synced_from_gaia_at": _json_datetime(item.synced_from_gaia_at),
            "payload": item.payload,
        }
        for item in response.catalogs
    ]


def build_mobile_workset_push_payloads(db: Session) -> list[dict[str, Any]]:
    response = get_mobile_worksets(db, operator_id=None)
    return [
        {
            "operator_id": str(item.operator_id),
            "workset_type": item.workset_type,
            "synced_from_gaia_at": _json_datetime(item.synced_from_gaia_at),
            "items": [
                {
                    "gaia_entity_id": subitem.gaia_entity_id,
                    "payload": subitem.payload,
                }
                for subitem in item.items
            ],
        }
        for item in response.worksets
    ]


def build_presenze_teams_push_payload(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    synced_at = now or datetime.now(timezone.utc)
    teams = db.scalars(select(OrganizationTeam).order_by(OrganizationTeam.name.asc())).all()
    memberships = db.execute(
        select(OrganizationTeamMembership, PresenzeCollaborator)
        .join(PresenzeCollaborator, PresenzeCollaborator.id == OrganizationTeamMembership.collaborator_id)
        .order_by(OrganizationTeamMembership.team_id.asc(), PresenzeCollaborator.name.asc())
    ).all()
    supervisors = db.execute(
        select(OrganizationTeamSupervisorAssignment, ApplicationUser)
        .join(ApplicationUser, ApplicationUser.id == OrganizationTeamSupervisorAssignment.application_user_id)
        .order_by(OrganizationTeamSupervisorAssignment.team_id.asc(), ApplicationUser.username.asc())
    ).all()

    memberships_by_team: dict[str, list[dict[str, Any]]] = {}
    for membership, collaborator in memberships:
        memberships_by_team.setdefault(str(membership.team_id), []).append(
            {
                "membership_id": str(membership.id),
                "collaborator_id": str(membership.collaborator_id),
                "employee_code": collaborator.employee_code,
                "collaborator_name": collaborator.name,
                "role": membership.role,
                "valid_from": _json_date(membership.valid_from),
                "valid_to": _json_date(membership.valid_to),
                "source_channel": _gate_channel(membership.source_channel),
                "updated_at": _json_datetime(membership.updated_at),
            }
        )

    supervisors_by_team = _presenze_supervisors_by_team(db, supervisors)

    return {
        "schema_version": 1,
        "source": "gaia",
        "rules_version": RULES_VERSION,
        "synced_from_gaia_at": synced_at.isoformat().replace("+00:00", "Z"),
        "teams": [
            {
                "team_id": str(team.id),
                "name": team.name,
                "code": team.code,
                "scope": team.scope,
                "active": team.active,
                "created_from_channel": _gate_channel(team.created_from_channel),
                "created_by_user_id": team.created_by_user_id,
                "audit": {},
                "created_at": _json_datetime(team.created_at),
                "updated_at": _json_datetime(team.updated_at),
                "memberships": memberships_by_team.get(str(team.id), []),
                "supervisors": supervisors_by_team.get(str(team.id), []),
            }
            for team in teams
        ],
    }


def build_presenze_rules_push_payload(*, now: datetime | None = None) -> dict[str, Any]:
    synced_at = now or datetime.now(timezone.utc)
    rules = _build_rules_response()
    return {
        "schema_version": 1,
        "source": "gaia",
        "rules_version": RULES_VERSION,
        "export_rules_version": EXPORT_RULES_VERSION,
        "synced_from_gaia_at": synced_at.isoformat().replace("+00:00", "Z"),
        "rules": rules.model_dump(mode="json"),
    }


def build_presenze_months_push_payload(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    synced_at = now or datetime.now(timezone.utc)
    counts: dict[str, int] = {}
    for work_date in db.scalars(select(PresenzeDailyRecord.work_date)).all():
        month = work_date.strftime("%Y-%m")
        counts[month] = counts.get(month, 0) + 1
    return {
        "schema_version": 1,
        "source": "gaia",
        "rules_version": RULES_VERSION,
        "synced_from_gaia_at": synced_at.isoformat().replace("+00:00", "Z"),
        "months": [{"month": month, "records_total": counts[month]} for month in sorted(counts)],
    }


def build_presenze_giornaliere_push_payload(db: Session, *, month: str, now: datetime | None = None) -> dict[str, Any]:
    record_items, _ = _presenze_mobile_record_items_for_month(db, month=month)
    return {
        "schema_version": 1,
        "source": "gaia",
        "month": month,
        "rules_version": RULES_VERSION,
        "export_rules_version": EXPORT_RULES_VERSION,
        "synced_from_gaia_at": _json_datetime(now or datetime.now(timezone.utc)),
        "records": record_items,
        "giornaliere": record_items,
    }


def build_presenze_anomalie_push_payload(db: Session, *, month: str, now: datetime | None = None) -> dict[str, Any]:
    synced_at = now or datetime.now(timezone.utc)
    record_items, analyses_by_record_id = _presenze_mobile_record_items_for_month(db, month=month)
    anomalies: list[dict[str, Any]] = []
    for item in record_items:
        analysis = analyses_by_record_id.get(item["record_id"])
        if analysis is None:
            continue
        if analysis.severity == "none":
            continue
        anomalies.append(
            {
                **item,
                "reasons": analysis.reasons,
                "operator_message": analysis.operator_message,
            }
        )
    return {
        "schema_version": 1,
        "source": "gaia",
        "month": month,
        "rules_version": RULES_VERSION,
        "synced_from_gaia_at": synced_at.isoformat().replace("+00:00", "Z"),
        "anomalies": anomalies,
        "anomalie": anomalies,
    }


def _presenze_mobile_record_items_for_month(
    db: Session,
    *,
    month: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    period_start, period_end = _month_period(month)
    records = _presenze_records_for_period(db, period_start=period_start, period_end=period_end)
    if not records:
        return [], {}

    collaborators = _collaborator_map(db, [record.collaborator_id for record in records])
    team_ids_by_collaborator = _team_ids_by_collaborator(
        db,
        [record.collaborator_id for record in records],
        period_start=period_start,
        period_end=period_end,
    )
    punches_by_record_id = _presenze_punches_by_record_id(db, records)
    classification_by_record_id = _build_classification_map(db, records, punches_by_record_id=punches_by_record_id)
    operai_rule_configs = load_operai_rule_configs(db)
    operational_quality_by_record_id = _build_operational_quality_map(
        db,
        records,
        punches_by_record_id=punches_by_record_id,
        classifications=classification_by_record_id,
        operai_rule_configs=operai_rule_configs,
    )

    record_items: list[dict[str, Any]] = []
    analyses_by_record_id: dict[str, Any] = {}
    for record in records:
        collaborator = collaborators.get(record.collaborator_id)
        serialized = _serialize_daily_record_matrix(
            record,
            classification=classification_by_record_id.get(record.id),
            operational_quality=operational_quality_by_record_id.get(record.id),
            operai_rule_configs=operai_rule_configs,
        )
        analysis = _gate_record_analysis_from_serialized(record, serialized)
        record_id = str(record.id)
        analyses_by_record_id[record_id] = analysis
        record_items.append(
            {
                **_presenze_mobile_record_payload(
                    record,
                    collaborator=collaborator,
                    team_ids=team_ids_by_collaborator.get(record.collaborator_id, []),
                    serialized=serialized,
                    severity=analysis.severity,
                    classification=classification_by_record_id[record.id],
                ),
                "has_complete_punches": _has_complete_punches(punches_by_record_id.get(record.id, [])),
            }
        )
    return record_items, analyses_by_record_id


def _presenze_supervisors_by_team(
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
                "valid_from": _json_date(supervisor.valid_from),
                "valid_to": _json_date(supervisor.valid_to),
                "source_channel": _gate_channel(supervisor.source_channel),
                "updated_at": _json_datetime(supervisor.updated_at),
            }
        )
    return result


def _presenze_mobile_record_payload(
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
        "work_date": _json_date(record.work_date),
        "weekday": _weekday_label(record.work_date),
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
        "validated_at": _json_datetime(record.validated_at) if record.validated_at is not None else None,
        "validated_by_user_id": record.validated_by_user_id,
        **_gate_record_feature_values(record, serialized=serialized, classification=classification),
    }


def _gate_record_feature_values(record: PresenzeDailyRecord, *, serialized, classification) -> dict[str, Any]:
    return {
        "km_value": record.km_value,
        "trasferta_minutes": record.trasferta_minutes,
        "trasferta_montano": record.trasferta_montano,
        "reperibilita_unit": record.reperibilita_unit,
        "reperibilita_quantity": record.reperibilita_quantity,
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


def _presenze_punches_by_record_id(
    db: Session,
    records: list[PresenzeDailyRecord],
) -> dict[UUID, list[PresenzeDailyPunch]]:
    if not records:
        return {}
    punches = db.scalars(
        select(PresenzeDailyPunch)
        .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in records]))
        .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
    ).all()
    punches_by_record_id: dict[UUID, list[PresenzeDailyPunch]] = {}
    for punch in punches:
        punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    return punches_by_record_id


def _has_complete_punches(punches: list[PresenzeDailyPunch]) -> bool:
    return bool(punches) and all(punch.entry_time is not None and punch.exit_time is not None for punch in punches)


async def run_gate_mobile_sync_once(
    db: Session,
    *,
    app_settings: Settings = settings,
    client: httpx.AsyncClient | None = None,
) -> GateMobileSyncReport:
    base_url = app_settings.gate_mobile_gateway_base_url.rstrip("/")
    token = app_settings.gate_mobile_connector_token
    if not base_url:
        raise RuntimeError("GATE_MOBILE_GATEWAY_BASE_URL non configurato")
    if not token:
        raise RuntimeError("GATE_MOBILE_CONNECTOR_TOKEN non configurato")

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(base_url=base_url, timeout=app_settings.gate_mobile_sync_timeout_seconds)

    try:
        headers = {"Authorization": f"Bearer {token}"}
        tasks = await _fetch_sync_plan_tasks(client, headers=headers)

        catalogs_pushed = 0
        for payload in build_mobile_catalog_push_payloads(db):
            push_response = await client.post(
                "/api/mobile/connector/catalogs/push",
                json=payload,
                headers=headers,
            )
            push_response.raise_for_status()
            catalogs_pushed += 1

        operators_pushed = 0
        if any(task.get("type") == "operators" for task in tasks):
            payload = build_mobile_operator_push_payload(db)
            push_response = await client.post(
                "/api/mobile/connector/operators/push",
                json=payload,
                headers=headers,
            )
            push_response.raise_for_status()
            operators_pushed = int(push_response.json().get("operators", {}).get("count", len(payload["operators"])))

        worksets_pushed = 0
        for payload in build_mobile_workset_push_payloads(db):
            push_response = await client.post(
                "/api/mobile/connector/worksets/push",
                json=payload,
                headers=headers,
            )
            push_response.raise_for_status()
            worksets_pushed += 1

        presenze_teams_pushed = 0
        if any(task.get("type") == "presenze_teams" for task in tasks):
            payload = build_presenze_teams_push_payload(db)
            push_response = await client.post(
                "/api/mobile/connector/presenze/teams/snapshot",
                json=payload,
                headers=headers,
            )
            push_response.raise_for_status()
            presenze_teams_pushed = int(push_response.json().get("teams", {}).get("count", len(payload["teams"])))

        presenze_rules_pushed = 0
        if any(task.get("type") == "presenze_rules" for task in tasks):
            push_response = await client.post(
                "/api/mobile/connector/presenze/rules/snapshot",
                json=build_presenze_rules_push_payload(),
                headers=headers,
            )
            push_response.raise_for_status()
            presenze_rules_pushed = 1

        presenze_months_pushed = 0
        if any(task.get("type") == "presenze_months" for task in tasks):
            push_response = await client.post(
                "/api/mobile/connector/presenze/months/snapshot",
                json=build_presenze_months_push_payload(db),
                headers=headers,
            )
            push_response.raise_for_status()
            presenze_months_pushed = 1

        presenze_giornaliere_pushed = 0
        for task in [item for item in tasks if item.get("type") == "presenze_giornaliere"]:
            for month in _task_months(task):
                payload = build_presenze_giornaliere_push_payload(db, month=month)
                push_response = await client.post(
                    "/api/mobile/connector/presenze/giornaliere/snapshot",
                    json=payload,
                    headers=headers,
                )
                push_response.raise_for_status()
                presenze_giornaliere_pushed += int(push_response.json().get("records", {}).get("count", len(payload["records"])))

        presenze_anomalie_pushed = 0
        for task in [item for item in tasks if item.get("type") == "presenze_anomalie"]:
            for month in _task_months(task):
                payload = build_presenze_anomalie_push_payload(db, month=month)
                push_response = await client.post(
                    "/api/mobile/connector/presenze/anomalie/snapshot",
                    json=payload,
                    headers=headers,
                )
                push_response.raise_for_status()
                presenze_anomalie_pushed += int(push_response.json().get("anomalies", {}).get("count", len(payload["anomalies"])))

        pending_actions_acknowledged = 0
        pending_actions_failed = 0
        if any(task.get("type") in {"presenze_pending_actions", "pending_actions"} for task in tasks):
            pending_result = await process_presenze_pending_actions(db, client=client, headers=headers)
            pending_actions_acknowledged = pending_result["acknowledged"]
            pending_actions_failed = pending_result["failed"]

        return GateMobileSyncReport(
            requested_tasks=tasks,
            catalogs_pushed=catalogs_pushed,
            operators_pushed=operators_pushed,
            worksets_pushed=worksets_pushed,
            presenze_teams_pushed=presenze_teams_pushed,
            presenze_rules_pushed=presenze_rules_pushed,
            presenze_months_pushed=presenze_months_pushed,
            presenze_giornaliere_pushed=presenze_giornaliere_pushed,
            presenze_anomalie_pushed=presenze_anomalie_pushed,
            presenze_pending_actions_acknowledged=pending_actions_acknowledged,
            presenze_pending_actions_failed=pending_actions_failed,
        )
    finally:
        if owns_client:
            await client.aclose()


async def execute_gate_mobile_sync(
    db: Session,
    *,
    app_settings: Settings = settings,
    client: httpx.AsyncClient | None = None,
    trigger_source: str = "manual_cli",
    raise_on_error: bool = True,
) -> GateMobileSyncExecutionResult:
    started_at = datetime.now(timezone.utc)
    run = GateMobileSyncRun(
        trigger_source=trigger_source,
        status="running",
        requested_tasks_count=0,
        operators_pushed=0,
        started_at=started_at,
    )
    db.add(run)
    db.flush()

    if not app_settings.gate_mobile_sync_enabled:
        return _finalize_run(
            db,
            run=run,
            status="skipped",
            started_at=started_at,
            error_kind="disabled",
            error_message="GATE_MOBILE_SYNC_ENABLED=false",
        )

    try:
        report = await run_gate_mobile_sync_once(db, app_settings=app_settings, client=client)
    except RuntimeError as exc:
        return _finalize_run(
            db,
            run=run,
            status="failed",
            started_at=started_at,
            error_kind="configuration_error",
            error_message=str(exc),
            exc=exc,
            raise_on_error=raise_on_error,
        )
    except httpx.HTTPStatusError as exc:
        return _finalize_run(
            db,
            run=run,
            status="failed",
            started_at=started_at,
            error_kind="http_status_error",
            error_message=(
                f"status={exc.response.status_code} method={exc.request.method} path={exc.request.url.path}"
            ),
            exc=exc,
            raise_on_error=raise_on_error,
        )
    except httpx.HTTPError as exc:
        return _finalize_run(
            db,
            run=run,
            status="failed",
            started_at=started_at,
            error_kind="transport_error",
            error_message=str(exc),
            exc=exc,
            raise_on_error=raise_on_error,
        )
    except Exception as exc:
        return _finalize_run(
            db,
            run=run,
            status="failed",
            started_at=started_at,
            error_kind="unexpected_error",
            error_message=str(exc),
            exc=exc,
            raise_on_error=raise_on_error,
        )

    return _finalize_run(
        db,
        run=run,
        status="succeeded",
        started_at=started_at,
        report=report,
    )


def get_gate_mobile_sync_status(db: Session, *, app_settings: Settings = settings, recent_limit: int = 10) -> dict[str, Any]:
    recent_runs = db.scalars(
        select(GateMobileSyncRun).order_by(GateMobileSyncRun.started_at.desc()).limit(recent_limit)
    ).all()
    latest_run = recent_runs[0] if recent_runs else None
    return {
        "sync_enabled": app_settings.gate_mobile_sync_enabled,
        "gateway_base_url": app_settings.gate_mobile_gateway_base_url.rstrip("/") or None,
        "gateway_configured": bool(app_settings.gate_mobile_gateway_base_url.strip()),
        "token_configured": bool(app_settings.gate_mobile_connector_token.strip()),
        "timeout_seconds": app_settings.gate_mobile_sync_timeout_seconds,
        "outbound_scope": [
            "catalogs",
            "operators",
            "worksets",
            "presenze_teams",
            "presenze_months",
            "presenze_giornaliere",
            "presenze_anomalie",
            "presenze_rules",
            "presenze_pending_actions",
        ],
        "internal_connector_api": {
            "path_prefix": "/api/mobile-sync",
            "auth_header": app_settings.mobile_connector_header_name,
        },
        "last_run": _serialize_run(latest_run),
        "recent_runs": [_serialize_run(item) for item in recent_runs],
    }


def get_running_gate_mobile_sync_run(db: Session) -> GateMobileSyncRun | None:
    return db.scalars(
        select(GateMobileSyncRun)
        .where(GateMobileSyncRun.status == "running")
        .order_by(GateMobileSyncRun.started_at.desc())
        .limit(1)
    ).first()


async def process_presenze_pending_actions(db: Session, *, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, int]:
    response = await client.get("/api/mobile/connector/presenze/pending-actions", headers=headers)
    response.raise_for_status()
    payload = response.json()
    actions = payload if isinstance(payload, list) else payload.get("actions", [])
    acknowledged = 0
    failed = 0
    for action in [item for item in actions if isinstance(item, dict)]:
        action_id = _pending_action_id(action)
        try:
            result = _apply_presenze_pending_action(db, action)
        except PendingActionApplyError as exc:
            db.rollback()
            await _fail_pending_action(client, headers=headers, action_id=action_id, message=str(exc), retryable=exc.retryable)
            failed += 1
            continue
        except ValueError as exc:
            db.rollback()
            await _fail_pending_action(client, headers=headers, action_id=action_id, message=str(exc), retryable=False)
            failed += 1
            continue
        except SQLAlchemyError as exc:
            db.rollback()
            await _fail_pending_action(client, headers=headers, action_id=action_id, message=str(exc), retryable=True)
            failed += 1
            continue
        except Exception as exc:
            db.rollback()
            await _fail_pending_action(client, headers=headers, action_id=action_id, message=str(exc), retryable=True)
            failed += 1
            continue
        ack_response = await client.post(
            f"/api/mobile/connector/presenze/pending-actions/{action_id}/ack",
            json=result,
            headers=headers,
        )
        ack_response.raise_for_status()
        acknowledged += 1
    return {"acknowledged": acknowledged, "failed": failed}


def _apply_presenze_pending_action(db: Session, action: dict[str, Any]) -> dict[str, Any]:
    action_type = action.get("type") or action.get("action_type")
    action_id = _pending_action_id(action)
    payload = _pending_action_payload(action)
    if action_type == OPERATOR_UPDATE_ACTION_TYPE:
        operator = _apply_operator_update_proposal(db, payload)
        return _ack_payload("wc_operator", operator.id, action_id=action_id)
    actor = _pending_action_user(db, payload)
    if action_type == "validate_daily_record":
        record = _pending_action_record(db, payload, actor)
        request = GatePresenzeDailyRecordValidateRequest.model_validate(payload)
        before = _gate_record_snapshot(record)
        record.validation_status = request.validation_status
        record.validation_note = request.operator_note
        if request.validation_status == "validated":
            record.validated_by_user_id = actor.id
            record.validated_at = datetime.now(timezone.utc)
        else:
            record.validated_by_user_id = None
            record.validated_at = None
        _append_gate_audit(
            record,
            action="validate",
            current_user=actor,
            operator_note=request.operator_note,
            client_request_id=request.client_request_id or action_id,
            before=before,
            after=_gate_record_snapshot(record),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return _ack_payload("presenze_daily_record", record.id, action_id=action_id)
    if action_type == "patch_daily_record":
        record = _pending_action_record(db, payload, actor)
        request = GatePresenzeDailyRecordPatchRequest.model_validate(payload)
        before = _gate_record_snapshot(record)
        patch_data = request.model_dump(exclude_unset=True, exclude={"operator_note", "client_request_id"})
        for field, value in patch_data.items():
            setattr(record, field, value)
        _append_gate_audit(
            record,
            action="patch",
            current_user=actor,
            operator_note=request.operator_note,
            client_request_id=request.client_request_id or action_id,
            before=before,
            after=_gate_record_snapshot(record),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return _ack_payload("presenze_daily_record", record.id, action_id=action_id)
    if action_type == "resolve_anomaly":
        record = _pending_action_record(db, payload, actor)
        request = GatePresenzeResolveAnomalyRequest.model_validate(payload)
        before = _gate_record_snapshot(record)
        record.validation_status = "validated"
        record.validation_note = request.operator_note
        record.validated_by_user_id = actor.id
        record.validated_at = datetime.now(timezone.utc)
        _append_gate_audit(
            record,
            action="resolve_anomaly",
            current_user=actor,
            operator_note=request.operator_note,
            client_request_id=request.client_request_id or action_id,
            before=before,
            after=_gate_record_snapshot(record),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return _ack_payload("presenze_daily_record", record.id, action_id=action_id)
    if action_type == "propose_team_change":
        raise PendingActionApplyError("propose_team_change non e ancora applicabile automaticamente: serve revisione GAIA")
    raise ValueError(f"Tipo pending action non supportato: {action_type}")


def _pending_action_payload(action: dict[str, Any]) -> dict[str, Any]:
    raw_payload = action.get("payload_json")
    if raw_payload is None:
        raw_payload = action.get("payload") if isinstance(action.get("payload"), (dict, str)) else action
    if isinstance(raw_payload, str):
        try:
            raw_payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise PendingActionApplyError("payload_json non e un JSON valido") from exc
    if not isinstance(raw_payload, dict):
        raise PendingActionApplyError("payload_json deve essere un oggetto JSON")
    return raw_payload


def _apply_operator_update_proposal(db: Session, payload: dict[str, Any]) -> WCOperator:
    _validate_operator_update_envelope(payload)
    operator_payload = payload["operator"]
    operator_id = _required_uuid(operator_payload, "operator_id")
    operation = str(payload["operation"])
    operator = db.get(WCOperator, operator_id)

    if operator is None:
        if operation != "create_operator":
            raise PendingActionApplyError(f"Operatore GAIA {operator_id} non trovato per {operation}")
        operator = WCOperator(id=operator_id, wc_id=_synthetic_wc_id(db, operator_id))
        db.add(operator)

    user = _resolve_operator_gaia_user(db, operator_payload)
    profile = _resolve_operator_profile(db, operator_payload, user)

    _apply_operator_identity_fields(db, operator, user, profile, operator_payload)
    _apply_operator_console_fields(operator, operator_payload)

    db.add(operator)
    if user is not None:
        db.add(user)
    if profile is not None:
        db.add(profile)
    db.commit()
    db.refresh(operator)
    return operator


def _validate_operator_update_envelope(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 1:
        raise PendingActionApplyError("schema_version non supportata per propose_operator_update")
    if payload.get("source") != "gate_admin_console":
        raise PendingActionApplyError("source non supportata per propose_operator_update")
    if payload.get("operation") not in OPERATOR_UPDATE_OPERATIONS:
        raise PendingActionApplyError("operation non supportata per propose_operator_update")
    if not isinstance(payload.get("operator"), dict):
        raise PendingActionApplyError("operator mancante o non valido in propose_operator_update")
    changed_fields = payload.get("changed_fields")
    if changed_fields is not None and not _is_string_list(changed_fields):
        raise PendingActionApplyError("changed_fields deve essere una lista di stringhe")
    password_changed = payload.get("password_changed")
    if password_changed is not None and not isinstance(password_changed, bool):
        raise PendingActionApplyError("password_changed deve essere booleano")


def _resolve_operator_gaia_user(db: Session, operator_payload: dict[str, Any]) -> ApplicationUser | None:
    user_id = operator_payload.get("gaia_user_id")
    if user_id is None:
        return None
    try:
        parsed_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise PendingActionApplyError("gaia_user_id non valido") from exc
    user = db.get(ApplicationUser, parsed_id)
    if user is None:
        raise PendingActionApplyError(f"Application user {parsed_id} non trovato")
    return user


def _resolve_operator_profile(
    db: Session,
    operator_payload: dict[str, Any],
    user: ApplicationUser | None,
) -> OperatorProfile | None:
    profile_id = operator_payload.get("gaia_operator_profile_id")
    if profile_id is not None:
        parsed_id = _parse_uuid(profile_id, "gaia_operator_profile_id")
        profile = db.get(OperatorProfile, parsed_id)
        if profile is None:
            raise PendingActionApplyError(f"Operator profile {parsed_id} non trovato")
        if user is not None and profile.user_id != user.id:
            raise PendingActionApplyError("gaia_operator_profile_id non appartiene al gaia_user_id indicato")
        return profile
    if user is None:
        return None
    return db.scalar(select(OperatorProfile).where(OperatorProfile.user_id == user.id))


def _apply_operator_identity_fields(
    db: Session,
    operator: WCOperator,
    user: ApplicationUser | None,
    profile: OperatorProfile | None,
    operator_payload: dict[str, Any],
) -> None:
    if "gaia_user_id" in operator_payload:
        operator.gaia_user_id = user.id if user is not None else None
    if "display_name" in operator_payload:
        display_name = _optional_text(operator_payload["display_name"], "display_name")
        if user is not None:
            user.full_name = display_name
        first_name, last_name = _split_display_name(display_name)
        operator.first_name = first_name
        operator.last_name = last_name
    if "email" in operator_payload:
        email = _optional_email(operator_payload["email"])
        _validate_unique_user_email(db, email, user)
        operator.email = email
        if user is not None and email is not None:
            user.email = email
    if "gaia_username" in operator_payload:
        username = _optional_text(operator_payload["gaia_username"], "gaia_username")
        _validate_unique_username(db, username, user)
        operator.username = username
        if user is not None and username is not None:
            user.username = username
    if "phone" in operator_payload:
        phone = _optional_text(operator_payload["phone"], "phone")
        if profile is not None:
            profile.phone = phone
        elif user is not None:
            user.phone_extension = phone
    if "status" in operator_payload:
        status = str(operator_payload["status"]).strip().upper()
        if status in OPERATOR_ACTIVE_STATUSES:
            operator.enabled = True
            if user is not None:
                user.is_active = True
        elif status in OPERATOR_DISABLED_STATUSES:
            operator.enabled = False
            if user is not None:
                user.is_active = False
        else:
            raise PendingActionApplyError(f"status operatore non supportato: {operator_payload['status']}")


def _apply_operator_console_fields(operator: WCOperator, operator_payload: dict[str, Any]) -> None:
    if "domains" in operator_payload:
        domains = operator_payload["domains"]
        if domains is not None and not _is_string_list(domains):
            raise PendingActionApplyError("operator.domains deve essere una lista di stringhe")
        operator.domains = _normalize_string_list(domains)
    if "gate_mobile_console_enabled" in operator_payload:
        enabled = operator_payload["gate_mobile_console_enabled"]
        if not isinstance(enabled, bool):
            raise PendingActionApplyError("gate_mobile_console_enabled deve essere booleano")
        operator.gate_mobile_console_enabled = enabled
    if "gate_mobile_console_role" in operator_payload:
        role = operator_payload["gate_mobile_console_role"]
        if role is not None:
            role = str(role).strip()
            if role not in GATE_MOBILE_CONSOLE_ROLES:
                raise PendingActionApplyError(f"gate_mobile_console_role non supportato: {role}")
        operator.gate_mobile_console_role = role
    if operator.gate_mobile_console_enabled and not operator.gate_mobile_console_role:
        raise PendingActionApplyError("gate_mobile_console_role richiesto quando la console e abilitata")
    if not operator.gate_mobile_console_enabled:
        operator.gate_mobile_console_role = None
    if "gate_mobile_console_pages" in operator_payload:
        pages = operator_payload["gate_mobile_console_pages"]
        if pages is not None and not _is_string_list(pages):
            raise PendingActionApplyError("gate_mobile_console_pages deve essere una lista di stringhe")
        operator.gate_mobile_console_pages = _normalize_string_list(pages)


def _required_uuid(payload: dict[str, Any], field: str) -> UUID:
    if payload.get(field) is None:
        raise PendingActionApplyError(f"{field} mancante in propose_operator_update")
    return _parse_uuid(payload[field], field)


def _parse_uuid(value: Any, field: str) -> UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise PendingActionApplyError(f"{field} non e un UUID valido") from exc


def _synthetic_wc_id(db: Session, operator_id: UUID) -> int:
    candidate = -((operator_id.int % 2_000_000_000) + 1)
    while db.scalar(select(WCOperator.id).where(WCOperator.wc_id == candidate, WCOperator.id != operator_id)) is not None:
        candidate -= 1
    return candidate


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise PendingActionApplyError(f"{field} non puo essere vuoto")
    return text


def _optional_email(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return normalize_email(str(value))
    except ValueError as exc:
        raise PendingActionApplyError("email operatore non valida") from exc


def _split_display_name(display_name: str | None) -> tuple[str | None, str | None]:
    if display_name is None:
        return None, None
    parts = display_name.split()
    if len(parts) == 1:
        return parts[0], None
    return " ".join(parts[:-1]), parts[-1]


def _validate_unique_user_email(db: Session, email: str | None, user: ApplicationUser | None) -> None:
    if email is None:
        return
    existing = db.scalar(select(ApplicationUser).where(ApplicationUser.email == email))
    if existing is not None and (user is None or existing.id != user.id):
        raise PendingActionApplyError(f"email gia assegnata a un altro utente GAIA: {email}")


def _validate_unique_username(db: Session, username: str | None, user: ApplicationUser | None) -> None:
    if username is None:
        return
    existing = db.scalar(select(ApplicationUser).where(ApplicationUser.username == username))
    if existing is not None and (user is None or existing.id != user.id):
        raise PendingActionApplyError(f"username gia assegnato a un altro utente GAIA: {username}")


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _normalize_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    normalized: list[str] = []
    for item in value:
        text = item.strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


async def _fail_pending_action(
    client: httpx.AsyncClient,
    *,
    headers: dict[str, str],
    action_id: str,
    message: str,
    retryable: bool,
) -> None:
    response = await client.post(
        f"/api/mobile/connector/presenze/pending-actions/{action_id}/fail",
        json={
            "failure_type": "validation",
            "error_code": "GAIA_PRESENZE_VALIDATION_ERROR",
            "message": message,
            "retryable": retryable,
            "details": {},
        },
        headers=headers,
    )
    response.raise_for_status()


def _pending_action_id(action: dict[str, Any]) -> str:
    value = action.get("id") or action.get("pending_action_id") or action.get("cloud_event_id") or action.get("client_request_id")
    if value is None:
        return str(uuid.uuid4())
    return str(value)


def _pending_action_user(db: Session, payload: dict[str, Any]) -> ApplicationUser:
    user_id = payload.get("application_user_id") or payload.get("user_id")
    if user_id is None and isinstance(payload.get("actor"), dict):
        user_id = payload["actor"].get("application_user_id") or payload["actor"].get("user_id")
    if user_id is None:
        raise ValueError("application_user_id mancante nella pending action")
    user = db.get(ApplicationUser, int(user_id))
    if user is None or not user.is_active:
        raise ValueError("Application user not found")
    if not user.module_presenze and not user.is_super_admin:
        raise ValueError("Utente non abilitato al modulo Presenze")
    return user


def _pending_action_record(db: Session, payload: dict[str, Any], actor: ApplicationUser) -> PresenzeDailyRecord:
    record_id = payload.get("record_id") or payload.get("daily_record_id")
    if record_id is None:
        raise ValueError("record_id mancante nella pending action")
    return _get_gate_record_or_404(db, actor, _current_pending_action_record_id(db, payload, record_id))


def _current_pending_action_record_id(db: Session, payload: dict[str, Any], record_id: Any) -> uuid.UUID:
    record_id = uuid.UUID(str(record_id))
    record = db.get(PresenzeDailyRecord, record_id)
    if record is None and payload.get("collaborator_id") is not None and payload.get("work_date") is not None:
        record = db.execute(
            select(PresenzeDailyRecord).where(
                PresenzeDailyRecord.collaborator_id == uuid.UUID(str(payload["collaborator_id"])),
                PresenzeDailyRecord.work_date == date.fromisoformat(str(payload["work_date"])),
            )
        ).scalar_one_or_none()
    return record.id if record is not None else record_id


def _ack_payload(entity_type: str, entity_id: Any, *, action_id: str) -> dict[str, Any]:
    return {
        "gaia_entity_type": entity_type,
        "gaia_entity_id": str(entity_id),
        "extra": {
            "pending_action_id": action_id,
            "rules_version": RULES_VERSION,
            "applied_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    }


def _task_months(task: dict[str, Any]) -> list[str]:
    if isinstance(task.get("months"), list) and task["months"]:
        return [str(month) for month in task["months"]]
    if task.get("month"):
        return [str(task["month"])]
    today = date.today()
    current = today.strftime("%Y-%m")
    previous_year = today.year if today.month > 1 else today.year - 1
    previous_month = today.month - 1 if today.month > 1 else 12
    previous = f"{previous_year:04d}-{previous_month:02d}"
    return [current, previous]


async def _fetch_sync_plan_tasks(client: httpx.AsyncClient, *, headers: dict[str, str]) -> list[dict[str, Any]]:
    full_capabilities = [
        "operators",
        "presenze_teams",
        "presenze_months",
        "presenze_giornaliere",
        "presenze_anomalie",
        "presenze_rules",
        "presenze_pending_actions",
    ]
    plan_response = await client.post(
        "/api/mobile/connector/sync/plan",
        json={"connector_id": "gaia", "capabilities": full_capabilities},
        headers=headers,
    )
    if plan_response.status_code != 400:
        plan_response.raise_for_status()
        return _sync_plan_tasks(plan_response)

    legacy_response = await client.post(
        "/api/mobile/connector/sync/plan",
        json={"connector_id": "gaia", "capabilities": ["operators", "presenze_teams"]},
        headers=headers,
    )
    legacy_response.raise_for_status()
    return _with_default_presenze_snapshot_tasks(_sync_plan_tasks(legacy_response))


def _sync_plan_tasks(response: httpx.Response) -> list[dict[str, Any]]:
    tasks = response.json().get("plan", {}).get("tasks", [])
    return [task for task in tasks if isinstance(task, dict)]


def _with_default_presenze_snapshot_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    task_types = {str(task.get("type")) for task in tasks}
    defaults = [
        {"type": "presenze_rules"},
        {"type": "presenze_months"},
        {"type": "presenze_giornaliere", "months": _task_months({})},
        {"type": "presenze_anomalie", "months": _task_months({})},
        {"type": "presenze_pending_actions"},
    ]
    return [*tasks, *[task for task in defaults if task["type"] not in task_types]]


def _presenze_records_for_period(db: Session, *, period_start: date, period_end: date) -> list[PresenzeDailyRecord]:
    return db.scalars(
        select(PresenzeDailyRecord)
        .where(PresenzeDailyRecord.work_date >= period_start, PresenzeDailyRecord.work_date <= period_end)
        .order_by(PresenzeDailyRecord.work_date.asc(), PresenzeDailyRecord.collaborator_id.asc())
    ).all()


def _json_datetime(value: datetime | None) -> str:
    fallback = value or datetime.now(timezone.utc)
    return fallback.isoformat().replace("+00:00", "Z")


def _json_date(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _gate_channel(value: str | None) -> str:
    if value in {"gaia_web", "gaia"}:
        return "gaia"
    if value in {"gate_mobile", "gate"}:
        return "gate"
    return value or "gaia"


def _serialize_run(run: GateMobileSyncRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "id": str(run.id),
        "trigger_source": run.trigger_source,
        "status": run.status,
        "requested_tasks_count": run.requested_tasks_count,
        "operators_pushed": run.operators_pushed,
        "duration_ms": run.duration_ms,
        "requested_tasks": run.requested_tasks_json or [],
        "error_kind": run.error_kind,
        "error_message": run.error_message,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def _finalize_run(
    db: Session,
    *,
    run: GateMobileSyncRun,
    status: str,
    started_at: datetime,
    report: GateMobileSyncReport | None = None,
    error_kind: str | None = None,
    error_message: str | None = None,
    exc: Exception | None = None,
    raise_on_error: bool = True,
) -> GateMobileSyncExecutionResult:
    finished_at = datetime.now(timezone.utc)
    run.status = status
    run.finished_at = finished_at
    run.duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
    run.error_kind = error_kind
    run.error_message = error_message
    run.requested_tasks_count = len(report.requested_tasks) if report is not None else 0
    run.operators_pushed = report.operators_pushed if report is not None else 0
    run.requested_tasks_json = report.requested_tasks if report is not None else None
    db.commit()
    db.refresh(run)
    result = GateMobileSyncExecutionResult(
        status=status,
        run_id=run.id,
        report=report,
        error_kind=error_kind,
        error_message=error_message,
    )
    if exc is not None and raise_on_error:
        raise exc
    return result


def _operator_display_name(operator: WCOperator, user: ApplicationUser) -> str:
    parts = [operator.first_name, operator.last_name]
    name = " ".join(part.strip() for part in parts if part and part.strip()).strip()
    if name:
        return name
    if user.full_name and user.full_name.strip():
        return user.full_name.strip()
    if user.username:
        return user.username
    if operator.username:
        return operator.username
    return str(operator.id)
