from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_role, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.user_presence import UserPresence
from app.schemas.presence import (
    UserPresenceHeartbeatRequest,
    UserPresenceHeartbeatResponse,
    UserPresenceModuleBucket,
    UserPresenceSummaryItem,
    UserPresenceSummaryResponse,
)

router = APIRouter(prefix="/auth/presence", tags=["auth/presence"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _sanitize_text(value: str | None, *, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:max_length]


@router.post("/heartbeat", response_model=UserPresenceHeartbeatResponse, summary="Record authenticated user presence")
def record_presence_heartbeat(
    payload: UserPresenceHeartbeatRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> UserPresenceHeartbeatResponse:
    now = _utcnow()
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    presence = db.get(UserPresence, current_user.id)
    if presence is None:
        presence = UserPresence(
            user_id=current_user.id,
            first_seen_at=now,
            last_seen_at=now,
            last_path=payload.path[:512],
            last_route_label=_sanitize_text(payload.route_label, max_length=255),
            last_module_key=_sanitize_text(payload.module_key, max_length=64),
            last_visible=payload.visible,
            last_ip=_sanitize_text(client_ip, max_length=64),
            last_user_agent=_sanitize_text(user_agent, max_length=512),
        )
    else:
        presence.last_seen_at = now
        presence.last_path = payload.path[:512]
        presence.last_route_label = _sanitize_text(payload.route_label, max_length=255)
        presence.last_module_key = _sanitize_text(payload.module_key, max_length=64)
        presence.last_visible = payload.visible
        presence.last_ip = _sanitize_text(client_ip, max_length=64)
        presence.last_user_agent = _sanitize_text(user_agent, max_length=512)

    db.add(presence)
    db.commit()
    return UserPresenceHeartbeatResponse(last_seen_at=now)


@router.get("/summary", response_model=UserPresenceSummaryResponse, summary="List recently active GAIA users")
def get_presence_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    __: Annotated[ApplicationUser, Depends(require_section("accessi.users"))],
    window_minutes: int = Query(default=15, ge=1, le=120),
) -> UserPresenceSummaryResponse:
    threshold = _utcnow() - timedelta(minutes=window_minutes)
    rows = db.execute(
        select(UserPresence, ApplicationUser)
        .join(ApplicationUser, ApplicationUser.id == UserPresence.user_id)
        .where(UserPresence.last_seen_at >= threshold)
        .order_by(UserPresence.last_seen_at.desc(), ApplicationUser.username.asc())
    ).all()

    now = _utcnow()
    items: list[UserPresenceSummaryItem] = []
    module_counts: Counter[str] = Counter()

    for presence, user in rows:
        last_seen_at = _coerce_utc(presence.last_seen_at)
        if presence.last_module_key:
            module_counts[presence.last_module_key] += 1
        items.append(
            UserPresenceSummaryItem(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                module_key=presence.last_module_key,
                route_label=presence.last_route_label,
                path=presence.last_path,
                visible=presence.last_visible,
                last_seen_at=last_seen_at,
                minutes_since_last_seen=max(0, int((now - last_seen_at).total_seconds() // 60)),
                last_login_at=user.last_login_at,
            )
        )

    by_module = [
        UserPresenceModuleBucket(module_key=module_key, count=count)
        for module_key, count in sorted(module_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    visible_users = sum(1 for item in items if item.visible)

    return UserPresenceSummaryResponse(
        window_minutes=window_minutes,
        active_users=len(items),
        visible_users=visible_users,
        items=items,
        by_module=by_module,
    )
