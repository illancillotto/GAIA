"""Router principale del modulo Ruolo."""
from fastapi import APIRouter

from app.modules.ruolo.routes.import_routes import router as import_router
from app.modules.ruolo.routes.query_routes import catasto_router, router as query_router

router = APIRouter()
router.include_router(import_router)
router.include_router(query_router)
