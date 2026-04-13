"""GAIA Operazioni module entry point."""

from fastapi import APIRouter, Depends

from app.api.deps import require_module
from app.modules.operazioni.routes.activities import router as activities_router
from app.modules.operazioni.routes.areas import router as areas_router
from app.modules.operazioni.routes.dashboard import router as dashboard_router
from app.modules.operazioni.routes.import_reports import router as import_reports_router
from app.modules.operazioni.routes.operators import router as operators_router
from app.modules.operazioni.routes.reports_dashboard import (
    router as reports_dashboard_router,
)
from app.modules.operazioni.routes.reports import router as reports_router
from app.modules.operazioni.routes.vehicles import router as vehicles_router

router = APIRouter(
    prefix="/operazioni",
    tags=["operazioni"],
    dependencies=[Depends(require_module("operazioni"))],
)

router.include_router(vehicles_router)
router.include_router(areas_router)
router.include_router(activities_router)
router.include_router(reports_dashboard_router)
router.include_router(import_reports_router)
router.include_router(reports_router)
router.include_router(operators_router)
router.include_router(dashboard_router)


@router.get("")
def operazioni_root() -> dict:
    return {
        "module": "operazioni",
        "status": "active",
        "message": "GAIA Operazioni module is active.",
    }
