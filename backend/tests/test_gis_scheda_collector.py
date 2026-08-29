from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.modules.gis.interrogazione.models import (
    InterrogationLevel,
    InterrogationResponse,
)
from app.modules.gis.scheda_territoriale import collector
from fastapi import HTTPException


class _Mappings:
    def __init__(self, row: dict | None) -> None:
        self.row = row

    def first(self) -> dict | None:
        return self.row


class _Result:
    def __init__(self, row: dict | None) -> None:
        self.row = row

    def mappings(self) -> _Mappings:
        return _Mappings(self.row)


class _Scalars:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows


class _Session:
    def __init__(self, row: dict | None, layers: list[object]) -> None:
        self.row = row
        self.layers = layers
        self.sql = ""

    def execute(self, statement: object, params: dict) -> _Result:
        self.sql = str(statement)
        assert params["particella_id"]
        return _Result(self.row)

    def scalars(self, statement: object) -> _Scalars:
        del statement
        return _Scalars(self.layers)


def _parcel() -> dict:
    return {
        "id": str(uuid4()),
        "foglio": "12",
        "particella": "34",
        "nome_comune": "Oristano",
        "min_lon": 8.59,
        "min_lat": 39.90,
        "max_lon": 8.61,
        "max_lat": 39.92,
        "lon": 8.60,
        "lat": 39.91,
    }


def _layer(title: str, *, theme: str, queryable: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        metadata_json={
            "theme": theme,
            "external": {"queryable": queryable, "attribution": f"Fonte {title}"},
        },
    )


def _response(point: object) -> InterrogationResponse:
    empty = InterrogationLevel("territorio", [])
    return InterrogationResponse(
        lon=point.lon,
        lat=point.lat,
        srid=point.srid,
        radius_m=point.radius_m,
        gaia=InterrogationLevel("gaia", []),
        catasto_ufficiale=InterrogationLevel("catasto_ufficiale", []),
        territorio=empty,
    )


def test_collector_uses_centroid_extent_permissions_and_map_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowed = _layer("Ortofoto", theme="ortofoto", queryable="wms_visual_only")
    denied = _layer("Vincolo", theme="vincoli", queryable="wfs_queryable")
    db = _Session(_parcel(), [allowed, denied])
    user = SimpleNamespace(id=4)
    monkeypatch.setattr(
        collector.services,
        "_permission_flags",
        lambda db, layer_id, user: {"can_view": layer_id == allowed.id},
    )
    captured: list[object] = []

    def interrogate(db: object, user: object, point: object, ids: list) -> object:
        captured.append((point, ids))
        return _response(point)

    monkeypatch.setattr(collector, "interrogate_point", interrogate)
    monkeypatch.setattr(
        collector.external_proxy,
        "proxy_external_request",
        lambda *args, **kwargs: SimpleNamespace(content=b"png", media_type="image/png"),
    )

    snapshot = collector.collect_sheet_snapshot(db, user, uuid4())  # type: ignore[arg-type]

    point, ids = captured[0]
    assert point.radius_m > 150
    assert ids == [allowed.id]
    assert snapshot["collection_scope"]["extent"]["min_lon"] == 8.59
    assert snapshot["excluded_layers"] == [
        {
            "layer_id": str(denied.id),
            "title": "Vincolo",
            "reason": "Escluso per mancanza del permesso can_view.",
        }
    ]
    assert snapshot["map_extract"]["data_url"].startswith("data:image/png;base64,")
    assert snapshot["attributions"] == ["Fonte Ortofoto"]
    assert "ST_Centroid" in db.sql and "ST_Extent" in db.sql


def test_collector_handles_small_extent_missing_map_and_proxy_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parcel = _parcel() | {
        "min_lon": 8.6,
        "max_lon": 8.6,
        "min_lat": 39.9,
        "max_lat": 39.9,
    }
    db = _Session(parcel, [])
    monkeypatch.setattr(
        collector, "interrogate_point", lambda db, user, point, ids: _response(point)
    )
    snapshot = collector.collect_sheet_snapshot(db, SimpleNamespace(id=1), uuid4())  # type: ignore[arg-type]
    assert snapshot["collection_scope"]["radius_m"] == 150
    assert snapshot["attributions"] == []
    assert snapshot["map_extract"]["status"] == "unavailable"

    ortho = _layer("Ortofoto", theme="ortofoto", queryable="wms_visual_only")
    db.layers = [ortho]
    monkeypatch.setattr(
        collector.services, "_permission_flags", lambda *args: {"can_view": True}
    )
    monkeypatch.setattr(
        collector.external_proxy,
        "proxy_external_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("proxy down")),
    )
    snapshot = collector.collect_sheet_snapshot(db, SimpleNamespace(id=1), uuid4())  # type: ignore[arg-type]
    assert snapshot["map_extract"] == {
        "status": "failed",
        "message": "proxy down",
        "scale": "1:5.000",
    }


def test_collector_rejects_unknown_parcel() -> None:
    with pytest.raises(HTTPException) as error:
        collector.collect_sheet_snapshot(_Session(None, []), SimpleNamespace(), uuid4())  # type: ignore[arg-type]
    assert error.value.status_code == 404
