"""Excel import service for fleet fuel transactions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from typing import Any
from uuid import UUID

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.fuel_cards import FuelCard, FuelCardAssignmentHistory
from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, WCRefuelEvent
from app.modules.operazioni.models.wc_operator import WCOperator


@dataclass
class FleetTransactionsImportResult:
    imported: int
    skipped: int
    errors: list[str]
    rows_read: int
    matched_white_refuels: int = 0


def _normalize_header(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = " ".join(value.strip().split())
        return normalized or None
    normalized = str(value).strip()
    return normalized or None


def _normalize_lookup_key(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    compact = re.sub(r"[^A-Z0-9]+", "", normalized.upper())
    return compact or None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    try:
        return Decimal(normalized.replace(",", "."))
    except InvalidOperation:
        return None


def _parse_datetime(data_value: Any, time_value: Any) -> datetime | None:
    if isinstance(data_value, datetime):
        return data_value
    if isinstance(data_value, date):
        if isinstance(time_value, datetime):
            return datetime.combine(data_value, time_value.time())
        if isinstance(time_value, time):
            return datetime.combine(data_value, time_value)
        return datetime.combine(data_value, time.min)

    date_text = _normalize_text(data_value)
    if date_text is None:
        return None
    if isinstance(time_value, datetime):
        time_text = time_value.strftime("%H:%M:%S")
    elif isinstance(time_value, time):
        time_text = time_value.strftime("%H:%M:%S")
    else:
        time_text = _normalize_text(time_value)

    for candidate in (
        date_text,
        f"{date_text} {time_text}" if time_text else None,
    ):
        if not candidate:
            continue
        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    return None


def _parse_rows(file_bytes: bytes) -> list[dict[str, Any]]:
    workbook = load_workbook(filename=BytesIO(file_bytes), data_only=True)
    worksheet = workbook.active
    rows = list(worksheet.iter_rows(values_only=True))
    if not rows:
        return []

    header_row_index: int | None = None
    headers: list[str] = []
    for index, row in enumerate(rows):
        candidate_headers = [_normalize_header(value) for value in row]
        if any(candidate_headers):
            header_row_index = index
            headers = candidate_headers
            break

    if header_row_index is None:
        return []

    items: list[dict[str, Any]] = []
    for row in rows[header_row_index + 1 :]:
        if not any(value is not None and str(value).strip() for value in row):
            continue
        items.append({headers[index]: row[index] for index in range(min(len(headers), len(row)))})
    return items


def _build_vehicle_lookup(db: Session) -> dict[str, Vehicle]:
    vehicles = db.scalars(select(Vehicle)).all()
    lookup: dict[str, Vehicle] = {}
    for vehicle in vehicles:
        for candidate in (
            vehicle.plate_number,
            vehicle.wc_vehicle_id,
            vehicle.asset_tag,
            vehicle.code,
        ):
            key = _normalize_lookup_key(candidate)
            if key and key not in lookup:
                lookup[key] = vehicle
    return lookup


def _build_fuel_card_lookup(db: Session) -> dict[str, FuelCard]:
    cards = db.scalars(select(FuelCard)).all()
    lookup: dict[str, FuelCard] = {}
    for card in cards:
        key = _normalize_lookup_key(card.codice)
        if key and key not in lookup:
            lookup[key] = card
    return lookup


def _resolve_fuel_card(row: dict[str, Any], fuel_card_lookup: dict[str, FuelCard]) -> FuelCard | None:
    key = _normalize_lookup_key(row.get("Identificativo"))
    if key is None:
        return None
    return fuel_card_lookup.get(key)


def _resolve_card_operator_id(
    db: Session,
    *,
    fuel_card: FuelCard | None,
    fueled_at: datetime,
) -> UUID | None:
    if fuel_card is None:
        return None

    assignment = db.scalar(
        select(FuelCardAssignmentHistory)
        .where(FuelCardAssignmentHistory.fuel_card_id == fuel_card.id)
        .where(FuelCardAssignmentHistory.start_at <= fueled_at)
        .where(
            (FuelCardAssignmentHistory.end_at.is_(None))
            | (FuelCardAssignmentHistory.end_at > fueled_at)
        )
        .order_by(FuelCardAssignmentHistory.start_at.desc())
    )
    if assignment is not None:
        return assignment.wc_operator_id
    return fuel_card.current_wc_operator_id


def _build_operator_lookup(db: Session) -> dict[UUID, WCOperator]:
    operators = db.scalars(select(WCOperator)).all()
    return {item.id: item for item in operators}


def _normalize_operator_name(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return re.sub(r"[^A-Z0-9]+", "", normalized.upper()) or None


def _resolve_matching_wc_refuel_event(
    db: Session,
    *,
    vehicle: Vehicle,
    fueled_at: datetime,
    card_operator_id: UUID | None,
    operator_lookup: dict[UUID, WCOperator],
) -> WCRefuelEvent | None:
    candidates = db.scalars(
        select(WCRefuelEvent)
        .where(WCRefuelEvent.matched_fuel_log_id.is_(None))
        .where(WCRefuelEvent.vehicle_id == vehicle.id)
    ).all()
    if not candidates:
        return None

    assigned_operator = operator_lookup.get(card_operator_id) if card_operator_id else None
    assigned_keys = set()
    if assigned_operator is not None:
        for candidate in (
            " ".join(part for part in [assigned_operator.last_name, assigned_operator.first_name] if part),
            " ".join(part for part in [assigned_operator.first_name, assigned_operator.last_name] if part),
            assigned_operator.username,
            assigned_operator.email,
        ):
            key = _normalize_operator_name(candidate)
            if key:
                assigned_keys.add(key)

    best: tuple[int, float, int, WCRefuelEvent] | None = None
    for event in candidates:
        delta_seconds = abs((event.fueled_at.replace(tzinfo=None) - fueled_at).total_seconds())
        if delta_seconds > 12 * 3600:
            continue

        score = 0
        if card_operator_id and event.wc_operator_id == card_operator_id:
            score += 100
        elif card_operator_id and event.wc_operator_id is None:
            operator_key = _normalize_operator_name(event.operator_name)
            if operator_key and operator_key in assigned_keys:
                score += 70

        if event.odometer_km is not None:
            score += 10
        if event.source_issue:
            score += 5

        candidate_tuple = (score, -delta_seconds, event.wc_id, event)
        if best is None or candidate_tuple > best:
            best = candidate_tuple

    return best[3] if best is not None else None


def _match_vehicle(row: dict[str, Any], vehicle_lookup: dict[str, Vehicle]) -> Vehicle | None:
    for candidate in (
        row.get("Targa"),
        row.get("Identificativo"),
        row.get("Veicolo"),
    ):
        key = _normalize_lookup_key(candidate)
        if key and key in vehicle_lookup:
            return vehicle_lookup[key]
    return None


def _find_existing_fuel_log(
    db: Session,
    *,
    vehicle_id,
    fueled_at: datetime,
    liters: Decimal,
    total_cost: Decimal | None,
    odometer_km: Decimal | None,
) -> VehicleFuelLog | None:
    existing_logs = db.scalars(
        select(VehicleFuelLog).where(
            VehicleFuelLog.vehicle_id == vehicle_id,
            VehicleFuelLog.fueled_at == fueled_at,
        )
    ).all()
    for item in existing_logs:
        if item.liters != liters:
            continue
        if item.total_cost != total_cost:
            continue
        if item.odometer_km != odometer_km:
            continue
        return item
    return None


def import_fleet_transactions(
    *,
    db: Session,
    current_user: ApplicationUser,
    file_bytes: bytes,
) -> FleetTransactionsImportResult:
    rows = _parse_rows(file_bytes)
    vehicle_lookup = _build_vehicle_lookup(db)
    fuel_card_lookup = _build_fuel_card_lookup(db)
    operator_lookup = _build_operator_lookup(db)
    imported = 0
    skipped = 0
    matched_white_refuels = 0
    errors: list[str] = []

    for index, row in enumerate(rows, start=1):
        fueled_at = _parse_datetime(row.get("Data"), row.get("Ora"))
        liters = _to_decimal(row.get("Volume"))
        total_cost = _to_decimal(row.get("Imp. Scontato")) or _to_decimal(row.get("Imp. intero"))
        odometer_raw = _to_decimal(row.get("Km"))
        odometer_km = Decimal(str(int(odometer_raw))) if odometer_raw is not None else None
        vehicle = _match_vehicle(row, vehicle_lookup)
        fuel_card = _resolve_fuel_card(row, fuel_card_lookup)

        if vehicle is None:
            skipped += 1
            errors.append(
                f"riga:{index}: mezzo non trovato per Targa={_normalize_text(row.get('Targa')) or '-'} "
                f"Identificativo={_normalize_text(row.get('Identificativo')) or '-'}"
            )
            continue
        if fueled_at is None:
            skipped += 1
            errors.append(f"riga:{index}: data/ora transazione non valida")
            continue
        if liters is None or liters <= 0:
            skipped += 1
            errors.append(f"riga:{index}: volume non valido")
            continue

        existing = _find_existing_fuel_log(
            db,
            vehicle_id=vehicle.id,
            fueled_at=fueled_at,
            liters=liters,
            total_cost=total_cost,
            odometer_km=odometer_km,
        )
        if existing is not None:
            skipped += 1
            continue

        assigned_operator_id = _resolve_card_operator_id(
            db,
            fuel_card=fuel_card,
            fueled_at=fueled_at,
        )
        matched_event = _resolve_matching_wc_refuel_event(
            db,
            vehicle=vehicle,
            fueled_at=fueled_at,
            card_operator_id=assigned_operator_id,
            operator_lookup=operator_lookup,
        )

        station_name_parts = [
            _normalize_text(row.get("Impianto")),
            _normalize_text(row.get("Città")),
        ]
        station_name = " - ".join(part for part in station_name_parts if part) or None
        notes = (
            "Import automatico transazioni flotte"
            f" | ticket={_normalize_text(row.get('N. ticket')) or '-'}"
            f" | pan={_normalize_text(row.get('PAN Carta')) or '-'}"
            f" | prodotto={_normalize_text(row.get('Prod.')) or '-'}"
            f" | identificativo={_normalize_text(row.get('Identificativo')) or '-'}"
            f" | indirizzo={_normalize_text(row.get('Indirizzo')) or '-'}"
        )

        fuel_log = VehicleFuelLog(
            vehicle_id=vehicle.id,
            usage_session_id=None,
            recorded_by_user_id=current_user.id,
            fueled_at=fueled_at,
            liters=liters,
            total_cost=total_cost,
            odometer_km=odometer_km,
            wc_id=matched_event.wc_id if matched_event is not None else None,
            operator_name=matched_event.operator_name if matched_event is not None else None,
            wc_synced_at=matched_event.wc_synced_at if matched_event is not None else None,
            station_name=station_name[:150] if station_name else None,
            notes=notes[:1000],
        )
        db.add(fuel_log)
        db.flush()
        if matched_event is not None:
            matched_event.matched_fuel_log_id = fuel_log.id
            matched_event.matched_fuel_card_id = fuel_card.id if fuel_card is not None else None
            matched_event.matched_at = datetime.now(UTC)
            matched_white_refuels += 1
        imported += 1

    db.commit()
    return FleetTransactionsImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors[:100],
        rows_read=len(rows),
        matched_white_refuels=matched_white_refuels,
    )
