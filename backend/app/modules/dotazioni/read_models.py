from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.dotazioni.models import DotazioneAsset, DotazioneCustody
from app.modules.dotazioni.schemas import (
    AssetFilters,
    AssetListResponse,
    AssetResponse,
    CustodyResponse,
)
from app.modules.operazioni.models.vehicles import Vehicle
from app.modules.organigramma.models import OrgUnit


def get_asset(db: Session, asset_id: UUID, *, lock: bool = False) -> DotazioneAsset:
    query = select(DotazioneAsset).where(DotazioneAsset.id == asset_id)
    if lock:
        query = query.with_for_update()
    asset = db.scalar(query)
    if asset is None:
        raise HTTPException(404, "Dotazione non trovata")
    return asset


def open_custody(db: Session, asset_id: UUID) -> DotazioneCustody | None:
    return db.scalar(
        select(DotazioneCustody).where(
            DotazioneCustody.asset_id == asset_id, DotazioneCustody.returned_at.is_(None)
        )
    )


def custody_response(db: Session, custody: DotazioneCustody) -> CustodyResponse:
    holder = db.get(ApplicationUser, custody.holder_user_id)
    previous = (
        db.get(ApplicationUser, custody.handover_from_user_id)
        if custody.handover_from_user_id is not None
        else None
    )
    return CustodyResponse(
        **{
            field: getattr(custody, field)
            for field in CustodyResponse.model_fields
            if field not in ("holder_name", "handover_from_name")
        },
        holder_name=holder.full_name or holder.username,
        handover_from_name=(previous.full_name or previous.username) if previous else None,
    )


def asset_response(db: Session, asset: DotazioneAsset) -> AssetResponse:
    custody = open_custody(db, asset.id)
    unit = db.get(OrgUnit, asset.assigned_org_unit_id) if asset.assigned_org_unit_id else None
    vehicle = db.get(Vehicle, asset.vehicle_id) if asset.vehicle_id else None
    effective = "in_use" if custody and asset.status == "available" else asset.status
    return AssetResponse(
        **{
            field: getattr(asset, field)
            for field in AssetResponse.model_fields
            if hasattr(asset, field)
        },
        effective_status=effective,
        assigned_org_unit_name=unit.nome if unit else None,
        plate_number=vehicle.plate_number if vehicle else None,
        vehicle_status=vehicle.current_status if vehicle else None,
        current_custody=custody_response(db, custody) if custody else None,
    )


def list_assets(db: Session, filters: AssetFilters) -> AssetListResponse:
    query = select(DotazioneAsset)
    occupied = select(DotazioneCustody.asset_id).where(DotazioneCustody.returned_at.is_(None))
    if filters.search:
        pattern = f"%{filters.search}%"
        query = query.where(
            or_(
                *(
                    column.ilike(pattern)
                    for column in (
                        DotazioneAsset.asset_code,
                        DotazioneAsset.name,
                        DotazioneAsset.serial_number,
                        DotazioneAsset.model,
                        DotazioneAsset.notes,
                    )
                )
            )
        )
    for key, value in (
        ("asset_type", filters.asset_type),
        ("assigned_org_unit_id", filters.org_unit_id),
        ("is_active", filters.active),
    ):
        if value is not None:
            query = query.where(getattr(DotazioneAsset, key) == value)
    if filters.status in ("available", "in_use"):
        query = query.where(DotazioneAsset.status == "available")
        query = query.where(
            DotazioneAsset.id.in_(occupied)
            if filters.status == "in_use"
            else DotazioneAsset.id.not_in(occupied)
        )
    elif filters.status:
        query = query.where(DotazioneAsset.status == filters.status)
    if filters.holder_user_id:
        query = query.where(
            DotazioneAsset.id.in_(
                occupied.where(DotazioneCustody.holder_user_id == filters.holder_user_id)
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    assets = db.scalars(
        query.order_by(DotazioneAsset.asset_code)
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    ).all()
    return AssetListResponse(items=[asset_response(db, asset) for asset in assets], total=total)
