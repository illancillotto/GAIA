from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_role
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.fuel_cards import FuelCard
from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.schemas.operators import (
    AutoLinkResult,
    GaiaUserMin,
    LinkGaiaRequest,
    OperatorFuelCardSummary,
    OperatorFuelLogSummary,
    OperatorUsageSessionSummary,
    OperatorVehicleUsageSummary,
    UnlinkedOperatorItem,
    UnlinkedOperatorsResponse,
    WCOperatorDetailResponse,
    WCOperatorDetailStats,
    WCOperatorListResponse,
    WCOperatorResponse,
)


router = APIRouter(prefix="/operators", tags=["operazioni/operators"])


def _vehicle_label(vehicle: Vehicle | None, fallback_id: UUID | None = None) -> str:
    if vehicle is None:
        return f"Mezzo {fallback_id}" if fallback_id else "Mezzo non trovato"
    parts = [vehicle.code, vehicle.name]
    if vehicle.plate_number:
        parts.append(vehicle.plate_number)
    return " · ".join(part for part in parts if part)


def _serialize_fuel_card(card: FuelCard) -> OperatorFuelCardSummary:
    return OperatorFuelCardSummary.model_validate(card)


def _serialize_operator(item: WCOperator, current_fuel_cards: list[FuelCard]) -> WCOperatorResponse:
    payload = WCOperatorResponse.model_validate(item).model_dump(exclude={"current_fuel_cards"})
    return WCOperatorResponse(
        **payload,
        current_fuel_cards=[_serialize_fuel_card(card) for card in current_fuel_cards],
    )


def _session_km(session: VehicleUsageSession) -> Decimal | None:
    if session.end_odometer_km is not None and session.start_odometer_km is not None:
        diff = session.end_odometer_km - session.start_odometer_km
        if diff >= 0:
            return diff
    return None


@router.get("", response_model=WCOperatorListResponse)
def list_operators_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None),
    role: str | None = Query(None),
    enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(WCOperator)
    if search:
        like = f"%{search}%"
        query = query.where(
            (WCOperator.username.ilike(like))
            | (WCOperator.email.ilike(like))
            | (WCOperator.first_name.ilike(like))
            | (WCOperator.last_name.ilike(like))
            | (WCOperator.tax.ilike(like))
        )
    if role:
        query = query.where(WCOperator.role == role)
    if enabled is not None:
        query = query.where(WCOperator.enabled == enabled)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(WCOperator.role.asc(), WCOperator.last_name.asc(), WCOperator.first_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    fuel_cards_by_operator: dict[UUID, list[FuelCard]] = {}
    operator_ids = [item.id for item in items]
    if operator_ids:
        current_cards = db.scalars(
            select(FuelCard)
            .where(FuelCard.current_wc_operator_id.in_(operator_ids))
            .order_by(FuelCard.codice.asc().nullslast(), FuelCard.pan.asc())
        ).all()
        for card in current_cards:
            if card.current_wc_operator_id is None:
                continue
            fuel_cards_by_operator.setdefault(card.current_wc_operator_id, []).append(card)

    return WCOperatorListResponse(
        items=[_serialize_operator(item, fuel_cards_by_operator.get(item.id, [])) for item in items],
        total=total,
    )


@router.get("/unlinked", response_model=UnlinkedOperatorsResponse)
def list_unlinked_operators(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    unlinked = db.scalars(
        select(WCOperator)
        .where(WCOperator.gaia_user_id.is_(None))
        .order_by(WCOperator.last_name.asc(), WCOperator.first_name.asc())
    ).all()

    # Build lookup maps for email and username matching
    all_gaia_users = db.scalars(select(ApplicationUser)).all()
    by_email: dict[str, ApplicationUser] = {}
    by_username: dict[str, ApplicationUser] = {}
    for u in all_gaia_users:
        if u.email:
            by_email[u.email.lower()] = u
        if u.username:
            by_username[u.username.lower()] = u

    items: list[UnlinkedOperatorItem] = []
    for op in unlinked:
        suggested: ApplicationUser | None = None
        if op.email:
            suggested = by_email.get(op.email.lower())
        if suggested is None and op.username:
            suggested = by_username.get(op.username.lower())

        items.append(UnlinkedOperatorItem(
            id=op.id,
            wc_id=op.wc_id,
            username=op.username,
            email=op.email,
            first_name=op.first_name,
            last_name=op.last_name,
            role=op.role,
            enabled=op.enabled,
            suggested_gaia_user=GaiaUserMin(
                id=suggested.id,
                username=suggested.username,
                email=suggested.email,
                is_active=suggested.is_active,
            ) if suggested else None,
        ))

    return UnlinkedOperatorsResponse(items=items, total=len(items))


@router.get("/gaia-users", response_model=list[GaiaUserMin])
def list_gaia_users_for_linking(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None),
):
    query = select(ApplicationUser)
    if search:
        like = f"%{search}%"
        query = query.where(
            ApplicationUser.username.ilike(like) | ApplicationUser.email.ilike(like)
        )
    users = db.scalars(query.order_by(ApplicationUser.username.asc()).limit(50)).all()
    return [GaiaUserMin(id=u.id, username=u.username, email=u.email, is_active=u.is_active) for u in users]


@router.post("/auto-link-gaia", response_model=AutoLinkResult)
def auto_link_gaia(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    unlinked = db.scalars(
        select(WCOperator).where(WCOperator.gaia_user_id.is_(None))
    ).all()

    all_gaia_users = db.scalars(select(ApplicationUser)).all()
    by_email: dict[str, ApplicationUser] = {}
    by_username: dict[str, ApplicationUser] = {}
    for u in all_gaia_users:
        if u.email:
            by_email[u.email.lower()] = u
        if u.username:
            by_username[u.username.lower()] = u

    linked = 0
    skipped = 0
    for op in unlinked:
        match: ApplicationUser | None = None
        if op.email:
            match = by_email.get(op.email.lower())
        if match is None and op.username:
            match = by_username.get(op.username.lower())
        if match:
            op.gaia_user_id = match.id
            linked += 1
        else:
            skipped += 1

    db.commit()
    return AutoLinkResult(linked=linked, already_linked=0, skipped=skipped)


@router.post("/{operator_id}/link-gaia", response_model=WCOperatorResponse)
def link_gaia_user(
    operator_id: UUID,
    body: LinkGaiaRequest,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    op = db.get(WCOperator, operator_id)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    gaia_user = db.get(ApplicationUser, body.gaia_user_id)
    if gaia_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GAIA user not found")
    op.gaia_user_id = gaia_user.id
    db.commit()
    db.refresh(op)
    current_cards = db.scalars(
        select(FuelCard)
        .where(FuelCard.current_wc_operator_id == op.id)
        .order_by(FuelCard.codice.asc().nullslast(), FuelCard.pan.asc())
    ).all()
    return _serialize_operator(op, current_cards)


@router.post("/{operator_id}/unlink-gaia", response_model=WCOperatorResponse)
def unlink_gaia_user(
    operator_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    op = db.get(WCOperator, operator_id)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    op.gaia_user_id = None
    db.commit()
    db.refresh(op)
    current_cards = db.scalars(
        select(FuelCard)
        .where(FuelCard.current_wc_operator_id == op.id)
        .order_by(FuelCard.codice.asc().nullslast(), FuelCard.pan.asc())
    ).all()
    return _serialize_operator(op, current_cards)


@router.get("/{operator_id}", response_model=WCOperatorResponse)
def get_operator_endpoint(
    operator_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    item = db.get(WCOperator, operator_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    current_cards = db.scalars(
        select(FuelCard)
        .where(FuelCard.current_wc_operator_id == item.id)
        .order_by(FuelCard.codice.asc().nullslast(), FuelCard.pan.asc())
    ).all()
    return _serialize_operator(item, current_cards)


@router.get("/{operator_id}/detail", response_model=WCOperatorDetailResponse)
def get_operator_detail_endpoint(
    operator_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_role("super_admin", "admin"))],
    db: Annotated[Session, Depends(get_db)],
):
    operator = db.get(WCOperator, operator_id)
    if operator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

    current_cards = db.scalars(
        select(FuelCard)
        .where(FuelCard.current_wc_operator_id == operator.id)
        .order_by(FuelCard.codice.asc().nullslast(), FuelCard.pan.asc())
    ).all()

    fuel_logs = db.scalars(
        select(VehicleFuelLog)
        .where(VehicleFuelLog.wc_operator_id == operator.id)
        .order_by(VehicleFuelLog.fueled_at.desc())
        .limit(8)
    ).all()
    fuel_log_vehicle_ids = {item.vehicle_id for item in fuel_logs}
    fuel_log_vehicles = {
        vehicle.id: vehicle
        for vehicle in db.scalars(select(Vehicle).where(Vehicle.id.in_(fuel_log_vehicle_ids))).all()
    } if fuel_log_vehicle_ids else {}

    fuel_stats = db.execute(
        select(
            func.count(VehicleFuelLog.id),
            func.coalesce(func.sum(VehicleFuelLog.liters), 0),
            func.coalesce(func.sum(VehicleFuelLog.total_cost), 0),
        ).where(VehicleFuelLog.wc_operator_id == operator.id)
    ).one()

    usage_filter = None
    normalized_name = " ".join(part for part in [operator.first_name, operator.last_name] if part).strip().lower()
    if operator.gaia_user_id is not None:
        usage_filter = VehicleUsageSession.actual_driver_user_id == operator.gaia_user_id
    elif normalized_name:
        usage_filter = func.lower(func.trim(VehicleUsageSession.operator_name)) == normalized_name

    recent_sessions: list[VehicleUsageSession] = []
    usage_sessions_count = 0
    total_km_travelled = Decimal("0")
    most_used_vehicle: OperatorVehicleUsageSummary | None = None
    last_used_vehicle_label: str | None = None

    if usage_filter is not None:
        recent_sessions = db.scalars(
            select(VehicleUsageSession)
            .where(usage_filter)
            .order_by(VehicleUsageSession.started_at.desc())
            .limit(8)
        ).all()

        km_expr = case(
            (
                (VehicleUsageSession.end_odometer_km.is_not(None))
                & (VehicleUsageSession.start_odometer_km.is_not(None))
                & (VehicleUsageSession.end_odometer_km >= VehicleUsageSession.start_odometer_km),
                VehicleUsageSession.end_odometer_km - VehicleUsageSession.start_odometer_km,
            ),
            else_=0,
        )

        usage_stats = db.execute(
            select(
                func.count(VehicleUsageSession.id),
                func.coalesce(func.sum(km_expr), 0),
            ).where(usage_filter)
        ).one()
        usage_sessions_count = int(usage_stats[0] or 0)
        total_km_travelled = usage_stats[1] or Decimal("0")

        top_vehicle_rows = db.execute(
            select(
                VehicleUsageSession.vehicle_id,
                func.count(VehicleUsageSession.id).label("usage_count"),
                func.coalesce(func.sum(km_expr), 0).label("km_travelled"),
            )
            .where(usage_filter)
            .group_by(VehicleUsageSession.vehicle_id)
            .order_by(func.count(VehicleUsageSession.id).desc(), func.coalesce(func.sum(km_expr), 0).desc())
            .limit(1)
        ).all()
        if top_vehicle_rows:
            vehicle_id, usage_count, km_travelled = top_vehicle_rows[0]
            vehicle = db.get(Vehicle, vehicle_id)
            most_used_vehicle = OperatorVehicleUsageSummary(
                vehicle_id=vehicle_id,
                vehicle_label=_vehicle_label(vehicle, vehicle_id),
                usage_count=int(usage_count or 0),
                km_travelled=km_travelled,
            )

        if recent_sessions:
            last_vehicle = db.get(Vehicle, recent_sessions[0].vehicle_id)
            last_used_vehicle_label = _vehicle_label(last_vehicle, recent_sessions[0].vehicle_id)

    session_vehicle_ids = {item.vehicle_id for item in recent_sessions}
    session_vehicles = {
        vehicle.id: vehicle
        for vehicle in db.scalars(select(Vehicle).where(Vehicle.id.in_(session_vehicle_ids))).all()
    } if session_vehicle_ids else {}

    operator_response = _serialize_operator(operator, current_cards)

    return WCOperatorDetailResponse(
        operator=operator_response,
        stats=WCOperatorDetailStats(
            fuel_cards_count=len(current_cards),
            fuel_logs_count=int(fuel_stats[0] or 0),
            usage_sessions_count=usage_sessions_count,
            total_liters=fuel_stats[1] or Decimal("0"),
            total_fuel_cost=fuel_stats[2] or Decimal("0"),
            total_km_travelled=total_km_travelled,
            most_used_vehicle=most_used_vehicle,
            last_used_vehicle_label=last_used_vehicle_label,
        ),
        current_fuel_cards=[_serialize_fuel_card(card) for card in current_cards],
        recent_fuel_logs=[
            OperatorFuelLogSummary(
                id=item.id,
                vehicle_id=item.vehicle_id,
                vehicle_label=_vehicle_label(fuel_log_vehicles.get(item.vehicle_id), item.vehicle_id),
                fueled_at=item.fueled_at,
                liters=item.liters,
                total_cost=item.total_cost,
                odometer_km=item.odometer_km,
                station_name=item.station_name,
            )
            for item in fuel_logs
        ],
        recent_usage_sessions=[
            OperatorUsageSessionSummary(
                id=item.id,
                vehicle_id=item.vehicle_id,
                vehicle_label=_vehicle_label(session_vehicles.get(item.vehicle_id), item.vehicle_id),
                started_at=item.started_at,
                ended_at=item.ended_at,
                status=item.status,
                km_travelled=_session_km(item),
            )
            for item in recent_sessions
        ],
    )
