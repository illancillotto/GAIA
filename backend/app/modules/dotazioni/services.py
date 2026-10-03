from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.dotazioni.models import DotazioneAsset, DotazioneEvent
from app.modules.dotazioni.permissions import require_action
from app.modules.dotazioni.read_models import get_asset, open_custody
from app.modules.network.models import NetworkDevice
from app.modules.operazioni.models.vehicles import Vehicle
from app.modules.organigramma.models import OrgUnit


def record_event(
    db: Session, asset: DotazioneAsset, actor: ApplicationUser, action: str, details: dict
) -> None:
    db.add(
        DotazioneEvent(asset_id=asset.id, actor_user_id=actor.id, action=action, details=details)
    )


def validate_links(db: Session, values: dict) -> None:
    for key, model in (
        ("assigned_org_unit_id", OrgUnit),
        ("network_device_id", NetworkDevice),
        ("vehicle_id", Vehicle),
    ):
        identifier = values.get(key)
        if identifier is None:
            continue
        item = db.get(model, identifier)
        if item is None:
            raise HTTPException(422, f"Riferimento {key} non valido")
        if model in (OrgUnit, Vehicle) and not item.is_active:
            raise HTTPException(422, f"Riferimento {key} inattivo")


def validate_vehicle(values: dict) -> None:
    if values.get("vehicle_id") and values["asset_type"] != "vehicle":
        raise HTTPException(422, "Il collegamento mezzo richiede tipo vehicle")
    if values["asset_type"] == "vehicle" and not values.get("vehicle_id"):
        raise HTTPException(422, "Una dotazione vehicle deve riferirsi a un mezzo esistente")


def create_asset(db: Session, actor: ApplicationUser, values: dict) -> DotazioneAsset:
    require_action(db, actor, "manage")
    if values.get("assigned_org_unit_id"):
        require_action(db, actor, "assign")
    validate_links(db, values)
    validate_vehicle(values)
    asset = DotazioneAsset(**values, created_by_user_id=actor.id, updated_by_user_id=actor.id)
    db.add(asset)
    db.flush()
    record_event(
        db,
        asset,
        actor,
        "asset_created",
        {key: str(value) if isinstance(value, UUID) else value for key, value in values.items()},
    )
    return asset


def update_asset(
    db: Session, actor: ApplicationUser, asset_id: UUID, values: dict
) -> DotazioneAsset:
    require_action(db, actor, "manage")
    asset = get_asset(db, asset_id, lock=True)
    if "assigned_org_unit_id" in values:
        require_action(db, actor, "assign")
    validate_links(db, values)
    merged = {"asset_type": asset.asset_type, "vehicle_id": asset.vehicle_id, **values}
    validate_vehicle(merged)
    if open_custody(db, asset.id) and (
        values.get("is_active") is False
        or values.get("status") == "retired"
        or merged.get("vehicle_id")
    ):
        raise HTTPException(409, "Chiudere la custodia prima di disattivare o collegare un mezzo")
    changes = {}
    for key, value in values.items():
        old = getattr(asset, key)
        if old != value:
            changes[key] = {
                "before": str(old) if isinstance(old, UUID) else old,
                "after": str(value) if isinstance(value, UUID) else value,
            }
            setattr(asset, key, value)
    asset.updated_by_user_id = actor.id
    record_event(db, asset, actor, "asset_updated", changes)
    if "assigned_org_unit_id" in changes:
        record_event(db, asset, actor, "asset_assigned", changes["assigned_org_unit_id"])
    if values.get("is_active") is False:
        record_event(db, asset, actor, "asset_disabled", changes)
    db.flush()
    return asset
