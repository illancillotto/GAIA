from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import catalog_queries, services
from app.modules.gis.schemas import (
    GisAuditLogListResponse,
    GisLayerExportListResponse,
    GisLayerExportRequest,
    GisLayerExportResponse,
)

router = APIRouter()


# Preserve the measured legacy layout while keeping the new module formatter-safe.
# fmt: off
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
# fmt: on
