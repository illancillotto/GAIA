"""GAIA Organigramma module entry point."""

from fastapi import APIRouter, Depends

from app.api.deps import require_module
from app.modules.organigramma.routes.assignments import router as assignments_router
from app.modules.organigramma.routes.overrides import router as overrides_router
from app.modules.organigramma.routes.sync import router as sync_router
from app.modules.organigramma.routes.units import router as units_router
from app.modules.organigramma.routes.visibility import router as visibility_router

router = APIRouter(
    prefix="/organigramma",
    tags=["organigramma"],
    dependencies=[Depends(require_module("organigramma"))],
)

router.include_router(units_router)
router.include_router(assignments_router)
router.include_router(overrides_router)
router.include_router(visibility_router)
router.include_router(sync_router)


@router.get("")
def organigramma_root() -> dict:
    return {
        "module": "organigramma",
        "status": "active",
        "message": "GAIA Organigramma module is active.",
    }
