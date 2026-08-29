from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Self
from uuid import UUID, uuid4

import httpx
import pytest
from app.core.config import settings
from app.modules.gis import external_proxy
from app.modules.gis import runtime_health as gis_runtime_health
from app.modules.gis.external_proxy import (
    ExternalProxyError,
    ExternalProxyPayload,
    execute_external_request,
    list_external_source_statuses,
    normalize_external_query,
    proxy_external_request,
    prune_external_cache,
)
from app.modules.gis.external_sources import ExternalSourceDefinition
from app.modules.gis.models import GisLayer
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError


def _external_metadata(**overrides: object) -> dict[str, object]:
    external: dict[str, object] = {
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
    external.update(overrides)
    return {"external": external}


def _layer(**overrides: object) -> GisLayer:
    values: dict[str, object] = {
        "id": uuid4(),
        "workspace": "territorio",
        "name": "aree_bonifica",
        "title": "Aree di bonifica",
        "source_type": "wms_external",
        "official_source": "ras_sitr",
        "metadata_json": _external_metadata(),
        "is_active": True,
    }
    values.update(overrides)
    return GisLayer(**values)


@pytest.mark.parametrize(
    ("service", "query", "operation", "expected"),
    [
        ("wms", [("REQUEST", "GetCapabilities")], "GetCapabilities", {}),
        (
            "wms",
            [
                ("request", "getmap"),
                ("bbox", "0,0,1,1"),
                ("crs", "EPSG:3857"),
                ("width", "256"),
                ("height", "256"),
                ("transparent", "true"),
            ],
            "GetMap",
            {
                "BBOX": "0,0,1,1",
                "CRS": "EPSG:3857",
                "WIDTH": "256",
                "HEIGHT": "256",
                "TRANSPARENT": "true",
            },
        ),
        (
            "wfs",
            [("request", "GetFeature"), ("count", "10"), ("bbox", "0,0,1,1")],
            "GetFeature",
            {"COUNT": "10", "BBOX": "0,0,1,1"},
        ),
    ],
)
def test_query_allowlist_normalizes_operations_and_parameters(
    service: str,
    query: list[tuple[str, str]],
    operation: str,
    expected: dict[str, str],
) -> None:
    assert normalize_external_query(service, query) == (operation, expected)


@pytest.mark.parametrize(
    ("service", "query", "message"),
    [
        ("wms", [("request", "GetMap"), ("REQUEST", "GetMap")], "Duplicate"),
        ("wms", [], "operation is not allowed"),
        ("wmts", [("request", "GetTile")], "operation is not allowed"),
        ("wms", [("request", "DeleteLayer")], "operation is not allowed"),
        (
            "wms",
            [("request", "GetCapabilities"), ("url", "https://evil.test")],
            "parameter is not allowed: url",
        ),
        (
            "wms",
            [("request", "GetCapabilities"), ("callback", "x")],
            "parameter is not allowed: callback",
        ),
        (
            "wms",
            [("request", "GetCapabilities"), ("sections", "x" * 16_385)],
            "parameter is too long",
        ),
        (
            "wms",
            [
                ("request", "GetMap"),
                ("bbox", "0,0,1,1"),
                ("crs", "EPSG:3857"),
                ("width", "many"),
                ("height", "256"),
            ],
            "must be an integer",
        ),
        (
            "wms",
            [
                ("request", "GetMap"),
                ("bbox", "0,0,1,1"),
                ("crs", "EPSG:3857"),
                ("width", "4097"),
                ("height", "256"),
            ],
            "outside the allowed range",
        ),
        (
            "wms",
            [("request", "GetMap"), ("width", "256"), ("height", "256")],
            "missing required parameters",
        ),
        (
            "wms",
            [
                ("request", "GetFeatureInfo"),
                ("bbox", "0,0,1,1"),
                ("crs", "EPSG:3857"),
                ("width", "256"),
                ("height", "256"),
                ("i", "10"),
            ],
            "missing required parameters",
        ),
    ],
)
def test_query_allowlist_rejects_unsafe_or_invalid_input(
    service: str,
    query: list[tuple[str, str]],
    message: str,
) -> None:
    with pytest.raises(ExternalProxyError, match=message) as exc_info:
        normalize_external_query(service, query)
    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert exc_info.value.detail


def test_cache_write_hit_expiration_corruption_and_pruning(tmp_path: Path) -> None:
    payload = ExternalProxyPayload(b"first", "image/png", 200, "MISS")
    external_proxy._write_cache(tmp_path, "a", payload)

    hit = external_proxy._read_cache(
        tmp_path, "a", 60, now=os.path.getmtime(tmp_path / "a.body")
    )
    assert hit == ExternalProxyPayload(b"first", "image/png", 200, "HIT")

    assert external_proxy._read_cache(tmp_path, "missing", 60) is None
    (tmp_path / "a.json").write_text("not-json", encoding="utf-8")
    assert external_proxy._read_cache(tmp_path, "a", 60) is None
    assert not (tmp_path / "a.body").exists()

    external_proxy._write_cache(tmp_path, "expired", payload)
    expired_mtime = os.path.getmtime(tmp_path / "expired.body")
    assert (
        external_proxy._read_cache(tmp_path, "expired", 1, now=expired_mtime + 1)
        is None
    )

    external_proxy._write_cache(
        tmp_path, "old", ExternalProxyPayload(b"1234", "text/plain", 200, "MISS")
    )
    external_proxy._write_cache(
        tmp_path, "new", ExternalProxyPayload(b"5678", "text/plain", 200, "MISS")
    )
    os.utime(tmp_path / "old.body", (1, 1))
    os.utime(tmp_path / "new.body", (2, 2))
    assert prune_external_cache(tmp_path, 4) == 1
    assert not (tmp_path / "old.body").exists()
    assert (tmp_path / "new.body").exists()
    assert prune_external_cache(tmp_path / "absent", 0) == 0


def test_cache_helpers_tolerate_filesystem_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = tmp_path / "item.body"
    metadata = tmp_path / "item.json"
    body.write_bytes(b"x")
    metadata.write_text(json.dumps({"media_type": "text/plain"}), encoding="utf-8")

    original_unlink = Path.unlink

    def fail_body_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path == body:
            raise OSError("locked")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_body_unlink)
    external_proxy._delete_cache_pair(body, metadata)
    assert body.exists()
    assert not metadata.exists()
    monkeypatch.setattr(Path, "unlink", original_unlink)
    body.unlink()

    bad_body = tmp_path / "bad.body"
    bad_body.write_bytes(b"x")
    original_stat = Path.stat

    def fail_bad_stat(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        if path == bad_body:
            raise OSError("unreadable")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fail_bad_stat)
    assert prune_external_cache(tmp_path, 0) == 0


def test_request_defaults_cover_feature_info_and_wfs() -> None:
    config = external_proxy.validate_external_layer_definition(
        "wms_external", _external_metadata()
    )
    assert config is not None
    assert external_proxy._request_defaults("GetFeatureInfo", config) == {
        "FORMAT": "image/png",
        "INFO_FORMAT": "application/json",
    }
    assert external_proxy._request_defaults("GetFeature", config) == {
        "OUTPUTFORMAT": "application/json"
    }
    assert external_proxy._request_defaults("GetCapabilities", config) == {}


class _Response:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.content = b"remote"
        self.status_code = 200
        self.headers = {"content-type": "image/png; charset=binary"}
        self.error = error

    def raise_for_status(self) -> None:
        if self.error:
            raise self.error


def test_remote_fetch_uses_fixed_headers_and_maps_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def successful_get(url: str, **kwargs: object) -> _Response:
        calls.append({"url": url, **kwargs})
        return _Response()

    monkeypatch.setattr(external_proxy.httpx, "get", successful_get)
    payload = external_proxy._fetch_remote("https://source.test/ows", 4.0)
    assert payload == ExternalProxyPayload(b"remote", "image/png", 200, "MISS")
    assert calls[0]["headers"] == {
        "User-Agent": "GAIA-GIS-External-Proxy/1.0",
        "Accept": "*/*",
    }
    assert "Authorization" not in calls[0]["headers"]
    assert calls[0]["follow_redirects"] is False

    def timeout(*_args: object, **_kwargs: object) -> _Response:
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(external_proxy.httpx, "get", timeout)
    with pytest.raises(ExternalProxyError) as timeout_error:
        external_proxy._fetch_remote("https://source.test/ows", 1.0)
    assert timeout_error.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    request = httpx.Request("GET", "https://source.test/ows")
    response = httpx.Response(503, request=request)
    monkeypatch.setattr(
        external_proxy.httpx,
        "get",
        lambda *_args, **_kwargs: _Response(
            error=httpx.HTTPStatusError("down", request=request, response=response)
        ),
    )
    with pytest.raises(ExternalProxyError) as upstream_error:
        external_proxy._fetch_remote("https://source.test/ows", 1.0)
    assert upstream_error.value.status_code == status.HTTP_502_BAD_GATEWAY


def test_execute_external_request_caches_by_normalized_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "gis_external_layers_enabled", True)
    monkeypatch.setattr(
        settings, "gis_external_ras_vector_url", "https://source.test/ows"
    )
    monkeypatch.setattr(settings, "gis_external_cache_dir", str(tmp_path))
    monkeypatch.setattr(settings, "gis_external_cache_max_mb", 1)
    calls: list[tuple[str, float]] = []

    def fetch(url: str, timeout: float) -> ExternalProxyPayload:
        calls.append((url, timeout))
        return ExternalProxyPayload(b"tile", "image/png", 200, "MISS")

    monkeypatch.setattr(external_proxy, "_fetch_remote", fetch)
    query = [
        ("request", "GetMap"),
        ("bbox", "0,0,1,1"),
        ("crs", "EPSG:3857"),
        ("width", "256"),
        ("height", "256"),
    ]

    miss = execute_external_request(_layer(), "wms", query)
    execute_external_request(_layer(), "wms", query)

    assert miss.cache_status == "MISS"
    assert len(calls) == 2

    layer = _layer()
    first = execute_external_request(layer, "wms", query)
    second = execute_external_request(layer, "wms", reversed(query))
    assert first.cache_status == "MISS"
    assert second.cache_status == "HIT"
    assert second.content == b"tile"
    assert "LAYERS=dbu%3Aareebonifica" in calls[-1][0]
    assert "TRANSPARENT=true" in calls[-1][0]
    assert "STYLES=" in calls[-1][0]


@pytest.mark.parametrize(
    ("layer", "service", "query", "status_code", "message"),
    [
        (_layer(source_type="postgis"), "wms", [], 422, "not external"),
        (_layer(source_type="wfs_external"), "wms", [], 422, "requires service wfs"),
        (
            _layer(
                source_type="wfs_external",
                metadata_json=_external_metadata(service="wfs", version="1.1.0"),
            ),
            "wms",
            [],
            422,
            "does not support WMS proxy operations",
        ),
        (_layer(), "wmts", [], 422, "does not support"),
        (_layer(), "wfs", [], 422, "operation is not allowed"),
        (
            _layer(metadata_json=_external_metadata(queryable="wms_visual_only")),
            "wfs",
            [],
            422,
            "does not support WFS queries",
        ),
    ],
)
def test_execute_external_request_rejects_invalid_layer_or_service(
    monkeypatch: pytest.MonkeyPatch,
    layer: GisLayer,
    service: str,
    query: list[tuple[str, str]],
    status_code: int,
    message: str,
) -> None:
    monkeypatch.setattr(settings, "gis_external_layers_enabled", True)
    monkeypatch.setattr(
        settings, "gis_external_ras_vector_url", "https://source.test/ows"
    )
    with pytest.raises(ExternalProxyError, match=message) as exc_info:
        execute_external_request(layer, service, query)
    assert exc_info.value.status_code == status_code


def test_execute_external_request_rejects_disabled_source_and_tolerates_cache_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "gis_external_layers_enabled", False)
    with pytest.raises(ExternalProxyError, match="source is disabled") as exc_info:
        execute_external_request(_layer(), "wms", [("request", "GetCapabilities")])
    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    monkeypatch.setattr(settings, "gis_external_layers_enabled", True)
    monkeypatch.setattr(
        settings, "gis_external_ras_vector_url", "https://source.test/ows"
    )
    monkeypatch.setattr(settings, "gis_external_cache_dir", str(tmp_path))
    monkeypatch.setattr(
        external_proxy,
        "_fetch_remote",
        lambda *_args: ExternalProxyPayload(b"ok", "text/xml", 200, "MISS"),
    )
    monkeypatch.setattr(
        external_proxy,
        "_write_cache",
        lambda *_args: (_ for _ in ()).throw(OSError("full")),
    )
    payload = execute_external_request(
        _layer(), "wms", [("request", "GetCapabilities")]
    )
    assert payload.content == b"ok"


class _AuditDb:
    def __init__(self, *, fail_commit: bool = False) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = fail_commit

    def add(self, item: object) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commits += 1
        if self.fail_commit:
            raise SQLAlchemyError("db down")

    def rollback(self) -> None:
        self.rollbacks += 1


def test_proxy_flag_resolution_error_audit_and_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=42)
    layer = _layer()
    db = _AuditDb()
    layer_id = UUID(str(layer.id))

    monkeypatch.setattr(settings, "gis_external_layers_enabled", False)
    with pytest.raises(HTTPException) as disabled:
        proxy_external_request(db, layer_id, user, service="wms", query_items=[])
    assert disabled.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    monkeypatch.setattr(settings, "gis_external_layers_enabled", True)
    monkeypatch.setattr(
        external_proxy.services,
        "resolve_external_layer_for_proxy",
        lambda *_args: layer,
    )
    monkeypatch.setattr(
        external_proxy,
        "execute_external_request",
        lambda *_args, **_kwargs: ExternalProxyPayload(
            b"ok", "text/plain", 200, "MISS"
        ),
    )
    assert (
        proxy_external_request(
            db, layer_id, user, service="wms", query_items=[]
        ).content
        == b"ok"
    )

    monkeypatch.setattr(
        external_proxy,
        "execute_external_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ExternalProxyError(502, "down")
        ),
    )
    with pytest.raises(HTTPException) as degraded:
        proxy_external_request(db, layer_id, user, service="wms", query_items=[])
    assert degraded.value.status_code == 502
    assert db.commits == 1
    audit = db.added[0]
    assert audit.event_type == "external_proxy.error"
    assert audit.payload_json["source_key"] == "ras_sitr_vector"


def test_audit_error_never_masks_proxy_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=42)
    layer = _layer(metadata_json={"external": {}})
    db = _AuditDb(fail_commit=True)

    external_proxy._audit_proxy_error(
        db,
        layer,
        user,
        "wms",
        ExternalProxyError(422, "invalid"),
    )

    assert db.added[0].payload_json["source_key"] is None
    assert db.rollbacks == 1


def test_source_status_response_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "gis_external_layers_enabled", True)
    statuses = list_external_source_statuses()
    assert len(statuses) == 3
    assert statuses[0]["supported_services"] == ["wms", "wfs"]


def _health_source(
    source_key: str, *, url: str = "https://source.test/ows"
) -> ExternalSourceDefinition:
    return ExternalSourceDefinition(
        source_key=source_key,
        base_url=url,
        service="wms",
        version="1.3.0",
        service_versions=(("wms", "1.3.0"),),
        timeout_seconds=5.0,
        enabled=True,
    )


class _HealthResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.read_count = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def getcode(self) -> int:
        return self.status_code

    def read(self, size: int) -> bytes:
        self.read_count += size
        return b"<"


def test_external_health_probe_reports_http_and_configuration_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float]] = []

    def urlopen_ok(url: str, *, timeout: float) -> _HealthResponse:
        calls.append((url, timeout))
        return _HealthResponse(200)

    monkeypatch.setattr(gis_runtime_health, "urlopen", urlopen_ok)
    monkeypatch.setattr(settings, "gis_runtime_health_timeout_seconds", 2.0)
    result = gis_runtime_health._probe_external_source(_health_source("ok"))
    assert result["status"] == "ok"
    assert result["http_status"] == 200
    assert calls[0][1] == 2.0
    assert "REQUEST=GetCapabilities" in calls[0][0]

    monkeypatch.setattr(
        gis_runtime_health,
        "urlopen",
        lambda *_args, **_kwargs: _HealthResponse(503),
    )
    assert (
        gis_runtime_health._probe_external_source(_health_source("bad"))["status"]
        == "critical"
    )

    invalid = gis_runtime_health._probe_external_source(
        _health_source("invalid", url="relative")
    )
    assert invalid["status"] == "critical"
    assert "error" in invalid


def test_external_health_aggregation_flag_cache_and_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked_at = datetime(2026, 8, 28, tzinfo=UTC)
    sources = (_health_source("one"), _health_source("two"))
    monkeypatch.setattr(gis_runtime_health, "get_external_sources", lambda: sources)
    gis_runtime_health.clear_external_health_cache()

    monkeypatch.setattr(settings, "gis_external_layers_enabled", False)
    disabled = gis_runtime_health._external_sources_health(checked_at)
    assert disabled.status == "not_configured"
    assert disabled.details["sources"] == ["one", "two"]

    monkeypatch.setattr(settings, "gis_external_layers_enabled", True)
    clock = iter((10.0, 20.0, 100.0, 400.0))
    monkeypatch.setattr(gis_runtime_health, "monotonic", lambda: next(clock))
    probes: list[str] = []

    def all_ok(source: ExternalSourceDefinition) -> dict[str, object]:
        probes.append(source.source_key)
        return {"source_key": source.source_key, "status": "ok", "latency_ms": 1.5}

    monkeypatch.setattr(gis_runtime_health, "_probe_external_source", all_ok)
    healthy = gis_runtime_health._external_sources_health(checked_at)
    cached = gis_runtime_health._external_sources_health(checked_at)
    assert healthy.status == "ok"
    assert healthy.latency_ms == 3.0
    assert cached is healthy
    assert probes == ["one", "two"]

    monkeypatch.setattr(
        gis_runtime_health,
        "_probe_external_source",
        lambda source: {
            "source_key": source.source_key,
            "status": "ok" if source.source_key == "one" else "critical",
            "latency_ms": 2.0,
        },
    )
    gis_runtime_health.clear_external_health_cache()
    warning = gis_runtime_health._external_sources_health(checked_at)
    assert warning.status == "warning"

    monkeypatch.setattr(
        gis_runtime_health,
        "_probe_external_source",
        lambda source: {
            "source_key": source.source_key,
            "status": "critical",
            "latency_ms": 2.0,
        },
    )
    critical = gis_runtime_health._external_sources_health(checked_at)
    assert critical.status == "critical"
