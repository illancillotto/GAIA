from __future__ import annotations

import sys
import types

import pytest

if "geoalchemy2" not in sys.modules:
    geoalchemy2_module = types.ModuleType("geoalchemy2")
    geoalchemy2_shape = types.ModuleType("geoalchemy2.shape")
    geoalchemy2_shape.to_shape = lambda value: value
    geoalchemy2_module.shape = geoalchemy2_shape
    sys.modules["geoalchemy2"] = geoalchemy2_module
    sys.modules["geoalchemy2.shape"] = geoalchemy2_shape

import app.main as app_main


class _FakeScheduler:
    def __init__(self) -> None:
        self.started = False
        self.shutdown_called = False

    def start(self) -> None:
        self.started = True

    def shutdown(self, wait: bool = False) -> None:
        self.shutdown_called = True


@pytest.mark.anyio
async def test_lifespan_registers_catasto_ade_autosync_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    scheduler = _FakeScheduler()

    monkeypatch.setattr(app_main, "_ensure_bootstrap_admin_on_startup", lambda: None)
    monkeypatch.setattr(app_main, "_ensure_sections_on_startup", lambda: None)
    monkeypatch.setattr(app_main, "_ensure_gis_catalog_on_startup", lambda: calls.append("gis_bootstrap"))
    monkeypatch.setattr(app_main, "AsyncIOScheduler", lambda timezone: scheduler)

    async def fake_register_catasto(_scheduler, _get_db) -> None:
        calls.append("catasto")

    async def fake_register_other(_scheduler, _get_db) -> None:
        calls.append("other")

    monkeypatch.setattr(app_main, "register_catasto_ade_autosync_scheduler", fake_register_catasto)
    monkeypatch.setattr(app_main, "register_bonifica_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_elaborazioni_db_backup_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_incass_autosync_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_ruolo_autosync_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_gis_export_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_presenze_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_network_telemetry_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_anpr_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_visure_router_scheduler", fake_register_other)
    monkeypatch.setattr(app_main, "register_wiki_telemetry_scheduler", fake_register_other)

    async with app_main.lifespan(app_main.app):
        assert scheduler.started is True

    assert "catasto" in calls
    assert "gis_bootstrap" in calls
    assert scheduler.shutdown_called is True
