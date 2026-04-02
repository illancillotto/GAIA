from fastapi import APIRouter

from app.modules.catasto.capacitas_routes import router as capacitas_router
from app.modules.catasto.routes import router as catasto_router

router = APIRouter()
router.include_router(catasto_router)
router.include_router(capacitas_router)
