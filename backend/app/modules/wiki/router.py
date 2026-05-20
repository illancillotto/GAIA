from fastapi import APIRouter

from app.modules.wiki.routes.articles import router as articles_router
from app.modules.wiki.routes.chat import router as chat_router
from app.modules.wiki.routes.index import router as index_router
from app.modules.wiki.routes.requests import router as requests_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(articles_router)
router.include_router(requests_router)
router.include_router(index_router)
