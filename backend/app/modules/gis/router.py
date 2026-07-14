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
    GisAnnotationStatus,
    GisAnnotationUpdate,
    GisChangeRequestCreate,
    GisChangeRequestResponse,
    GisChangeRequestReview,
    GisChangeRequestStatus,
    GisChangeRequestUpdate,
    GisLayerCreate,
    GisLayerExportRequest,
    GisLayerExportResponse,
    GisLayerListResponse,
    GisLayerMetadataUpdate,
    GisLayerPermissionResponse,
    GisLayerPermissionUpsert,
    GisLayerResponse,
    GisQgisGovernanceResponse,
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
    workspace: str | None = None,
    domain_module: str | None = None,
    source_type: str | None = None,
    official_source: str | None = None,
    is_active: bool | None = None,
) -> GisLayerListResponse:
    items = services.list_layers(
        db,
        current_user,
        workspace=workspace,
        domain_module=domain_module,
        source_type=source_type,
        official_source=official_source,
        is_active=is_active,
    )
    return GisLayerListResponse(items=items, total=len(items))


@router.get("/workspaces/{workspace}/layers", response_model=GisLayerListResponse)
def list_workspace_layers(
    workspace: str,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerListResponse:
    items = services.list_layers(db, current_user, workspace=workspace)
    return GisLayerListResponse(items=items, total=len(items))


@router.get("/qgis/governance", response_model=GisQgisGovernanceResponse)
def get_qgis_governance(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisQgisGovernanceResponse:
    return services.get_qgis_governance(db, current_user)


@router.get("/layers/{layer_id}", response_model=GisLayerResponse)
def get_layer(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.get_layer(db, layer_id, current_user)


@router.patch("/layers/{layer_id}/metadata", response_model=GisLayerResponse)
def update_layer_metadata(
    layer_id: UUID,
    body: GisLayerMetadataUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.update_layer_metadata(db, layer_id, body, current_user)


@router.post("/layers/{layer_id}/activate", response_model=GisLayerResponse)
def activate_layer(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.set_layer_active(db, layer_id, True, current_user)


@router.post("/layers/{layer_id}/deactivate", response_model=GisLayerResponse)
def deactivate_layer(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.set_layer_active(db, layer_id, False, current_user)


@router.get("/layers/{layer_id}/annotations", response_model=list[GisAnnotationResponse])
def list_annotations(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: GisAnnotationStatus | None = Query(None, alias="status"),
    feature_id: str | None = None,
) -> list[GisAnnotationResponse]:
    return services.list_annotations(db, layer_id, current_user, status_filter=status_filter, feature_id=feature_id)


@router.post("/layers/{layer_id}/annotations", response_model=GisAnnotationResponse, status_code=status.HTTP_201_CREATED)
def create_annotation(
    layer_id: UUID,
    body: GisAnnotationCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.create_annotation(db, layer_id, body, current_user)


@router.patch("/layers/{layer_id}/annotations/{annotation_id}", response_model=GisAnnotationResponse)
def update_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    body: GisAnnotationUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.update_annotation(db, layer_id, annotation_id, body, current_user)


@router.post("/layers/{layer_id}/annotations/{annotation_id}/in-review", response_model=GisAnnotationResponse)
def mark_annotation_in_review(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.in_review, current_user)


@router.post("/layers/{layer_id}/annotations/{annotation_id}/close", response_model=GisAnnotationResponse)
def close_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.closed, current_user)


@router.post("/layers/{layer_id}/annotations/{annotation_id}/reject", response_model=GisAnnotationResponse)
def reject_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.rejected, current_user)


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


@router.delete("/layers/{layer_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_permission(
    layer_id: UUID,
    permission_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    services.revoke_permission(db, layer_id, permission_id, current_user)


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
    status_filter: GisChangeRequestStatus | None = Query(None, alias="status"),
    layer_id: UUID | None = None,
) -> list[GisChangeRequestResponse]:
    return services.list_change_requests(db, current_user, status_filter=status_filter, layer_id=layer_id)


@router.patch("/change-requests/{change_request_id}", response_model=GisChangeRequestResponse)
def update_change_request(
    change_request_id: UUID,
    body: GisChangeRequestUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.update_change_request(db, change_request_id, body, current_user)


@router.post("/change-requests/{change_request_id}/request-changes", response_model=GisChangeRequestResponse)
def request_change_request_changes(
    change_request_id: UUID,
    body: GisChangeRequestReview,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.request_change_request_changes(db, change_request_id, body, current_user)


@router.post("/change-requests/{change_request_id}/reject", response_model=GisChangeRequestResponse)
def reject_change_request(
    change_request_id: UUID,
    body: GisChangeRequestReview,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.reject_change_request(db, change_request_id, body, current_user)


@router.post("/change-requests/{change_request_id}/approve", response_model=GisChangeRequestResponse)
def approve_change_request(
    change_request_id: UUID,
    body: GisChangeRequestReview,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.approve_change_request(db, change_request_id, body, current_user)


@router.post("/change-requests/{change_request_id}/apply", response_model=GisChangeRequestResponse)
def apply_change_request(
    change_request_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisChangeRequestResponse:
    return services.apply_change_request(db, change_request_id, current_user)


@router.post("/layers/{layer_id}/export-shapefile", response_model=GisLayerExportResponse, status_code=status.HTTP_202_ACCEPTED)
def request_shapefile_export(
    layer_id: UUID,
    body: GisLayerExportRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerExportResponse:
    return services.request_shapefile_export(db, layer_id, body, current_user)
