from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.modules.gis import runtime_health
from app.modules.gis.schemas import GisRuntimeComponentHealth

CHECKED_AT = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one(self) -> object:
        return self.value


class _FakeDb:
    def __init__(self, *, dialect: str = "sqlite", fail: bool = False) -> None:
        self.dialect = dialect
        self.fail = fail

    def execute(self, statement: object) -> _ScalarResult:
        if self.fail:
            raise SQLAlchemyError("database offline")
        statement_text = str(statement)
        return _ScalarResult("3.4" if "PostGIS_Version" in statement_text else 1)

    def get_bind(self) -> SimpleNamespace:
        return SimpleNamespace(dialect=SimpleNamespace(name=self.dialect))

    def scalar(self, statement: object) -> None:
        if self.fail:
            raise SQLAlchemyError("database offline")


class _HttpResponse(AbstractContextManager["_HttpResponse"]):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.read_calls = 0

    def __exit__(self, *args: object) -> None:
        return None

    def getcode(self) -> int:
        return self.status_code

    def read(self, size: int) -> bytes:
        self.read_calls += size
        return b"x"


def _component(status: str) -> GisRuntimeComponentHealth:
    return GisRuntimeComponentHealth(
        key="postgis",
        label="PostGIS",
        status=status,
        message="test",
        checked_at=CHECKED_AT,
    )


def test_postgis_probe_reports_sqlite_postgres_and_failures() -> None:
    sqlite_result = runtime_health._probe_postgis(_FakeDb(), CHECKED_AT)
    postgres_result = runtime_health._probe_postgis(
        _FakeDb(dialect="postgresql"), CHECKED_AT
    )
    failed_result = runtime_health._probe_postgis(
        _FakeDb(fail=True), CHECKED_AT
    )

    assert sqlite_result.status == "warning"
    assert sqlite_result.details["postgis_version"] is None
    assert postgres_result.status == "ok"
    assert postgres_result.details["postgis_version"] == "3.4"
    assert failed_result.status == "critical"
    assert failed_result.details["error"] == "database offline"


def test_http_probe_handles_configuration_status_and_network_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    not_configured = runtime_health._probe_http_service(
        key="qgis", label="QGIS Server", url=" ", checked_at=CHECKED_AT
    )
    response = _HttpResponse(204)
    monkeypatch.setattr(runtime_health, "urlopen", lambda *args, **kwargs: response)
    available = runtime_health._probe_http_service(
        key="martin", label="Martin", url="http://martin/catalog", checked_at=CHECKED_AT
    )
    monkeypatch.setattr(
        runtime_health,
        "urlopen",
        lambda *args, **kwargs: _HttpResponse(503),
    )
    unhealthy = runtime_health._probe_http_service(
        key="martin", label="Martin", url="http://martin/catalog", checked_at=CHECKED_AT
    )

    def _raise_network_error(*args: object, **kwargs: object) -> None:
        raise URLError("offline")

    monkeypatch.setattr(runtime_health, "urlopen", _raise_network_error)
    offline = runtime_health._probe_http_service(
        key="martin", label="Martin", url="http://martin/catalog", checked_at=CHECKED_AT
    )

    assert not_configured.status == "not_configured"
    assert available.status == "ok"
    assert response.read_calls == 1
    assert unhealthy.status == "critical"
    assert unhealthy.details["http_status"] == 503
    assert offline.status == "critical"
    assert "offline" in str(offline.details["error"])


def test_nas_probe_handles_unconfigured_available_missing_and_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(runtime_health.settings, "gis_nas_health_path", "")
    assert runtime_health._probe_nas(_FakeDb(), CHECKED_AT).status == "not_configured"

    monkeypatch.setattr(runtime_health.settings, "gis_nas_health_path", str(tmp_path))
    monkeypatch.setattr(
        runtime_health,
        "probe_artifact_storage",
        lambda path: SimpleNamespace(
            transport="local", readable=True, writable=True
        ),
    )
    available = runtime_health._probe_nas(_FakeDb(), CHECKED_AT)
    assert available.status == "ok"
    assert available.details["readable"] is True

    missing = tmp_path / "missing"
    monkeypatch.setattr(runtime_health.settings, "gis_nas_health_path", str(missing))
    monkeypatch.setattr(
        runtime_health,
        "probe_artifact_storage",
        lambda path: SimpleNamespace(
            transport="local", readable=False, writable=False
        ),
    )
    assert runtime_health._probe_nas(_FakeDb(), CHECKED_AT).status == "critical"

    monkeypatch.setattr(runtime_health.settings, "gis_nas_health_path", str(tmp_path))
    monkeypatch.setattr(
        runtime_health,
        "probe_artifact_storage",
        lambda path: (_ for _ in ()).throw(OSError("nas offline")),
    )
    failed = runtime_health._probe_nas(_FakeDb(), CHECKED_AT)
    assert failed.status == "critical"
    assert failed.details["error"] == "nas offline"


def test_scheduled_export_health_and_nas_status_cover_latest_cycle() -> None:
    class _SequenceDb:
        def __init__(self, values: list[object]) -> None:
            self.values = iter(values)

        def scalar(self, statement: object) -> object:
            return next(self.values)

    missing = runtime_health._latest_scheduled_export_health(_SequenceDb([None]))
    latest = runtime_health._latest_scheduled_export_health(
        _SequenceDb(["scheduled-20260826T003000Z", 6, 1])
    )

    assert missing == runtime_health._ScheduledExportHealth(None, 0, 0)
    assert latest == runtime_health._ScheduledExportHealth(
        "scheduled-20260826T003000Z", 6, 1
    )
    assert runtime_health._nas_status(False, True, 0)[0] == "critical"
    assert runtime_health._nas_status(True, True, 1)[0] == "warning"
    assert runtime_health._nas_status(True, True, 0)[0] == "ok"


def test_nas_probe_warns_when_latest_scheduled_cycle_failed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _SequenceDb:
        def __init__(self) -> None:
            self.values = iter(
                (
                    CHECKED_AT,
                    "scheduled-20260826T003000Z",
                    6,
                    1,
                )
            )

        def scalar(self, statement: object) -> object:
            return next(self.values)

    monkeypatch.setattr(runtime_health.settings, "gis_nas_health_path", str(tmp_path))
    monkeypatch.setattr(
        runtime_health,
        "probe_artifact_storage",
        lambda path: SimpleNamespace(
            transport="sftp", readable=True, writable=True
        ),
    )

    result = runtime_health._probe_nas(_SequenceDb(), CHECKED_AT)

    assert result.status == "warning"
    assert result.details["latest_scheduled_completed"] == 6
    assert result.details["latest_scheduled_failed"] == 1


def test_runtime_health_aggregates_critical_warning_and_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_health.settings, "gis_export_scheduler_enabled", False)
    monkeypatch.setattr(runtime_health, "_probe_postgis", lambda db, checked_at: _component("critical"))
    monkeypatch.setattr(runtime_health, "_probe_http_service", lambda **kwargs: _component("ok"))
    monkeypatch.setattr(runtime_health, "_probe_nas", lambda db, checked_at: _component("ok"))
    assert runtime_health.get_runtime_health(_FakeDb()).status == "critical"

    monkeypatch.setattr(runtime_health, "_probe_postgis", lambda db, checked_at: _component("warning"))
    assert runtime_health.get_runtime_health(_FakeDb()).status == "warning"

    monkeypatch.setattr(runtime_health, "_probe_postgis", lambda db, checked_at: _component("ok"))
    result = runtime_health.get_runtime_health(_FakeDb())
    assert result.status == "ok"
    assert result.export_scheduler_enabled is False
    assert len(result.components) == 4
