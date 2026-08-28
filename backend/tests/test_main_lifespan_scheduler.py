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


@pytest.mark.anyio
async def test_lifespan_runs_bootstraps_without_starting_schedulers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(app_main, "_ensure_bootstrap_admin_on_startup", lambda: calls.append("admin"))
    monkeypatch.setattr(app_main, "_ensure_sections_on_startup", lambda: calls.append("sections"))
    monkeypatch.setattr(app_main, "_ensure_gis_catalog_on_startup", lambda: calls.append("gis_bootstrap"))

    async with app_main.lifespan(app_main.app):
        calls.append("serving")

    assert calls == ["admin", "sections", "gis_bootstrap", "serving"]
    assert not hasattr(app_main, "AsyncIOScheduler")
