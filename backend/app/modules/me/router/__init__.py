from __future__ import annotations

import sys
from types import ModuleType

from fastapi import APIRouter

from app.modules.me.router import common
from app.modules.me.router.routes import assets, operazioni, status_presenze, summary

router = APIRouter(tags=["me"])
for child_router in (
    status_presenze.router,
    summary.router,
    operazioni.router,
    assets.router,
):
    router.include_router(child_router)

_COMPAT_MODULES = (
    common,
    status_presenze,
    summary,
    operazioni,
    assets,
)
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
