from fastapi import APIRouter

from app.modules.elaborazioni.autosync_campaign_routes import router as autosync_campaign_router
from app.modules.elaborazioni.runtime_routes import router as runtime_router

router = APIRouter()
router.include_router(runtime_router)
router.include_router(autosync_campaign_router, prefix="/elaborazioni", tags=["elaborazioni"])

__all__ = ["router"]
