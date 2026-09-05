from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_role
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    NetworkFirewall,
)
from app.modules.network.router.common import _require_network_module, _serialize_sophos_config
from app.modules.network.router.helpers.firewalls import (
    _build_firewall_log_coverage_summary,
    _serialize_alert,
    _serialize_firewall,
    _serialize_firewall_event,
    _serialize_firewall_metric,
)
from app.modules.network.schemas import (
    NetworkAlertResponse,
    NetworkAlertUpdateRequest,
    NetworkFirewallEventResponse,
    NetworkFirewallLogCoverageSummary,
    NetworkFirewallMetricResponse,
    NetworkFirewallResponse,
    NetworkSophosConfigRead,
    NetworkSophosConfigUpdateRequest,
    SophosSyslogIngestRequest,
)
from app.modules.network.services import (
    list_network_alerts,
    update_network_alert,
)
from app.modules.network.sophos import (
    ingest_sophos_syslog,
    list_network_firewall_events,
    list_network_firewalls,
)
from app.modules.network.sophos_runtime import (
    clear_sophos_runtime_policy_cache,
    get_or_create_sophos_config,
)
from app.modules.network.sophos_snmp import (
    list_network_firewall_metrics,
)

router = APIRouter()


# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

@router.get("/alerts", response_model=list[NetworkAlertResponse])
def get_alerts(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
) -> list[NetworkAlertResponse]:
    _require_network_module(current_user)
    return [_serialize_alert(item) for item in list_network_alerts(db, status_filter, severity)]


@router.get("/firewalls", response_model=list[NetworkFirewallResponse])
def get_firewalls(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkFirewallResponse]:
    _require_network_module(current_user)
    return [_serialize_firewall(item) for item in list_network_firewalls(db)]


@router.get("/sophos-config", response_model=NetworkSophosConfigRead)
def get_sophos_config(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkSophosConfigRead:
    _require_network_module(current_user)
    return _serialize_sophos_config(get_or_create_sophos_config(db))


@router.put("/sophos-config", response_model=NetworkSophosConfigRead)
def put_sophos_config(
    payload: NetworkSophosConfigUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkSophosConfigRead:
    _require_network_module(current_user)
    config = get_or_create_sophos_config(db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(config, field, value)
    config.updated_at = datetime.now(UTC)
    config.updated_by_user_id = current_user.id
    db.add(config)
    db.commit()
    db.refresh(config)
    clear_sophos_runtime_policy_cache()
    return _serialize_sophos_config(config)


@router.get("/firewalls/{firewall_id}/events", response_model=list[NetworkFirewallEventResponse])
def get_firewall_events(
    firewall_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    severity: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[NetworkFirewallEventResponse]:
    _require_network_module(current_user)
    return [_serialize_firewall_event(item, db) for item in list_network_firewall_events(db, firewall_id=firewall_id, severity=severity, limit=limit)]


@router.get("/firewalls/{firewall_id}/metrics", response_model=list[NetworkFirewallMetricResponse])
def get_firewall_metrics(
    firewall_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    metric_key: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[NetworkFirewallMetricResponse]:
    _require_network_module(current_user)
    return [_serialize_firewall_metric(item) for item in list_network_firewall_metrics(db, firewall_id=firewall_id, metric_key=metric_key, limit=limit)]


@router.get("/firewalls/{firewall_id}/log-coverage", response_model=NetworkFirewallLogCoverageSummary)
def get_firewall_log_coverage(
    firewall_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
) -> NetworkFirewallLogCoverageSummary:
    _require_network_module(current_user)
    firewall = db.get(NetworkFirewall, firewall_id)
    if firewall is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall not found")
    return _build_firewall_log_coverage_summary(db, firewall=firewall, window_hours=window_hours)


@router.post("/firewalls/{firewall_id}/metrics/poll", response_model=list[NetworkFirewallMetricResponse], status_code=status.HTTP_201_CREATED)
def poll_firewall_metrics(
    firewall_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkFirewallMetricResponse]:
    import app.modules.network.router as network_router
    _require_network_module(current_user)
    metrics = network_router.poll_sophos_firewall_metrics(db)
    return [_serialize_firewall_metric(item) for item in metrics if item.firewall_id == firewall_id]


@router.post("/firewalls/sophos/syslog", response_model=NetworkFirewallEventResponse, status_code=status.HTTP_201_CREATED)
def post_sophos_syslog(
    payload: SophosSyslogIngestRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkFirewallEventResponse:
    _require_network_module(current_user)
    event = ingest_sophos_syslog(
        db,
        message=payload.message,
        firewall_id=payload.firewall_id,
        firewall_name=payload.firewall_name,
        management_ip=payload.management_ip,
        observed_at=payload.observed_at,
    )
    return _serialize_firewall_event(event, db)


@router.patch("/alerts/{alert_id}", response_model=NetworkAlertResponse)
def patch_alert(
    alert_id: int,
    payload: NetworkAlertUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkAlertResponse:
    _require_network_module(current_user)
    assigned_to_user_id = payload.assigned_to_user_id
    if assigned_to_user_id is not None:
        assigned_user = db.get(ApplicationUser, assigned_to_user_id)
        if assigned_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    alert = update_network_alert(
        db,
        alert_id,
        status=payload.status,
        assigned_to_user_id=assigned_to_user_id,
        verification_status=payload.verification_status,
        verification_notes=payload.verification_notes,
    )
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return _serialize_alert(alert)


# fmt: on
