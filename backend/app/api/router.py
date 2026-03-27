from fastapi import APIRouter

from app.modules.accessi.router import router as accessi_router
from app.modules.anagrafica.router import router as anagrafica_router
from app.modules.catasto.router import router as catasto_router
from app.modules.core.router import router as core_router
from app.modules.network.router import router as network_router

api_router = APIRouter()
api_router.include_router(core_router)
api_router.include_router(accessi_router)
api_router.include_router(catasto_router)
api_router.include_router(network_router)
api_router.include_router(anagrafica_router)
