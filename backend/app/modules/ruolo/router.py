"""Router principale del modulo Ruolo."""
from fastapi import APIRouter

from app.modules.ruolo.routes.import_routes import router as import_router
from app.modules.ruolo.routes.query_routes import catasto_router, router as query_router
from app.modules.ruolo.routes.tributi_routes import router as tributi_router

router = APIRouter()
router.include_router(import_router)
router.include_router(query_router)
router.include_router(tributi_router)
