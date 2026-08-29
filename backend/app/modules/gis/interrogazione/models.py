from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

ProbeStatus = Literal["ok", "empty", "failed", "skipped"]


@dataclass(frozen=True)
class InterrogationPoint:
    lon: float
    lat: float
    srid: int
    radius_m: float


@dataclass(frozen=True)
class ProbeResult:
    source_id: str
    title: str
    status: ProbeStatus
    duration_ms: float
    data: list[dict[str, Any]] = field(default_factory=list)
    message: str | None = None


@dataclass(frozen=True)
class InterrogationLevel:
    key: Literal["gaia", "catasto_ufficiale", "territorio"]
    sources: list[ProbeResult]


@dataclass(frozen=True)
class InterrogationResponse:
    lon: float
    lat: float
    srid: int
    radius_m: float
    gaia: InterrogationLevel
    catasto_ufficiale: InterrogationLevel
    territorio: InterrogationLevel


@dataclass(frozen=True)
class RemoteLayer:
    id: UUID
    name: str
    title: str
    official_source: str
    source_key: str
    remote_layer: str
    queryable: Literal["wfs_queryable", "wms_infoable", "wms_visual_only"]
    service: Literal["wms", "wfs"]
    version: str
    format: str
    transparent: bool
    srid: int
    info_format: str | None
    cache_ttl_seconds: int
    license: str
    attribution: str
