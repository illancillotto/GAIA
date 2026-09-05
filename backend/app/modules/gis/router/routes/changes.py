from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import services
from app.modules.gis.schemas import (
    GisChangeRequestCreate,
    GisChangeRequestResponse,
    GisChangeRequestReview,
    GisChangeRequestStatus,
    GisChangeRequestUpdate,
    GisLayerPermissionResponse,
    GisLayerPermissionUpsert,
)

router = APIRouter()


# Preserve the measured legacy layout while keeping the new module formatter-safe.
# fmt: off
@router.get(
    "/layers/{layer_id}/permissions", response_model=list[GisLayerPermissionResponse]
)
def list_permissions(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GisLayerPermissionResponse]:
    return services.list_permissions(db, layer_id, current_user)


@router.post(
    "/layers/{layer_id}/permissions", response_model=GisLayerPermissionResponse
)
def upsert_permission(
    layer_id: UUID,
    body: GisLayerPermissionUpsert,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerPermissionResponse:
    return services.upsert_permission(db, layer_id, body, current_user)


@router.delete(
    "/layers/{layer_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_permission(
    layer_id: UUID,
    permission_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    services.revoke_permission(db, layer_id, permission_id, current_user)


@router.post(
    "/layers/{layer_id}/change-requests",
    response_model=GisChangeRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_change_request(
    layer_id: UUID,
    body: GisChangeRequestCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.create_change_request(db, layer_id, body, current_user)


@router.get("/change-requests", response_model=list[GisChangeRequestResponse])
def list_change_requests(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: GisChangeRequestStatus | None = Query(None, alias="status"),
    layer_id: UUID | None = None,
) -> list[GisChangeRequestResponse]:
    return services.list_change_requests(db, current_user, status_filter=status_filter, layer_id=layer_id)


@router.patch(
    "/change-requests/{change_request_id}", response_model=GisChangeRequestResponse
)
def update_change_request(
    change_request_id: UUID,
    body: GisChangeRequestUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.update_change_request(db, change_request_id, body, current_user)


@router.post(
    "/change-requests/{change_request_id}/request-changes",
    response_model=GisChangeRequestResponse,
)
def request_change_request_changes(
    change_request_id: UUID,
    body: GisChangeRequestReview,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.request_change_request_changes(db, change_request_id, body, current_user)


@router.post(
    "/change-requests/{change_request_id}/reject",
    response_model=GisChangeRequestResponse,
)
def reject_change_request(
    change_request_id: UUID,
    body: GisChangeRequestReview,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.reject_change_request(db, change_request_id, body, current_user)


@router.post(
    "/change-requests/{change_request_id}/approve",
    response_model=GisChangeRequestResponse,
)
def approve_change_request(
    change_request_id: UUID,
    body: GisChangeRequestReview,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.approve_change_request(db, change_request_id, body, current_user)


@router.post(
    "/change-requests/{change_request_id}/apply",
    response_model=GisChangeRequestResponse,
)
def apply_change_request(
    change_request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.apply_change_request(db, change_request_id, current_user)
# fmt: on
