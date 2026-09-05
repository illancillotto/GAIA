from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import external_proxy, runtime_health, services, territorio_catalog
from app.modules.gis.schemas import (
    GisCatalogDashboardResponse,
    GisExternalSourceResponse,
    GisLayerCreate,
    GisLayerListResponse,
    GisLayerResponse,
    GisRuntimeHealthResponse,
    GisTerritorioLayerListResponse,
)

router = APIRouter()


# Preserve the measured legacy layout while keeping the new module formatter-safe.
# fmt: off
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
# fmt: on
