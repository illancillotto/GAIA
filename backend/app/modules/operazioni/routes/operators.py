from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.schemas.operators import (
    WCOperatorListResponse,
    WCOperatorResponse,
)


router = APIRouter(prefix="/operators", tags=["operazioni/operators"])


@router.get("", response_model=WCOperatorListResponse)
def list_operators_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None),
    role: str | None = Query(None),
    enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(WCOperator)
    if search:
        like = f"%{search}%"
        query = query.where(
            (WCOperator.username.ilike(like))
            | (WCOperator.email.ilike(like))
            | (WCOperator.first_name.ilike(like))
            | (WCOperator.last_name.ilike(like))
            | (WCOperator.tax.ilike(like))
        )
    if role:
        query = query.where(WCOperator.role == role)
    if enabled is not None:
        query = query.where(WCOperator.enabled == enabled)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(WCOperator.role.asc(), WCOperator.last_name.asc(), WCOperator.first_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return WCOperatorListResponse(
        items=[WCOperatorResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{operator_id}", response_model=WCOperatorResponse)
def get_operator_endpoint(
    operator_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    item = db.get(WCOperator, operator_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    return WCOperatorResponse.model_validate(item)
