from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.modules.gis import qgis_external_router
from app.modules.gis.external_proxy import ExternalProxyPayload
from fastapi import HTTPException
from starlette.requests import Request


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


def layer():
    return SimpleNamespace(
        id=uuid4(),
        name="aree_bonifica",
        metadata_json={"external": {"version": "1.3.0"}},
    )


def test_qgis_proxy_strips_only_valid_controlled_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = layer()
    db = SimpleNamespace(get=lambda model, layer_id: item)
    captured: list[object] = []
    monkeypatch.setattr(
        qgis_external_router.external_proxy,
        "proxy_external_request",
        lambda *args, **kwargs: (
            captured.append((args, kwargs))
            or ExternalProxyPayload(b"png", "image/png", 200, "hit")
        ),
    )
    response = qgis_external_router.proxy_qgis_wms(
        item.id,
        request(
            "SERVICE=WMS&VERSION=1.3.0&LAYERS=aree_bonifica&REQUEST=GetMap&BBOX=1,2,3,4&WIDTH=256&HEIGHT=256&CRS=EPSG:3857"
        ),
        SimpleNamespace(id=1),
        db,
    )
    assert response.body == b"png"
    assert response.headers["x-gaia-external-cache"] == "hit"
    assert captured[0][1]["query_items"] == [
        ("REQUEST", "GetMap"),
        ("BBOX", "1,2,3,4"),
        ("WIDTH", "256"),
        ("HEIGHT", "256"),
        ("CRS", "EPSG:3857"),
    ]


@pytest.mark.parametrize(
    ("query", "detail"),
    [
        ("LAYERS=other", "QGIS layer mismatch"),
        ("SERVICE=WFS", "QGIS service must be WMS"),
        ("VERSION=1.1.0", "QGIS WMS version mismatch"),
    ],
)
def test_qgis_proxy_rejects_control_parameter_mismatches(
    query: str, detail: str
) -> None:
    with pytest.raises(HTTPException) as error:
        qgis_external_router._forwarded_items(layer(), request(query))
    assert error.value.status_code == 422
    assert error.value.detail == detail


def test_qgis_proxy_rejects_unknown_layer() -> None:
    with pytest.raises(HTTPException) as error:
        qgis_external_router.proxy_qgis_wms(
            uuid4(),
            request("REQUEST=GetCapabilities"),
            SimpleNamespace(),
            SimpleNamespace(get=lambda *args: None),
        )
    assert error.value.status_code == 404
