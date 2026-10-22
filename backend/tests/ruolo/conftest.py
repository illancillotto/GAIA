from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

if "geoalchemy2.shape" not in sys.modules:
    geoalchemy2_module = ModuleType("geoalchemy2")
    geoalchemy2_shape_module = ModuleType("geoalchemy2.shape")

    def _to_shape(_geometry: object) -> SimpleNamespace:
        return SimpleNamespace(__geo_interface__={"type": "Point", "coordinates": [8.0, 39.0]})

    geoalchemy2_shape_module.to_shape = _to_shape
    geoalchemy2_module.shape = geoalchemy2_shape_module
    sys.modules["geoalchemy2"] = geoalchemy2_module
    sys.modules["geoalchemy2.shape"] = geoalchemy2_shape_module

if "shapefile" not in sys.modules:
    shapefile_module = ModuleType("shapefile")
    shapefile_module.Reader = object
    sys.modules["shapefile"] = shapefile_module


@pytest.fixture(autouse=True)
def _td896_sample_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ruolo tests render the TD 896 slip without a real Poste authorization code.
    monkeypatch.setattr("app.core.config.settings.td896_sample_mode", True)
