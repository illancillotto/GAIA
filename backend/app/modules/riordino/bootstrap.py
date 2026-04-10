"""Bootstrap del modulo Riordino - registrazione route nel monolite."""

from fastapi import APIRouter

from app.modules.riordino.routes.practices import router as practices_router
from app.modules.riordino.routes.workflow import router as workflow_router
from app.modules.riordino.routes.appeals import router as appeals_router
from app.modules.riordino.routes.issues import router as issues_router
from app.modules.riordino.routes.documents import router as documents_router
from app.modules.riordino.routes.gis import router as gis_router
from app.modules.riordino.routes.links import router as links_router
from app.modules.riordino.routes.dashboard import router as dashboard_router
from app.modules.riordino.routes.notifications import router as notifications_router
from app.modules.riordino.routes.config import router as config_router

router = APIRouter()

router.include_router(practices_router, prefix="/practices", tags=["Pratiche"])
router.include_router(workflow_router, prefix="/practices", tags=["Workflow"])
router.include_router(appeals_router, prefix="/practices", tags=["Ricorsi"])
router.include_router(issues_router, prefix="/practices", tags=["Issue"])
router.include_router(documents_router, prefix="/practices", tags=["Documenti"])
router.include_router(gis_router, prefix="/practices", tags=["GIS"])
router.include_router(links_router, prefix="/practices", tags=["Collegamenti"])
router.include_router(dashboard_router, tags=["Dashboard"])
router.include_router(notifications_router, prefix="/notifications", tags=["Notifiche"])
router.include_router(config_router, prefix="/config", tags=["Configurazione"])
