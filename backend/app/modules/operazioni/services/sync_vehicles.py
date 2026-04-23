from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client import BonificaRefuelRow
from app.modules.elaborazioni.bonifica_oristanese.apps.taken_charge.client import (
    BonificaTakenChargeRow,
)
from app.modules.elaborazioni.bonifica_oristanese.apps.vehicles.client import BonificaVehicleRow
from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession, WCRefuelEvent
from app.modules.operazioni.models.wc_operator import WCOperator
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


def _normalized_vehicle_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_operator_key(value: str | None) -> str | None:
    if value is None:
        return None
    compact = re.sub(r"[^A-Z0-9]+", "", value.upper())
    return compact or None


def _sanitize_wc_refuel_odometer_km(odometer_km: int | None) -> tuple[Decimal | None, str | None]:
    if odometer_km is None:
        return None, None

    # DB column is Numeric(12, 3) => max integer part is < 1e9.
    # WhiteCompany data may contain operator mistakes / placeholder max-int values.
    if odometer_km >= 1_000_000_000:
        return Decimal("0"), f"ANOMALIA_KM: lettura KM non valida inserita dall'utente (valore={odometer_km})."

    if odometer_km < 0:
        return Decimal("0"), f"ANOMALIA_KM: lettura KM negativa inserita dall'utente (valore={odometer_km})."

    return Decimal(str(odometer_km)), None


def _build_operator_lookup(db: Session) -> dict[str, WCOperator]:
    operators = db.scalars(select(WCOperator)).all()
    lookup: dict[str, WCOperator] = {}
    for operator in operators:
        for candidate in (
            " ".join(part for part in [operator.last_name, operator.first_name] if part),
            " ".join(part for part in [operator.first_name, operator.last_name] if part),
            operator.username,
            operator.email,
        ):
            key = _normalize_operator_key(candidate)
            if key and key not in lookup:
                lookup[key] = operator
    return lookup


def _resolve_operator_id(operator_name: str | None, operator_lookup: dict[str, WCOperator]) -> uuid.UUID | None:
    key = _normalize_operator_key(operator_name)
    if key is None:
        return None
    operator = operator_lookup.get(key)
    return operator.id if operator is not None else None


def _upsert_wc_refuel_event(
    db: Session,
    *,
    row: BonificaRefuelRow,
    vehicle_id,
    fueled_at: datetime,
    source_issue: str | None,
    wc_operator_id,
) -> tuple[WCRefuelEvent, bool]:
    event = db.scalar(select(WCRefuelEvent).where(WCRefuelEvent.wc_id == row.wc_id))
    created = event is None
    if event is None:
        event = WCRefuelEvent(wc_id=row.wc_id, fueled_at=fueled_at)
        db.add(event)

    sanitized_odometer_km, odometer_anomaly = _sanitize_wc_refuel_odometer_km(row.odometer_km)
    merged_source_issue = source_issue
    if odometer_anomaly:
        merged_source_issue = (f"{merged_source_issue} | {odometer_anomaly}" if merged_source_issue else odometer_anomaly)

    event.vehicle_id = vehicle_id
    event.wc_operator_id = wc_operator_id
    event.vehicle_code = row.vehicle_code
    event.operator_name = row.operator_name
    event.fueled_at = fueled_at
    event.odometer_km = sanitized_odometer_km
    event.source_issue = merged_source_issue
    event.wc_synced_at = datetime.now(timezone.utc)
    db.flush()
    return event, created


def _find_existing_vehicle(db: Session, row: BonificaVehicleRow) -> Vehicle | None:
    vehicle = db.scalar(select(Vehicle).where(Vehicle.wc_id == row.wc_id))
    if vehicle is not None:
        return vehicle

    vehicle_code = _normalized_vehicle_code(row.vehicle_code)
    if vehicle_code is None:
        return None

    vehicle = db.scalar(select(Vehicle).where(Vehicle.wc_vehicle_id == vehicle_code))
    if vehicle is not None:
        return vehicle

    return db.scalar(select(Vehicle).where(Vehicle.plate_number == vehicle_code))


def _sync_vehicle(db: Session, row: BonificaVehicleRow, current_user: ApplicationUser) -> bool:
    vehicle = _find_existing_vehicle(db, row)
    created = vehicle is None
    vehicle_code = _normalized_vehicle_code(row.vehicle_code)

    if vehicle is None:
        vehicle = Vehicle(
            code=_build_vehicle_code(row.wc_id),
            wc_id=row.wc_id,
            plate_number=(vehicle_code[:20] if vehicle_code and len(vehicle_code) <= 20 else None),
            wc_vehicle_id=vehicle_code,
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

    vehicle.wc_id = row.wc_id
    vehicle.wc_vehicle_id = vehicle_code
    if vehicle_code and len(vehicle_code) <= 20:
        vehicle.plate_number = vehicle_code
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
            with db.begin_nested():
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
            # If the session was open and WC now has return data, close it
            ended_at_update = parse_italian_datetime(row.ended_at_text)
            if existing.status == "open" and ended_at_update is not None and row.km_end is not None:
                existing.ended_at = ended_at_update
                existing.end_odometer_km = _to_decimal(row.km_end)
                existing.km_end = row.km_end
                existing.status = "closed"
                usage_sessions_synced += 1
            else:
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
    operator_lookup = _build_operator_lookup(db)

    for row in rows:
        existing = db.scalar(select(VehicleFuelLog).where(VehicleFuelLog.wc_id == row.wc_id))
        if existing is not None:
            event = db.scalar(select(WCRefuelEvent).where(WCRefuelEvent.wc_id == row.wc_id))
            if event is not None and event.matched_fuel_log_id != existing.id:
                event.matched_fuel_log_id = existing.id
                event.matched_at = datetime.now(timezone.utc)
                event.wc_synced_at = event.wc_synced_at or datetime.now(timezone.utc)
                db.flush()
            fuel_logs_skipped += 1
            continue

        vehicle = db.scalar(select(Vehicle).where(Vehicle.wc_vehicle_id == row.vehicle_code))
        if vehicle is None:
            vehicle = db.scalar(select(Vehicle).where(Vehicle.plate_number == row.vehicle_code))

        fueled_at = parse_italian_datetime(row.fueled_at_text)
        if fueled_at is None:
            errors.append(f"refuel:{row.wc_id}: data rifornimento non valida")
            continue
        wc_operator_id = _resolve_operator_id(row.operator_name, operator_lookup)
        sanitized_odometer_km, odometer_anomaly = _sanitize_wc_refuel_odometer_km(row.odometer_km)
        row_source_issue = row.source_issue
        if odometer_anomaly:
            row_source_issue = (f"{row_source_issue} | {odometer_anomaly}" if row_source_issue else odometer_anomaly)

        if row_source_issue or row.liters is None or row.liters <= 0:
            source_issue = row_source_issue
            if source_issue is None and (row.liters is None or row.liters <= 0):
                source_issue = "Dettaglio White senza litri/costo/distributore: evento salvato per riconciliazione con carte carburante."
            _upsert_wc_refuel_event(
                db,
                row=row,
                vehicle_id=vehicle.id if vehicle is not None else None,
                fueled_at=fueled_at,
                source_issue=source_issue,
                wc_operator_id=wc_operator_id,
            )
            fuel_logs_synced += 1
            continue

        if vehicle is None:
            errors.append(f"refuel:{row.wc_id}: vehicle `{row.vehicle_code}` non trovato")
            continue

        fuel_log = VehicleFuelLog(
            vehicle_id=vehicle.id,
            usage_session_id=None,
            recorded_by_user_id=current_user.id,
            fueled_at=fueled_at,
            liters=row.liters,
            total_cost=row.total_cost,
            odometer_km=sanitized_odometer_km,
            wc_id=row.wc_id,
            operator_name=row.operator_name,
            wc_synced_at=datetime.now(timezone.utc),
            station_name=row.station_name,
            notes="Sync automatico White Company da registro rifornimenti",
        )
        db.add(fuel_log)
        db.flush()
        event, _ = _upsert_wc_refuel_event(
            db,
            row=row,
            vehicle_id=vehicle.id,
            fueled_at=fueled_at,
            source_issue=None,
            wc_operator_id=wc_operator_id,
        )
        event.matched_fuel_log_id = fuel_log.id
        event.matched_at = datetime.now(timezone.utc)
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
