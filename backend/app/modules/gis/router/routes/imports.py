from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import catalog_queries, services
from app.modules.gis.schemas import (
    GisShapefileImportChangeRequestCreate,
    GisShapefileImportChangeRequestResponse,
    GisShapefileImportListResponse,
    GisShapefileImportPreviewResponse,
    GisShapefileImportResponse,
    GisShapefileImportStatus,
)

router = APIRouter()


# Preserve the measured legacy layout while keeping the new module formatter-safe.
# fmt: off
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
# fmt: on
