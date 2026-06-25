from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileSyncRun
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.routes.mobile_sync import get_mobile_catalogs, get_mobile_worksets


@dataclass(frozen=True)
class GateMobileSyncReport:
    requested_tasks: list[dict[str, Any]]
    catalogs_pushed: int
    operators_pushed: int
    worksets_pushed: int


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
    response = get_mobile_worksets(db)
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
        plan_response = await client.post(
            "/api/mobile/connector/sync/plan",
            json={"connector_id": "gaia", "capabilities": ["operators"]},
            headers=headers,
        )
        plan_response.raise_for_status()
        tasks = plan_response.json().get("plan", {}).get("tasks", [])

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

        return GateMobileSyncReport(
            requested_tasks=tasks,
            catalogs_pushed=catalogs_pushed,
            operators_pushed=operators_pushed,
            worksets_pushed=worksets_pushed,
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
        "outbound_scope": ["catalogs", "operators", "worksets"],
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


def _json_datetime(value: datetime | None) -> str:
    fallback = value or datetime.now(timezone.utc)
    return fallback.isoformat().replace("+00:00", "Z")


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
