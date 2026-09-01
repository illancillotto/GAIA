from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.modules.gis import qgis_ogc_proxy, qgis_ogc_router
from app.modules.gis.models import GisLayer


def layer(**overrides: object) -> GisLayer:
    values = {
        "id": uuid4(),
        "workspace": "catasto",
        "name": "particelle-ufficiali",
        "title": "Particelle ufficiali",
        "source_type": "postgis",
        "postgis_schema": "catasto",
        "postgis_table": "particelle",
        "geometry_column": "geometry",
        "geometry_type": "MULTIPOLYGON",
        "srid": 4326,
        "is_active": True,
        "metadata_json": {"qgis": {"mode": "read_only"}},
    }
    values.update(overrides)
    return GisLayer(**values)


class FakeDb:
    def __init__(self, item: GisLayer | None) -> None:
        self.item = item

    def get(self, model: object, layer_id: UUID) -> GisLayer | None:
        assert model is GisLayer
        return self.item if self.item is not None and self.item.id == layer_id else None


def request(query: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": query.encode(),
            "headers": [],
        }
    )


def assert_http_error(status_code: int, detail: str, callback: object) -> None:
    with pytest.raises(HTTPException) as error:
        callback()
    assert error.value.status_code == status_code
    assert error.value.detail == detail


def test_ogc_route_requires_gaia_authentication() -> None:
    response = TestClient(app).get(
        f"/gis/ogc/layers/{uuid4()}?SERVICE=WMS&REQUEST=GetCapabilities"
    )
    assert response.status_code == 401


def test_service_layer_name_is_stable_and_safe() -> None:
    assert qgis_ogc_proxy.service_layer_name(layer()) == (
        "catasto__particelle_ufficiali"
    )


def test_resolve_publishable_layer_applies_catalog_and_permission_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=7, role="viewer")
    missing_id = uuid4()
    assert_http_error(
        404,
        "GIS layer not found",
        lambda: qgis_ogc_proxy.resolve_publishable_layer(FakeDb(None), missing_id, user),
    )
    inactive = layer(is_active=False)
    assert_http_error(
        404,
        "GIS layer not found",
        lambda: qgis_ogc_proxy.resolve_publishable_layer(
            FakeDb(inactive), inactive.id, user
        ),
    )
    for hidden in (
        layer(source_type="wms_external"),
        layer(metadata_json={"qgis": {"mode": "not_published"}}),
    ):
        assert_http_error(
            404,
            "Layer non pubblicabile tramite il proxy OGC GAIA.",
            lambda hidden=hidden: qgis_ogc_proxy.resolve_publishable_layer(
                FakeDb(hidden), hidden.id, user
            ),
        )

    visible = layer()
    monkeypatch.setattr(
        qgis_ogc_proxy.services,
        "_permission_flags",
        lambda *args: {"can_view": False},
    )
    assert_http_error(
        403,
        "GIS layer permission denied",
        lambda: qgis_ogc_proxy.resolve_publishable_layer(
            FakeDb(visible), visible.id, user
        ),
    )
    monkeypatch.setattr(
        qgis_ogc_proxy.services,
        "_permission_flags",
        lambda *args: {"can_view": True},
    )
    assert (
        qgis_ogc_proxy.resolve_publishable_layer(FakeDb(visible), visible.id, user)
        is visible
    )


def test_normalize_wms_get_map_controls_layer_and_parameters() -> None:
    item = layer()
    name = qgis_ogc_proxy.service_layer_name(item)
    result = qgis_ogc_proxy.normalize_query(
        item,
        [
            ("SERVICE", "WMS"),
            ("REQUEST", "GetMap"),
            ("VERSION", "1.3.0"),
            ("LAYERS", name),
            ("BBOX", "1,2,3,4"),
            ("WIDTH", "256"),
            ("HEIGHT", "128"),
            ("CRS", "EPSG:4326"),
            ("FORMAT", "image/png"),
        ],
    )
    assert result == (
        "wms",
        "GetMap",
        "1.3.0",
        {
            "BBOX": "1,2,3,4",
            "WIDTH": "256",
            "HEIGHT": "128",
            "CRS": "EPSG:4326",
            "FORMAT": "image/png",
        },
    )


def test_normalize_wfs_get_feature_uses_read_only_defaults() -> None:
    item = layer()
    name = qgis_ogc_proxy.service_layer_name(item)
    assert qgis_ogc_proxy.normalize_query(
        item,
        [
            ("SERVICE", "WFS"),
            ("REQUEST", "GetFeature"),
            ("TYPENAMES", name),
            ("COUNT", "10"),
            ("STARTINDEX", "0"),
        ],
    ) == (
        "wfs",
        "GetFeature",
        "2.0.0",
        {"COUNT": "10", "STARTINDEX": "0"},
    )


@pytest.mark.parametrize(
    ("query", "status_code", "detail"),
    [
        (
            [("SERVICE", "WMS"), ("service", "WMS")],
            422,
            "Parametro OGC duplicato: service",
        ),
        (
            [("SERVICE", "WMS"), ("REQUEST", "GetMap"), ("FILTER", "x" * 16_385)],
            422,
            "Parametro OGC troppo lungo: FILTER",
        ),
        (
            [("SERVICE", "WFS"), ("REQUEST", "Transaction")],
            400,
            "WFS-T non e abilitato: il proxy OGC GAIA e solo lettura.",
        ),
        (
            [("SERVICE", "WCS"), ("REQUEST", "GetCoverage")],
            422,
            "Operazione OGC non consentita.",
        ),
        (
            [("SERVICE", "WMS"), ("REQUEST", "GetMap"), ("VERSION", "9.9")],
            422,
            "Versione OGC non supportata.",
        ),
        (
            [("SERVICE", "WMS"), ("REQUEST", "GetMap"), ("LAYERS", "other")],
            422,
            "Layer OGC non coerente con layer_id.",
        ),
        (
            [("SERVICE", "WFS"), ("REQUEST", "GetFeature"), ("TYPENAME", "other")],
            422,
            "Layer OGC non coerente con layer_id.",
        ),
        (
            [("SERVICE", "WMS"), ("REQUEST", "GetCapabilities"), ("MAP", "/tmp/x")],
            422,
            "Parametro OGC non consentito: map",
        ),
        (
            [("SERVICE", "WFS"), ("REQUEST", "GetFeature"), ("COUNT", "many")],
            422,
            "Il parametro OGC COUNT deve essere intero.",
        ),
        (
            [("SERVICE", "WFS"), ("REQUEST", "GetFeature"), ("COUNT", "10001")],
            422,
            "Il parametro OGC COUNT supera il limite consentito.",
        ),
        (
            [("SERVICE", "WMS"), ("REQUEST", "GetMap")],
            422,
            "GetMap richiede BBOX, WIDTH, HEIGHT e CRS/SRS.",
        ),
    ],
)
def test_normalize_rejects_unsafe_or_invalid_queries(
    query: list[tuple[str, str]], status_code: int, detail: str
) -> None:
    assert_http_error(
        status_code,
        detail,
        lambda: qgis_ogc_proxy.normalize_query(layer(), query),
    )


def test_upstream_params_force_the_catalog_layer() -> None:
    item = layer()
    name = qgis_ogc_proxy.service_layer_name(item)
    assert qgis_ogc_proxy._upstream_params(
        item, "wms", "GetMap", "1.3.0", {"WIDTH": "10"}
    ) == {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.3.0",
        "WIDTH": "10",
        "LAYERS": name,
    }
    assert qgis_ogc_proxy._upstream_params(
        item, "wfs", "GetFeature", "2.0.0", {}
    )["TYPENAMES"] == name
    assert qgis_ogc_proxy._upstream_params(
        item, "wfs", "GetFeature", "1.1.0", {}
    )["TYPENAME"] == name
    assert "LAYERS" not in qgis_ogc_proxy._upstream_params(
        item, "wms", "GetCapabilities", "1.3.0", {}
    )


WMS_CAPABILITIES = b"""<?xml version="1.0"?>
<WMS_Capabilities xmlns:xlink="http://www.w3.org/1999/xlink">
  <Capability><Request><GetMap><OnlineResource xlink:href="http://qgis/ows" /></GetMap></Request>
    <Layer><Title>GAIA</Title>
      <Layer><Name>catasto__particelle_ufficiali</Name><Title>Particelle</Title></Layer>
      <Layer><Name>rete__riservata</Name><Title>Riservata</Title></Layer>
    </Layer>
  </Capability>
</WMS_Capabilities>"""

WFS_CAPABILITIES = b"""<?xml version="1.0"?>
<WFS_Capabilities xmlns:xlink="http://www.w3.org/1999/xlink">
  <OperationsMetadata><Operation name="GetFeature"/><Operation name="Transaction"/></OperationsMetadata>
  <FeatureTypeList>
    <Other/>
    <FeatureType><Name>gaia:catasto__particelle_ufficiali</Name><Title>Particelle</Title></FeatureType>
    <FeatureType><Name>gaia:rete__riservata</Name><Title>Riservata</Title></FeatureType>
  </FeatureTypeList>
  <Transaction/><OnlineResource xlink:href="http://qgis/ows" />
</WFS_Capabilities>"""

WMS_GROUP_CAPABILITIES = b"""<WMS_Capabilities><Capability><Layer>
  <Layer><Name>catasto__particelle_ufficiali</Name><Title>Particelle</Title>
    <Layer><Name>nested_hidden</Name></Layer>
  </Layer>
</Layer></Capability></WMS_Capabilities>"""


@pytest.mark.parametrize(
    ("service", "content", "present", "absent"),
    [
        ("wms", WMS_CAPABILITIES, "Particelle", "Riservata"),
        ("wfs", WFS_CAPABILITIES, "Particelle", "Riservata"),
    ],
)
def test_filter_capabilities_keeps_only_the_authorized_layer_and_gaia_url(
    monkeypatch: pytest.MonkeyPatch,
    service: str,
    content: bytes,
    present: str,
    absent: str,
) -> None:
    item = layer()
    monkeypatch.setattr(
        qgis_ogc_proxy.settings,
        "gis_qgis_proxy_base_url",
        "https://gaia.example.local/",
    )
    filtered = qgis_ogc_proxy.filter_capabilities(
        content,
        service,
        qgis_ogc_proxy.service_layer_name(item),
        item.id,
    ).decode()
    assert present in filtered
    assert absent not in filtered
    assert "Transaction" not in filtered
    assert f"https://gaia.example.local/gis/ogc/layers/{item.id}" in filtered
    assert "http://qgis/ows" not in filtered


@pytest.mark.parametrize(
    ("content", "service", "detail"),
    [
        (b"not xml", "wms", "Capabilities QGIS Server non valide."),
        (
            b"<WMS_Capabilities><Capability><Layer/></Capability></WMS_Capabilities>",
            "wms",
            "Il layer richiesto non compare nelle capabilities QGIS Server.",
        ),
        (
            b"<WFS_Capabilities><FeatureTypeList/></WFS_Capabilities>",
            "wfs",
            "Il layer richiesto non compare nelle capabilities QGIS Server.",
        ),
    ],
)
def test_filter_capabilities_rejects_invalid_or_inconsistent_upstream(
    content: bytes, service: str, detail: str
) -> None:
    assert_http_error(
        502,
        detail,
        lambda: qgis_ogc_proxy.filter_capabilities(
            content, service, "catasto__particelle_ufficiali", uuid4()
        ),
    )


def test_filter_wms_capabilities_removes_nested_layers_from_the_target() -> None:
    filtered = qgis_ogc_proxy.filter_capabilities(
        WMS_GROUP_CAPABILITIES,
        "wms",
        "catasto__particelle_ufficiali",
        uuid4(),
    )
    assert b"Particelle" in filtered
    assert b"nested_hidden" not in filtered


def test_execute_request_forwards_only_controlled_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = layer()
    captured: dict[str, object] = {}

    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        captured.update({"url": url, **kwargs})
        return httpx.Response(
            200,
            content=b"png",
            headers={"content-type": "image/png; charset=binary"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(qgis_ogc_proxy.httpx, "get", fake_get)
    monkeypatch.setattr(
        qgis_ogc_proxy.settings,
        "gis_qgis_server_internal_url",
        "http://qgis-server/ows/",
    )
    payload = qgis_ogc_proxy.execute_request(
        item,
        "wms",
        "GetMap",
        "1.3.0",
        {"BBOX": "1,2,3,4", "WIDTH": "10", "HEIGHT": "10", "CRS": "EPSG:4326"},
    )
    assert payload == qgis_ogc_proxy.QgisOgcPayload(b"png", "image/png", 200)
    assert captured["url"] == "http://qgis-server/ows/"
    assert captured["follow_redirects"] is False
    assert captured["params"]["LAYERS"] == "catasto__particelle_ufficiali"
    assert "URL" not in captured["params"]
    assert "MAP" not in captured["params"]


def test_execute_request_filters_capabilities_and_defaults_content_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = layer()
    monkeypatch.setattr(
        qgis_ogc_proxy.httpx,
        "get",
        lambda url, **kwargs: httpx.Response(
            200,
            content=WMS_CAPABILITIES,
            request=httpx.Request("GET", url),
        ),
    )
    payload = qgis_ogc_proxy.execute_request(
        item, "wms", "GetCapabilities", "1.3.0", {}
    )
    assert payload.media_type == "application/xml"
    assert b"Riservata" not in payload.content


@pytest.mark.parametrize("failure", ["status", "request"])
def test_execute_request_maps_qgis_failures_to_governed_503(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        request_value = httpx.Request("GET", url)
        if failure == "request":
            raise httpx.ConnectError("offline", request=request_value)
        return httpx.Response(500, request=request_value)

    monkeypatch.setattr(qgis_ogc_proxy.httpx, "get", fake_get)
    assert_http_error(
        503,
        "QGIS Server non raggiungibile; il servizio OGC non e disponibile.",
        lambda: qgis_ogc_proxy.execute_request(
            layer(), "wms", "GetCapabilities", "1.3.0", {}
        ),
    )


def test_proxy_request_and_router_return_read_only_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = layer()
    user = SimpleNamespace(id=7, role="viewer")
    monkeypatch.setattr(
        qgis_ogc_proxy,
        "resolve_publishable_layer",
        lambda db, layer_id, current_user: item,
    )
    monkeypatch.setattr(
        qgis_ogc_proxy,
        "execute_request",
        lambda *args: qgis_ogc_proxy.QgisOgcPayload(b"map", "image/png", 200),
    )
    payload = qgis_ogc_proxy.proxy_request(
        FakeDb(item),
        item.id,
        user,
        [
            ("SERVICE", "WMS"),
            ("REQUEST", "GetMap"),
            ("BBOX", "1,2,3,4"),
            ("WIDTH", "10"),
            ("HEIGHT", "10"),
            ("CRS", "EPSG:4326"),
        ],
    )
    assert payload.content == b"map"

    monkeypatch.setattr(qgis_ogc_router.qgis_ogc_proxy, "proxy_request", lambda *args: payload)
    response = qgis_ogc_router.proxy_qgis_ogc(
        item.id,
        request("SERVICE=WMS&REQUEST=GetCapabilities"),
        user,
        FakeDb(item),
    )
    assert response.body == b"map"
    assert response.headers["x-gaia-ogc-mode"] == "read-only"


def test_wfs_transaction_is_always_rejected_after_permission_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = layer()
    user = SimpleNamespace(id=7, role="viewer")
    checked: list[UUID] = []
    monkeypatch.setattr(
        qgis_ogc_proxy,
        "resolve_publishable_layer",
        lambda db, layer_id, current_user: checked.append(layer_id) or item,
    )
    assert_http_error(
        400,
        "WFS-T non e abilitato: il proxy OGC GAIA e solo lettura.",
        lambda: qgis_ogc_proxy.reject_write_request(FakeDb(item), item.id, user),
    )
    assert checked == [item.id]

    monkeypatch.setattr(
        qgis_ogc_router.qgis_ogc_proxy,
        "reject_write_request",
        lambda *args: (_ for _ in ()).throw(HTTPException(400, "rejected")),
    )
    assert_http_error(
        400,
        "rejected",
        lambda: qgis_ogc_router.reject_qgis_wfs_transaction(
            item.id, user, FakeDb(item)
        ),
    )
