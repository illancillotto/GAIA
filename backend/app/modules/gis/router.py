from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import (
    catalog_queries,
    external_proxy,
    runtime_health,
    services,
    territorio_catalog,
)
from app.modules.gis.interrogazione import models as interrogazione_models
from app.modules.gis.interrogazione import service as interrogazione_service
from app.modules.gis.scheda_territoriale.router import router as scheda_router
from app.modules.gis.qgis_external_router import router as qgis_external_router
from app.modules.gis.schemas import (
    GisAnnotationCreate,
    GisAnnotationResponse,
    GisAnnotationStatus,
    GisAnnotationUpdate,
    GisAuditLogListResponse,
    GisCatalogDashboardResponse,
    GisChangeRequestCreate,
    GisChangeRequestResponse,
    GisChangeRequestReview,
    GisChangeRequestStatus,
    GisChangeRequestUpdate,
    GisExternalSourceResponse,
    GisInterrogazioneRequest,
    GisInterrogazioneResponse,
    GisLayerCreate,
    GisLayerExportListResponse,
    GisLayerExportRequest,
    GisLayerExportResponse,
    GisLayerFeatureListResponse,
    GisLayerListResponse,
    GisLayerMetadataUpdate,
    GisLayerPermissionResponse,
    GisLayerPermissionUpsert,
    GisLayerResponse,
    GisOgcPocResponse,
    GisQgisGovernanceResponse,
    GisRuntimeHealthResponse,
    GisShapefileImportChangeRequestCreate,
    GisShapefileImportChangeRequestResponse,
    GisShapefileImportListResponse,
    GisShapefileImportPreviewResponse,
    GisShapefileImportResponse,
    GisShapefileImportStatus,
    GisTerritorioLayerListResponse,
)

router = APIRouter(
    prefix="/gis",
    tags=["gis-platform"],
    dependencies=[Depends(require_module("gis"))],
)
router.include_router(scheda_router)
router.include_router(qgis_external_router)


@router.post(
    "/layers", response_model=GisLayerResponse, status_code=status.HTTP_201_CREATED
)
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


@router.get("/catalog/dashboard", response_model=GisCatalogDashboardResponse)
def get_catalog_dashboard(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisCatalogDashboardResponse:
    return services.get_catalog_dashboard(db, current_user)


@router.get("/runtime-health", response_model=GisRuntimeHealthResponse)
def get_runtime_health(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisRuntimeHealthResponse:
    del current_user
    return runtime_health.get_runtime_health(db)


@router.get("/external/sources", response_model=list[GisExternalSourceResponse])
def list_external_sources(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> list[GisExternalSourceResponse]:
    if not services.is_gis_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GIS admin role required",
        )
    return [
        GisExternalSourceResponse.model_validate(item)
        for item in external_proxy.list_external_source_statuses()
    ]


@router.get("/territorio/layers", response_model=GisTerritorioLayerListResponse)
def list_territorio_layers(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisTerritorioLayerListResponse:
    return territorio_catalog.list_territorio_layers(db, current_user)


@router.post("/interroga", response_model=GisInterrogazioneResponse)
def interroga(
    body: GisInterrogazioneRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisInterrogazioneResponse:
    point = interrogazione_models.InterrogationPoint(
        lon=body.lon,
        lat=body.lat,
        srid=body.srid,
        radius_m=body.radius_m or settings.gis_interrogazione_default_radius_m,
    )
    result = interrogazione_service.interrogate_point(
        db,
        current_user,
        point,
        body.layer_ids,
    )
    return GisInterrogazioneResponse.model_validate(result, from_attributes=True)


def _external_proxy_response(payload: external_proxy.ExternalProxyPayload) -> Response:
    return Response(
        content=payload.content,
        status_code=payload.status_code,
        media_type=payload.media_type,
        headers={"X-GAIA-External-Cache": payload.cache_status},
    )


@router.get("/external/{layer_id}/wms")
def proxy_external_wms(
    layer_id: UUID,
    request: Request,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    payload = external_proxy.proxy_external_request(
        db,
        layer_id,
        current_user,
        service="wms",
        query_items=request.query_params.multi_items(),
    )
    return _external_proxy_response(payload)


@router.get("/external/{layer_id}/wfs")
def proxy_external_wfs(
    layer_id: UUID,
    request: Request,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    payload = external_proxy.proxy_external_request(
        db,
        layer_id,
        current_user,
        service="wfs",
        query_items=request.query_params.multi_items(),
    )
    return _external_proxy_response(payload)


@router.get("/qgis/governance", response_model=GisQgisGovernanceResponse)
def get_qgis_governance(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisQgisGovernanceResponse:
    return services.get_qgis_governance(db, current_user)


@router.get("/ogc/poc", response_model=GisOgcPocResponse)
def get_ogc_poc(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisOgcPocResponse:
    return services.get_ogc_poc(db, current_user)


@router.get("/qgis/project")
def download_qgis_project(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    artifact = services.build_qgis_project_download(db, current_user)
    return Response(
        content=artifact.content,
        media_type="application/vnd.qgis.qgisproject+zip",
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "X-GIS-QGIS-Layer-Count": str(artifact.layer_count),
        },
    )


@router.post(
    "/imports/shapefile",
    response_model=GisShapefileImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_shapefile_import(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    workspace: Annotated[str, Form()],
    target_layer_name: Annotated[str, Form()],
    target_layer_title: Annotated[str, Form()],
    source_srid: Annotated[str | None, Form()] = None,
    domain_module: Annotated[str | None, Form()] = None,
    official_source: Annotated[str, Form()] = "shapefile_upload",
    encoding: Annotated[str | None, Form()] = None,
) -> GisShapefileImportResponse:
    return services.create_shapefile_import(
        db,
        filename=file.filename or "upload.zip",
        zip_bytes=file.file.read(),
        workspace=workspace,
        domain_module=domain_module,
        target_layer_name=target_layer_name,
        target_layer_title=target_layer_title,
        official_source=official_source,
        source_srid=source_srid,
        encoding=encoding,
        current_user=current_user,
    )


@router.get("/imports", response_model=GisShapefileImportListResponse)
def list_shapefile_imports(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    import_status: Annotated[
        GisShapefileImportStatus | None, Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GisShapefileImportListResponse:
    return catalog_queries.list_shapefile_imports(
        db,
        current_user,
        import_status=import_status,
        limit=limit,
        offset=offset,
    )


@router.get("/imports/{import_id}", response_model=GisShapefileImportResponse)
def get_shapefile_import(
    import_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisShapefileImportResponse:
    return services.get_shapefile_import(db, import_id, current_user)


@router.get(
    "/imports/{import_id}/preview", response_model=GisShapefileImportPreviewResponse
)
def preview_shapefile_import(
    import_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GisShapefileImportPreviewResponse:
    return services.preview_shapefile_import(db, import_id, current_user, limit=limit, offset=offset)


@router.post(
    "/imports/{import_id}/change-requests",
    response_model=GisShapefileImportChangeRequestResponse,
)
def create_change_requests_from_shapefile_import(
    import_id: UUID,
    body: GisShapefileImportChangeRequestCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisShapefileImportChangeRequestResponse:
    return services.create_change_requests_from_shapefile_import(db, import_id, body, current_user)


@router.post("/imports/{import_id}/validate", response_model=GisShapefileImportResponse)
def validate_shapefile_import(
    import_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisShapefileImportResponse:
    return services.validate_shapefile_import(db, import_id, current_user)


@router.post("/imports/{import_id}/reject", response_model=GisShapefileImportResponse)
def reject_shapefile_import(
    import_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisShapefileImportResponse:
    return services.reject_shapefile_import(db, import_id, current_user)


@router.post("/imports/{import_id}/publish", response_model=GisShapefileImportResponse)
def publish_shapefile_import(
    import_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisShapefileImportResponse:
    return services.publish_shapefile_import(db, import_id, current_user)


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


@router.get("/layers/{layer_id}/features", response_model=GisLayerFeatureListResponse)
def list_layer_features(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    query: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> GisLayerFeatureListResponse:
    return catalog_queries.list_layer_features(
        db,
        layer_id,
        current_user,
        query=query,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/layers/{layer_id}/annotations", response_model=list[GisAnnotationResponse]
)
def list_annotations(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: GisAnnotationStatus | None = Query(None, alias="status"),
    feature_id: str | None = None,
) -> list[GisAnnotationResponse]:
    return services.list_annotations(db, layer_id, current_user, status_filter=status_filter, feature_id=feature_id)


@router.post(
    "/layers/{layer_id}/annotations",
    response_model=GisAnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_annotation(
    layer_id: UUID,
    body: GisAnnotationCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.create_annotation(db, layer_id, body, current_user)


@router.patch(
    "/layers/{layer_id}/annotations/{annotation_id}",
    response_model=GisAnnotationResponse,
)
def update_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    body: GisAnnotationUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.update_annotation(db, layer_id, annotation_id, body, current_user)


@router.post(
    "/layers/{layer_id}/annotations/{annotation_id}/in-review",
    response_model=GisAnnotationResponse,
)
def mark_annotation_in_review(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.in_review, current_user)


@router.post(
    "/layers/{layer_id}/annotations/{annotation_id}/close",
    response_model=GisAnnotationResponse,
)
def close_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.closed, current_user)


@router.post(
    "/layers/{layer_id}/annotations/{annotation_id}/reject",
    response_model=GisAnnotationResponse,
)
def reject_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.rejected, current_user)


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


@router.post(
    "/layers/{layer_id}/export-shapefile",
    response_model=GisLayerExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_shapefile_export(
    layer_id: UUID,
    body: GisLayerExportRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerExportResponse:
    return services.request_shapefile_export(db, layer_id, body, current_user)


@router.get("/exports", response_model=GisLayerExportListResponse)
def list_shapefile_exports(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    layer_id: UUID | None = None,
    export_status: Annotated[str | None, Query(alias="status", max_length=32)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GisLayerExportListResponse:
    return catalog_queries.list_shapefile_exports(
        db,
        current_user,
        layer_id=layer_id,
        export_status=export_status,
        limit=limit,
        offset=offset,
    )


@router.get("/audit", response_model=GisAuditLogListResponse)
def list_audit_logs(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    layer_id: UUID | None = None,
    event_type: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GisAuditLogListResponse:
    return catalog_queries.list_audit_logs(
        db,
        current_user,
        layer_id=layer_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
