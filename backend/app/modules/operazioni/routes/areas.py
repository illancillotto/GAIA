from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.wc_area import WCArea
from app.modules.operazioni.schemas.areas import WCAreaListResponse, WCAreaResponse


router = APIRouter(prefix="/areas", tags=["operazioni/areas"])


@router.get("", response_model=WCAreaListResponse)
def list_areas_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None),
    is_district: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(WCArea)
    if search:
        like = f"%{search}%"
        query = query.where((WCArea.name.ilike(like)) | (WCArea.description.ilike(like)))
    if is_district is not None:
        query = query.where(WCArea.is_district == is_district)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(WCArea.name.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return WCAreaListResponse(items=[WCAreaResponse.model_validate(item) for item in items], total=total)


@router.get("/{area_id}", response_model=WCAreaResponse)
def get_area_endpoint(
    area_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    item = db.get(WCArea, area_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return WCAreaResponse.model_validate(item)
