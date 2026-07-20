from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace


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
