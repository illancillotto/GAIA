from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import external_proxy
from app.modules.gis.models import GisLayer

router = APIRouter()


def _validate_controlled_parameter(
    layer: GisLayer, key: str, value: str, version: object
) -> bool:
    if key == "layers" and value != layer.name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "QGIS layer mismatch")
    if key == "service" and value.lower() != "wms":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "QGIS service must be WMS"
        )
    if key == "version" and value != version:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "QGIS WMS version mismatch"
        )
    return key in {"layers", "service", "version"}


def _forwarded_items(layer: GisLayer, request: Request) -> list[tuple[str, str]]:
    metadata = layer.metadata_json if isinstance(layer.metadata_json, dict) else {}
    external = (
        metadata.get("external") if isinstance(metadata.get("external"), dict) else {}
    )
    forwarded: list[tuple[str, str]] = []
    for key, value in request.query_params.multi_items():
        normalized = key.lower()
        if not _validate_controlled_parameter(
            layer, normalized, value, external.get("version")
        ):
            forwarded.append((key, value))
    return forwarded


@router.get("/external/{layer_id}/qgis-wms")
def proxy_qgis_wms(
    layer_id: UUID,
    request: Request,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    layer = db.get(GisLayer, layer_id)
    if layer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "GIS layer not found")
    payload = external_proxy.proxy_external_request(
        db,
        layer_id,
        current_user,
        service="wms",
        query_items=_forwarded_items(layer, request),
    )
    return Response(
        content=payload.content,
        status_code=payload.status_code,
        media_type=payload.media_type,
        headers={"X-GAIA-External-Cache": payload.cache_status},
    )
