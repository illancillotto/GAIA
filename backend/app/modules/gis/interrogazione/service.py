from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.gis import services
from app.modules.gis.external_sources import ExternalSourceConfigurationError
from app.modules.gis.interrogazione import local_probes, remote_probes
from app.modules.gis.interrogazione.models import (
    InterrogationLevel,
    InterrogationPoint,
    InterrogationResponse,
    ProbeResult,
    RemoteLayer,
)
from app.modules.gis.models import GisLayer
from app.modules.gis.schemas import GisExternalLayerConfig


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _remote_layer(layer: GisLayer) -> RemoteLayer:
    metadata = _mapping(layer.metadata_json)
    try:
        config = GisExternalLayerConfig.model_validate(
            _mapping(metadata.get("external"))
        )
    except ValidationError as exc:
        raise ExternalSourceConfigurationError(
            f"Configurazione esterna non valida per {layer.name}"
        ) from exc
    return RemoteLayer(
        id=layer.id,
        name=layer.name,
        title=layer.title,
        official_source=layer.official_source,
        **config.model_dump(),
    )


def _visible_layers(
    db: Session,
    current_user: ApplicationUser,
    layer_ids: list[UUID] | None,
) -> list[RemoteLayer]:
    statement = select(GisLayer).where(
        GisLayer.workspace == "territorio",
        GisLayer.is_active.is_(True),
    )
    if layer_ids is not None:
        statement = statement.where(GisLayer.id.in_(layer_ids))
    layers = db.scalars(statement.order_by(GisLayer.name.asc())).all()
    visible = [
        layer
        for layer in layers
        if services._permission_flags(db, layer.id, current_user)["can_view"]
    ]
    return [_remote_layer(layer) for layer in visible]


def _failure(layer: RemoteLayer, exc: Exception) -> ProbeResult:
    return ProbeResult(
        source_id=str(layer.id),
        title=layer.title,
        status="failed",
        duration_ms=0.0,
        message=str(exc),
    )


def _safe_remote_probe(
    layer: RemoteLayer,
    point: InterrogationPoint,
) -> ProbeResult:
    try:
        return remote_probes.probe_remote_layer(
            layer,
            point,
            settings.gis_interrogazione_remote_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - third-party isolation boundary
        return _failure(layer, exc)


def _run_remote_probes(
    layers: list[RemoteLayer],
    point: InterrogationPoint,
) -> list[ProbeResult]:
    runnable = [layer for layer in layers if layer.queryable != "wms_visual_only"]
    allowed_ids = {
        layer.id for layer in runnable[: settings.gis_interrogazione_max_remote_layers]
    }
    results: dict[UUID, ProbeResult] = {
        layer.id: remote_probes.skipped_remote_probe(
            layer,
            "Limite massimo di sorgenti remote raggiunto.",
        )
        for layer in runnable
        if layer.id not in allowed_ids
    }
    executable = [layer for layer in layers if layer.id in allowed_ids]
    if executable:
        with ThreadPoolExecutor(max_workers=len(executable)) as executor:
            future_by_id = {
                layer.id: executor.submit(_safe_remote_probe, layer, point)
                for layer in executable
            }
            results.update(
                {layer_id: future.result() for layer_id, future in future_by_id.items()}
            )
    for layer in layers:
        if layer.queryable == "wms_visual_only":
            results[layer.id] = remote_probes.skipped_remote_probe(
                layer,
                "Layer disponibile solo per la visualizzazione.",
            )
    return [results[layer.id] for layer in layers]


def interrogate_point(
    db: Session,
    current_user: ApplicationUser,
    point: InterrogationPoint,
    layer_ids: list[UUID] | None = None,
) -> InterrogationResponse:
    if not settings.gis_interrogazione_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Interrogazione GIS non abilitata",
        )
    try:
        gaia_sources = local_probes.probe_gaia(db, point)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Interrogazione del livello GAIA non riuscita",
        ) from exc

    layers = _visible_layers(db, current_user, layer_ids)
    layers.sort(key=lambda layer: layer.official_source != "agenzia_entrate")
    remote_results = _run_remote_probes(layers, point)
    official_ids = {
        str(layer.id) for layer in layers if layer.official_source == "agenzia_entrate"
    }
    return InterrogationResponse(
        lon=point.lon,
        lat=point.lat,
        srid=point.srid,
        radius_m=point.radius_m,
        gaia=InterrogationLevel(key="gaia", sources=gaia_sources),
        catasto_ufficiale=InterrogationLevel(
            key="catasto_ufficiale",
            sources=[item for item in remote_results if item.source_id in official_ids],
        ),
        territorio=InterrogationLevel(
            key="territorio",
            sources=[
                item for item in remote_results if item.source_id not in official_ids
            ],
        ),
    )
