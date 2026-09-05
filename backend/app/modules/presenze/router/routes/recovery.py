from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeRecoveryAdjustment,
)
from app.modules.presenze.router.common import RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_view_all_inaz_data
from app.modules.presenze.router.helpers.daily_records import _get_collaborator_or_404
from app.modules.presenze.router.helpers.recovery import (
    _build_recovery_dashboard,
    _serialize_recovery_adjustment,
    _serialize_recovery_adjustments,
)
from app.modules.presenze.schemas import (
    PresenzeRecoveryAdjustmentCreate,
    PresenzeRecoveryAdjustmentResponse,
    PresenzeRecoveryAdjustmentReview,
    PresenzeRecoveryAdjustmentUpdate,
    PresenzeRecoveryDashboardResponse,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/recovery/dashboard", response_model=PresenzeRecoveryDashboardResponse)
def get_recovery_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    negative_only: bool = Query(default=False),
    pending_validation_only: bool = Query(default=False),
    pending_adjustments_only: bool = Query(default=False),
    manual_adjustments_only: bool = Query(default=False),
) -> PresenzeRecoveryDashboardResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery dashboard requires HR or admin privileges")
    return _build_recovery_dashboard(
        db,
        date_from=date_from,
        date_to=date_to,
        q=q,
        negative_only=negative_only,
        pending_validation_only=pending_validation_only,
        pending_adjustments_only=pending_adjustments_only,
        manual_adjustments_only=manual_adjustments_only,
    )

@router.get("/recovery/adjustments", response_model=list[PresenzeRecoveryAdjustmentResponse])
def list_recovery_adjustments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    approval_status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
) -> list[PresenzeRecoveryAdjustmentResponse]:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery dashboard requires HR or admin privileges")
    stmt = select(PresenzeRecoveryAdjustment)
    if collaborator_id is not None:
        stmt = stmt.where(PresenzeRecoveryAdjustment.collaborator_id == collaborator_id)
    if approval_status is not None:
        stmt = stmt.where(PresenzeRecoveryAdjustment.approval_status == approval_status)
    rows = db.execute(
        stmt.order_by(PresenzeRecoveryAdjustment.adjustment_date.desc(), PresenzeRecoveryAdjustment.created_at.desc())
    ).scalars().all()
    return _serialize_recovery_adjustments(db, rows)

@router.post("/recovery/adjustments", response_model=PresenzeRecoveryAdjustmentResponse, status_code=201)
def create_recovery_adjustment(
    payload: PresenzeRecoveryAdjustmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeRecoveryAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery adjustments require HR or admin privileges")
    _get_collaborator_or_404(db, payload.collaborator_id)
    item = PresenzeRecoveryAdjustment(
        **payload.model_dump(),
        approval_status="pending",
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_recovery_adjustment(db, item)

@router.patch("/recovery/adjustments/{adjustment_id}", response_model=PresenzeRecoveryAdjustmentResponse)
def update_recovery_adjustment(
    adjustment_id: uuid.UUID,
    payload: PresenzeRecoveryAdjustmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeRecoveryAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery adjustments require HR or admin privileges")
    item = db.get(PresenzeRecoveryAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recovery adjustment not found")
    changed_fields = payload.model_dump(exclude_unset=True)
    for field, value in changed_fields.items():
        setattr(item, field, value)
    if changed_fields:
        item.approval_status = "pending"
        item.approval_note = None
        item.reviewed_by_user_id = None
        item.reviewed_at = None
    item.updated_by_user_id = current_user.id
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_recovery_adjustment(db, item)

@router.post("/recovery/adjustments/{adjustment_id}/review", response_model=PresenzeRecoveryAdjustmentResponse)
def review_recovery_adjustment(
    adjustment_id: uuid.UUID,
    payload: PresenzeRecoveryAdjustmentReview,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeRecoveryAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery adjustments require HR or admin privileges")
    item = db.get(PresenzeRecoveryAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recovery adjustment not found")
    item.approval_status = payload.approval_status
    item.approval_note = payload.approval_note
    item.reviewed_by_user_id = current_user.id
    item.reviewed_at = datetime.now(UTC)
    item.updated_by_user_id = current_user.id
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_recovery_adjustment(db, item)

@router.delete("/recovery/adjustments/{adjustment_id}", status_code=204)
def delete_recovery_adjustment(
    adjustment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Recovery adjustments require HR or admin privileges")
    item = db.get(PresenzeRecoveryAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Recovery adjustment not found")
    db.delete(item)
    db.commit()

# fmt: on
