from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.modules.accessi.router import router as accessi_router
from app.modules.utenze.router import router as utenze_router
from app.modules.utenze.anpr.routes import router as utenze_anpr_router
from app.modules.catasto.router import router as catasto_router
from app.modules.core.router import router as core_router
from app.modules.elaborazioni.router import router as elaborazioni_router
from app.modules.inventory.router import router as inventory_router
from app.modules.inaz.router import router as inaz_router
from app.modules.me.router import router as me_router
from app.modules.network.router import router as network_router
from app.modules.operazioni.router import router as operazioni_router
from app.modules.organigramma.router import router as organigramma_router
from app.modules.operazioni.routes.mobile_sync import router as mobile_sync_router
from app.modules.operazioni.routes.operator_invitations import public_router as operator_invitations_public_router
from app.modules.riordino.bootstrap import router as riordino_router
from app.modules.ruolo.router import router as ruolo_router
from app.modules.ruolo.routes.query_routes import catasto_router as catasto_parcels_router
from app.modules.wiki.router import router as wiki_router


def _build_alias_router(source_router: APIRouter, *, source_prefix: str, target_prefix: str) -> APIRouter:
    alias_router = APIRouter()
    for route in source_router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(source_prefix):
            continue
        alias_path = target_prefix + route.path[len(source_prefix) :]
        alias_router.add_api_route(
            alias_path,
            route.endpoint,
            response_model=route.response_model,
            status_code=route.status_code,
            tags=route.tags,
            dependencies=route.dependencies,
            summary=route.summary,
            description=route.description,
            response_description=route.response_description,
            responses=route.responses,
            deprecated=route.deprecated,
            methods=route.methods,
            operation_id=f"{route.operation_id or route.name}_alias_{target_prefix.strip('/').replace('/', '_')}",
            name=f"{route.name}_{target_prefix.strip('/').replace('/', '_')}",
            response_model_include=route.response_model_include,
            response_model_exclude=route.response_model_exclude,
            response_model_by_alias=route.response_model_by_alias,
            response_model_exclude_unset=route.response_model_exclude_unset,
            response_model_exclude_defaults=route.response_model_exclude_defaults,
            response_model_exclude_none=route.response_model_exclude_none,
            include_in_schema=route.include_in_schema,
            response_class=route.response_class,
            callbacks=route.callbacks,
            openapi_extra=route.openapi_extra,
        )
    return alias_router


api_router = APIRouter()
api_router.include_router(core_router)
api_router.include_router(accessi_router)
api_router.include_router(catasto_router)
api_router.include_router(catasto_parcels_router, prefix="/catasto")
api_router.include_router(elaborazioni_router)
api_router.include_router(inventory_router)
api_router.include_router(inaz_router)
api_router.include_router(_build_alias_router(inaz_router, source_prefix="/inaz", target_prefix="/presenze"))
api_router.include_router(me_router)
api_router.include_router(_build_alias_router(me_router, source_prefix="/me/inaz", target_prefix="/me/presenze"))
api_router.include_router(network_router)
api_router.include_router(utenze_router, prefix="/utenze")
api_router.include_router(utenze_anpr_router)
api_router.include_router(operazioni_router)
api_router.include_router(organigramma_router)
api_router.include_router(mobile_sync_router)
api_router.include_router(operator_invitations_public_router)
api_router.include_router(riordino_router, prefix="/api/riordino")
api_router.include_router(ruolo_router, prefix="/ruolo")
api_router.include_router(wiki_router, prefix="/wiki")
