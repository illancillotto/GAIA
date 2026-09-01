from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.gis import services
from app.modules.gis.external_sources import (
    ExternalSourceConfigurationError,
    build_external_request_url,
    get_external_source,
    get_external_sources,
    validate_external_layer_definition,
)
from app.modules.gis.models import GisAuditLog, GisLayer
from app.modules.gis.schemas import GisExternalLayerConfig
from app.modules.gis.territorio_availability import require_external_layers_enabled

_OPERATIONS = {
    "wms": {
        "getcapabilities": "GetCapabilities",
        "getmap": "GetMap",
        "getlegendgraphic": "GetLegendGraphic",
        "getfeatureinfo": "GetFeatureInfo",
    },
    "wfs": {
        "getcapabilities": "GetCapabilities",
        "getfeature": "GetFeature",
    },
}
_PARAMS = {
    "GetCapabilities": {
        "acceptversions": "ACCEPTVERSIONS",
        "sections": "SECTIONS",
        "updatesequence": "UPDATESEQUENCE",
        "acceptformats": "ACCEPTFORMATS",
    },
    "GetMap": {
        "bbox": "BBOX",
        "crs": "CRS",
        "srs": "SRS",
        "width": "WIDTH",
        "height": "HEIGHT",
        "styles": "STYLES",
        "format": "FORMAT",
        "transparent": "TRANSPARENT",
        "bgcolor": "BGCOLOR",
        "exceptions": "EXCEPTIONS",
        "time": "TIME",
    },
    "GetLegendGraphic": {
        "format": "FORMAT",
        "width": "WIDTH",
        "height": "HEIGHT",
        "style": "STYLE",
        "scale": "SCALE",
        "legend_options": "LEGEND_OPTIONS",
    },
    "GetFeatureInfo": {
        "bbox": "BBOX",
        "crs": "CRS",
        "srs": "SRS",
        "width": "WIDTH",
        "height": "HEIGHT",
        "i": "I",
        "j": "J",
        "x": "X",
        "y": "Y",
        "styles": "STYLES",
        "format": "FORMAT",
        "info_format": "INFO_FORMAT",
        "feature_count": "FEATURE_COUNT",
        "exceptions": "EXCEPTIONS",
    },
    "GetFeature": {
        "outputformat": "OUTPUTFORMAT",
        "count": "COUNT",
        "maxfeatures": "MAXFEATURES",
        "startindex": "STARTINDEX",
        "bbox": "BBOX",
        "srsname": "SRSNAME",
        "filter": "FILTER",
        "cql_filter": "CQL_FILTER",
        "propertyname": "PROPERTYNAME",
        "sortby": "SORTBY",
    },
}
_CONTROLLED_PARAMS = {
    "service",
    "version",
    "layers",
    "layer",
    "query_layers",
    "typename",
    "typenames",
    "url",
}
_INTEGER_LIMITS = {
    "WIDTH": 4096,
    "HEIGHT": 4096,
    "FEATURE_COUNT": 100,
    "COUNT": 10_000,
    "MAXFEATURES": 10_000,
    "STARTINDEX": 10_000_000,
}


class ExternalProxyError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class ExternalProxyPayload:
    content: bytes
    media_type: str
    status_code: int
    cache_status: str


def list_external_source_statuses() -> list[dict[str, object]]:
    return [
        {
            "source_key": source.source_key,
            "base_url": source.base_url,
            "service": source.service,
            "version": source.version,
            "supported_services": list(source.supported_services),
            "timeout_seconds": source.timeout_seconds,
            "enabled": source.enabled,
            "status": source.status,
        }
        for source in get_external_sources()
    ]


def normalize_external_query(
    service: str,
    query_items: Iterable[tuple[str, str]],
) -> tuple[str, dict[str, str]]:
    operation_name: str | None = None
    raw_params: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw_key, value in query_items:
        key = raw_key.lower()
        if key in seen:
            raise ExternalProxyError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Duplicate external GIS parameter: {raw_key}",
            )
        seen.add(key)
        if key == "request":
            operation_name = value
        else:
            raw_params.append((key, value))
    operations = _OPERATIONS.get(service)
    operation = operations.get((operation_name or "").lower()) if operations else None
    if operation is None:
        raise ExternalProxyError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "External GIS operation is not allowed",
        )

    allowed = _PARAMS[operation]
    normalized: dict[str, str] = {}
    for key, value in raw_params:
        if key in _CONTROLLED_PARAMS or key not in allowed:
            raise ExternalProxyError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"External GIS parameter is not allowed: {key}",
            )
        if len(value) > 16_384:
            raise ExternalProxyError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"External GIS parameter is too long: {key}",
            )
        canonical = allowed[key]
        _validate_integer_param(canonical, value)
        normalized[canonical] = value
    _validate_required_params(operation, normalized)
    return operation, normalized


def _validate_integer_param(name: str, value: str) -> None:
    limit = _INTEGER_LIMITS.get(name)
    if limit is None:
        return
    try:
        numeric = int(value)
    except ValueError as exc:
        raise ExternalProxyError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"External GIS parameter must be an integer: {name}",
        ) from exc
    minimum = 0 if name == "STARTINDEX" else 1
    if not minimum <= numeric <= limit:
        raise ExternalProxyError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"External GIS parameter is outside the allowed range: {name}",
        )


def _validate_required_params(operation: str, params: dict[str, str]) -> None:
    required = {
        "GetMap": ({"BBOX", "WIDTH", "HEIGHT"}, ({"CRS", "SRS"},)),
        "GetFeatureInfo": (
            {"BBOX", "WIDTH", "HEIGHT"},
            ({"CRS", "SRS"}, {"I", "X"}, {"J", "Y"}),
        ),
    }.get(operation)
    if required is None:
        return
    fixed, alternatives = required
    missing = sorted(fixed - params.keys())
    if missing or any(not group.intersection(params) for group in alternatives):
        raise ExternalProxyError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"External GIS operation {operation} is missing required parameters",
        )


def _request_defaults(operation: str, config: GisExternalLayerConfig) -> dict[str, str]:
    if operation in {"GetMap", "GetLegendGraphic", "GetFeatureInfo"}:
        defaults = {"FORMAT": config.format}
        if operation == "GetMap":
            defaults["TRANSPARENT"] = str(config.transparent).lower()
            defaults["STYLES"] = ""
        if operation == "GetFeatureInfo" and config.info_format:
            defaults["INFO_FORMAT"] = config.info_format
        return defaults
    if operation == "GetFeature":
        return {"OUTPUTFORMAT": config.info_format or config.format}
    return {}


def _cache_key(
    layer: GisLayer,
    service: str,
    operation: str,
    params: dict[str, str],
) -> str:
    payload = json.dumps(
        {
            "layer_id": str(layer.id),
            "service": service,
            "operation": operation,
            "params": sorted(params.items()),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_paths(cache_dir: Path, cache_key: str) -> tuple[Path, Path]:
    return cache_dir / f"{cache_key}.body", cache_dir / f"{cache_key}.json"


def _read_cache(
    cache_dir: Path,
    cache_key: str,
    ttl_seconds: int,
    *,
    now: float | None = None,
) -> ExternalProxyPayload | None:
    body_path, metadata_path = _cache_paths(cache_dir, cache_key)
    try:
        age = (time.time() if now is None else now) - body_path.stat().st_mtime
        if age >= ttl_seconds:
            _delete_cache_pair(body_path, metadata_path)
            return None
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return ExternalProxyPayload(
            content=body_path.read_bytes(),
            media_type=str(metadata["media_type"]),
            status_code=int(metadata["status_code"]),
            cache_status="HIT",
        )
    except (FileNotFoundError, OSError, ValueError, KeyError, json.JSONDecodeError):
        _delete_cache_pair(body_path, metadata_path)
        return None


def _delete_cache_pair(body_path: Path, metadata_path: Path) -> None:
    for path in (body_path, metadata_path):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _write_cache(
    cache_dir: Path,
    cache_key: str,
    payload: ExternalProxyPayload,
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    body_path, metadata_path = _cache_paths(cache_dir, cache_key)
    _atomic_write(body_path, payload.content)
    _atomic_write(
        metadata_path,
        json.dumps(
            {"media_type": payload.media_type, "status_code": payload.status_code},
            separators=(",", ":"),
        ).encode("utf-8"),
    )


def prune_external_cache(cache_dir: Path, max_bytes: int) -> int:
    entries: list[tuple[float, int, Path]] = []
    for path in cache_dir.glob("*.body") if cache_dir.exists() else ():
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append((stat.st_mtime, stat.st_size, path))
    total = sum(size for _mtime, size, _path in entries)
    removed = 0
    for _mtime, size, body_path in sorted(entries):
        if total <= max_bytes:
            break
        _delete_cache_pair(body_path, body_path.with_suffix(".json"))
        total -= size
        removed += 1
    return removed


def _fetch_remote(url: str, timeout_seconds: float) -> ExternalProxyPayload:
    try:
        response = httpx.get(
            url,
            timeout=timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": "GAIA-GIS-External-Proxy/1.0", "Accept": "*/*"},
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ExternalProxyError(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Timeout della sorgente territoriale.",
        ) from exc
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise ExternalProxyError(
            status.HTTP_502_BAD_GATEWAY,
            "Sorgente territoriale non raggiungibile.",
        ) from exc
    return ExternalProxyPayload(
        content=response.content,
        media_type=response.headers.get(
            "content-type", "application/octet-stream"
        ).split(";", 1)[0],
        status_code=response.status_code,
        cache_status="MISS",
    )


def execute_external_request(
    layer: GisLayer,
    service: str,
    query_items: Iterable[tuple[str, str]],
) -> ExternalProxyPayload:
    try:
        layer_config = validate_external_layer_definition(
            layer.source_type, layer.metadata_json
        )
        if layer_config is None:
            raise ExternalSourceConfigurationError("Layer is not external")
        source = get_external_source(layer_config.source_key)
        source.version_for(service)
    except ExternalSourceConfigurationError as exc:
        raise ExternalProxyError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            str(exc),
        ) from exc
    if not source.enabled:
        raise ExternalProxyError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Consultazione territoriale non attiva in questo ambiente.",
        )
    if service == "wms" and layer.source_type != "wms_external":
        raise ExternalProxyError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Layer does not support WMS proxy operations",
        )
    if service == "wfs" and layer_config.queryable != "wfs_queryable":
        raise ExternalProxyError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Layer does not support WFS queries",
        )

    operation, params = normalize_external_query(service, query_items)
    remote_params = {**_request_defaults(operation, layer_config), **params}
    url = build_external_request_url(
        source,
        layer_config,
        service=service,
        operation=operation,
        params=remote_params,
    )
    cache_dir = Path(settings.gis_external_cache_dir)
    cache_key = _cache_key(layer, service, operation, remote_params)
    cached = _read_cache(cache_dir, cache_key, layer_config.cache_ttl_seconds)
    if cached is not None:
        return cached
    payload = _fetch_remote(url, source.timeout_seconds)
    try:
        _write_cache(cache_dir, cache_key, payload)
        prune_external_cache(
            cache_dir, settings.gis_external_cache_max_mb * 1024 * 1024
        )
    except OSError:
        pass
    return payload


def proxy_external_request(
    db: Session,
    layer_id: UUID,
    current_user: ApplicationUser,
    *,
    service: str,
    query_items: Iterable[tuple[str, str]],
) -> ExternalProxyPayload:
    require_external_layers_enabled()
    layer = services.resolve_external_layer_for_proxy(db, layer_id, current_user)
    try:
        return execute_external_request(layer, service, query_items)
    except ExternalProxyError as exc:
        _audit_proxy_error(db, layer, current_user, service, exc)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _audit_proxy_error(
    db: Session,
    layer: GisLayer,
    current_user: ApplicationUser,
    service: str,
    error: ExternalProxyError,
) -> None:
    try:
        config = validate_external_layer_definition(
            layer.source_type, layer.metadata_json
        )
        source_key = config.source_key if config else None
    except ExternalSourceConfigurationError:
        source_key = None
    db.add(
        GisAuditLog(
            layer_id=layer.id,
            event_type="external_proxy.error",
            actor_user_id=current_user.id,
            target_type="external_source",
            payload_json={
                "source_key": source_key,
                "service": service,
                "status_code": error.status_code,
                "error": error.detail,
            },
        )
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
