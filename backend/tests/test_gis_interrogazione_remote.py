from __future__ import annotations

from typing import Self
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from app.modules.gis.external_sources import ExternalSourceDefinition
from app.modules.gis.interrogazione import remote_probes
from app.modules.gis.interrogazione.models import InterrogationPoint, RemoteLayer


def _layer(queryable: str = "wfs_queryable") -> RemoteLayer:
    return RemoteLayer(
        id=uuid4(),
        name="remote",
        title="Remote layer",
        official_source="ras_sitr",
        source_key="test_source",
        remote_layer="dbu:remote",
        queryable=queryable,  # type: ignore[arg-type]
        service="wms",
        version="1.3.0",
        format="image/png",
        transparent=True,
        srid=4326,
        info_format="application/json",
        cache_ttl_seconds=60,
        license="CC BY 4.0",
        attribution="Source",
    )


def _point(srid: int = 4326) -> InterrogationPoint:
    return InterrogationPoint(lon=9, lat=40, srid=srid, radius_m=100)


def _source(enabled: bool = True) -> ExternalSourceDefinition:
    return ExternalSourceDefinition(
        source_key="test_source",
        base_url="https://example.test/ows",
        service="wms",
        version="1.3.0",
        service_versions=(("wms", "1.3.0"), ("wfs", "1.1.0")),
        timeout_seconds=8,
        enabled=enabled,
    )


class _Response:
    def __init__(
        self,
        *,
        content_type: str,
        payload: object = None,
        text: str = "",
        error: Exception | None = None,
    ) -> None:
        self.headers = {"content-type": content_type}
        self.payload = payload
        self.text = text
        self.error = error

    def json(self) -> object:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    def raise_for_status(self) -> None:
        if self.error:
            raise self.error


class _Client:
    response: _Response
    calls: list[tuple[str, dict[str, str]]]
    error: Exception | None = None

    def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
        assert timeout == 3
        assert follow_redirects is True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def get(self, url: str, headers: dict[str, str]) -> _Response:
        self.calls.append((url, headers))
        if self.error:
            raise self.error
        return self.response


@pytest.fixture(autouse=True)
def configure_source(monkeypatch: pytest.MonkeyPatch) -> None:
    _Client.calls = []
    _Client.error = None
    monkeypatch.setattr(remote_probes, "get_external_source", lambda key: _source())
    monkeypatch.setattr(remote_probes.httpx, "Client", _Client)


def test_wfs_probe_uses_spatial_filter_and_normalizes_feature_collection() -> None:
    _Client.response = _Response(
        content_type="application/json",
        payload={"type": "FeatureCollection", "features": [{"id": "f.1"}]},
    )

    result = remote_probes.probe_remote_layer(_layer(), _point(), 3)

    assert result.status == "ok"
    assert result.data == [{"id": "f.1"}]
    query = parse_qs(urlsplit(_Client.calls[0][0]).query)
    assert query["SERVICE"] == ["WFS"]
    assert query["REQUEST"] == ["GetFeature"]
    assert query["TYPENAME"] == ["dbu:remote"]
    assert query["BBOX"][0].endswith("EPSG:4326")
    assert _Client.calls[0][1] == {"Accept": "application/json"}


def test_wms_probe_normalizes_json_html_and_empty_responses() -> None:
    layer = _layer("wms_infoable")
    _Client.response = _Response(
        content_type="application/json", payload={"parcel": "12"}
    )
    json_result = remote_probes.probe_remote_layer(layer, _point(3857), 3)

    _Client.response = _Response(
        content_type="text/html", text="<p>Zona <strong>A</strong></p>"
    )
    html_result = remote_probes.probe_remote_layer(layer, _point(), 3)

    _Client.response = _Response(content_type="text/plain", text="   ")
    empty_result = remote_probes.probe_remote_layer(layer, _point(), 3)

    assert json_result.data == [{"parcel": "12"}]
    assert html_result.data == [{"text": "Zona A"}]
    assert empty_result.status == "empty"
    assert empty_result.message == "Nessun elemento trovato."
    query = parse_qs(urlsplit(_Client.calls[0][0]).query)
    assert query["REQUEST"] == ["GetFeatureInfo"]
    assert query["CRS"] == ["EPSG:3857"]


def test_remote_probe_maps_malformed_json_timeout_and_unsupported_payload() -> None:
    _Client.response = _Response(
        content_type="application/json", payload=ValueError("bad json")
    )
    malformed = remote_probes.probe_remote_layer(_layer(), _point(), 3)

    _Client.error = httpx.ReadTimeout("slow")
    timeout = remote_probes.probe_remote_layer(_layer(), _point(), 3)

    _Client.error = None
    _Client.response = _Response(content_type="application/json", payload=[1, 2])
    filtered = remote_probes.probe_remote_layer(_layer(), _point(), 3)

    _Client.response = _Response(content_type="application/json", payload="bad")
    unsupported = remote_probes.probe_remote_layer(_layer(), _point(), 3)

    assert malformed.status == "failed"
    assert malformed.message == "bad json"
    assert timeout.status == "failed"
    assert timeout.message == "slow"
    assert filtered.status == "empty"
    assert unsupported.status == "failed"


def test_wms_infoable_probe_extracts_dtm_quota_as_indicative_value() -> None:
    layer = _layer("wms_infoable")
    _Client.response = _Response(
        content_type="application/json",
        payload={
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {"GRAY_INDEX": "5.322000026702881"}}],
        },
    )

    result = remote_probes.probe_remote_layer(layer, _point(), 3)

    assert result.status == "ok"
    assert result.data == [{"quota (m s.l.m.)": 5.32}]
    assert result.message == remote_probes._QUOTA_DISCLAIMER
    assert "rilievo di cantiere" in result.message


def test_wms_infoable_probe_ignores_gray_index_extraction_when_key_missing() -> None:
    layer = _layer("wms_infoable")
    _Client.response = _Response(
        content_type="application/json", payload={"parcel": "12"}
    )

    result = remote_probes.probe_remote_layer(layer, _point(), 3)

    assert result.status == "ok"
    assert result.data == [{"parcel": "12"}]
    assert result.message is None


def test_wms_infoable_probe_treats_unparsable_gray_index_as_missing_quota() -> None:
    layer = _layer("wms_infoable")
    _Client.response = _Response(
        content_type="application/json",
        payload={"properties": {"GRAY_INDEX": "no data"}},
    )

    result = remote_probes.probe_remote_layer(layer, _point(), 3)

    assert result.status == "ok"
    assert result.data == [{"properties": {"GRAY_INDEX": "no data"}}]
    assert result.message is None


def test_visual_only_and_disabled_sources_never_make_http_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visual = remote_probes.probe_remote_layer(_layer("wms_visual_only"), _point(), 3)
    monkeypatch.setattr(
        remote_probes, "get_external_source", lambda key: _source(False)
    )
    disabled = remote_probes.probe_remote_layer(_layer(), _point(), 3)
    limited = remote_probes.skipped_remote_probe(_layer(), "limit")

    assert visual.status == "skipped"
    assert disabled.status == "skipped"
    assert limited.message == "limit"
    assert _Client.calls == []
