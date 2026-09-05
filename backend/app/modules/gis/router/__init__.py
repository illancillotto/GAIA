from __future__ import annotations

import sys
from types import ModuleType

from fastapi import APIRouter, Depends

from app.api.deps import require_module
from app.modules.gis.qgis_external_router import router as qgis_external_router
from app.modules.gis.qgis_ogc_router import router as qgis_ogc_router
from app.modules.gis.router.routes import (
    annotations,
    catalog,
    changes,
    exports_audit,
    external,
    imports,
    layers,
)
from app.modules.gis.scheda_territoriale.router import router as scheda_router

router = APIRouter(
    prefix="/gis",
    tags=["gis-platform"],
    dependencies=[Depends(require_module("gis"))],
)
for child_router in (
    scheda_router,
    qgis_external_router,
    qgis_ogc_router,
):
    router.include_router(child_router)

_LOCAL_ROUTE_MODULES = (
    catalog,
    external,
    imports,
    layers,
    annotations,
    changes,
    exports_audit,
)
for route_module in _LOCAL_ROUTE_MODULES:
    for route in route_module.router.routes:
        route.endpoint.__module__ = __name__
    router.include_router(route_module.router)

_COMPAT_MODULES = _LOCAL_ROUTE_MODULES
_MISSING = object()
_PATCH_ORIGINALS: dict[str, list[tuple[ModuleType, object]]] = {}


def __getattr__(name: str):
    for module in _COMPAT_MODULES:
        value = getattr(module, name, _MISSING)
        if value is not _MISSING and name != "router":
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class _CompatFacadeModule(ModuleType):
    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("__") or name in {
            "router",
            "_LOCAL_ROUTE_MODULES",
            "_COMPAT_MODULES",
            "_MISSING",
            "_PATCH_ORIGINALS",
        }:
            return super().__setattr__(name, value)
        originals = []
        for module in _COMPAT_MODULES:
            original = getattr(module, name, _MISSING)
            if original is not _MISSING:
                originals.append((module, original))
                setattr(module, name, value)
        if originals:
            _PATCH_ORIGINALS[name] = originals
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        for module, original in _PATCH_ORIGINALS.pop(name, []):
            setattr(module, name, original)
        if name in self.__dict__:
            super().__delattr__(name)


sys.modules[__name__].__class__ = _CompatFacadeModule

__all__ = ["router"]
