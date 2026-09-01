from __future__ import annotations

import time
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.core.config import settings
from app.modules.gis import router
from app.modules.gis.interrogazione import remote_probes, service
from app.modules.gis.interrogazione.models import (
    InterrogationLevel,
    InterrogationPoint,
    InterrogationResponse,
    ProbeResult,
    RemoteLayer,
)
from app.modules.gis.models import GisLayer
from app.modules.gis.schemas import GisInterrogazioneRequest
from fastapi import HTTPException
from pydantic import ValidationError


def _point() -> InterrogationPoint:
    return InterrogationPoint(lon=9, lat=40, srid=4326, radius_m=150)


def _result(source_id: str = "particella") -> ProbeResult:
    return ProbeResult(source_id, source_id.title(), "ok", 1.0, [{"id": "1"}])


def _layer(
    name: str,
    *,
    official_source: str = "ras_sitr",
    queryable: str = "wfs_queryable",
) -> RemoteLayer:
    return RemoteLayer(
        id=uuid4(),
        name=name,
        title=name.title(),
        official_source=official_source,
        source_key="ras_sitr_vector",
        remote_layer=f"dbu:{name}",
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


@pytest.fixture(autouse=True)
def enable_interrogation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "gis_interrogazione_enabled", True)
    monkeypatch.setattr(settings, "gis_interrogazione_max_remote_layers", 12)
    monkeypatch.setattr(settings, "gis_interrogazione_remote_timeout_seconds", 0.2)
    monkeypatch.setattr(
        service.local_probes, "probe_gaia", lambda db, point: [_result()]
    )


def test_remote_probes_run_in_parallel_and_keep_levels_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ade = _layer("catasto", official_source="agenzia_entrate")
    ras = _layer("vincolo")
    starts: list[float] = []

    def delayed(
        layer: RemoteLayer, point: InterrogationPoint, timeout: float
    ) -> ProbeResult:
        del point
        assert timeout == 0.2
        starts.append(time.perf_counter())
        time.sleep(0.04)
        return _result(str(layer.id))

    monkeypatch.setattr(service, "_visible_layers", lambda db, user, ids: [ras, ade])
    monkeypatch.setattr(remote_probes, "probe_remote_layer", delayed)

    started = time.perf_counter()
    response = service.interrogate_point(SimpleNamespace(), SimpleNamespace(), _point())
    elapsed = time.perf_counter() - started

    assert elapsed < 0.075
    assert max(starts) - min(starts) < 0.02
    assert response.gaia.sources[0].source_id == "particella"
    assert response.catasto_ufficiale.sources[0].source_id == str(ade.id)
    assert response.territorio.sources[0].source_id == str(ras.id)


def test_single_remote_failure_is_degraded_without_aborting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failing = _layer("failing")
    healthy = _layer("healthy")
    monkeypatch.setattr(
        service, "_visible_layers", lambda db, user, ids: [failing, healthy]
    )

    def probe(
        layer: RemoteLayer, point: InterrogationPoint, timeout: float
    ) -> ProbeResult:
        del point, timeout
        if layer.id == failing.id:
            raise RuntimeError("remote down")
        return _result(str(layer.id))

    monkeypatch.setattr(remote_probes, "probe_remote_layer", probe)

    response = service.interrogate_point(SimpleNamespace(), SimpleNamespace(), _point())

    assert [item.status for item in response.territorio.sources] == ["failed", "ok"]
    assert response.territorio.sources[0].message == "remote down"


def test_all_remote_failures_keep_the_gaia_level_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layers = [_layer("first"), _layer("second")]
    gaia = [_result(source_id) for source_id in ("particella", "distretto")]
    monkeypatch.setattr(service, "_visible_layers", lambda db, user, ids: layers)
    monkeypatch.setattr(service.local_probes, "probe_gaia", lambda db, point: gaia)
    monkeypatch.setattr(
        remote_probes,
        "probe_remote_layer",
        lambda layer, point, timeout: (_ for _ in ()).throw(
            RuntimeError("source unreachable")
        ),
    )

    response = service.interrogate_point(SimpleNamespace(), SimpleNamespace(), _point())

    assert response.gaia.sources == gaia
    assert [item.status for item in response.territorio.sources] == [
        "failed",
        "failed",
    ]


def test_remote_limit_and_visual_only_layers_are_never_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "gis_interrogazione_max_remote_layers", 1)
    first = _layer("first")
    limited = _layer("limited")
    visual = _layer("visual", queryable="wms_visual_only")
    monkeypatch.setattr(
        service, "_visible_layers", lambda db, user, ids: [first, limited, visual]
    )
    calls: list[UUID] = []

    def probe(
        layer: RemoteLayer, point: InterrogationPoint, timeout: float
    ) -> ProbeResult:
        del point, timeout
        calls.append(layer.id)
        return _result(str(layer.id))

    monkeypatch.setattr(remote_probes, "probe_remote_layer", probe)

    response = service.interrogate_point(SimpleNamespace(), SimpleNamespace(), _point())

    assert calls == [first.id]
    assert [item.status for item in response.territorio.sources] == [
        "ok",
        "skipped",
        "skipped",
    ]
    assert "Limite massimo" in response.territorio.sources[1].message
    assert "visualizzazione" in response.territorio.sources[2].message


def test_gaia_failure_and_disabled_flag_are_governed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service.local_probes,
        "probe_gaia",
        lambda db, point: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    with pytest.raises(HTTPException) as failed:
        service.interrogate_point(SimpleNamespace(), SimpleNamespace(), _point())
    assert failed.value.status_code == 502
    assert failed.value.__cause__ is not None

    monkeypatch.setattr(settings, "gis_interrogazione_enabled", False)
    with pytest.raises(HTTPException) as disabled:
        service.interrogate_point(SimpleNamespace(), SimpleNamespace(), _point())
    assert disabled.value.status_code == 503
    assert disabled.value.detail == (
        "Interrogazione territoriale non attiva in questo ambiente."
    )


class _Scalars:
    def __init__(self, layers: list[GisLayer]) -> None:
        self.layers = layers

    def all(self) -> list[GisLayer]:
        return self.layers


class _Session:
    def __init__(self, layers: list[GisLayer]) -> None:
        self.layers = layers

    def scalars(self, statement: object) -> _Scalars:
        del statement
        return _Scalars(self.layers)


def _db_layer(name: str, queryable: str = "wfs_queryable") -> GisLayer:
    return GisLayer(
        id=uuid4(),
        workspace="territorio",
        name=name,
        title=name.title(),
        source_type="wms_external",
        official_source="ras_sitr",
        is_active=True,
        metadata_json={
            "external": {
                "source_key": "ras_sitr_vector",
                "service": "wms",
                "version": "1.3.0",
                "remote_layer": f"dbu:{name}",
                "format": "image/png",
                "transparent": True,
                "srid": 4326,
                "queryable": queryable,
                "info_format": "application/json",
                "cache_ttl_seconds": 60,
                "license": "CC BY 4.0",
                "attribution": "Source",
            }
        },
    )


def test_visible_layers_respect_permissions_selection_and_validate_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visible = _db_layer("visible")
    denied = _db_layer("denied")
    monkeypatch.setattr(
        service.services,
        "_permission_flags",
        lambda db, layer_id, user: {"can_view": layer_id == visible.id},
    )

    layers = service._visible_layers(
        _Session([visible, denied]),  # type: ignore[arg-type]
        SimpleNamespace(),
        [visible.id],
    )

    assert [layer.id for layer in layers] == [visible.id]
    assert layers[0].remote_layer == "dbu:visible"

    all_layers = service._visible_layers(
        _Session([visible]),  # type: ignore[arg-type]
        SimpleNamespace(),
        None,
    )
    assert [layer.id for layer in all_layers] == [visible.id]

    visible.metadata_json = {"external": {"bad": True}}
    with pytest.raises(service.ExternalSourceConfigurationError):
        service._remote_layer(visible)


def test_remote_probe_runner_accepts_an_empty_catalog() -> None:
    assert service._run_remote_probes([], _point()) == []


def test_router_uses_default_radius_and_serializes_dataclass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[InterrogationPoint] = []

    def interrogate(
        db: object, user: object, point: InterrogationPoint, ids: object
    ) -> InterrogationResponse:
        del db, user, ids
        captured.append(point)
        return InterrogationResponse(
            lon=point.lon,
            lat=point.lat,
            srid=point.srid,
            radius_m=point.radius_m,
            gaia=InterrogationLevel("gaia", [_result()]),
            catasto_ufficiale=InterrogationLevel("catasto_ufficiale", []),
            territorio=InterrogationLevel("territorio", []),
        )

    monkeypatch.setattr(router.interrogazione_service, "interrogate_point", interrogate)
    monkeypatch.setattr(settings, "gis_interrogazione_default_radius_m", 175)

    response = router.interroga(
        GisInterrogazioneRequest(lon=9, lat=40),
        SimpleNamespace(),
        SimpleNamespace(),
    )

    assert captured[0].radius_m == 175
    assert response.gaia.sources[0].status == "ok"
    with pytest.raises(ValidationError):
        GisInterrogazioneRequest(lon=9, lat=40, radius_m=0)
