from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import external_proxy, services
from app.modules.gis.interrogazione import models as interrogazione_models
from app.modules.gis.interrogazione import service as interrogazione_service
from app.modules.gis.schemas import (
    GisInterrogazioneRequest,
    GisInterrogazioneResponse,
    GisOgcPocResponse,
    GisQgisGovernanceResponse,
)

router = APIRouter()


# Preserve the measured legacy layout while keeping the new module formatter-safe.
# fmt: off
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
# fmt: on
