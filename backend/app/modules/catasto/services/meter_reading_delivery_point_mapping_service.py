from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import (
    CatDeliveryPoint,
    CatDistretto,
    CatMeterReading,
    CatMeterReadingDeliveryPointMapping,
)
from app.modules.catasto.services.delivery_points_import import normalize_distretto_code, normalize_point_code


def _normalize_mapping_key(*, distretto: CatDistretto | None, punto_consegna: str | None) -> tuple[str, str]:
    distretto_code = normalize_distretto_code(distretto.num_distretto if distretto else None)
    point_code = normalize_point_code(punto_consegna)
    if not distretto_code or not point_code:
        raise ValueError("Distretto o punto consegna non validi per il mapping manuale.")
    return distretto_code, point_code


def _base_distretto_code(value: str | None) -> str | None:
    normalized = normalize_distretto_code(value)
    if not normalized:
        return None
    return normalized.split("_", 1)[0]


def upsert_delivery_point_mapping(
    db: Session,
    *,
    distretto: CatDistretto | None,
    punto_consegna: str | None,
    delivery_point: CatDeliveryPoint,
    current_user: ApplicationUser | None,
    change_note: str | None = None,
) -> CatMeterReadingDeliveryPointMapping:
    distretto_code, point_code = _normalize_mapping_key(distretto=distretto, punto_consegna=punto_consegna)
    if _base_distretto_code(delivery_point.distretto_code) != distretto_code:
        raise ValueError("Il punto GIS selezionato non appartiene al distretto della lettura.")

    mapping = db.execute(
        select(CatMeterReadingDeliveryPointMapping).where(
            CatMeterReadingDeliveryPointMapping.distretto_code == distretto_code,
            CatMeterReadingDeliveryPointMapping.source_point_code == point_code,
        )
    ).scalar_one_or_none()
    if mapping is None:
        mapping = CatMeterReadingDeliveryPointMapping(
            distretto_code=distretto_code,
            source_point_code=point_code,
            delivery_point_id=delivery_point.id,
            created_by=current_user.id if current_user else None,
        )
        db.add(mapping)

    mapping.delivery_point_id = delivery_point.id
    mapping.change_note = change_note.strip() if isinstance(change_note, str) and change_note.strip() else None
    mapping.updated_by = current_user.id if current_user else None
    db.flush()
    return mapping


def apply_delivery_point_mapping_to_readings(
    db: Session,
    *,
    mapping: CatMeterReadingDeliveryPointMapping,
) -> dict[str, int]:
    linked = 0
    untouched = 0
    readings = db.execute(
        select(CatMeterReading)
        .join(CatDistretto, CatDistretto.id == CatMeterReading.distretto_id)
    ).scalars().all()

    for reading in readings:
        if normalize_distretto_code(reading.distretto.num_distretto if reading.distretto else None) != mapping.distretto_code:
            continue
        if normalize_point_code(reading.punto_consegna) != mapping.source_point_code:
            continue
        if reading.delivery_point_id == mapping.delivery_point_id:
            untouched += 1
            continue
        reading.delivery_point_id = mapping.delivery_point_id
        linked += 1

    db.flush()
    return {"linked": linked, "untouched": untouched}


def apply_all_delivery_point_mappings(db: Session) -> dict[str, int]:
    linked = 0
    untouched = 0
    mappings = db.execute(select(CatMeterReadingDeliveryPointMapping)).scalars().all()
    for mapping in mappings:
        stats = apply_delivery_point_mapping_to_readings(db, mapping=mapping)
        linked += stats["linked"]
        untouched += stats["untouched"]
    return {"linked": linked, "untouched": untouched, "mappings": len(mappings)}


def create_mapping_from_reading(
    db: Session,
    *,
    reading: CatMeterReading,
    delivery_point: CatDeliveryPoint,
    current_user: ApplicationUser | None,
    change_note: str | None = None,
) -> tuple[CatMeterReadingDeliveryPointMapping, dict[str, int]]:
    mapping = upsert_delivery_point_mapping(
        db,
        distretto=reading.distretto,
        punto_consegna=reading.punto_consegna,
        delivery_point=delivery_point,
        current_user=current_user,
        change_note=change_note,
    )
    stats = apply_delivery_point_mapping_to_readings(db, mapping=mapping)
    return mapping, stats
