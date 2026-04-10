"""Parcel and party link routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import (
    ParcelLinkCreate,
    ParcelLinkResponse,
    PartyLinkCreate,
    PartyLinkResponse,
)
from app.modules.riordino.services import (
    create_parcel,
    create_party,
    delete_parcel,
    delete_party,
    import_parcels_csv,
    list_parcels,
    list_parties,
)

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.practices"))])


@router.post("/{practice_id}/parcels", response_model=ParcelLinkResponse)
def create_parcel_endpoint(
    practice_id: UUID,
    payload: ParcelLinkCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parcel = create_parcel(db, practice_id, payload.model_dump())
    db.commit()
    return parcel


@router.get("/{practice_id}/parcels", response_model=list[ParcelLinkResponse])
def list_parcels_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return [ParcelLinkResponse.model_validate(item) for item in list_parcels(db, practice_id)]


@router.delete("/{practice_id}/parcels/{parcel_id}", response_model=ParcelLinkResponse)
def delete_parcel_endpoint(
    practice_id: UUID,
    parcel_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parcel = delete_parcel(db, practice_id, parcel_id)
    db.commit()
    return parcel


@router.post("/{practice_id}/parcels/import-csv", response_model=list[ParcelLinkResponse])
def import_parcels_csv_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    items = import_parcels_csv(db, practice_id, file)
    db.commit()
    return [ParcelLinkResponse.model_validate(item) for item in items]


@router.post("/{practice_id}/parties", response_model=PartyLinkResponse)
def create_party_endpoint(
    practice_id: UUID,
    payload: PartyLinkCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    party = create_party(db, practice_id, payload.model_dump())
    db.commit()
    return party


@router.get("/{practice_id}/parties", response_model=list[PartyLinkResponse])
def list_parties_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return [PartyLinkResponse.model_validate(item) for item in list_parties(db, practice_id)]


@router.delete("/{practice_id}/parties/{party_id}", response_model=PartyLinkResponse)
def delete_party_endpoint(
    practice_id: UUID,
    party_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    party = delete_party(db, practice_id, party_id)
    db.commit()
    return party
