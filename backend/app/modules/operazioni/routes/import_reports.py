"""Import endpoints for Operazioni field reports."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import FleetUnresolvedTransaction
from app.modules.operazioni.services.import_fleet_transactions import (
    ResolvedTransaction,
    import_fleet_transactions,
    resolve_fleet_transactions,
    skip_unresolved_transaction,
)
from app.modules.operazioni.services.import_white import import_white_reports

router = APIRouter(prefix="", tags=["operazioni/reports-import"])


class ResolvedTransactionIn(BaseModel):
    vehicle_id: str
    fueled_at_iso: str
    liters: str
    total_cost: str | None = None
    odometer_km: str | None = None
    card_code: str | None = None
    station_name: str | None = None
    notes_extra: str | None = None
    unresolved_id: str | None = None


@router.post("/reports/import-white", response_model=dict)
async def import_white_reports_endpoint(
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

    result = import_white_reports(
        db=db,
        current_user=current_user,
        file_bytes=file_bytes,
    )
    return {
        "imported": result.imported,
        "skipped": result.skipped,
        "errors": result.errors,
        "categories_created": result.categories_created,
        "total_events_created": result.total_events_created,
    }


@router.post("/vehicles/fuel-logs/import-fleet-transactions", response_model=dict)
async def import_fleet_transactions_endpoint(
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

    result = import_fleet_transactions(
        db=db,
        current_user=current_user,
        file_bytes=file_bytes,
    )
    return {
        "imported": result.imported,
        "skipped": result.skipped,
        "errors": result.errors,
        "rows_read": result.rows_read,
        "import_ref": result.import_ref,
        "matched_white_refuels": result.matched_white_refuels,
        "unresolved": [
            {
                "db_id": u.db_id,
                "row_index": u.row_index,
                "reason_type": u.reason_type,
                "reason_detail": u.reason_detail,
                "targa": u.targa,
                "identificativo": u.identificativo,
                "fueled_at_iso": u.fueled_at_iso,
                "liters": u.liters,
                "total_cost": u.total_cost,
                "odometer_km": u.odometer_km,
                "operator_name": u.operator_name,
                "wc_operator_id": u.wc_operator_id,
                "card_code": u.card_code,
                "station_name": u.station_name,
                "notes_extra": u.notes_extra,
            }
            for u in result.unresolved
        ],
    }


@router.post("/vehicles/fuel-logs/resolve-fleet-transactions", response_model=dict)
def resolve_fleet_transactions_endpoint(
    body: list[ResolvedTransactionIn],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    from uuid import UUID
    resolutions = [
        ResolvedTransaction(
            vehicle_id=UUID(item.vehicle_id),
            fueled_at_iso=item.fueled_at_iso,
            liters=item.liters,
            total_cost=item.total_cost,
            odometer_km=item.odometer_km,
            card_code=item.card_code,
            station_name=item.station_name,
            notes_extra=item.notes_extra,
            unresolved_id=item.unresolved_id,
        )
        for item in body
    ]
    result = resolve_fleet_transactions(
        db=db,
        current_user=current_user,
        resolutions=resolutions,
    )
    return {"imported": result.imported, "skipped": result.skipped, "errors": result.errors}


@router.post("/vehicles/fuel-logs/unresolved-transactions/{unresolved_id}/skip", response_model=dict)
def skip_unresolved_transaction_endpoint(
    unresolved_id: str,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ok = skip_unresolved_transaction(db=db, current_user=current_user, unresolved_id=unresolved_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Riga non trovata")
    return {"ok": True}


@router.get("/vehicles/fuel-logs/unresolved-transactions", response_model=dict)
def list_unresolved_transactions(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str = "pending",
    page: int = 1,
    page_size: int = 50,
):
    q = select(FleetUnresolvedTransaction)
    if status_filter != "all":
        q = q.where(FleetUnresolvedTransaction.status == status_filter)
    q = q.order_by(FleetUnresolvedTransaction.created_at.desc())

    total = db.scalar(select(FleetUnresolvedTransaction.id).where(
        FleetUnresolvedTransaction.status == status_filter if status_filter != "all"
        else FleetUnresolvedTransaction.status.isnot(None)
    ).with_only_columns(
        *[FleetUnresolvedTransaction.__table__.c.id]
    )) or 0

    from sqlalchemy import func as sqlfunc
    count_q = select(sqlfunc.count()).select_from(FleetUnresolvedTransaction)
    if status_filter != "all":
        count_q = count_q.where(FleetUnresolvedTransaction.status == status_filter)
    total = db.scalar(count_q) or 0

    items = db.scalars(
        q.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
        "items": [
            {
                "id": str(item.id),
                "import_ref": item.import_ref,
                "status": item.status,
                "row_index": item.row_index,
                "reason_type": item.reason_type,
                "reason_detail": item.reason_detail,
                "targa": item.targa,
                "identificativo": item.identificativo,
                "fueled_at_iso": item.fueled_at_iso,
                "liters": item.liters,
                "total_cost": item.total_cost,
                "odometer_km": item.odometer_km,
                "operator_name": item.operator_name,
                "wc_operator_id": item.wc_operator_id,
                "card_code": item.card_code,
                "station_name": item.station_name,
                "notes_extra": item.notes_extra,
                "resolved_vehicle_id": str(item.resolved_vehicle_id) if item.resolved_vehicle_id else None,
                "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
    }
