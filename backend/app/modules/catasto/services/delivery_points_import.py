from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

from shapely.geometry import shape
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatDeliveryPoint, CatDistretto, CatIrrigationCanal, CatMeterReading


SOURCE_DATASET_2026_DEF = "2026_DEF"
POINT_FOLDER_WITH_METER = "Punti_Cons-Con_contatoti"
POINT_FOLDER_WITHOUT_METER = "Punti_Cons-Con_Senza_contatoti"


@dataclass(frozen=True)
class ParsedDeliveryFeature:
    feature_kind: str
    distretto_code: str
    has_meter: bool
    source_file: str
    source_updated_at: datetime
    properties: dict[str, Any]
    geometry_wkt: str
    point_code: str | None = None
    canal_source_key: str | None = None


def normalize_distretto_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    normalized = re.sub(r"\bD(?=\d)", "", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    if normalized.isdigit() and len(normalized) <= 2:
        normalized = normalized.zfill(2)
    return normalized or None


def normalize_point_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized or None


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def normalize_meter_code(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized.upper()


def strip_activity_suffix(point_code: str | None) -> str | None:
    normalized = normalize_point_code(point_code)
    if not normalized:
        return None
    stripped = re.sub(r"_[A-Z]+$", "", normalized)
    return stripped or None


def insert_dot_after_numeric_prefix(point_code: str | None) -> str | None:
    normalized = normalize_point_code(point_code)
    if not normalized:
        return None
    dotted = re.sub(r"^(\d+)([A-Z])(?=[_-])", r"\1.\2", normalized)
    return dotted or None


def map_alpha_suffix_to_numeric(point_code: str | None) -> str | None:
    normalized = normalize_point_code(point_code)
    if not normalized:
        return None
    match = re.search(r"[-_]([A-Z])$", normalized)
    if not match:
        return normalized
    suffix_number = ord(match.group(1)) - ord("A") + 1
    return f"{normalized[:-2]}_{suffix_number}"


def _normalize_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _record_to_properties(field_names: list[str], record: Any) -> dict[str, Any]:
    values = list(record)
    return {
        field_names[index]: values[index]
        for index in range(min(len(field_names), len(values)))
    }


def _distretto_code_from_path(path: Path) -> str:
    stem = path.stem.upper()
    if "_PUNTI_CONSEGNA" in stem:
        prefix = stem.split("_PUNTI_CONSEGNA", 1)[0]
    elif "_CANALETTE" in stem:
        prefix = stem.split("_CANALETTE", 1)[0]
    else:
        prefix = stem
    normalized = normalize_distretto_code(prefix)
    if not normalized:
        raise ValueError(f"Impossibile derivare il distretto dal file {path.name}")
    return normalized


def _source_updated_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _canal_source_key(distretto_code: str, properties: dict[str, Any], geometry_wkt: str) -> str:
    raw = "|".join(
        [
            distretto_code,
            _normalize_text(properties.get("ID_Canale")) or "",
            _normalize_text(properties.get("Tipo_Canal")) or "",
            geometry_wkt,
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def parse_delivery_points_shapefile(path: str | Path) -> list[ParsedDeliveryFeature]:
    import shapefile

    shp_path = Path(path)
    parent_name = shp_path.parent.name
    if parent_name not in {POINT_FOLDER_WITH_METER, POINT_FOLDER_WITHOUT_METER}:
        raise ValueError(f"Cartella sorgente non supportata per {shp_path}")

    has_meter = parent_name == POINT_FOLDER_WITH_METER
    distretto_code = _distretto_code_from_path(shp_path)
    source_updated_at = _source_updated_at(shp_path)

    with shapefile.Reader(str(shp_path)) as reader:
        field_names = [field[0] for field in reader.fields[1:]]
        features: list[ParsedDeliveryFeature] = []
        for shape_record in reader.iterShapeRecords():
            properties = _record_to_properties(field_names, shape_record.record)
            geometry = shape(shape_record.shape.__geo_interface__)
            geometry_wkt = geometry.wkt
            geom_type = geometry.geom_type.upper()
            point_geometry = None
            if geom_type in {"POINT", "POINTZ"}:
                point_geometry = geometry
            elif geom_type == "MULTIPOINT" and len(geometry.geoms) == 1:
                point_geometry = geometry.geoms[0]

            if point_geometry is not None:
                point_code = normalize_point_code(
                    properties.get("PUNTO_CONS") or properties.get("PUNT_CONS") or properties.get("PUNTO_CON")
                )
                if not point_code:
                    continue
                features.append(
                    ParsedDeliveryFeature(
                        feature_kind="point",
                        distretto_code=distretto_code,
                        has_meter=has_meter,
                        source_file=shp_path.name,
                        source_updated_at=source_updated_at,
                        properties=properties,
                        geometry_wkt=point_geometry.wkt,
                        point_code=point_code,
                    )
                )
            elif geom_type == "LINESTRING":
                features.append(
                    ParsedDeliveryFeature(
                        feature_kind="canal",
                        distretto_code=distretto_code,
                        has_meter=False,
                        source_file=shp_path.name,
                        source_updated_at=source_updated_at,
                        properties=properties,
                        geometry_wkt=geometry_wkt,
                        canal_source_key=_canal_source_key(distretto_code, properties, geometry_wkt),
                    )
                )
        return features


def _apply_geometry_update(
    db: Session,
    *,
    table_name: str,
    row_id: UUID,
    geometry_column: str,
    geometry_wkt: str,
    source_srid: int = 3003,
) -> None:
    row_id_value = str(row_id)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text(
                f"""
                UPDATE {table_name}
                SET {geometry_column} = ST_Transform(
                    ST_SetSRID(ST_GeomFromText(:geometry_wkt), :source_srid),
                    4326
                )
                WHERE id = :row_id
                """
            ),
            {"geometry_wkt": geometry_wkt, "source_srid": source_srid, "row_id": row_id_value},
        )
        return
    row_id_value = row_id.hex
    db.execute(
        text(f"UPDATE {table_name} SET {geometry_column} = :geometry_wkt WHERE id = :row_id"),
        {"geometry_wkt": geometry_wkt, "row_id": row_id_value},
    )


def _upsert_delivery_point(db: Session, feature: ParsedDeliveryFeature) -> CatDeliveryPoint:
    assert feature.point_code is not None
    point = db.execute(
        select(CatDeliveryPoint).where(
            CatDeliveryPoint.distretto_code == feature.distretto_code,
            CatDeliveryPoint.punto_consegna_code == feature.point_code,
        )
    ).scalar_one_or_none()
    if point is None:
        point = CatDeliveryPoint(
            distretto_code=feature.distretto_code,
            punto_consegna_code=feature.point_code,
            source_dataset=SOURCE_DATASET_2026_DEF,
        )
        db.add(point)
        db.flush()

    point.tipologia = _normalize_text(feature.properties.get("TIPOLOGIA"))
    point.tipo = _normalize_text(feature.properties.get("TIPO"))
    point.cod_cont = _normalize_text(feature.properties.get("COD_CONT"))
    point.photo_ref = _normalize_text(feature.properties.get("FOTO"))
    point.has_meter = feature.has_meter
    point.source_file = feature.source_file
    point.source_updated_at = feature.source_updated_at
    point.source_x = _normalize_decimal(feature.properties.get("X"))
    point.source_y = _normalize_decimal(feature.properties.get("Y"))
    point.source_payload_json = {key: value for key, value in feature.properties.items() if value not in (None, "")}
    point.is_active = True
    db.flush()
    _apply_geometry_update(
        db,
        table_name="cat_delivery_points",
        row_id=point.id,
        geometry_column="geometry",
        geometry_wkt=feature.geometry_wkt,
    )
    return point


def _upsert_irrigation_canal(db: Session, feature: ParsedDeliveryFeature) -> CatIrrigationCanal:
    assert feature.canal_source_key is not None
    canal = db.execute(
        select(CatIrrigationCanal).where(CatIrrigationCanal.source_key == feature.canal_source_key)
    ).scalar_one_or_none()
    if canal is None:
        canal = CatIrrigationCanal(
            source_key=feature.canal_source_key,
            distretto_code=feature.distretto_code,
            source_dataset=SOURCE_DATASET_2026_DEF,
        )
        db.add(canal)
        db.flush()

    canal.label = _normalize_text(feature.properties.get("ID_Canale"))
    canal.tipo_canale = _normalize_text(feature.properties.get("Tipo_Canal"))
    canal.source_file = feature.source_file
    canal.source_updated_at = feature.source_updated_at
    canal.source_payload_json = {key: value for key, value in feature.properties.items() if value not in (None, "")}
    canal.is_active = True
    db.flush()
    _apply_geometry_update(
        db,
        table_name="cat_irrigation_canals",
        row_id=canal.id,
        geometry_column="geometry",
        geometry_wkt=feature.geometry_wkt,
    )
    return canal


def link_meter_readings_to_delivery_points(db: Session) -> dict[str, int]:
    distretti = db.execute(select(CatDistretto)).scalars().all()
    distretto_by_id = {item.id: normalize_distretto_code(item.num_distretto) for item in distretti}
    points = db.execute(
        select(CatDeliveryPoint).where(
            CatDeliveryPoint.source_dataset == SOURCE_DATASET_2026_DEF,
            CatDeliveryPoint.is_active.is_(True),
        )
    ).scalars().all()
    point_index = {
        (point.distretto_code, point.punto_consegna_code): point.id
        for point in points
    }

    linked = 0
    unlinked = 0
    readings = db.execute(select(CatMeterReading)).scalars().all()
    for reading in readings:
        distretto_code = distretto_by_id.get(reading.distretto_id)
        point_code = normalize_point_code(reading.punto_consegna)
        if not distretto_code or not point_code:
            if reading.delivery_point_id is None:
                unlinked += 1
            continue
        match = point_index.get((distretto_code, point_code))
        if match is None:
            match = resolve_delivery_point_id(
                db,
                distretto=reading.distretto,
                punto_consegna=reading.punto_consegna,
                matricola=reading.matricola,
            )
        if match is None:
            if reading.delivery_point_id is not None:
                reading.delivery_point_id = None
            unlinked += 1
            continue
        if reading.delivery_point_id != match:
            reading.delivery_point_id = match
            linked += 1

    db.flush()
    return {"linked": linked, "unlinked": unlinked}


def import_delivery_points_2026_def(
    db: Session,
    *,
    root_path: str | Path,
    source_dataset: str = SOURCE_DATASET_2026_DEF,
) -> dict[str, int]:
    root = Path(root_path)
    if not root.exists():
        raise ValueError(f"Cartella non trovata: {root}")

    with_meter_dir = root / POINT_FOLDER_WITH_METER
    without_meter_dir = root / POINT_FOLDER_WITHOUT_METER
    if not with_meter_dir.is_dir() or not without_meter_dir.is_dir():
        raise ValueError(
            f"La cartella {root} deve contenere {POINT_FOLDER_WITH_METER} e {POINT_FOLDER_WITHOUT_METER}"
        )

    db.execute(
        text(
            """
            UPDATE cat_delivery_points
            SET is_active = false
            WHERE source_dataset = :source_dataset
            """
        ),
        {"source_dataset": source_dataset},
    )
    db.execute(
        text(
            """
            UPDATE cat_irrigation_canals
            SET is_active = false
            WHERE source_dataset = :source_dataset
            """
        ),
        {"source_dataset": source_dataset},
    )

    point_total = 0
    canal_total = 0
    shapefiles = sorted(root.rglob("*.shp"))
    for shp_path in shapefiles:
        features = parse_delivery_points_shapefile(shp_path)
        for feature in features:
            if feature.feature_kind == "point":
                _upsert_delivery_point(db, feature)
                point_total += 1
            elif feature.feature_kind == "canal":
                _upsert_irrigation_canal(db, feature)
                canal_total += 1

    link_stats = link_meter_readings_to_delivery_points(db)
    db.commit()
    return {
        "points_processed": point_total,
        "canals_processed": canal_total,
        "meter_readings_linked": link_stats["linked"],
        "meter_readings_unlinked": link_stats["unlinked"],
    }


def resolve_delivery_point_id(
    db: Session,
    *,
    distretto: CatDistretto | None,
    punto_consegna: str | None,
    matricola: Any | None = None,
    cache: dict[tuple[str, str, str | None], UUID | None] | None = None,
) -> UUID | None:
    distretto_code = normalize_distretto_code(distretto.num_distretto if distretto else None)
    point_code = normalize_point_code(punto_consegna)
    meter_code = normalize_meter_code(matricola)
    if not distretto_code or not point_code:
        return None
    key = (distretto_code, point_code, meter_code)
    if cache is not None and key in cache:
        return cache[key]

    def _resolve_candidates(target_point_code: str) -> UUID | None:
        point_id = db.execute(
            select(CatDeliveryPoint.id).where(
                CatDeliveryPoint.distretto_code == distretto_code,
                CatDeliveryPoint.punto_consegna_code == target_point_code,
                CatDeliveryPoint.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if point_id is not None:
            return point_id

        candidates = db.execute(
            select(CatDeliveryPoint).where(
                CatDeliveryPoint.distretto_code.like(f"{distretto_code}\\_%", escape="\\"),
                CatDeliveryPoint.punto_consegna_code == target_point_code,
                CatDeliveryPoint.is_active.is_(True),
            )
        ).scalars().all()
        if len(candidates) == 1:
            return candidates[0].id
        if len(candidates) > 1 and meter_code:
            matched = [candidate for candidate in candidates if normalize_meter_code(candidate.cod_cont) == meter_code]
            if len(matched) == 1:
                return matched[0].id
        return None

    candidate_codes = [point_code]
    stripped_point_code = strip_activity_suffix(point_code)
    if stripped_point_code and stripped_point_code not in candidate_codes:
        candidate_codes.append(stripped_point_code)
    dotted_point_code = insert_dot_after_numeric_prefix(point_code)
    if dotted_point_code and dotted_point_code not in candidate_codes:
        candidate_codes.append(dotted_point_code)
    if stripped_point_code:
        dotted_stripped_point_code = insert_dot_after_numeric_prefix(stripped_point_code)
        if dotted_stripped_point_code and dotted_stripped_point_code not in candidate_codes:
            candidate_codes.append(dotted_stripped_point_code)
    alpha_numeric_point_code = map_alpha_suffix_to_numeric(point_code)
    if alpha_numeric_point_code and alpha_numeric_point_code not in candidate_codes:
        candidate_codes.append(alpha_numeric_point_code)
    if stripped_point_code:
        alpha_numeric_stripped_point_code = map_alpha_suffix_to_numeric(stripped_point_code)
        if alpha_numeric_stripped_point_code and alpha_numeric_stripped_point_code not in candidate_codes:
            candidate_codes.append(alpha_numeric_stripped_point_code)

    point_id = None
    for candidate_code in candidate_codes:
        point_id = _resolve_candidates(candidate_code)
        if point_id is not None:
            break
    if cache is not None:
        cache[key] = point_id
    return point_id
