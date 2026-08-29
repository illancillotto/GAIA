from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import ValidationError

from app.core.config import settings
from app.modules.gis.schemas import GisExternalLayerConfig

EXTERNAL_SOURCE_TYPES = frozenset({"wms_external", "wfs_external"})


class ExternalSourceConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class ExternalSourceDefinition:
    source_key: str
    base_url: str
    service: str
    version: str
    service_versions: tuple[tuple[str, str], ...]
    timeout_seconds: float
    enabled: bool

    @property
    def supported_services(self) -> tuple[str, ...]:
        return tuple(service for service, _version in self.service_versions)

    def version_for(self, service: str) -> str:
        for candidate, version in self.service_versions:
            if candidate == service:
                return version
        raise ExternalSourceConfigurationError(
            f"External source {self.source_key} does not support {service}"
        )

    @property
    def status(self) -> str:
        if not self.base_url.strip():
            return "not_configured"
        return "enabled" if self.enabled else "disabled"


def is_external_source_type(source_type: str) -> bool:
    return source_type in EXTERNAL_SOURCE_TYPES


def get_external_sources() -> tuple[ExternalSourceDefinition, ...]:
    timeout = settings.gis_external_default_timeout_seconds
    globally_enabled = settings.gis_external_layers_enabled
    definitions = (
        (
            "ras_sitr_vector",
            settings.gis_external_ras_vector_url,
            "wms",
            "1.3.0",
            (("wms", "1.3.0"), ("wfs", "1.1.0")),
        ),
        (
            "ras_sitr_raster",
            settings.gis_external_ras_raster_url,
            "wms",
            "1.3.0",
            (("wms", "1.3.0"),),
        ),
        (
            "ade_catasto_wms",
            settings.gis_external_ade_wms_url,
            "wms",
            "1.3.0",
            (("wms", "1.3.0"),),
        ),
    )
    return tuple(
        ExternalSourceDefinition(
            source_key=source_key,
            base_url=base_url.strip(),
            service=service,
            version=version,
            service_versions=service_versions,
            timeout_seconds=timeout,
            enabled=globally_enabled and bool(base_url.strip()),
        )
        for source_key, base_url, service, version, service_versions in definitions
    )


def get_external_source(source_key: str) -> ExternalSourceDefinition:
    for source in get_external_sources():
        if source.source_key == source_key:
            return source
    raise ExternalSourceConfigurationError(f"Unknown external GIS source: {source_key}")


def validate_external_layer_definition(
    source_type: str,
    metadata: dict[str, Any] | None,
) -> GisExternalLayerConfig | None:
    if not is_external_source_type(source_type):
        return None
    if not isinstance(metadata, dict):
        raise ExternalSourceConfigurationError(
            "External GIS layers require metadata.external"
        )
    try:
        config = GisExternalLayerConfig.model_validate(metadata.get("external"))
    except ValidationError as exc:
        raise ExternalSourceConfigurationError(
            "Invalid metadata.external configuration"
        ) from exc

    expected_service = "wms" if source_type == "wms_external" else "wfs"
    if config.service != expected_service:
        raise ExternalSourceConfigurationError(
            f"{source_type} requires service {expected_service}"
        )
    source = get_external_source(config.source_key)
    expected_version = source.version_for(config.service)
    if config.version != expected_version:
        raise ExternalSourceConfigurationError(
            f"External source {source.source_key} requires "
            f"{config.service} version {expected_version}"
        )
    return config


def normalize_external_layer_metadata(
    source_type: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    config = validate_external_layer_definition(source_type, metadata)
    if config is None:
        return metadata
    normalized = deepcopy(metadata)
    normalized["external"] = config.model_dump(mode="json")
    normalized["read_only"] = True
    normalized["qgis"] = {
        **_mapping(normalized.get("qgis")),
        "mode": "not_published",
        "editable": False,
    }
    normalized["export"] = {
        **_mapping(normalized.get("export")),
        "shapefile": False,
    }
    return normalized


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_external_request_url(
    source: ExternalSourceDefinition,
    layer_config: GisExternalLayerConfig,
    *,
    service: str,
    operation: str,
    params: dict[str, str],
) -> str:
    if not source.base_url:
        raise ExternalSourceConfigurationError(
            f"External source {source.source_key} has no URL"
        )
    version = source.version_for(service)
    split = urlsplit(source.base_url)
    if split.scheme not in {"http", "https"} or not split.netloc:
        raise ExternalSourceConfigurationError(
            f"External source {source.source_key} has an invalid URL"
        )
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query.update(params)
    query.update(
        {
            "SERVICE": service.upper(),
            "VERSION": version,
            "REQUEST": operation,
        }
    )
    if operation not in {"GetCapabilities"}:
        if service == "wms":
            query["LAYER" if operation == "GetLegendGraphic" else "LAYERS"] = (
                layer_config.remote_layer
            )
            if operation == "GetFeatureInfo":
                query["QUERY_LAYERS"] = layer_config.remote_layer
        else:
            query["TYPENAME"] = layer_config.remote_layer
    return urlunsplit(
        (split.scheme, split.netloc, split.path, urlencode(query), split.fragment)
    )


def build_capabilities_url(source: ExternalSourceDefinition) -> str:
    split = urlsplit(source.base_url)
    if split.scheme not in {"http", "https"} or not split.netloc:
        raise ExternalSourceConfigurationError(
            f"External source {source.source_key} has an invalid URL"
        )
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query.update(
        {
            "SERVICE": source.service.upper(),
            "VERSION": source.version,
            "REQUEST": "GetCapabilities",
        }
    )
    return urlunsplit(
        (split.scheme, split.netloc, split.path, urlencode(query), split.fragment)
    )
