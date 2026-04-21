from fastapi import APIRouter

from app.modules.accessi.router import router as accessi_router
from app.modules.utenze.router import router as utenze_router
from app.modules.catasto.router import router as catasto_router
from app.modules.core.router import router as core_router
from app.modules.elaborazioni.router import router as elaborazioni_router
from app.modules.inventory.router import router as inventory_router
from app.modules.network.router import router as network_router
from app.modules.operazioni.router import router as operazioni_router
from app.modules.operazioni.routes.operator_invitations import public_router as operator_invitations_public_router
from app.modules.riordino.bootstrap import router as riordino_router
from app.modules.ruolo.router import router as ruolo_router
from app.modules.ruolo.routes.query_routes import catasto_router as catasto_parcels_router

api_router = APIRouter()
api_router.include_router(core_router)
api_router.include_router(accessi_router)
api_router.include_router(catasto_router)
api_router.include_router(catasto_parcels_router, prefix="/catasto")
api_router.include_router(elaborazioni_router)
api_router.include_router(inventory_router)
api_router.include_router(network_router)
api_router.include_router(utenze_router, prefix="/utenze")
api_router.include_router(operazioni_router)
api_router.include_router(operator_invitations_public_router)
api_router.include_router(riordino_router, prefix="/api/riordino")
api_router.include_router(ruolo_router, prefix="/ruolo")
