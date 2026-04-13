from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.inventory.models import WarehouseRequest
from app.modules.inventory.schemas import (
    WarehouseRequestListResponse,
    WarehouseRequestResponse,
)


router = APIRouter(
    prefix="/api/inventory",
    tags=["inventory"],
    dependencies=[Depends(require_module("inventario"))],
)


@router.get("/warehouse-requests", response_model=WarehouseRequestListResponse)
def list_warehouse_requests_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None),
    archived: bool | None = Query(None),
    status_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(WarehouseRequest)
    if search:
        like = f"%{search}%"
        query = query.where(
            (WarehouseRequest.report_type.ilike(like))
            | (WarehouseRequest.reported_by.ilike(like))
            | (WarehouseRequest.requested_by.ilike(like))
        )
    if archived is not None:
        query = query.where(WarehouseRequest.archived == archived)
    if status_active is not None:
        query = query.where(WarehouseRequest.status_active == status_active)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(WarehouseRequest.request_date.desc(), WarehouseRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return WarehouseRequestListResponse(
        items=[WarehouseRequestResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/warehouse-requests/{request_id}", response_model=WarehouseRequestResponse)
def get_warehouse_request_endpoint(
    request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    item = db.get(WarehouseRequest, request_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse request not found")
    return WarehouseRequestResponse.model_validate(item)
