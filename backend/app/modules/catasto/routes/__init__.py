from fastapi import APIRouter

from app.modules.catasto.routes.anomalie import router as anomalie_router
from app.modules.catasto.routes.anagrafica import router as anagrafica_router
from app.modules.catasto.routes.distretti import router as distretti_router
from app.modules.catasto.routes.gis import router as gis_router
from app.modules.catasto.routes.import_routes import router as import_router
from app.modules.catasto.routes.legacy import router as legacy_router
from app.modules.catasto.routes.particelle import router as particelle_router
from app.modules.catasto.routes.schemi import router as schemi_router

router = APIRouter()
router.include_router(legacy_router)
router.include_router(import_router)
router.include_router(distretti_router)
router.include_router(particelle_router)
router.include_router(anomalie_router)
router.include_router(anagrafica_router)
router.include_router(schemi_router)
router.include_router(gis_router)

__all__ = ["router"]
