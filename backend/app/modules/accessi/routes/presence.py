from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
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
    UserPresenceRecentAction,
    UserPresenceModuleBucket,
    UserPresenceRecentRoute,
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


def _load_recent_routes(value: str | None) -> list[dict[str, str | None]]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    items: list[dict[str, str | None]] = []
    for item in payload[:5]:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path:
            continue
        items.append(
            {
                "path": path[:512],
                "route_label": _sanitize_text(item.get("route_label") if isinstance(item.get("route_label"), str) else None, max_length=255),
                "module_key": _sanitize_text(item.get("module_key") if isinstance(item.get("module_key"), str) else None, max_length=64),
                "seen_at": item.get("seen_at") if isinstance(item.get("seen_at"), str) else None,
            }
        )
    return items


def _serialize_recent_routes(
    *,
    current_json: str | None,
    path: str,
    route_label: str | None,
    module_key: str | None,
    seen_at: datetime,
) -> str:
    seen_at_iso = seen_at.isoformat()
    existing = _load_recent_routes(current_json)
    latest = existing[0] if existing else None
    if (
        latest
        and latest.get("path") == path
        and latest.get("route_label") == route_label
        and latest.get("module_key") == module_key
    ):
        latest["seen_at"] = seen_at_iso
        return json.dumps(existing[:5])

    updated = [
        {
            "path": path,
            "route_label": route_label,
            "module_key": module_key,
            "seen_at": seen_at_iso,
        },
        *[item for item in existing if item.get("path") != path or item.get("route_label") != route_label or item.get("module_key") != module_key],
    ]
    return json.dumps(updated[:5])


def _build_recent_routes(value: str | None) -> list[UserPresenceRecentRoute]:
    routes: list[UserPresenceRecentRoute] = []
    for item in _load_recent_routes(value):
        seen_at_raw = item.get("seen_at")
        if not isinstance(seen_at_raw, str):
            continue
        try:
            seen_at = _coerce_utc(datetime.fromisoformat(seen_at_raw))
        except ValueError:
            continue
        routes.append(
            UserPresenceRecentRoute(
                path=item["path"] or "/",
                route_label=item.get("route_label"),
                module_key=item.get("module_key"),
                seen_at=seen_at,
            )
        )
    return routes


def _load_recent_actions(value: str | None) -> list[dict[str, str | None]]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    items: list[dict[str, str | None]] = []
    for item in payload[:5]:
        if not isinstance(item, dict):
            continue
        action_label = item.get("action_label")
        if not isinstance(action_label, str) or not action_label.strip():
            continue
        items.append(
            {
                "action_label": _sanitize_text(action_label, max_length=255),
                "occurred_at": item.get("occurred_at") if isinstance(item.get("occurred_at"), str) else None,
            }
        )
    return items


def _serialize_recent_actions(*, current_json: str | None, action_label: str | None, occurred_at: datetime) -> str:
    existing = _load_recent_actions(current_json)
    if not action_label:
        return json.dumps(existing[:5])
    occurred_at_iso = occurred_at.isoformat()
    latest = existing[0] if existing else None
    if latest and latest.get("action_label") == action_label:
        latest["occurred_at"] = occurred_at_iso
        return json.dumps(existing[:5])
    updated = [
        {
            "action_label": action_label,
            "occurred_at": occurred_at_iso,
        },
        *[item for item in existing if item.get("action_label") != action_label],
    ]
    return json.dumps(updated[:5])


def _build_recent_actions(value: str | None) -> list[UserPresenceRecentAction]:
    actions: list[UserPresenceRecentAction] = []
    for item in _load_recent_actions(value):
        occurred_at_raw = item.get("occurred_at")
        action_label = item.get("action_label")
        if not isinstance(occurred_at_raw, str) or not isinstance(action_label, str):
            continue
        try:
            occurred_at = _coerce_utc(datetime.fromisoformat(occurred_at_raw))
        except ValueError:
            continue
        actions.append(
            UserPresenceRecentAction(
                action_label=action_label,
                occurred_at=occurred_at,
            )
        )
    return actions


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
        route_label = _sanitize_text(payload.route_label, max_length=255)
        module_key = _sanitize_text(payload.module_key, max_length=64)
        action_label = _sanitize_text(payload.action_label, max_length=255)
        presence = UserPresence(
            user_id=current_user.id,
            first_seen_at=now,
            last_seen_at=now,
            last_path=payload.path[:512],
            last_route_label=route_label,
            last_module_key=module_key,
            last_action_label=action_label,
            recent_routes_json=_serialize_recent_routes(
                current_json=None,
                path=payload.path[:512],
                route_label=route_label,
                module_key=module_key,
                seen_at=now,
            ),
            recent_actions_json=_serialize_recent_actions(
                current_json=None,
                action_label=action_label,
                occurred_at=now,
            ),
            last_visible=payload.visible,
            last_ip=_sanitize_text(client_ip, max_length=64),
            last_user_agent=_sanitize_text(user_agent, max_length=512),
        )
    else:
        route_label = _sanitize_text(payload.route_label, max_length=255)
        module_key = _sanitize_text(payload.module_key, max_length=64)
        action_label = _sanitize_text(payload.action_label, max_length=255)
        presence.last_seen_at = now
        presence.last_path = payload.path[:512]
        presence.last_route_label = route_label
        presence.last_module_key = module_key
        presence.last_action_label = action_label
        presence.recent_routes_json = _serialize_recent_routes(
            current_json=presence.recent_routes_json,
            path=payload.path[:512],
            route_label=route_label,
            module_key=module_key,
            seen_at=now,
        )
        presence.recent_actions_json = _serialize_recent_actions(
            current_json=presence.recent_actions_json,
            action_label=action_label,
            occurred_at=now,
        )
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
                action_label=presence.last_action_label,
                visible=presence.last_visible,
                last_seen_at=last_seen_at,
                minutes_since_last_seen=max(0, int((now - last_seen_at).total_seconds() // 60)),
                last_login_at=user.last_login_at,
                recent_routes=_build_recent_routes(presence.recent_routes_json),
                recent_actions=_build_recent_actions(presence.recent_actions_json),
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
