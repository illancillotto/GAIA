"""Activity domain routes."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.activities import (
    ActivityApproval,
    ActivityCatalog,
    OperatorActivity,
    OperatorActivityEvent,
)

router = APIRouter(prefix="/activities", tags=["operazioni/activities"])


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
    query = select(OperatorActivity)
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

    count_q = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_q) or 0
    items = db.scalars(
        query.order_by(OperatorActivity.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": str(a.id),
                "status": a.status,
                "started_at": a.started_at,
                "ended_at": a.ended_at,
                "operator_user_id": a.operator_user_id,
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
        "status": activity.status,
        "started_at": activity.started_at,
        "ended_at": activity.ended_at,
        "operator_user_id": activity.operator_user_id,
        "vehicle_id": str(activity.vehicle_id) if activity.vehicle_id else None,
        "text_note": activity.text_note,
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
