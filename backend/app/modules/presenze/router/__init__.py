from __future__ import annotations

import sys
from types import ModuleType

from fastapi import APIRouter

from app.modules.presenze.router.helpers import access as access_helpers
from app.modules.presenze.router.helpers import bank_hours as bank_hours_helpers
from app.modules.presenze.router.helpers import collaborators as collaborator_helpers
from app.modules.presenze.router.helpers import daily_records as daily_record_helpers
from app.modules.presenze.router.helpers import jobs as job_helpers
from app.modules.presenze.router.helpers import recovery as recovery_helpers
from app.modules.presenze.router.helpers import schedule_definitions
from app.modules.presenze.router.helpers import schedules as schedule_helpers
from app.modules.presenze.router.routes import (
    access,
    bank_hours,
    collaborators_daily,
    configuration,
    dashboard,
    exports,
    guidance,
    imports,
    recovery,
    sync_config,
    sync_jobs,
)

router = APIRouter(tags=["presenze"])
for child_router in (
    access.router,
    configuration.router,
    collaborators_daily.router,
    recovery.router,
    bank_hours.router,
    imports.router,
    sync_config.router,
    guidance.router,
    sync_jobs.router,
    exports.router,
    dashboard.router,
):
    router.include_router(child_router)

_COMPAT_MODULES = (
    access,
    configuration,
    collaborators_daily,
    recovery,
    bank_hours,
    imports,
    sync_config,
    guidance,
    sync_jobs,
    exports,
    dashboard,
    access_helpers,
    schedule_definitions,
    schedule_helpers,
    collaborator_helpers,
    daily_record_helpers,
    recovery_helpers,
    bank_hours_helpers,
    job_helpers,
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
