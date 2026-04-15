from __future__ import annotations

from typing import Annotated
from uuid import UUID

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.fuel_cards import FuelCard, FuelCardAssignmentHistory
from app.modules.operazioni.schemas.fuel_cards import (
    FuelCardAssignRequest,
    FuelCardAssignmentResponse,
    FuelCardImportResult,
    FuelCardListResponse,
    FuelCardResponse,
)
from app.modules.operazioni.services.import_fuel_cards import import_fuel_cards

router = APIRouter(prefix="/fuel-cards", tags=["operazioni/fuel-cards"])


@router.get("", response_model=FuelCardListResponse)
def list_fuel_cards_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None),
    blocked: bool | None = Query(None),
    assigned: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(FuelCard)
    if search:
        like = f"%{search}%"
        query = query.where(
            or_(
                FuelCard.pan.ilike(like),
                FuelCard.codice.ilike(like),
                FuelCard.sigla.ilike(like),
                FuelCard.cod.ilike(like),
                FuelCard.current_driver_raw.ilike(like),
            )
        )
    if blocked is not None:
        query = query.where(FuelCard.is_blocked == blocked)
    if assigned is not None:
        query = query.where(
            FuelCard.current_wc_operator_id.is_not(None)
            if assigned
            else FuelCard.current_wc_operator_id.is_(None)
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(FuelCard.is_blocked.desc(), FuelCard.expires_at.asc().nullslast(), FuelCard.codice.asc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return FuelCardListResponse(
        items=[
            FuelCardResponse(
                **FuelCardResponse.model_validate(item).model_dump(exclude={"driver"}),
                driver=item.current_driver_raw,
            )
            for item in items
        ],
        total=total,
    )


@router.get("/unmatched", response_model=FuelCardListResponse)
def list_unmatched_fuel_cards_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = (
        select(FuelCard)
        .where(FuelCard.current_wc_operator_id.is_(None))
        .where(FuelCard.ignore_driver_match.is_(False))
        .where(FuelCard.current_driver_raw.is_not(None))
        .where(FuelCard.current_driver_raw != "")
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(FuelCard.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return FuelCardListResponse(
        items=[
            FuelCardResponse(
                **FuelCardResponse.model_validate(item).model_dump(exclude={"driver"}),
                driver=item.current_driver_raw,
            )
            for item in items
        ],
        total=total,
    )


@router.post("/{fuel_card_id}/ignore", response_model=FuelCardResponse)
def ignore_fuel_card_driver_endpoint(
    fuel_card_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    note: str | None = None,
):
    card = db.get(FuelCard, fuel_card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel card not found")

    card.ignore_driver_match = True
    card.ignored_at = datetime.utcnow()
    card.ignored_by_user_id = current_user.id
    card.ignored_note = note
    db.commit()

    payload = FuelCardResponse.model_validate(card).model_dump()
    payload["driver"] = card.current_driver_raw
    return FuelCardResponse(**payload)


@router.get("/{fuel_card_id}", response_model=FuelCardResponse)
def get_fuel_card_endpoint(
    fuel_card_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    item = db.get(FuelCard, fuel_card_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel card not found")
    data = FuelCardResponse.model_validate(item).model_dump()
    data["driver"] = item.current_driver_raw
    return FuelCardResponse(**data)


@router.get("/{fuel_card_id}/assignments", response_model=list[FuelCardAssignmentResponse])
def list_fuel_card_assignments_endpoint(
    fuel_card_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    card = db.get(FuelCard, fuel_card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel card not found")
    items = db.scalars(
        select(FuelCardAssignmentHistory)
        .where(FuelCardAssignmentHistory.fuel_card_id == fuel_card_id)
        .order_by(FuelCardAssignmentHistory.start_at.desc())
    ).all()
    return [FuelCardAssignmentResponse.model_validate(item) for item in items]


@router.post("/{fuel_card_id}/assign", response_model=FuelCardResponse)
def assign_fuel_card_endpoint(
    fuel_card_id: UUID,
    data: FuelCardAssignRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    card = db.get(FuelCard, fuel_card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel card not found")

    now = datetime.utcnow()
    current_assignment = db.scalar(
        select(FuelCardAssignmentHistory)
        .where(
            FuelCardAssignmentHistory.fuel_card_id == fuel_card_id,
            FuelCardAssignmentHistory.end_at.is_(None),
        )
        .order_by(FuelCardAssignmentHistory.start_at.desc())
    )
    if current_assignment and current_assignment.wc_operator_id != data.wc_operator_id:
        current_assignment.end_at = now
        current_assignment.note = (
            (current_assignment.note or "").strip()
            + (" | " if current_assignment.note else "")
            + "Chiusura per riassegnazione manuale"
        )[:1000]

    db.add(
        FuelCardAssignmentHistory(
            fuel_card_id=fuel_card_id,
            wc_operator_id=data.wc_operator_id,
            driver_raw=data.driver_raw or card.current_driver_raw,
            start_at=now,
            end_at=None,
            changed_by_user_id=current_user.id,
            source="manual",
            note=data.note or "Assegnazione manuale carta carburante",
        )
    )

    card.current_wc_operator_id = data.wc_operator_id
    if data.driver_raw is not None:
        card.current_driver_raw = data.driver_raw
    db.commit()

    payload = FuelCardResponse.model_validate(card).model_dump()
    payload["driver"] = card.current_driver_raw
    return FuelCardResponse(**payload)


@router.post("/import-excel", response_model=FuelCardImportResult)
async def import_fuel_cards_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="È richiesto un file Excel .xlsx",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il file caricato è vuoto",
        )

    result = import_fuel_cards(db=db, current_user=current_user, file_bytes=file_bytes)
    return FuelCardImportResult(
        imported=result.imported,
        updated=result.updated,
        skipped=result.skipped,
        assignments_created=result.assignments_created,
        assignments_closed=result.assignments_closed,
        rows_read=result.rows_read,
        unmatched_drivers=result.unmatched_drivers,
        errors=result.errors,
    )

