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
    GisAnnotationCreate,
    GisAnnotationResponse,
    GisChangeRequestApprove,
    GisChangeRequestCreate,
    GisChangeRequestResponse,
    GisLayerCreate,
    GisLayerExportRequest,
    GisLayerExportResponse,
    GisLayerListResponse,
    GisLayerPermissionResponse,
    GisLayerPermissionUpsert,
    GisLayerResponse,
)


router = APIRouter(prefix="/gis", tags=["gis-platform"])


@router.post("/layers", response_model=GisLayerResponse, status_code=status.HTTP_201_CREATED)
def create_layer(
    body: GisLayerCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.create_layer(db, body, current_user)


@router.get("/layers", response_model=GisLayerListResponse)
def list_layers(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerListResponse:
    items = services.list_layers(db, current_user)
    return GisLayerListResponse(items=items, total=len(items))


@router.get("/workspaces/{workspace}/layers", response_model=GisLayerListResponse)
def list_workspace_layers(
    workspace: str,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerListResponse:
    items = services.list_layers(db, current_user, workspace=workspace)
    return GisLayerListResponse(items=items, total=len(items))


@router.get("/layers/{layer_id}", response_model=GisLayerResponse)
def get_layer(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.get_layer(db, layer_id, current_user)


@router.get("/layers/{layer_id}/annotations", response_model=list[GisAnnotationResponse])
def list_annotations(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GisAnnotationResponse]:
    return services.list_annotations(db, layer_id, current_user)


@router.post("/layers/{layer_id}/annotations", response_model=GisAnnotationResponse, status_code=status.HTTP_201_CREATED)
def create_annotation(
    layer_id: UUID,
    body: GisAnnotationCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.create_annotation(db, layer_id, body, current_user)


@router.get("/layers/{layer_id}/permissions", response_model=list[GisLayerPermissionResponse])
def list_permissions(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GisLayerPermissionResponse]:
    return services.list_permissions(db, layer_id, current_user)


@router.post("/layers/{layer_id}/permissions", response_model=GisLayerPermissionResponse)
def upsert_permission(
    layer_id: UUID,
    body: GisLayerPermissionUpsert,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerPermissionResponse:
    return services.upsert_permission(db, layer_id, body, current_user)


@router.post("/layers/{layer_id}/change-requests", response_model=GisChangeRequestResponse, status_code=status.HTTP_201_CREATED)
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
    status_filter: str | None = Query(None, alias="status"),
) -> list[GisChangeRequestResponse]:
    return services.list_change_requests(db, current_user, status_filter=status_filter)


@router.post("/change-requests/{change_request_id}/approve", response_model=GisChangeRequestResponse)
def approve_change_request(
    change_request_id: UUID,
    body: GisChangeRequestApprove,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.approve_change_request(db, change_request_id, body, current_user)


@router.post("/layers/{layer_id}/export-shapefile", response_model=GisLayerExportResponse, status_code=status.HTTP_202_ACCEPTED)
def request_shapefile_export(
    layer_id: UUID,
    body: GisLayerExportRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerExportResponse:
    return services.request_shapefile_export(db, layer_id, body, current_user)
