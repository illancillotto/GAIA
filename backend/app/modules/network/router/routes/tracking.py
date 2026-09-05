from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    NetworkAlert,
    NetworkDetectionWatchlist,
    NetworkDevice,
    NetworkTrackedSubject,
)
from app.modules.network.router.common import _require_network_module
from app.modules.network.router.helpers.inference import (
    _build_inferred_assigned_arp_subjects,
    _build_inferred_tracked_subjects,
)
from app.modules.network.router.helpers.tracking import (
    _build_arp_timeline,
    _build_tracked_subject_activity_summary,
    _ensure_detection_watchlist_seeded,
    _get_active_tracked_subject_map,
    _normalize_tracked_value,
    _reconcile_legacy_ip_tracked_subject,
    _reconcile_legacy_ip_tracked_subjects,
    _serialize_tracked_subject,
)
from app.modules.network.schemas import (
    NetworkArpTimelineItem,
    NetworkDetectionWatchlistRuleCreateRequest,
    NetworkDetectionWatchlistRuleRead,
    NetworkDetectionWatchlistRuleUpdateRequest,
    NetworkTrackedSubjectActivitySummary,
    NetworkTrackedSubjectCreateRequest,
    NetworkTrackedSubjectResponse,
    NetworkTrackedSubjectUpdateRequest,
    NetworkVpnBypassSummary,
)

router = APIRouter()


# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

@router.get("/tracking", response_model=list[NetworkTrackedSubjectResponse])
def get_tracked_subjects(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = Query(default=False),
    include_inferred: bool = Query(default=False),
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
    search: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
) -> list[NetworkTrackedSubjectResponse]:
    _require_network_module(current_user)
    _reconcile_legacy_ip_tracked_subjects(db)
    query = select(NetworkTrackedSubject).order_by(NetworkTrackedSubject.updated_at.desc(), NetworkTrackedSubject.id.desc())
    if not include_inactive:
        query = query.where(NetworkTrackedSubject.is_active.is_(True))
    if entity_type:
        query = query.where(NetworkTrackedSubject.entity_type == entity_type)
    if search:
        normalized_search = f"%{search.strip()}%"
        query = query.where(
            or_(
                NetworkTrackedSubject.value.ilike(normalized_search),
                NetworkTrackedSubject.label.ilike(normalized_search),
                NetworkTrackedSubject.notes.ilike(normalized_search),
            )
        )
    subjects = db.scalars(query).all()
    items = [_serialize_tracked_subject(db, subject, window_hours=window_hours) for subject in subjects]
    if include_inferred:
        active_subject_map = _get_active_tracked_subject_map(db)
        items.extend(
            _build_inferred_assigned_arp_subjects(
                db,
                active_subjects=active_subject_map,
                window_hours=window_hours,
                entity_type=entity_type,
                search=search,
            )
        )
        items.extend(
            _build_inferred_tracked_subjects(
                db,
                window_hours=window_hours,
                entity_type=entity_type,
                search=search,
            )
        )
        items.sort(
            key=lambda subject: (
                subject.activity_summary.suspicious_events if subject.activity_summary else 0,
                1 if subject.device_id is not None else 0,
                subject.updated_at,
            ),
            reverse=True,
        )
    return items


@router.post("/tracking", response_model=NetworkTrackedSubjectResponse, status_code=status.HTTP_201_CREATED)
def create_tracked_subject(
    payload: NetworkTrackedSubjectCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkTrackedSubjectResponse:
    _require_network_module(current_user)

    device: NetworkDevice | None = None
    value = payload.value.strip() if payload.value else None
    normalized_value = value
    if payload.entity_type == "device":
        device = db.get(NetworkDevice, payload.device_id)
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        normalized_value = str(device.id)
        value = device.ip_address
        legacy_subject = db.scalar(
            select(NetworkTrackedSubject).where(
                NetworkTrackedSubject.entity_type == "ip",
                NetworkTrackedSubject.device_id.is_(None),
                NetworkTrackedSubject.value == device.ip_address,
            )
        )
        if legacy_subject is not None:
            reconciled_subject, _ = _reconcile_legacy_ip_tracked_subject(db, legacy_subject)
            db.commit()
            db.refresh(reconciled_subject)
            if payload.label is not None:
                reconciled_subject.label = payload.label or None
            if payload.notes is not None:
                reconciled_subject.notes = payload.notes or None
            reconciled_subject.is_active = True
            db.add(reconciled_subject)
            db.commit()
            db.refresh(reconciled_subject)
            return _serialize_tracked_subject(db, reconciled_subject, include_activity_summary=False)
    else:
        if value is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing tracking value")
        normalized_value = _normalize_tracked_value(payload.entity_type, value)

    existing = db.scalar(
        select(NetworkTrackedSubject).where(
            NetworkTrackedSubject.entity_type == payload.entity_type,
            NetworkTrackedSubject.normalized_value == normalized_value,
        )
    )
    if existing is not None:
        if payload.label is not None:
            existing.label = payload.label or None
        if payload.notes is not None:
            existing.notes = payload.notes or None
        existing.is_active = True
        if device is not None:
            existing.device_id = device.id
            existing.value = device.ip_address
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return _serialize_tracked_subject(db, existing, include_activity_summary=False)

    subject = NetworkTrackedSubject(
        entity_type=payload.entity_type,
        normalized_value=normalized_value or "",
        value=value or "",
        label=payload.label or None,
        notes=payload.notes or None,
        is_active=True,
        device_id=device.id if device is not None else None,
        created_by_user_id=current_user.id,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _serialize_tracked_subject(db, subject, include_activity_summary=False)


@router.patch("/tracking/{subject_id}", response_model=NetworkTrackedSubjectResponse)
def patch_tracked_subject(
    subject_id: int,
    payload: NetworkTrackedSubjectUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkTrackedSubjectResponse:
    _require_network_module(current_user)
    subject = db.get(NetworkTrackedSubject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked subject not found")
    updates = payload.model_dump(exclude_unset=True)
    for field_name, field_value in updates.items():
        setattr(subject, field_name, field_value)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _serialize_tracked_subject(db, subject, include_activity_summary=False)


@router.get("/tracking/{subject_id}/activities", response_model=NetworkTrackedSubjectActivitySummary)
def get_tracked_subject_activities(
    subject_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
    limit: int = Query(default=25, ge=1, le=200),
) -> NetworkTrackedSubjectActivitySummary:
    _require_network_module(current_user)
    subject = db.get(NetworkTrackedSubject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked subject not found")
    return _build_tracked_subject_activity_summary(db, subject, window_hours=window_hours, limit=limit)


@router.get("/detection-watchlist", response_model=list[NetworkDetectionWatchlistRuleRead])
def get_detection_watchlist(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NetworkDetectionWatchlistRuleRead]:
    _require_network_module(current_user)
    _ensure_detection_watchlist_seeded(db)
    items = db.scalars(
        select(NetworkDetectionWatchlist).order_by(
            NetworkDetectionWatchlist.category.asc(),
            NetworkDetectionWatchlist.match_type.asc(),
            NetworkDetectionWatchlist.pattern.asc(),
        )
    ).all()
    return [NetworkDetectionWatchlistRuleRead.model_validate(item) for item in items]


@router.post("/detection-watchlist", response_model=NetworkDetectionWatchlistRuleRead, status_code=status.HTTP_201_CREATED)
def create_detection_watchlist_rule(
    payload: NetworkDetectionWatchlistRuleCreateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDetectionWatchlistRuleRead:
    _require_network_module(current_user)
    _ensure_detection_watchlist_seeded(db)
    normalized_pattern = payload.pattern.strip().lower()
    existing = db.scalar(
        select(NetworkDetectionWatchlist).where(
            NetworkDetectionWatchlist.category == payload.category,
            NetworkDetectionWatchlist.rule_mode == payload.rule_mode,
            NetworkDetectionWatchlist.match_type == payload.match_type,
            NetworkDetectionWatchlist.pattern == normalized_pattern,
        )
    )
    if existing is not None:
        existing.label = payload.label or existing.label
        existing.notes = payload.notes or existing.notes
        existing.is_active = payload.is_active
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return NetworkDetectionWatchlistRuleRead.model_validate(existing)

    item = NetworkDetectionWatchlist(
        category=payload.category,
        rule_mode=payload.rule_mode,
        match_type=payload.match_type,
        pattern=normalized_pattern,
        label=payload.label,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return NetworkDetectionWatchlistRuleRead.model_validate(item)


@router.patch("/detection-watchlist/{rule_id}", response_model=NetworkDetectionWatchlistRuleRead)
def patch_detection_watchlist_rule(
    rule_id: int,
    payload: NetworkDetectionWatchlistRuleUpdateRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDetectionWatchlistRuleRead:
    _require_network_module(current_user)
    item = db.get(NetworkDetectionWatchlist, rule_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist rule not found")
    updates = payload.model_dump(exclude_unset=True)
    for field_name, field_value in updates.items():
        setattr(item, field_name, field_value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return NetworkDetectionWatchlistRuleRead.model_validate(item)


@router.get("/vpn-bypass/summary", response_model=NetworkVpnBypassSummary)
def get_vpn_bypass_summary(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
) -> NetworkVpnBypassSummary:
    _require_network_module(current_user)
    _ensure_detection_watchlist_seeded(db)
    subjects = get_tracked_subjects(
        current_user=current_user,
        db=db,
        include_inactive=False,
        include_inferred=True,
        window_hours=window_hours,
        search=None,
        entity_type=None,
    )
    suspicious_subjects = 0
    vpn_subjects = 0
    proxy_subjects = 0
    tor_subjects = 0
    encrypted_dns_subjects = 0
    total_suspicious_events = 0
    for subject in subjects:
        activity = subject.activity_summary or NetworkTrackedSubjectActivitySummary(window_hours=window_hours)
        if activity.suspicious_events > 0:
            suspicious_subjects += 1
            total_suspicious_events += activity.suspicious_events
        if activity.vpn_suspected_events > 0:
            vpn_subjects += 1
        if activity.proxy_suspected_events > 0:
            proxy_subjects += 1
        if activity.tor_suspected_events > 0:
            tor_subjects += 1
        if activity.encrypted_dns_events > 0:
            encrypted_dns_subjects += 1

    open_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type.in_([
                "VPN_BYPASS_SUSPECTED",
                "VPN_BYPASS_TRANSIENT_DEVICE",
                "ARP_EPHEMERAL_DEVICE",
                "ARP_MAC_CHANGE_SUSPECTED",
                "ARP_IP_ROTATION_SUSPECTED",
            ]),
        )
    ) or 0
    transient_device_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type == "VPN_BYPASS_TRANSIENT_DEVICE",
        )
    ) or 0
    arp_ephemeral_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type == "ARP_EPHEMERAL_DEVICE",
        )
    ) or 0
    arp_identity_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type == "ARP_MAC_CHANGE_SUSPECTED",
        )
    ) or 0
    arp_spoofing_alerts = db.scalar(
        select(func.count()).select_from(NetworkAlert).where(
            NetworkAlert.status == "open",
            NetworkAlert.alert_type == "ARP_IP_ROTATION_SUSPECTED",
        )
    ) or 0
    watchlist_rules = db.scalar(select(func.count()).select_from(NetworkDetectionWatchlist)) or 0
    return NetworkVpnBypassSummary(
        total_subjects=suspicious_subjects,
        vpn_subjects=vpn_subjects,
        proxy_subjects=proxy_subjects,
        tor_subjects=tor_subjects,
        encrypted_dns_subjects=encrypted_dns_subjects,
        total_suspicious_events=total_suspicious_events,
        open_alerts=open_alerts,
        transient_device_alerts=transient_device_alerts,
        arp_ephemeral_alerts=arp_ephemeral_alerts,
        arp_identity_alerts=arp_identity_alerts,
        arp_spoofing_alerts=arp_spoofing_alerts,
        watchlist_rules=watchlist_rules,
    )


@router.get("/vpn-bypass/arp-timeline", response_model=list[NetworkArpTimelineItem])
def get_vpn_bypass_arp_timeline(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=168, ge=1, le=24 * 30),
    limit: int = Query(default=12, ge=1, le=50),
) -> list[NetworkArpTimelineItem]:
    _require_network_module(current_user)
    return _build_arp_timeline(db, window_hours=window_hours, limit=limit)


# fmt: on
