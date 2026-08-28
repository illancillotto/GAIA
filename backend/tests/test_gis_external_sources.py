from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest
from app.core.config import settings
from app.modules.gis.external_sources import (
    ExternalSourceConfigurationError,
    ExternalSourceDefinition,
    build_capabilities_url,
    build_external_request_url,
    get_external_source,
    get_external_sources,
    is_external_source_type,
    normalize_external_layer_metadata,
    validate_external_layer_definition,
)
from app.modules.gis.schemas import GisExternalLayerConfig


def _external_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "source_key": "ras_sitr_vector",
        "service": "wms",
        "version": "1.3.0",
        "remote_layer": "dbu:areebonifica",
        "format": "image/png",
        "transparent": True,
        "srid": 3857,
        "queryable": "wfs_queryable",
        "info_format": "application/json",
        "cache_ttl_seconds": 300,
        "license": "IODL 2.0",
        "attribution": "Regione Autonoma della Sardegna",
    }
    config.update(overrides)
    return config


def _source(**overrides: object) -> ExternalSourceDefinition:
    values: dict[str, object] = {
        "source_key": "ras_sitr_vector",
        "base_url": "https://maps.example.test/ows?token=public",
        "service": "wms",
        "version": "1.3.0",
        "service_versions": (("wms", "1.3.0"), ("wfs", "1.1.0")),
        "timeout_seconds": 12.0,
        "enabled": True,
    }
    values.update(overrides)
    return ExternalSourceDefinition(**values)  # type: ignore[arg-type]


def test_registry_reflects_settings_and_source_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "gis_external_layers_enabled", True)
    monkeypatch.setattr(settings, "gis_external_default_timeout_seconds", 7.5)
    monkeypatch.setattr(
        settings, "gis_external_ras_vector_url", " https://vector.test/ows "
    )
    monkeypatch.setattr(settings, "gis_external_ras_raster_url", "")
    monkeypatch.setattr(settings, "gis_external_ade_wms_url", "https://ade.test/wms")

    sources = get_external_sources()

    assert [source.source_key for source in sources] == [
        "ras_sitr_vector",
        "ras_sitr_raster",
        "ade_catasto_wms",
    ]
    assert sources[0].base_url == "https://vector.test/ows"
    assert sources[0].supported_services == ("wms", "wfs")
    assert sources[0].timeout_seconds == 7.5
    assert sources[0].status == "enabled"
    assert sources[1].status == "not_configured"
    assert sources[2].version_for("wms") == "1.3.0"

    monkeypatch.setattr(settings, "gis_external_layers_enabled", False)
    assert get_external_sources()[0].status == "disabled"


def test_registry_lookup_and_source_type_validation() -> None:
    assert is_external_source_type("wms_external") is True
    assert is_external_source_type("postgis") is False
    assert get_external_source("ras_sitr_vector").source_key == "ras_sitr_vector"

    with pytest.raises(ExternalSourceConfigurationError, match="Unknown external"):
        get_external_source("client_supplied")
    with pytest.raises(ExternalSourceConfigurationError, match="does not support"):
        _source().version_for("wmts")


@pytest.mark.parametrize(
    ("source_type", "metadata", "message"),
    [
        ("wms_external", None, "require metadata.external"),
        ("wms_external", {}, "Invalid metadata.external"),
        (
            "wms_external",
            {"external": _external_config(service="wfs", version="1.1.0")},
            "requires service wms",
        ),
        (
            "wms_external",
            {"external": _external_config(source_key="unknown")},
            "Unknown external GIS source",
        ),
        (
            "wms_external",
            {"external": _external_config(version="1.1.0")},
            "requires wms version 1.3.0",
        ),
    ],
)
def test_external_layer_validation_rejects_invalid_definitions(
    source_type: str,
    metadata: dict[str, object] | None,
    message: str,
) -> None:
    with pytest.raises(ExternalSourceConfigurationError, match=message):
        validate_external_layer_definition(source_type, metadata)


def test_external_layer_validation_and_normalization_enforce_read_only_policy() -> None:
    metadata = {
        "external": _external_config(),
        "read_only": False,
        "qgis": {"mode": "controlled_edit", "custom": "kept"},
        "export": {"shapefile": True, "reason": "kept"},
    }

    config = validate_external_layer_definition("wms_external", metadata)
    normalized = normalize_external_layer_metadata("wms_external", metadata)

    assert config is not None
    assert config.remote_layer == "dbu:areebonifica"
    assert normalized is not metadata
    assert normalized == {
        "external": _external_config(),
        "read_only": True,
        "qgis": {"mode": "not_published", "custom": "kept", "editable": False},
        "export": {"shapefile": False, "reason": "kept"},
    }
    assert normalize_external_layer_metadata("postgis", metadata) is metadata

    normalized_non_mappings = normalize_external_layer_metadata(
        "wms_external",
        {"external": _external_config(), "qgis": "bad", "export": []},
    )
    assert normalized_non_mappings["qgis"] == {
        "mode": "not_published",
        "editable": False,
    }
    assert normalized_non_mappings["export"] == {"shapefile": False}


@pytest.mark.parametrize(
    "overrides",
    [
        {"service": "wfs", "version": "1.1.0", "queryable": "wms_visual_only"},
        {"queryable": "wms_infoable", "info_format": None},
    ],
)
def test_external_schema_rejects_incoherent_query_modes(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ExternalSourceConfigurationError, match="Invalid metadata"):
        validate_external_layer_definition(
            "wfs_external"
            if overrides["queryable"] == "wms_visual_only"
            else "wms_external",
            {"external": _external_config(**overrides)},
        )


def test_external_request_url_is_governed_by_source_and_layer() -> None:
    source = _source()
    config = GisExternalLayerConfig.model_validate(_external_config())

    map_url = build_external_request_url(
        source,
        config,
        service="wms",
        operation="GetMap",
        params={"BBOX": "0,0,1,1"},
    )
    map_query = parse_qs(urlsplit(map_url).query)
    assert urlsplit(map_url).netloc == "maps.example.test"
    assert map_query == {
        "token": ["public"],
        "BBOX": ["0,0,1,1"],
        "SERVICE": ["WMS"],
        "VERSION": ["1.3.0"],
        "REQUEST": ["GetMap"],
        "LAYERS": ["dbu:areebonifica"],
    }

    legend_query = parse_qs(
        urlsplit(
            build_external_request_url(
                source,
                config,
                service="wms",
                operation="GetLegendGraphic",
                params={},
            )
        ).query
    )
    assert legend_query["LAYER"] == ["dbu:areebonifica"]

    info_query = parse_qs(
        urlsplit(
            build_external_request_url(
                source,
                config,
                service="wms",
                operation="GetFeatureInfo",
                params={},
            )
        ).query
    )
    assert info_query["QUERY_LAYERS"] == ["dbu:areebonifica"]

    feature_query = parse_qs(
        urlsplit(
            build_external_request_url(
                source,
                config,
                service="wfs",
                operation="GetFeature",
                params={},
            )
        ).query
    )
    assert feature_query["TYPENAME"] == ["dbu:areebonifica"]
    assert feature_query["VERSION"] == ["1.1.0"]

    capabilities_query = parse_qs(
        urlsplit(
            build_external_request_url(
                source,
                config,
                service="wms",
                operation="GetCapabilities",
                params={},
            )
        ).query
    )
    assert "LAYERS" not in capabilities_query


def test_capabilities_url_and_invalid_source_urls() -> None:
    query = parse_qs(urlsplit(build_capabilities_url(_source())).query)
    assert query["SERVICE"] == ["WMS"]
    assert query["REQUEST"] == ["GetCapabilities"]

    config = GisExternalLayerConfig.model_validate(_external_config())
    with pytest.raises(ExternalSourceConfigurationError, match="has no URL"):
        build_external_request_url(
            _source(base_url=""),
            config,
            service="wms",
            operation="GetMap",
            params={},
        )
    with pytest.raises(ExternalSourceConfigurationError, match="invalid URL"):
        build_external_request_url(
            _source(base_url="file:///tmp/map"),
            config,
            service="wms",
            operation="GetMap",
            params={},
        )
    with pytest.raises(ExternalSourceConfigurationError, match="invalid URL"):
        build_capabilities_url(_source(base_url="relative/path"))
