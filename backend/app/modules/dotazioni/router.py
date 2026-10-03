from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.dotazioni import custody, services
from app.modules.dotazioni.models import DotazioneAsset, DotazioneCustody, DotazioneEvent
from app.modules.dotazioni.permissions import allowed
from app.modules.dotazioni.read_models import (
    asset_response,
    custody_response,
    get_asset,
    list_assets,
)
from app.modules.dotazioni.schemas import (
    AssetCreate,
    AssetFilters,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
    CustodyListResponse,
    CustodyNotes,
    CustodyTake,
    CustodyTransfer,
)
from app.modules.network.models import NetworkDevice
from app.modules.operazioni.models.vehicles import Vehicle
from app.modules.organigramma.models import OrgUnit

router = APIRouter(
    prefix="/api/dotazioni", tags=["dotazioni"], dependencies=[Depends(require_module("dotazioni"))]
)
Database = Annotated[Session, Depends(get_db)]
Actor = Annotated[ApplicationUser, Depends(require_active_user)]
Read = Depends(require_section("dotazioni.view"))
History = Depends(require_section("dotazioni.history"))


def write(db: Session, operation) -> AssetResponse:
    try:
        asset = operation()
        response = asset_response(db, asset)
        db.commit()
        return response
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            409, "Codice o collegamento duplicato, oppure dotazione gia in custodia"
        ) from error
    except Exception:
        db.rollback()
        raise


@router.get("/assets", response_model=AssetListResponse, dependencies=[Read])
def assets(db: Database, filters: Annotated[AssetFilters, Depends()]):
    return list_assets(db, filters)


@router.post("/assets", response_model=AssetResponse, status_code=201)
def create(body: AssetCreate, db: Database, actor: Actor):
    return write(db, lambda: services.create_asset(db, actor, body.model_dump()))


@router.get("/assets/by-code/{asset_code}", response_model=AssetResponse, dependencies=[Read])
def by_code(asset_code: str, db: Database):
    asset = db.scalar(select(DotazioneAsset).where(DotazioneAsset.asset_code == asset_code.upper()))
    if asset is None:
        raise HTTPException(404, "Dotazione non trovata")
    return asset_response(db, asset)


@router.get("/assets/{asset_id}", response_model=AssetResponse, dependencies=[Read])
def detail(asset_id: UUID, db: Database):
    return asset_response(db, get_asset(db, asset_id))


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
def update(asset_id: UUID, body: AssetUpdate, db: Database, actor: Actor):
    return write(
        db, lambda: services.update_asset(db, actor, asset_id, body.model_dump(exclude_unset=True))
    )


@router.post("/assets/{asset_id}/take", response_model=AssetResponse)
def take(asset_id: UUID, body: CustodyTake, db: Database, actor: Actor):
    return write(
        db, lambda: custody.take(db, actor, asset_id, body.holder_user_id or actor.id, body.notes)
    )


@router.post("/assets/{asset_id}/return", response_model=AssetResponse)
def give_back(asset_id: UUID, body: CustodyNotes, db: Database, actor: Actor):
    return write(db, lambda: custody.give_back(db, actor, asset_id, body.notes))


@router.post("/assets/{asset_id}/transfer", response_model=AssetResponse)
def transfer(asset_id: UUID, body: CustodyTransfer, db: Database, actor: Actor):
    return write(db, lambda: custody.transfer(db, actor, asset_id, body.holder_user_id, body.notes))


@router.get("/assets/{asset_id}/custody", dependencies=[Read])
def current(asset_id: UUID, db: Database):
    return asset_response(db, get_asset(db, asset_id)).current_custody


@router.get(
    "/assets/{asset_id}/custody-history", response_model=CustodyListResponse, dependencies=[History]
)
def history(
    asset_id: UUID,
    db: Database,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    get_asset(db, asset_id)
    query = select(DotazioneCustody).where(DotazioneCustody.asset_id == asset_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(DotazioneCustody.taken_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return CustodyListResponse(items=[custody_response(db, item) for item in items], total=total)


@router.get("/assets/{asset_id}/events", dependencies=[History])
def events(
    asset_id: UUID,
    db: Database,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    get_asset(db, asset_id)
    query = select(DotazioneEvent).where(DotazioneEvent.asset_id == asset_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(DotazioneEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "action": item.action,
                "actor_user_id": item.actor_user_id,
                "details": item.details,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "total": total,
    }


@router.get("/operators/{user_id}/assets", response_model=AssetListResponse, dependencies=[Read])
def operator_assets(user_id: int, db: Database, filters: Annotated[AssetFilters, Depends()]):
    if db.get(ApplicationUser, user_id) is None:
        raise HTTPException(404, "Utente non trovato")
    return list_assets(db, filters.model_copy(update={"holder_user_id": user_id}))


@router.get(
    "/org-units/{org_unit_id}/assets", response_model=AssetListResponse, dependencies=[Read]
)
def unit_assets(org_unit_id: UUID, db: Database, filters: Annotated[AssetFilters, Depends()]):
    if db.get(OrgUnit, org_unit_id) is None:
        raise HTTPException(404, "Unita non trovata")
    return list_assets(db, filters.model_copy(update={"org_unit_id": org_unit_id}))


@router.get("/lookups", dependencies=[Read])
def lookups(db: Database, actor: Actor):
    users = db.scalars(
        select(ApplicationUser)
        .where(ApplicationUser.is_active.is_(True))
        .order_by(ApplicationUser.username)
    ).all()
    units = db.scalars(
        select(OrgUnit).where(OrgUnit.is_active.is_(True)).order_by(OrgUnit.nome)
    ).all()
    network = db.scalars(select(NetworkDevice).order_by(NetworkDevice.id)).all()
    vehicles = db.scalars(
        select(Vehicle).where(Vehicle.is_active.is_(True)).order_by(Vehicle.name)
    ).all()
    return {
        "users": [{"id": item.id, "name": item.full_name or item.username} for item in users],
        "org_units": [{"id": item.id, "name": item.nome} for item in units],
        "network_devices": [
            {"id": item.id, "name": item.display_name or item.hostname or item.ip_address}
            for item in network
        ],
        "vehicles": [{"id": item.id, "name": item.name} for item in vehicles],
        "permissions": [
            f"dotazioni.{action}"
            for action in ("view", "manage", "assign", "custody", "history")
            if allowed(db, actor, action)
        ],
    }
