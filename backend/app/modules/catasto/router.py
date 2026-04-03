from fastapi import APIRouter

from app.modules.catasto.routes import router as catasto_router

router = APIRouter()
router.include_router(catasto_router)
