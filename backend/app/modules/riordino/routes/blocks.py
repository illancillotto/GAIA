"""Riordino block routes."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import (
    BlockCreate,
    BlockCoordinatorSummaryResponse,
    BlockDetailResponse,
    BlockListResponse,
    BlockParcelReviewRequest,
    BlockParcelSnapshotResponse,
    BlockResponse,
    BlockSisterVisuraCompleteRequest,
    BlockSisterVisuraRequest,
    BlockUpdate,
    BlockWizardResponse,
)
from app.modules.riordino.services.block_service import (
    complete_sister_visura,
    create_block,
    delete_block,
    get_block,
    get_block_coordinator_summary,
    get_block_wizard,
    list_blocks,
    request_sister_visura,
    review_block_parcel,
    update_block,
)

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.practices"))])


@router.post("", response_model=BlockResponse, status_code=status.HTTP_201_CREATED)
def create_block_endpoint(
    payload: BlockCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    block = create_block(db, payload.model_dump(), current_user)
    db.commit()
    db.refresh(block)
    return block


@router.get("", response_model=BlockListResponse)
def list_blocks_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    coordinator: int | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    items, total = list_blocks(
        db,
        current_user=current_user,
        status_filter=status_filter,
        coordinator=coordinator,
        page=page,
        per_page=per_page,
    )
    return BlockListResponse(
        items=[BlockResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if per_page else 0,
    )


@router.get("/{block_id}", response_model=BlockDetailResponse)
def get_block_endpoint(
    block_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_block(db, block_id, current_user)


@router.get("/{block_id}/wizard", response_model=BlockWizardResponse)
def get_block_wizard_endpoint(
    block_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_block_wizard(db, block_id, current_user)


@router.get("/{block_id}/coordinator-summary", response_model=BlockCoordinatorSummaryResponse)
def get_block_coordinator_summary_endpoint(
    block_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_block_coordinator_summary(db, block_id, current_user)


@router.patch("/{block_id}", response_model=BlockResponse)
def update_block_endpoint(
    block_id: UUID,
    payload: BlockUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    block = update_block(db, block_id, payload.model_dump(exclude_unset=True), current_user)
    db.commit()
    db.refresh(block)
    return block


@router.patch("/{block_id}/parcels/{snapshot_id}/review", response_model=BlockParcelSnapshotResponse)
def review_block_parcel_endpoint(
    block_id: UUID,
    snapshot_id: UUID,
    payload: BlockParcelReviewRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    snapshot = review_block_parcel(db, block_id, snapshot_id, payload.model_dump(), current_user)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.post("/{block_id}/parcels/{snapshot_id}/sister/request", response_model=BlockParcelSnapshotResponse)
def request_sister_visura_endpoint(
    block_id: UUID,
    snapshot_id: UUID,
    payload: BlockSisterVisuraRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    snapshot = request_sister_visura(db, block_id, snapshot_id, payload.model_dump(), current_user)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.post("/{block_id}/parcels/{snapshot_id}/sister/complete", response_model=BlockParcelSnapshotResponse)
def complete_sister_visura_endpoint(
    block_id: UUID,
    snapshot_id: UUID,
    payload: BlockSisterVisuraCompleteRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    snapshot = complete_sister_visura(db, block_id, snapshot_id, payload.model_dump(), current_user)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.delete("/{block_id}", response_model=BlockResponse)
def delete_block_endpoint(
    block_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    block = delete_block(db, block_id, current_user)
    db.commit()
    db.refresh(block)
    return block
