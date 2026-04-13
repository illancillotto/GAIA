from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client import BonificaRefuelRow
from app.modules.elaborazioni.bonifica_oristanese.apps.taken_charge.client import (
    BonificaTakenChargeRow,
)
from app.modules.elaborazioni.bonifica_oristanese.apps.vehicles.client import BonificaVehicleRow
from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.services.parsing import parse_italian_datetime


@dataclass(frozen=True)
class WhiteVehiclesSyncResult:
    vehicles_synced: int
    vehicles_skipped: int
    fuel_logs_synced: int
    fuel_logs_skipped: int
    usage_sessions_synced: int
    usage_sessions_skipped: int
    errors: list[str]


def _build_vehicle_code(wc_id: int) -> str:
    return f"WC-{wc_id}"


def _to_decimal(value: int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _sync_vehicle(db: Session, row: BonificaVehicleRow, current_user: ApplicationUser) -> bool:
    vehicle = db.scalar(select(Vehicle).where(Vehicle.wc_id == row.wc_id))
    created = vehicle is None

    if vehicle is None:
        vehicle = Vehicle(
            code=_build_vehicle_code(row.wc_id),
            wc_id=row.wc_id,
            plate_number=(row.vehicle_code[:20] if row.vehicle_code and len(row.vehicle_code) <= 20 else None),
            wc_vehicle_id=row.vehicle_code,
            name=(row.vehicle_name or f"Mezzo White {row.wc_id}")[:150],
            vehicle_type=row.vehicle_type_label[:100],
            vehicle_type_wc=row.vehicle_type_label[:20],
            current_status="available",
            is_active=True,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
            notes=None,
            wc_synced_at=datetime.now(timezone.utc),
        )
        db.add(vehicle)
        db.flush()
        return True

    vehicle.wc_vehicle_id = row.vehicle_code
    if row.vehicle_code and len(row.vehicle_code) <= 20:
        vehicle.plate_number = row.vehicle_code
    if row.vehicle_name:
        vehicle.name = row.vehicle_name[:150]
    vehicle.vehicle_type = row.vehicle_type_label[:100]
    vehicle.vehicle_type_wc = row.vehicle_type_label[:20]
    vehicle.updated_by_user_id = current_user.id
    vehicle.wc_synced_at = datetime.now(timezone.utc)
    db.flush()
    return created


def sync_white_vehicles(
    *,
    db: Session,
    current_user: ApplicationUser,
    rows: list[BonificaVehicleRow],
) -> WhiteVehiclesSyncResult:
    vehicles_synced = 0
    usage_sessions_synced = 0
    vehicles_skipped = 0
    usage_sessions_skipped = 0
    errors: list[str] = []

    for row in rows:
        try:
            created = _sync_vehicle(db, row, current_user)
            if created:
                vehicles_synced += 1
            else:
                vehicles_skipped += 1
        except Exception as exc:  # pragma: no cover - defensive branch
            errors.append(f"vehicle:{row.wc_id}: {exc}")

    db.commit()
    return WhiteVehiclesSyncResult(
        vehicles_synced=vehicles_synced,
        vehicles_skipped=vehicles_skipped,
        fuel_logs_synced=0,
        fuel_logs_skipped=0,
        usage_sessions_synced=usage_sessions_synced,
        usage_sessions_skipped=usage_sessions_skipped,
        errors=errors,
    )


def sync_white_taken_charge(
    *,
    db: Session,
    current_user: ApplicationUser,
    rows: list[BonificaTakenChargeRow],
) -> WhiteVehiclesSyncResult:
    vehicles_synced = 0
    vehicles_skipped = 0
    usage_sessions_synced = 0
    usage_sessions_skipped = 0
    errors: list[str] = []

    ordered_rows = sorted(
        rows,
        key=lambda row: parse_italian_datetime(row.started_at_text) or datetime.min,
    )

    for row in ordered_rows:
        existing = db.scalar(select(VehicleUsageSession).where(VehicleUsageSession.wc_id == row.wc_id))
        if existing is not None:
            usage_sessions_skipped += 1
            continue

        vehicle = db.scalar(select(Vehicle).where(Vehicle.wc_vehicle_id == row.vehicle_code))
        if vehicle is None:
            vehicle = db.scalar(select(Vehicle).where(Vehicle.plate_number == row.vehicle_code))
        if vehicle is None:
            errors.append(f"taken_charge:{row.wc_id}: vehicle `{row.vehicle_code}` non trovato")
            continue

        started_at = parse_italian_datetime(row.started_at_text)
        if started_at is None:
            errors.append(f"taken_charge:{row.wc_id}: data presa in carico non valida")
            continue

        ended_at = parse_italian_datetime(row.ended_at_text)
        session = VehicleUsageSession(
            vehicle_id=vehicle.id,
            started_by_user_id=current_user.id,
            actual_driver_user_id=None,
            team_id=None,
            related_assignment_id=None,
            started_at=started_at,
            ended_at=ended_at,
            start_odometer_km=_to_decimal(row.km_start),
            end_odometer_km=_to_decimal(row.km_end) if row.km_end is not None else None,
            notes="Sync automatico White Company da presa in carico automezzi",
            status="closed" if ended_at is not None else "open",
            wc_id=row.wc_id,
            km_start=row.km_start,
            km_end=row.km_end,
            operator_name=row.operator_name,
            wc_synced_at=datetime.now(timezone.utc),
        )
        db.add(session)

        vehicle.updated_by_user_id = current_user.id
        vehicle.current_status = "in_use" if ended_at is None else "available"
        vehicle.wc_synced_at = datetime.now(timezone.utc)
        usage_sessions_synced += 1

    db.commit()
    return WhiteVehiclesSyncResult(
        vehicles_synced=vehicles_synced,
        vehicles_skipped=vehicles_skipped,
        fuel_logs_synced=0,
        fuel_logs_skipped=0,
        usage_sessions_synced=usage_sessions_synced,
        usage_sessions_skipped=usage_sessions_skipped,
        errors=errors,
    )


def sync_white_refuels(
    *,
    db: Session,
    current_user: ApplicationUser,
    rows: list[BonificaRefuelRow],
) -> WhiteVehiclesSyncResult:
    vehicles_synced = 0
    vehicles_skipped = 0
    fuel_logs_synced = 0
    fuel_logs_skipped = 0
    usage_sessions_synced = 0
    usage_sessions_skipped = 0
    errors: list[str] = []

    for row in rows:
        existing = db.scalar(select(VehicleFuelLog).where(VehicleFuelLog.wc_id == row.wc_id))
        if existing is not None:
            fuel_logs_skipped += 1
            continue

        vehicle = db.scalar(select(Vehicle).where(Vehicle.wc_vehicle_id == row.vehicle_code))
        if vehicle is None:
            vehicle = db.scalar(select(Vehicle).where(Vehicle.plate_number == row.vehicle_code))
        if vehicle is None:
            errors.append(f"refuel:{row.wc_id}: vehicle `{row.vehicle_code}` non trovato")
            continue

        fueled_at = parse_italian_datetime(row.fueled_at_text)
        if fueled_at is None:
            errors.append(f"refuel:{row.wc_id}: data rifornimento non valida")
            continue
        if row.liters is None or row.liters <= 0:
            fuel_logs_skipped += 1
            continue

        fuel_log = VehicleFuelLog(
            vehicle_id=vehicle.id,
            usage_session_id=None,
            recorded_by_user_id=current_user.id,
            fueled_at=fueled_at,
            liters=row.liters,
            total_cost=row.total_cost,
            odometer_km=Decimal(str(row.odometer_km)) if row.odometer_km is not None else None,
            wc_id=row.wc_id,
            operator_name=row.operator_name,
            wc_synced_at=datetime.now(timezone.utc),
            station_name=row.station_name,
            notes="Sync automatico White Company da registro rifornimenti",
        )
        db.add(fuel_log)
        fuel_logs_synced += 1

    db.commit()
    return WhiteVehiclesSyncResult(
        vehicles_synced=vehicles_synced,
        vehicles_skipped=vehicles_skipped,
        fuel_logs_synced=fuel_logs_synced,
        fuel_logs_skipped=fuel_logs_skipped,
        usage_sessions_synced=usage_sessions_synced,
        usage_sessions_skipped=usage_sessions_skipped,
        errors=errors,
    )
