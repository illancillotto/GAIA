from __future__ import annotations

import base64
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.gis import external_proxy, services
from app.modules.gis.interrogazione.models import InterrogationPoint
from app.modules.gis.interrogazione.service import interrogate_point
from app.modules.gis.models import GisLayer

_PARCEL_CONTEXT_SQL = """
SELECT id::text, cfm, foglio, particella, subalterno, codice_catastale,
       nome_comune, num_distretto, nome_distretto, superficie_mq,
       superficie_grafica_mq,
       ST_X(ST_Centroid(geometry)) AS lon,
       ST_Y(ST_Centroid(geometry)) AS lat,
       ST_XMin(ST_Extent(geometry)) AS min_lon,
       ST_YMin(ST_Extent(geometry)) AS min_lat,
       ST_XMax(ST_Extent(geometry)) AS max_lon,
       ST_YMax(ST_Extent(geometry)) AS max_lat
FROM cat_particelle_current
WHERE id = :particella_id
GROUP BY id, cfm, foglio, particella, subalterno, codice_catastale,
         nome_comune, num_distretto, nome_distretto, superficie_mq,
         superficie_grafica_mq, geometry
"""


def _parcel_context(db: Session, parcel_id: UUID) -> dict[str, Any]:
    row = (
        db.execute(text(_PARCEL_CONTEXT_SQL), {"particella_id": parcel_id})
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Particella non trovata")
    return dict(row)


def _radius_m(parcel: dict[str, Any]) -> float:
    width = abs(float(parcel["max_lon"]) - float(parcel["min_lon"])) * 85_000
    height = abs(float(parcel["max_lat"]) - float(parcel["min_lat"])) * 111_320
    return max(150.0, ((width / 2) ** 2 + (height / 2) ** 2) ** 0.5)


def _catalog_layers(
    db: Session, user: ApplicationUser
) -> tuple[list[GisLayer], list[dict[str, str]]]:
    layers = db.scalars(
        select(GisLayer).where(
            GisLayer.workspace == "territorio", GisLayer.is_active.is_(True)
        )
    ).all()
    allowed: list[GisLayer] = []
    excluded: list[dict[str, str]] = []
    for layer in layers:
        if services._permission_flags(db, layer.id, user)["can_view"]:
            allowed.append(layer)
        else:
            excluded.append(
                {
                    "layer_id": str(layer.id),
                    "title": layer.title,
                    "reason": "Escluso per mancanza del permesso can_view.",
                }
            )
    return allowed, excluded


def _external_config(layer: GisLayer) -> dict[str, Any]:
    metadata = layer.metadata_json if isinstance(layer.metadata_json, dict) else {}
    external = metadata.get("external")
    return external if isinstance(external, dict) else {}


def _map_extract(
    db: Session,
    user: ApplicationUser,
    parcel: dict[str, Any],
    layers: list[GisLayer],
) -> dict[str, Any]:
    ortho = next(
        (
            layer
            for layer in layers
            if _external_config(layer).get("queryable") == "wms_visual_only"
            and (layer.metadata_json or {}).get("theme") == "ortofoto"
        ),
        None,
    )
    if ortho is None:
        return {"status": "unavailable", "message": "Ortofoto non autorizzata."}
    bbox = ",".join(
        str(parcel[key]) for key in ("min_lon", "min_lat", "max_lon", "max_lat")
    )
    try:
        payload = external_proxy.proxy_external_request(
            db,
            ortho.id,
            user,
            service="wms",
            query_items=(
                ("request", "GetMap"),
                ("bbox", bbox),
                ("crs", "EPSG:4326"),
                ("width", "900"),
                ("height", "520"),
                ("styles", ""),
                ("format", "image/png"),
                ("transparent", "false"),
            ),
        )
        return {
            "status": "ok",
            "data_url": f"data:{payload.media_type};base64,{base64.b64encode(payload.content).decode()}",
            "scale": "1:5.000",
            "attribution": _external_config(ortho).get("attribution", ""),
        }
    except Exception as exc:  # noqa: BLE001 - map is optional, snapshot keeps failure
        return {"status": "failed", "message": str(exc), "scale": "1:5.000"}


def collect_sheet_snapshot(
    db: Session,
    user: ApplicationUser,
    parcel_id: UUID,
) -> dict[str, Any]:
    parcel = _parcel_context(db, parcel_id)
    allowed, excluded = _catalog_layers(db, user)
    point = InterrogationPoint(
        lon=float(parcel["lon"]),
        lat=float(parcel["lat"]),
        srid=4326,
        radius_m=_radius_m(parcel),
    )
    interrogation = interrogate_point(db, user, point, [layer.id for layer in allowed])
    return {
        "collected_at": datetime.now(UTC).isoformat(),
        "collection_scope": {
            "centroid": {"lon": point.lon, "lat": point.lat},
            "extent": {
                key: parcel[key] for key in ("min_lon", "min_lat", "max_lon", "max_lat")
            },
            "radius_m": point.radius_m,
        },
        "parcel": parcel,
        "interrogation": asdict(interrogation),
        "excluded_layers": excluded,
        "attributions": sorted(
            {
                str(_external_config(layer).get("attribution"))
                for layer in allowed
                if _external_config(layer).get("attribution")
            }
        ),
        "map_extract": _map_extract(db, user, parcel, allowed),
    }
