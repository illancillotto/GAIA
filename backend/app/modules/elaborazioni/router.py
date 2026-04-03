from fastapi import APIRouter

from app.modules.elaborazioni.routes import router as elaborazioni_router

router = APIRouter()
router.include_router(elaborazioni_router)
