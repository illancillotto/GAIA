from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.dotazioni.models import DotazioneAsset, DotazioneCustody
from app.modules.dotazioni.permissions import (
    allowed,
    member_unit_ids,
    require_close_scope,
    require_take_scope,
)
from app.modules.dotazioni.read_models import get_asset, open_custody
from app.modules.dotazioni.services import record_event


def validate_holder(db: Session, holder_id: int) -> None:
    holder = db.get(ApplicationUser, holder_id)
    if holder is None or not holder.is_active:
        raise HTTPException(422, "Custode inesistente o inattivo")


def require_available(asset: DotazioneAsset) -> None:
    if asset.vehicle_id:
        raise HTTPException(409, "I mezzi sono gestiti in Operazioni")
    if not asset.is_active or asset.status != "available":
        raise HTTPException(409, "Dotazione non disponibile")


def close_custody(
    custody: DotazioneCustody, actor: ApplicationUser, now: datetime, notes: str | None
) -> None:
    taken = (
        custody.taken_at.replace(tzinfo=UTC)
        if custody.taken_at.tzinfo is None
        else custody.taken_at
    )
    if now < taken:
        raise HTTPException(409, "Timestamp di restituzione precedente alla presa")
    custody.returned_at = now
    custody.returned_by_user_id = actor.id
    custody.return_notes = notes


def take(
    db: Session, actor: ApplicationUser, asset_id: UUID, holder_id: int, notes: str | None
) -> DotazioneAsset:
    asset = get_asset(db, asset_id, lock=True)
    require_take_scope(db, actor, asset, holder_id)
    validate_holder(db, holder_id)
    require_available(asset)
    if open_custody(db, asset.id):
        raise HTTPException(409, "Dotazione gia in custodia")
    db.add(
        DotazioneCustody(
            asset_id=asset.id,
            holder_user_id=holder_id,
            taken_at=datetime.now(UTC),
            recorded_by_user_id=actor.id,
            notes=notes,
        )
    )
    record_event(db, asset, actor, "custody_started", {"holder_user_id": holder_id, "notes": notes})
    db.flush()
    return asset


def give_back(
    db: Session, actor: ApplicationUser, asset_id: UUID, notes: str | None
) -> DotazioneAsset:
    asset = get_asset(db, asset_id, lock=True)
    custody = open_custody(db, asset.id)
    if custody is None:
        raise HTTPException(409, "Dotazione senza custodia aperta")
    require_close_scope(db, actor, custody.holder_user_id)
    close_custody(custody, actor, datetime.now(UTC), notes)
    record_event(
        db,
        asset,
        actor,
        "custody_returned",
        {"holder_user_id": custody.holder_user_id, "notes": notes},
    )
    db.flush()
    return asset


def transfer(
    db: Session, actor: ApplicationUser, asset_id: UUID, holder_id: int, notes: str | None
) -> DotazioneAsset:
    asset = get_asset(db, asset_id, lock=True)
    custody = open_custody(db, asset.id)
    if custody is None:
        raise HTTPException(409, "Dotazione senza custodia aperta")
    require_close_scope(db, actor, custody.holder_user_id)
    validate_holder(db, holder_id)
    require_available(asset)
    if holder_id == custody.holder_user_id:
        raise HTTPException(409, "Il nuovo custode coincide con quello corrente")
    if not allowed(db, actor, "manage") and asset.assigned_org_unit_id not in member_unit_ids(
        db, holder_id
    ):
        raise HTTPException(403, "Destinatario fuori dal perimetro della dotazione")
    now = datetime.now(UTC)
    previous_id = custody.holder_user_id
    close_custody(custody, actor, now, notes)
    db.flush()
    db.add(
        DotazioneCustody(
            asset_id=asset.id,
            holder_user_id=holder_id,
            taken_at=now,
            recorded_by_user_id=actor.id,
            handover_from_user_id=previous_id,
            notes=notes,
        )
    )
    record_event(
        db,
        asset,
        actor,
        "custody_transferred",
        {"previous_holder_user_id": previous_id, "holder_user_id": holder_id, "notes": notes},
    )
    db.flush()
    return asset
