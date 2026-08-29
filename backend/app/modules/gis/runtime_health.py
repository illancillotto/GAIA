from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from time import monotonic, perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.gis.artifact_storage import probe_artifact_storage
from app.modules.gis.external_sources import (
    ExternalSourceConfigurationError,
    ExternalSourceDefinition,
    build_capabilities_url,
    get_external_sources,
)
from app.modules.gis.models import GisLayer, GisLayerExport
from app.modules.gis.schemas import (
    GisRuntimeComponentHealth,
    GisRuntimeHealthResponse,
)


@dataclass(frozen=True)
class _ScheduledExportHealth:
    version: str | None
    completed: int
    failed: int


_COMPONENT_LABELS = {
    "postgis": "PostGIS",
    "martin": "Martin tile server",
    "qgis": "QGIS Server",
    "nas": "NAS GIS",
    "external_sources": "Sorgenti GIS esterne",
}
_EXTERNAL_HEALTH_TTL_SECONDS = 300.0
_EXTERNAL_HEALTH_CACHE_LOCK = Lock()
_EXTERNAL_HEALTH_CACHE: (
    tuple[tuple[object, ...], float, GisRuntimeComponentHealth] | None
) = None


def _runtime_component(
    *,
    key: str,
    component_status: str,
    message: str,
    checked_at: datetime,
    latency_ms: float | None = None,
    details: dict | None = None,
) -> GisRuntimeComponentHealth:
    return GisRuntimeComponentHealth(
        key=key,
        label=_COMPONENT_LABELS[key],
        status=component_status,
        message=message,
        latency_ms=latency_ms,
        checked_at=checked_at,
        details=details or {},
    )


def _probe_postgis(db: Session, checked_at: datetime) -> GisRuntimeComponentHealth:
    started_at = perf_counter()
    try:
        db.execute(text("SELECT 1")).scalar_one()
        dialect = db.get_bind().dialect.name
        postgis_version = None
        component_status = "warning"
        message = "Database disponibile; estensione PostGIS non verificabile."
        if dialect == "postgresql":
            postgis_version = db.execute(text("SELECT PostGIS_Version() ")).scalar_one()
            component_status = "ok"
            message = "PostgreSQL e PostGIS rispondono correttamente."
        latest_layer_update = db.scalar(select(func.max(GisLayer.updated_at)))
        latest_export = db.scalar(select(func.max(GisLayerExport.completed_at)))
    except (SQLAlchemyError, OSError, RuntimeError, ValueError) as exc:
        return _runtime_component(
            key="postgis",
            component_status="critical",
            message="Database geografico non raggiungibile.",
            checked_at=checked_at,
            latency_ms=round((perf_counter() - started_at) * 1000, 1),
            details={"error": str(exc)},
        )
    return _runtime_component(
        key="postgis",
        component_status=component_status,
        message=message,
        checked_at=checked_at,
        latency_ms=round((perf_counter() - started_at) * 1000, 1),
        details={
            "dialect": dialect,
            "postgis_version": postgis_version,
            "latest_layer_update": latest_layer_update,
            "latest_completed_export": latest_export,
        },
    )


def _probe_http_service(
    *,
    key: str,
    label: str,
    url: str | None,
    checked_at: datetime,
) -> GisRuntimeComponentHealth:
    if not url or not url.strip():
        return _runtime_component(
            key=key,
            component_status="not_configured",
            message=f"{label} non configurato in questo ambiente.",
            checked_at=checked_at,
        )
    started_at = perf_counter()
    try:
        with urlopen(
            url,
            timeout=settings.gis_runtime_health_timeout_seconds,
        ) as response:
            status_code = response.getcode()
            response.read(1)
        latency_ms = round((perf_counter() - started_at) * 1000, 1)
        if 200 <= status_code < 400:
            return _runtime_component(
                key=key,
                component_status="ok",
                message=f"{label} risponde correttamente.",
                checked_at=checked_at,
                latency_ms=latency_ms,
                details={"url": url, "http_status": status_code},
            )
        return _runtime_component(
            key=key,
            component_status="critical",
            message=f"{label} ha restituito HTTP {status_code}.",
            checked_at=checked_at,
            latency_ms=latency_ms,
            details={"url": url, "http_status": status_code},
        )
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return _runtime_component(
            key=key,
            component_status="critical",
            message=f"{label} non raggiungibile.",
            checked_at=checked_at,
            latency_ms=round((perf_counter() - started_at) * 1000, 1),
            details={"url": url, "error": str(exc)},
        )


def _latest_scheduled_export_health(db: Session) -> _ScheduledExportHealth:
    version = db.scalar(
        select(func.max(GisLayerExport.version_label)).where(
            GisLayerExport.version_label.like("scheduled-%")
        )
    )
    if not version:
        return _ScheduledExportHealth(version=None, completed=0, failed=0)
    counts = {
        status: db.scalar(
            select(func.count(GisLayerExport.id)).where(
                GisLayerExport.version_label == version,
                GisLayerExport.status == status,
            )
        )
        or 0
        for status in ("completed", "failed")
    }
    return _ScheduledExportHealth(
        version=version,
        completed=counts["completed"],
        failed=counts["failed"],
    )


def _nas_status(
    readable: bool, writable: bool, scheduled_failed: int
) -> tuple[str, str]:
    if not (readable and writable):
        return (
            "critical",
            "Percorso NAS assente o senza permessi di lettura e scrittura.",
        )
    if scheduled_failed:
        return (
            "warning",
            "Percorso NAS disponibile, ma l'ultimo ciclo di export contiene errori.",
        )
    return "ok", "Percorso NAS disponibile in lettura e scrittura."


def _probe_nas(db: Session, checked_at: datetime) -> GisRuntimeComponentHealth:
    configured_path = settings.gis_nas_health_path.strip()
    if not configured_path:
        return _runtime_component(
            key="nas",
            component_status="not_configured",
            message="Percorso NAS GIS non configurato.",
            checked_at=checked_at,
        )
    started_at = perf_counter()
    try:
        probe = probe_artifact_storage(configured_path)
        readable = probe.readable
        writable = probe.writable
        latest_export = db.scalar(select(func.max(GisLayerExport.completed_at)))
        scheduled = _latest_scheduled_export_health(db)
    except (OSError, SQLAlchemyError) as exc:
        return _runtime_component(
            key="nas",
            component_status="critical",
            message="Verifica del percorso NAS non riuscita.",
            checked_at=checked_at,
            latency_ms=round((perf_counter() - started_at) * 1000, 1),
            details={"path": configured_path, "error": str(exc)},
        )
    component_status, message = _nas_status(readable, writable, scheduled.failed)
    return _runtime_component(
        key="nas",
        component_status=component_status,
        message=message,
        checked_at=checked_at,
        latency_ms=round((perf_counter() - started_at) * 1000, 1),
        details={
            "path": configured_path,
            "transport": probe.transport,
            "readable": readable,
            "writable": writable,
            "latest_completed_export": latest_export,
            "latest_scheduled_version": scheduled.version,
            "latest_scheduled_completed": scheduled.completed,
            "latest_scheduled_failed": scheduled.failed,
        },
    )


def _external_health_fingerprint() -> tuple[object, ...]:
    return tuple(
        (
            source.source_key,
            source.base_url,
            source.enabled,
            source.timeout_seconds,
        )
        for source in get_external_sources()
    )


def clear_external_health_cache() -> None:
    global _EXTERNAL_HEALTH_CACHE
    with _EXTERNAL_HEALTH_CACHE_LOCK:
        _EXTERNAL_HEALTH_CACHE = None


def _probe_external_source(
    source: ExternalSourceDefinition,
) -> dict[str, object]:
    started_at = perf_counter()
    try:
        url = build_capabilities_url(source)
        with urlopen(
            url,
            timeout=min(
                source.timeout_seconds,
                settings.gis_runtime_health_timeout_seconds,
            ),
        ) as response:
            status_code = response.getcode()
            response.read(1)
        source_status = "ok" if 200 <= status_code < 400 else "critical"
        detail: dict[str, object] = {"http_status": status_code}
    except (
        ExternalSourceConfigurationError,
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as exc:
        source_status = "critical"
        detail = {"error": str(exc)}
    return {
        "source_key": source.source_key,
        "status": source_status,
        "latency_ms": round((perf_counter() - started_at) * 1000, 1),
        **detail,
    }


def _external_sources_health(
    checked_at: datetime,
) -> GisRuntimeComponentHealth:
    global _EXTERNAL_HEALTH_CACHE
    sources = get_external_sources()
    if not settings.gis_external_layers_enabled:
        return _runtime_component(
            key="external_sources",
            component_status="not_configured",
            message="Layer GIS esterni disabilitati in questo ambiente.",
            checked_at=checked_at,
            details={"sources": [source.source_key for source in sources]},
        )

    fingerprint = _external_health_fingerprint()
    cached_at = monotonic()
    with _EXTERNAL_HEALTH_CACHE_LOCK:
        cached = _EXTERNAL_HEALTH_CACHE
        if (
            cached is not None
            and cached[0] == fingerprint
            and cached_at - cached[1] < _EXTERNAL_HEALTH_TTL_SECONDS
        ):
            return cached[2]

    results = [_probe_external_source(source) for source in sources]
    ok_count = sum(result["status"] == "ok" for result in results)
    if ok_count == len(results):
        component_status = "ok"
        message = "Tutte le sorgenti GIS esterne rispondono correttamente."
    elif ok_count:
        component_status = "warning"
        message = "Alcune sorgenti GIS esterne non sono raggiungibili."
    else:
        component_status = "critical"
        message = "Nessuna sorgente GIS esterna e raggiungibile."
    component = _runtime_component(
        key="external_sources",
        component_status=component_status,
        message=message,
        checked_at=checked_at,
        latency_ms=round(sum(float(item["latency_ms"]) for item in results), 1),
        details={"cache_ttl_seconds": 300, "sources": results},
    )
    with _EXTERNAL_HEALTH_CACHE_LOCK:
        _EXTERNAL_HEALTH_CACHE = (fingerprint, cached_at, component)
    return component


def get_runtime_health(db: Session) -> GisRuntimeHealthResponse:
    checked_at = datetime.now(UTC)
    components = [
        _probe_postgis(db, checked_at),
        _probe_http_service(
            key="martin",
            label="Martin tile server",
            url=settings.gis_martin_health_url,
            checked_at=checked_at,
        ),
        _probe_http_service(
            key="qgis",
            label="QGIS Server",
            url=settings.gis_qgis_server_health_url,
            checked_at=checked_at,
        ),
        _probe_nas(db, checked_at),
        _external_sources_health(checked_at),
    ]
    statuses = {component.status for component in components}
    overall_status = (
        "critical"
        if "critical" in statuses
        else "warning"
        if statuses & {"warning", "not_configured"}
        else "ok"
    )
    return GisRuntimeHealthResponse(
        generated_at=checked_at,
        status=overall_status,
        export_scheduler_enabled=settings.gis_export_scheduler_enabled,
        components=components,
    )
