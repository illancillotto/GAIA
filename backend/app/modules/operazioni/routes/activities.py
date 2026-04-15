"""Activity domain routes."""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.activities import (
    ActivityApproval,
    ActivityCatalog,
    OperatorActivity,
    OperatorActivityAttachment,
    OperatorActivityEvent,
)
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.gps import GpsTrackSummary

router = APIRouter(prefix="/activities", tags=["operazioni/activities"])


def _as_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _build_gps_summary_payload(summary: GpsTrackSummary) -> dict:
    return {
        "id": str(summary.id),
        "source_type": summary.source_type,
        "provider_name": summary.provider_name,
        "provider_track_id": summary.provider_track_id,
        "started_at": summary.started_at,
        "ended_at": summary.ended_at,
        "start_latitude": float(summary.start_latitude)
        if summary.start_latitude is not None
        else None,
        "start_longitude": float(summary.start_longitude)
        if summary.start_longitude is not None
        else None,
        "end_latitude": float(summary.end_latitude)
        if summary.end_latitude is not None
        else None,
        "end_longitude": float(summary.end_longitude)
        if summary.end_longitude is not None
        else None,
        "total_distance_km": float(summary.total_distance_km)
        if summary.total_distance_km is not None
        else None,
        "total_duration_seconds": summary.total_duration_seconds,
    }


def _extract_track_points(raw_payload: object) -> list[dict]:
    points: list[dict] = []
    seen: set[tuple[float, float, str | None]] = set()

    def visit(node: object) -> None:
        if isinstance(node, dict):
            lat = _as_float(
                node.get("latitude")
                or node.get("lat")
                or node.get("Latitude")
                or node.get("LAT")
            )
            lng = _as_float(
                node.get("longitude")
                or node.get("lng")
                or node.get("lon")
                or node.get("Longitude")
                or node.get("LON")
            )
            if lat is not None and lng is not None:
                ts = node.get("timestamp") or node.get("recorded_at") or node.get("datetime")
                key = (lat, lng, str(ts) if ts is not None else None)
                if key not in seen:
                    seen.add(key)
                    points.append(
                        {
                            "latitude": lat,
                            "longitude": lng,
                            "timestamp": str(ts) if ts is not None else None,
                        }
                    )
            for value in node.values():
                visit(value)
            return

        if isinstance(node, list):
            for item in node:
                visit(item)

    visit(raw_payload)
    return points


@router.get("/catalog", response_model=list[dict])
def get_activity_catalog(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = db.scalars(
        select(ActivityCatalog)
        .where(ActivityCatalog.is_active == True)
        .order_by(ActivityCatalog.sort_order)
    ).all()
    return [
        {
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "category": c.category,
            "requires_vehicle": c.requires_vehicle,
            "requires_note": c.requires_note,
            "sort_order": c.sort_order,
            "is_active": c.is_active,
        }
        for c in items
    ]


@router.get("", response_model=dict)
def list_activities(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    operator_user_id: int | None = None,
    team_id: UUID | None = None,
    vehicle_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    catalog_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(OperatorActivity).join(
        ActivityCatalog,
        ActivityCatalog.id == OperatorActivity.activity_catalog_id,
    )
    if operator_user_id:
        query = query.where(OperatorActivity.operator_user_id == operator_user_id)
    if team_id:
        query = query.where(OperatorActivity.team_id == team_id)
    if vehicle_id:
        query = query.where(OperatorActivity.vehicle_id == vehicle_id)
    if status_filter:
        query = query.where(OperatorActivity.status == status_filter)
    if catalog_id:
        query = query.where(OperatorActivity.activity_catalog_id == catalog_id)
    if date_from:
        query = query.where(
            OperatorActivity.started_at >= datetime.fromisoformat(date_from)
        )
    if date_to:
        query = query.where(
            OperatorActivity.started_at <= datetime.fromisoformat(date_to)
        )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                cast(OperatorActivity.id, String).ilike(term),
                ActivityCatalog.name.ilike(term),
                ActivityCatalog.description.ilike(term),
                OperatorActivity.text_note.ilike(term),
                OperatorActivity.review_note.ilike(term),
                OperatorActivity.status.ilike(term),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_q) or 0
    items = db.scalars(
        query.order_by(OperatorActivity.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    catalog_names = {
        str(catalog.id): catalog.name
        for catalog in db.scalars(select(ActivityCatalog).where(ActivityCatalog.id.in_({item.activity_catalog_id for item in items}))).all()
    } if items else {}
    return {
        "items": [
            {
                "id": str(a.id),
                "status": a.status,
                "started_at": a.started_at,
                "ended_at": a.ended_at,
                "operator_user_id": a.operator_user_id,
                "catalog_name": catalog_names.get(str(a.activity_catalog_id)),
                "text_note": a.text_note,
            }
            for a in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if page_size else 0,
    }


@router.post("/start", response_model=dict, status_code=status.HTTP_201_CREATED)
def start_activity(
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    activity = OperatorActivity(
        **data,
        status="in_progress",
        created_by_user_id=current_user.id,
    )
    db.add(activity)
    db.flush()
    event = OperatorActivityEvent(
        operator_activity_id=activity.id,
        event_type="started",
        event_at=activity.started_at,
        actor_user_id=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(activity)
    return {
        "id": str(activity.id),
        "status": activity.status,
        "started_at": activity.started_at,
    }


@router.post("/{activity_id}/stop", response_model=dict)
def stop_activity(
    activity_id: UUID,
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    activity = db.get(OperatorActivity, activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )
    if activity.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Activity is not in progress"
        )

    for k, v in data.items():
        setattr(activity, k, v)
    activity.status = "submitted" if data.get("submit_for_review", False) else "draft"
    if activity.started_at and activity.ended_at:
        activity.duration_minutes_calculated = int(
            (activity.ended_at - activity.started_at).total_seconds() / 60
        )

    event = OperatorActivityEvent(
        operator_activity_id=activity.id,
        event_type="stopped",
        event_at=activity.ended_at or datetime.now(),
        actor_user_id=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(activity)
    return {
        "id": str(activity.id),
        "status": activity.status,
        "ended_at": activity.ended_at,
    }


@router.get("/{activity_id}", response_model=dict)
def get_activity(
    activity_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    activity = db.get(OperatorActivity, activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )
    return {
        "id": str(activity.id),
        "activity_catalog_id": str(activity.activity_catalog_id),
        "status": activity.status,
        "started_at": activity.started_at,
        "ended_at": activity.ended_at,
        "operator_user_id": activity.operator_user_id,
        "team_id": str(activity.team_id) if activity.team_id else None,
        "vehicle_id": str(activity.vehicle_id) if activity.vehicle_id else None,
        "duration_minutes_declared": activity.duration_minutes_declared,
        "duration_minutes_calculated": activity.duration_minutes_calculated,
        "gps_track_summary_id": str(activity.gps_track_summary_id)
        if activity.gps_track_summary_id
        else None,
        "audio_note_attachment_id": str(activity.audio_note_attachment_id)
        if activity.audio_note_attachment_id
        else None,
        "text_note": activity.text_note,
        "submitted_at": activity.submitted_at,
        "reviewed_by_user_id": activity.reviewed_by_user_id,
        "reviewed_at": activity.reviewed_at,
        "review_outcome": activity.review_outcome,
        "review_note": activity.review_note,
        "server_received_at": activity.server_received_at,
        "created_at": activity.created_at,
        "updated_at": activity.updated_at,
    }


@router.get("/{activity_id}/attachments", response_model=list[dict])
def list_activity_attachments(
    activity_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    activity = db.get(OperatorActivity, activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    rows = db.execute(
        select(OperatorActivityAttachment, Attachment)
        .join(Attachment, OperatorActivityAttachment.attachment_id == Attachment.id)
        .where(OperatorActivityAttachment.operator_activity_id == activity_id)
        .where(Attachment.is_deleted == False)
        .order_by(OperatorActivityAttachment.created_at.desc())
    ).all()
    return [
        {
            "id": str(attachment.id),
            "original_filename": attachment.original_filename,
            "mime_type": attachment.mime_type,
            "attachment_type": attachment.attachment_type,
            "file_size_bytes": attachment.file_size_bytes,
            "created_at": attachment.created_at,
        }
        for _, attachment in rows
    ]


@router.get("/{activity_id}/gps-summary", response_model=dict | None)
def get_activity_gps_summary(
    activity_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    activity = db.get(OperatorActivity, activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )
    if not activity.gps_track_summary_id:
        return None

    summary = db.get(GpsTrackSummary, activity.gps_track_summary_id)
    if not summary:
        return None

    return _build_gps_summary_payload(summary)


@router.get("/{activity_id}/gps-viewer", response_model=dict | None)
def get_activity_gps_viewer(
    activity_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    activity = db.get(OperatorActivity, activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )
    if not activity.gps_track_summary_id:
        return None

    summary = db.get(GpsTrackSummary, activity.gps_track_summary_id)
    if not summary:
        return None

    points = _extract_track_points(summary.raw_payload_json)
    if not points:
        synthetic_points = []
        if summary.start_latitude is not None and summary.start_longitude is not None:
            synthetic_points.append(
                {
                    "latitude": float(summary.start_latitude),
                    "longitude": float(summary.start_longitude),
                    "timestamp": summary.started_at.isoformat()
                    if summary.started_at
                    else None,
                }
            )
        if summary.end_latitude is not None and summary.end_longitude is not None:
            synthetic_points.append(
                {
                    "latitude": float(summary.end_latitude),
                    "longitude": float(summary.end_longitude),
                    "timestamp": summary.ended_at.isoformat()
                    if summary.ended_at
                    else None,
                }
            )
        points = synthetic_points

    latitudes = [point["latitude"] for point in points]
    longitudes = [point["longitude"] for point in points]

    return {
        "summary": _build_gps_summary_payload(summary),
        "points": points,
        "bounds": {
            "min_latitude": min(latitudes) if latitudes else None,
            "max_latitude": max(latitudes) if latitudes else None,
            "min_longitude": min(longitudes) if longitudes else None,
            "max_longitude": max(longitudes) if longitudes else None,
        },
        "viewer_mode": "track" if len(points) > 2 else "segment",
        "point_count": len(points),
        "uses_raw_payload": bool(summary.raw_payload_json and len(points) > 2),
    }


@router.post("/{activity_id}/approve", response_model=dict)
def approve_activity(
    activity_id: UUID,
    data: dict,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    activity = db.get(OperatorActivity, activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    decision = data.get("decision", "approved")
    activity.review_outcome = decision
    activity.reviewed_by_user_id = current_user.id
    activity.reviewed_at = datetime.now()
    activity.review_note = data.get("note")

    if decision == "approved":
        activity.status = "approved"
    elif decision == "rejected":
        activity.status = "rejected"
    elif decision == "needs_integration":
        activity.status = "under_review"

    approval = ActivityApproval(
        operator_activity_id=activity.id,
        reviewer_user_id=current_user.id,
        decision=decision,
        decision_at=datetime.now(),
        note=data.get("note"),
    )
    db.add(approval)

    event = OperatorActivityEvent(
        operator_activity_id=activity.id,
        event_type=f"approval_{decision}",
        event_at=datetime.now(),
        actor_user_id=current_user.id,
        payload_json={"decision": decision, "note": data.get("note")},
    )
    db.add(event)
    db.commit()
    db.refresh(activity)
    return {
        "id": str(activity.id),
        "status": activity.status,
        "review_outcome": activity.review_outcome,
    }
