from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.dashboard_schemas import (
    PresenzeDashboardCollaboratorResponse,
    PresenzeDashboardReviewCaseResponse,
    PresenzeDashboardSnapshotMetaResponse,
    PresenzeDashboardWorkspaceResponse,
)
from app.modules.presenze.models import (
    PresenzeSyncJob,
)
from app.modules.presenze.router.common import RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_view_all_inaz_data
from app.modules.presenze.schemas import (
    PresenzeDashboardSummaryResponse,
    PresenzeSyncJobResponse,
)
from app.modules.presenze.services.dashboard_projection import (
    build_dashboard_projection,
    build_dashboard_summary,
    get_dashboard_snapshot,
)
from app.modules.presenze.services.visibility_policy import (
    collaborator_visibility_filter,
    daily_record_visibility_filter,
    resolve_presenze_visibility,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/dashboard/summary", response_model=PresenzeDashboardSummaryResponse)
def get_dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> PresenzeDashboardSummaryResponse:
    collaborator_filter = None
    record_filter = None
    if not _can_view_all_inaz_data(current_user):
        visibility = resolve_presenze_visibility(db, current_user)
        collaborator_filter = collaborator_visibility_filter(visibility)
        record_filter = daily_record_visibility_filter(visibility)
    return build_dashboard_summary(
        db,
        period_start=period_start,
        period_end=period_end,
        collaborator_filter=collaborator_filter,
        record_filter=record_filter,
    )


@router.get("/dashboard", response_model=PresenzeDashboardWorkspaceResponse)
def get_dashboard_workspace(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> PresenzeDashboardWorkspaceResponse:
    can_view_all = _can_view_all_inaz_data(current_user)
    snapshot = get_dashboard_snapshot(db, period_start=period_start, period_end=period_end) if can_view_all else None
    if snapshot is not None:
        projection = snapshot.payload_json
        generated_at = snapshot.generated_at
    else:
        collaborator_filter = None
        record_filter = None
        if not can_view_all:
            visibility = resolve_presenze_visibility(db, current_user)
            collaborator_filter = collaborator_visibility_filter(visibility)
            record_filter = daily_record_visibility_filter(visibility)
        projection = build_dashboard_projection(
            db,
            period_start=period_start,
            period_end=period_end,
            collaborator_filter=collaborator_filter,
            record_filter=record_filter,
        )
        generated_at = datetime.now(UTC)

    jobs_stmt = select(PresenzeSyncJob).order_by(PresenzeSyncJob.created_at.desc()).limit(6)
    if not can_view_all:
        jobs_stmt = jobs_stmt.where(PresenzeSyncJob.requested_by_user_id == current_user.id)
    jobs = db.execute(jobs_stmt).scalars().all()
    latest_job = jobs[0] if jobs else None
    return PresenzeDashboardWorkspaceResponse(
        summary=PresenzeDashboardSummaryResponse.model_validate(projection["summary"]),
        review_cases=[PresenzeDashboardReviewCaseResponse.model_validate(item) for item in projection["review_cases"]],
        recent_collaborators=[
            PresenzeDashboardCollaboratorResponse.model_validate(item) for item in projection["recent_collaborators"]
        ],
        sync_jobs=[PresenzeSyncJobResponse.model_validate(job) for job in jobs],
        snapshot=PresenzeDashboardSnapshotMetaResponse(
            cached=snapshot is not None,
            stale=snapshot is not None and latest_job is not None and snapshot.source_sync_job_id != latest_job.id,
            generated_at=generated_at,
            source_sync_job_id=snapshot.source_sync_job_id if snapshot is not None else None,
        ),
    )

# fmt: on
