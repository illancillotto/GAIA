from __future__ import annotations

import re
import time
from typing import Any

import httpx

from app.modules.gis.external_sources import (
    ExternalSourceConfigurationError,
    build_external_request_url,
    get_external_source,
)
from app.modules.gis.interrogazione.models import (
    InterrogationPoint,
    ProbeResult,
    ProbeStatus,
    RemoteLayer,
)
from app.modules.gis.schemas import GisExternalLayerConfig

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def _layer_config(layer: RemoteLayer) -> GisExternalLayerConfig:
    return GisExternalLayerConfig(
        source_key=layer.source_key,
        service=layer.service,
        version=layer.version,
        remote_layer=layer.remote_layer,
        format=layer.format,
        transparent=layer.transparent,
        srid=layer.srid,
        queryable=layer.queryable,
        info_format=layer.info_format,
        cache_ttl_seconds=layer.cache_ttl_seconds,
        license=layer.license,
        attribution=layer.attribution,
    )


def _bbox(point: InterrogationPoint) -> str:
    delta = point.radius_m / 111_320 if point.srid == 4326 else point.radius_m
    bounds = (
        point.lon - delta,
        point.lat - delta,
        point.lon + delta,
        point.lat + delta,
    )
    return ",".join(f"{value:.8f}" for value in bounds)


def _request_url(layer: RemoteLayer, point: InterrogationPoint) -> str:
    source = get_external_source(layer.source_key)
    config = _layer_config(layer)
    if layer.queryable == "wfs_queryable":
        return build_external_request_url(
            source,
            config,
            service="wfs",
            operation="GetFeature",
            params={
                "BBOX": f"{_bbox(point)},EPSG:{point.srid}",
                "SRSNAME": f"EPSG:{point.srid}",
                "OUTPUTFORMAT": "application/json",
                "COUNT": "25",
            },
        )
    return build_external_request_url(
        source,
        config,
        service="wms",
        operation="GetFeatureInfo",
        params={
            "BBOX": _bbox(point),
            "CRS": f"EPSG:{point.srid}",
            "WIDTH": "101",
            "HEIGHT": "101",
            "I": "50",
            "J": "50",
            "STYLES": "",
            "FORMAT": layer.format,
            "INFO_FORMAT": layer.info_format or "application/json",
            "FEATURE_COUNT": "25",
        },
    )


def _json_data(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("features"), list):
        return [item for item in payload["features"] if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise ValueError("Formato JSON remoto non supportato")


def _response_data(response: httpx.Response) -> list[dict[str, Any]]:
    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        return _json_data(response.json())
    text = _WHITESPACE.sub(" ", _HTML_TAG.sub(" ", response.text)).strip()
    if not text:
        return []
    return [{"text": text}]


def _result(
    layer: RemoteLayer,
    status: ProbeStatus,
    started_at: float,
    *,
    data: list[dict[str, Any]] | None = None,
    message: str | None = None,
) -> ProbeResult:
    return ProbeResult(
        source_id=str(layer.id),
        title=layer.title,
        status=status,
        duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        data=data or [],
        message=message,
    )


def skipped_remote_probe(layer: RemoteLayer, message: str) -> ProbeResult:
    return ProbeResult(
        source_id=str(layer.id),
        title=layer.title,
        status="skipped",
        duration_ms=0.0,
        message=message,
    )


def probe_remote_layer(
    layer: RemoteLayer,
    point: InterrogationPoint,
    timeout_seconds: float,
) -> ProbeResult:
    started_at = time.perf_counter()
    if layer.queryable == "wms_visual_only":
        return _result(
            layer,
            "skipped",
            started_at,
            message="Layer disponibile solo per la visualizzazione.",
        )
    try:
        source = get_external_source(layer.source_key)
        if not source.enabled:
            return _result(
                layer,
                "skipped",
                started_at,
                message="Sorgente esterna disabilitata.",
            )
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(
                _request_url(layer, point),
                headers={"Accept": layer.info_format or "application/json"},
            )
            response.raise_for_status()
            data = _response_data(response)
        return _result(
            layer,
            "ok" if data else "empty",
            started_at,
            data=data,
            message=None if data else "Nessun elemento trovato.",
        )
    except (httpx.HTTPError, ValueError, ExternalSourceConfigurationError) as exc:
        return _result(layer, "failed", started_at, message=str(exc))
