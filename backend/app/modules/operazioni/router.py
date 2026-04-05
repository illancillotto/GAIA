"""GAIA Operazioni module entry point."""

from fastapi import APIRouter

from app.modules.operazioni.routes.activities import router as activities_router
from app.modules.operazioni.routes.dashboard import router as dashboard_router
from app.modules.operazioni.routes.reports import router as reports_router
from app.modules.operazioni.routes.vehicles import router as vehicles_router

router = APIRouter(prefix="/operazioni", tags=["operazioni"])

router.include_router(vehicles_router)
router.include_router(activities_router)
router.include_router(reports_router)
router.include_router(dashboard_router)


@router.get("")
def operazioni_root() -> dict:
    return {
        "module": "operazioni",
        "status": "active",
        "message": "GAIA Operazioni module is active.",
    }
