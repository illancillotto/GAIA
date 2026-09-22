"""Router principale del modulo Ruolo."""
from fastapi import APIRouter

from app.modules.ruolo.routes.import_routes import router as import_router
from app.modules.ruolo.routes.notice_confirmation_routes import router as notice_confirmation_router
from app.modules.ruolo.routes.notice_document_routes import router as notice_document_router
from app.modules.ruolo.routes.notice_import_routes import router as notice_import_router
from app.modules.ruolo.routes.notice_register_routes import router as notice_register_router
from app.modules.ruolo.routes.query_routes import catasto_router as catasto_router
from app.modules.ruolo.routes.query_routes import router as query_router
from app.modules.ruolo.routes.tributi_routes import router as tributi_router

router = APIRouter()
router.include_router(import_router)
router.include_router(query_router)
router.include_router(tributi_router)
router.include_router(notice_confirmation_router)
router.include_router(notice_document_router)
router.include_router(notice_import_router)
router.include_router(notice_register_router)
