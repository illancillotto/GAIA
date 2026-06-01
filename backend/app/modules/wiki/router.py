from fastapi import APIRouter

from app.modules.wiki.routes.articles import router as articles_router
from app.modules.wiki.routes.audit import router as audit_router
from app.modules.wiki.routes.chat import router as chat_router
from app.modules.wiki.routes.conversations import router as conversations_router
from app.modules.wiki.routes.index import router as index_router
from app.modules.wiki.routes.requests import router as requests_router
from app.modules.wiki.routes.telemetry import router as telemetry_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(conversations_router)
router.include_router(articles_router)
router.include_router(audit_router)
router.include_router(telemetry_router)
router.include_router(requests_router)
router.include_router(index_router)
