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
    PresenzeBankHoursAdjustment,
)
from app.modules.presenze.router.common import RequirePresenzeModule
from app.modules.presenze.router.helpers.access import _can_view_all_inaz_data
from app.modules.presenze.router.helpers.bank_hours import (
    _build_bank_hours_collaborator_detail,
    _build_bank_hours_dashboard,
    _serialize_bank_hours_adjustment,
    _serialize_bank_hours_adjustments,
    _validate_bank_hours_adjustment_balance,
)
from app.modules.presenze.router.helpers.daily_records import _get_collaborator_or_404
from app.modules.presenze.schemas import (
    PresenzeBankHoursAdjustmentCreate,
    PresenzeBankHoursAdjustmentResponse,
    PresenzeBankHoursAdjustmentReview,
    PresenzeBankHoursAdjustmentUpdate,
    PresenzeBankHoursCollaboratorDetailResponse,
    PresenzeBankHoursDashboardResponse,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/bank-hours/dashboard", response_model=PresenzeBankHoursDashboardResponse)
def get_bank_hours_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    negative_only: bool = Query(default=False),
    pending_adjustments_only: bool = Query(default=False),
    manual_adjustments_only: bool = Query(default=False),
) -> PresenzeBankHoursDashboardResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours dashboard requires HR or admin privileges")
    return _build_bank_hours_dashboard(
        db,
        date_from=date_from,
        date_to=date_to,
        q=q,
        negative_only=negative_only,
        pending_adjustments_only=pending_adjustments_only,
        manual_adjustments_only=manual_adjustments_only,
    )

@router.get("/bank-hours/collaborators/{collaborator_id}", response_model=PresenzeBankHoursCollaboratorDetailResponse)
def get_bank_hours_collaborator_detail(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> PresenzeBankHoursCollaboratorDetailResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours dashboard requires HR or admin privileges")
    collaborator = _get_collaborator_or_404(db, collaborator_id)
    return _build_bank_hours_collaborator_detail(
        db,
        collaborator,
        date_from=date_from,
        date_to=date_to,
    )

@router.get("/bank-hours/adjustments", response_model=list[PresenzeBankHoursAdjustmentResponse])
def list_bank_hours_adjustments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    approval_status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
) -> list[PresenzeBankHoursAdjustmentResponse]:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours dashboard requires HR or admin privileges")
    stmt = select(PresenzeBankHoursAdjustment)
    if collaborator_id is not None:
        stmt = stmt.where(PresenzeBankHoursAdjustment.collaborator_id == collaborator_id)
    if approval_status is not None:
        stmt = stmt.where(PresenzeBankHoursAdjustment.approval_status == approval_status)
    rows = db.execute(
        stmt.order_by(PresenzeBankHoursAdjustment.adjustment_date.desc(), PresenzeBankHoursAdjustment.created_at.desc())
    ).scalars().all()
    return _serialize_bank_hours_adjustments(db, rows)

@router.post("/bank-hours/adjustments", response_model=PresenzeBankHoursAdjustmentResponse, status_code=201)
def create_bank_hours_adjustment(
    payload: PresenzeBankHoursAdjustmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours adjustments require HR or admin privileges")
    _get_collaborator_or_404(db, payload.collaborator_id)
    item = PresenzeBankHoursAdjustment(
        **payload.model_dump(),
        approval_status="pending",
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_bank_hours_adjustment(db, item)

@router.patch("/bank-hours/adjustments/{adjustment_id}", response_model=PresenzeBankHoursAdjustmentResponse)
def update_bank_hours_adjustment(
    adjustment_id: uuid.UUID,
    payload: PresenzeBankHoursAdjustmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours adjustments require HR or admin privileges")
    item = db.get(PresenzeBankHoursAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Bank hours adjustment not found")
    changed_fields = payload.model_dump(exclude_unset=True)
    for field, value in changed_fields.items():
        setattr(item, field, value)
    if changed_fields:
        _validate_bank_hours_adjustment_balance(db, item, current_item_id=item.id)
        item.approval_status = "pending"
        item.approval_note = None
        item.reviewed_by_user_id = None
        item.reviewed_at = None
    item.updated_by_user_id = current_user.id
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_bank_hours_adjustment(db, item)

@router.post("/bank-hours/adjustments/{adjustment_id}/review", response_model=PresenzeBankHoursAdjustmentResponse)
def review_bank_hours_adjustment(
    adjustment_id: uuid.UUID,
    payload: PresenzeBankHoursAdjustmentReview,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeBankHoursAdjustmentResponse:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours adjustments require HR or admin privileges")
    item = db.get(PresenzeBankHoursAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Bank hours adjustment not found")
    if payload.approval_status == "approved":
        _validate_bank_hours_adjustment_balance(db, item, current_item_id=item.id)
    item.approval_status = payload.approval_status
    item.approval_note = payload.approval_note
    item.reviewed_by_user_id = current_user.id
    item.reviewed_at = datetime.now(UTC)
    item.updated_by_user_id = current_user.id
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_bank_hours_adjustment(db, item)

@router.delete("/bank-hours/adjustments/{adjustment_id}", status_code=204)
def delete_bank_hours_adjustment(
    adjustment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    if not _can_view_all_inaz_data(current_user):
        raise HTTPException(status_code=403, detail="Bank hours adjustments require HR or admin privileges")
    item = db.get(PresenzeBankHoursAdjustment, adjustment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Bank hours adjustment not found")
    db.delete(item)
    db.commit()

# fmt: on
