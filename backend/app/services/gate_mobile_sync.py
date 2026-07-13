from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.application_user import ApplicationUser
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
    _gate_record_snapshot,
    _get_gate_record_or_404,
    _month_period,
    _serialize_gate_record_item,
    _team_ids_by_collaborator,
)
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PresenzeCollaborator,
    PresenzeDailyRecord,
)
from app.modules.presenze.schemas import GatePresenzeDailyRecordPatchRequest, GatePresenzeDailyRecordValidateRequest, GatePresenzeResolveAnomalyRequest


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
            }
            for operator, user, profile in rows
        ],
    }


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

    supervisors_by_team: dict[str, list[dict[str, Any]]] = {}
    for supervisor, user in supervisors:
        supervisors_by_team.setdefault(str(supervisor.team_id), []).append(
            {
                "supervisor_assignment_id": str(supervisor.id),
                "application_user_id": supervisor.application_user_id,
                "username": user.username,
                "user_label": user.full_name or user.username,
                "permission_scope": supervisor.permission_scope,
                "valid_from": _json_date(supervisor.valid_from),
                "valid_to": _json_date(supervisor.valid_to),
                "source_channel": _gate_channel(supervisor.source_channel),
                "updated_at": _json_datetime(supervisor.updated_at),
            }
        )

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
    synced_at = now or datetime.now(timezone.utc)
    period_start, period_end = _month_period(month)
    records = _presenze_records_for_period(db, period_start=period_start, period_end=period_end)
    collaborators = _collaborator_map(db, [record.collaborator_id for record in records])
    team_ids_by_collaborator = _team_ids_by_collaborator(
        db,
        [record.collaborator_id for record in records],
        period_start=period_start,
        period_end=period_end,
    )
    record_items = [
        _serialize_gate_record_item(
            db,
            record,
            collaborator=collaborators.get(record.collaborator_id),
            team_ids=team_ids_by_collaborator.get(record.collaborator_id, []),
        ).model_dump(mode="json")
        for record in records
    ]
    return {
        "schema_version": 1,
        "source": "gaia",
        "month": month,
        "rules_version": RULES_VERSION,
        "synced_from_gaia_at": synced_at.isoformat().replace("+00:00", "Z"),
        "records": record_items,
        "giornaliere": record_items,
    }


def build_presenze_anomalie_push_payload(db: Session, *, month: str, now: datetime | None = None) -> dict[str, Any]:
    synced_at = now or datetime.now(timezone.utc)
    giornaliere_payload = build_presenze_giornaliere_push_payload(db, month=month, now=synced_at)
    record_map = {
        str(record.id): record
        for record in _presenze_records_for_period(db, period_start=_month_period(month)[0], period_end=_month_period(month)[1])
    }
    anomalies: list[dict[str, Any]] = []
    for item in giornaliere_payload["records"]:
        record = record_map.get(item["record_id"])
        if record is None:
            continue
        analysis = _gate_record_analysis(db, record)
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
        except Exception as exc:
            await _fail_pending_action(client, headers=headers, action_id=action_id, message=str(exc), retryable=False)
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
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else action
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
        raise ValueError("propose_team_change non e ancora applicabile automaticamente: serve revisione GAIA")
    raise ValueError(f"Tipo pending action non supportato: {action_type}")


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
    return _get_gate_record_or_404(db, actor, uuid.UUID(str(record_id)))


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
