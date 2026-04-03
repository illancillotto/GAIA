from fastapi import APIRouter

from app.modules.elaborazioni.capacitas_routes import router as capacitas_router
from app.modules.elaborazioni.routes import router as elaborazioni_router

router = APIRouter()
router.include_router(elaborazioni_router)
router.include_router(capacitas_router)
