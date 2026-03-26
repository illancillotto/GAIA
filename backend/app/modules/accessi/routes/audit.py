from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.schemas.audit import (
    DashboardSummaryResponse,
    NasGroupResponse,
    NasUserResponse,
    ReviewResponse,
    ShareResponse,
    SyncRunResponse,
)
from app.services.audit import (
    get_audit_dashboard_summary,
    get_nas_groups,
    get_nas_users,
    get_reviews,
    get_shares,
    get_sync_runs,
)

router = APIRouter(tags=["audit"])


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(**get_audit_dashboard_summary(db))


@router.get("/nas-users", response_model=list[NasUserResponse])
def nas_users(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NasUserResponse]:
    return [NasUserResponse.model_validate(item) for item in get_nas_users(db)]


@router.get("/nas-users/section", response_model=list[NasUserResponse])
def nas_users_section(
    _: Annotated[ApplicationUser, Depends(require_section("accessi.users"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[NasUserResponse]:
    return [NasUserResponse.model_validate(item) for item in get_nas_users(db)]


@router.get("/nas-groups", response_model=list[NasGroupResponse])
def nas_groups(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NasGroupResponse]:
    return [NasGroupResponse.model_validate(item) for item in get_nas_groups(db)]


@router.get("/shares", response_model=list[ShareResponse])
def shares(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ShareResponse]:
    return [ShareResponse.model_validate(item) for item in get_shares(db)]


@router.get("/reviews", response_model=list[ReviewResponse])
def reviews(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ReviewResponse]:
    return [ReviewResponse.model_validate(item) for item in get_reviews(db)]


@router.get("/sync-runs", response_model=list[SyncRunResponse])
def sync_runs(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SyncRunResponse]:
    return [SyncRunResponse.model_validate(item) for item in get_sync_runs(db)]
