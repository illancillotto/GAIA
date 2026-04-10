"""Dashboard and storage routes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser

from app.modules.operazioni.models.activities import OperatorActivity
from app.modules.operazioni.models.reports import InternalCase
from app.modules.operazioni.models.vehicles import Vehicle, VehicleUsageSession
from app.modules.operazioni.services.attachment_service import (
    create_attachment_record,
    create_quota_metric,
    get_active_alerts,
    get_latest_metric,
    soft_delete_attachment,
)
from app.modules.operazioni.models.attachments import Attachment

router = APIRouter(tags=["operazioni/dashboard-storage"])


# --- Dashboard ---


@router.get("/dashboard/summary", response_model=dict)
def dashboard_summary(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from datetime import date, datetime

    today_start = datetime.combine(date.today(), datetime.min.time())

    vehicles_total = (
        db.scalar(select(func.count(Vehicle.id)).where(Vehicle.is_active == True)) or 0
    )
    vehicles_available = (
        db.scalar(
            select(func.count(Vehicle.id)).where(
                Vehicle.current_status == "available", Vehicle.is_active == True
            )
        )
        or 0
    )
    vehicles_in_use = (
        db.scalar(
            select(func.count(Vehicle.id)).where(
                Vehicle.current_status == "in_use", Vehicle.is_active == True
            )
        )
        or 0
    )
    vehicles_maintenance = (
        db.scalar(
            select(func.count(Vehicle.id)).where(
                Vehicle.current_status == "maintenance", Vehicle.is_active == True
            )
        )
        or 0
    )

    activities_today = (
        db.scalar(
            select(func.count(OperatorActivity.id)).where(
                OperatorActivity.started_at >= today_start
            )
        )
        or 0
    )
    activities_in_progress = (
        db.scalar(
            select(func.count(OperatorActivity.id)).where(
                OperatorActivity.status == "in_progress"
            )
        )
        or 0
    )
    activities_submitted = (
        db.scalar(
            select(func.count(OperatorActivity.id)).where(
                OperatorActivity.status == "submitted"
            )
        )
        or 0
    )

    cases_open = (
        db.scalar(
            select(func.count(InternalCase.id)).where(
                InternalCase.status.in_(["open", "assigned", "in_progress"])
            )
        )
        or 0
    )

    quota = get_latest_metric(db)
    storage_pct = float(quota.percentage_used) if quota else 0
    storage_alert = "none"
    if storage_pct >= 95:
        storage_alert = "critical_95"
    elif storage_pct >= 85:
        storage_alert = "warning_85"
    elif storage_pct >= 70:
        storage_alert = "warning_70"

    return {
        "vehicles": {
            "total": vehicles_total,
            "available": vehicles_available,
            "in_use": vehicles_in_use,
            "maintenance": vehicles_maintenance,
        },
        "activities": {
            "today_total": activities_today,
            "in_progress": activities_in_progress,
            "submitted": activities_submitted,
        },
        "cases": {"open": cases_open},
        "storage": {"percentage_used": storage_pct, "alert_level": storage_alert},
    }


@router.get("/dashboard/pending-approvals", response_model=list[dict])
def pending_approvals(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    activities = db.scalars(
        select(OperatorActivity)
        .where(OperatorActivity.status.in_(["submitted", "under_review"]))
        .order_by(OperatorActivity.submitted_at.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": str(a.id),
            "status": a.status,
            "submitted_at": a.submitted_at,
            "operator_user_id": a.operator_user_id,
        }
        for a in activities
    ]


@router.get("/dashboard/open-critical-cases", response_model=list[dict])
def open_critical_cases(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from app.modules.operazioni.models.reports import FieldReportSeverity

    cases = (
        db.query(InternalCase)
        .join(FieldReportSeverity, InternalCase.severity_id == FieldReportSeverity.id)
        .where(InternalCase.status.in_(["open", "assigned", "in_progress"]))
        .order_by(FieldReportSeverity.rank_order.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": str(c.id),
            "case_number": c.case_number,
            "status": c.status,
            "title": c.title,
        }
        for c in cases
    ]


# --- Storage ---


@router.get("/storage/metrics/latest", response_model=dict)
def latest_storage_metric(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    metric = get_latest_metric(db)
    if not metric:
        metric = create_quota_metric(db)
        db.commit()
    alerts = get_active_alerts(db)
    return {
        "measured_at": metric.measured_at,
        "total_bytes_used": metric.total_bytes_used,
        "quota_bytes": metric.quota_bytes,
        "percentage_used": float(metric.percentage_used),
        "active_alerts": [
            {"level": a.alert_level, "threshold": float(a.threshold_percentage)}
            for a in alerts
        ],
    }


@router.get("/storage/alerts", response_model=list[dict])
def storage_alerts(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    alerts = get_active_alerts(db)
    return [
        {
            "id": str(a.id),
            "level": a.alert_level,
            "threshold": float(a.threshold_percentage),
            "triggered_at": a.triggered_at,
        }
        for a in alerts
    ]


@router.post("/storage/recalculate", response_model=dict)
def recalculate_storage(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    metric = create_quota_metric(db)
    db.commit()
    return {
        "measured_at": metric.measured_at,
        "total_bytes_used": metric.total_bytes_used,
        "percentage_used": float(metric.percentage_used),
    }


@router.get("/attachments/{attachment_id}", response_model=dict)
def get_attachment(
    attachment_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    attachment = db.get(Attachment, attachment_id)
    if not attachment or attachment.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
        )
    return {
        "id": str(attachment.id),
        "original_filename": attachment.original_filename,
        "mime_type": attachment.mime_type,
        "attachment_type": attachment.attachment_type,
        "file_size_bytes": attachment.file_size_bytes,
        "created_at": attachment.created_at,
    }


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    attachment = db.get(Attachment, attachment_id)
    if not attachment or attachment.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
        )

    path = Path(attachment.storage_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found"
        )

    return FileResponse(
        path,
        media_type=attachment.mime_type,
        filename=attachment.original_filename,
    )


@router.delete("/attachments/{attachment_id}", response_model=dict)
def delete_attachment(
    attachment_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        attachment = soft_delete_attachment(db, attachment_id)
        db.commit()
        return {"id": str(attachment.id), "is_deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
