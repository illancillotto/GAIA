import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.models import (
    BonificaUserStaging,
)
from app.modules.utenze.routes.support import (
    _approve_bonifica_staging_item,
    _require_bonifica_staging_exists,
    _serialize_bonifica_staging,
)
from app.modules.utenze.schemas import (
    BonificaUserStagingBulkApproveRequest,
    BonificaUserStagingBulkApproveResponse,
    BonificaUserStagingListResponse,
    BonificaUserStagingResponse,
)

router = APIRouter(tags=["utenze"])
RequireUtenzeModule = Depends(require_module("utenze"))


# Preserve reviewed legacy callable layout for the merge-base LOC ratchet.
# fmt: off
@router.get("/bonifica-staging", response_model=BonificaUserStagingListResponse)
def get_bonifica_staging(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
) -> BonificaUserStagingListResponse:
    query = select(BonificaUserStaging).order_by(
        BonificaUserStaging.updated_at.desc(),
        BonificaUserStaging.created_at.desc(),
    )
    if review_status:
        query = query.where(BonificaUserStaging.review_status == review_status)

    tokens = [token.strip().lower() for token in (search or "").split() if token.strip()]
    for token in tokens:
        term = f"%{token}%"
        query = query.where(
            or_(
                func.lower(func.coalesce(BonificaUserStaging.username, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.email, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.business_name, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.first_name, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.last_name, "")).like(term),
                func.lower(func.coalesce(BonificaUserStaging.tax, "")).like(term),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return BonificaUserStagingListResponse(
        items=[_serialize_bonifica_staging(db, item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.post("/bonifica-staging/bulk-approve", response_model=BonificaUserStagingBulkApproveResponse)
def bulk_approve_bonifica_staging(
    payload: BonificaUserStagingBulkApproveRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaUserStagingBulkApproveResponse:
    approved = 0
    skipped = 0
    errors: list[str] = []

    for raw_id in payload.ids:
        try:
            staging_id = uuid.UUID(raw_id)
        except ValueError:
            errors.append(f"{raw_id}: invalid uuid")
            continue

        staging = db.get(BonificaUserStaging, staging_id)
        if staging is None:
            errors.append(f"{raw_id}: staging item not found")
            continue
        if staging.review_status != "new":
            skipped += 1
            continue
        _approve_bonifica_staging_item(db, current_user, staging)
        approved += 1

    return BonificaUserStagingBulkApproveResponse(
        approved=approved,
        skipped=skipped,
        errors=errors,
    )

@router.get("/bonifica-staging/{staging_id}", response_model=BonificaUserStagingResponse)
def get_bonifica_staging_item(
    staging_id: uuid.UUID,
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaUserStagingResponse:
    staging = _require_bonifica_staging_exists(db, staging_id)
    return _serialize_bonifica_staging(db, staging)

@router.post("/bonifica-staging/{staging_id}/approve", response_model=BonificaUserStagingResponse)
def approve_bonifica_staging_item(
    staging_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaUserStagingResponse:
    staging = _require_bonifica_staging_exists(db, staging_id)
    return _approve_bonifica_staging_item(db, current_user, staging)

@router.post("/bonifica-staging/{staging_id}/reject", response_model=BonificaUserStagingResponse)
def reject_bonifica_staging_item(
    staging_id: uuid.UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> BonificaUserStagingResponse:
    staging = _require_bonifica_staging_exists(db, staging_id)
    staging.review_status = "rejected"
    staging.reviewed_by = current_user.id
    staging.reviewed_at = datetime.now(UTC)
    db.add(staging)
    db.commit()
    return _serialize_bonifica_staging(db, staging)
# fmt: on
