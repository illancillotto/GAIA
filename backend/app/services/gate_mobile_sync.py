from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.operazioni.models.wc_operator import WCOperator


@dataclass(frozen=True)
class GateMobileSyncReport:
    requested_tasks: list[dict[str, Any]]
    operators_pushed: int


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

        return GateMobileSyncReport(requested_tasks=tasks, operators_pushed=operators_pushed)
    finally:
        if owns_client:
            await client.aclose()


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
