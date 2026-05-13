from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
from math import ceil, cos, radians, sqrt
from typing import Any
from uuid import UUID
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatAdeSyncRun


ADE_WFS_URL = "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php"
ADE_WFS_CRS = "EPSG:6706"
ADE_WFS_TYPENAME = "CP:CadastralParcel"
MAX_TILE_KM2 = 4.0
DEFAULT_COUNT = 1000
DEFAULT_MAX_PAGES = 20
ADE_APPLY_CATEGORIES = {"nuove_in_ade", "geometrie_variate", "mancanti_in_ade"}

NS = {
    "wfs": "http://www.opengis.net/wfs/2.0",
    "gml": "http://www.opengis.net/gml/3.2",
    "CP": "http://mapserver.gis.umn.edu/mapserver",
}


@dataclass(frozen=True)
class AdeWfsBbox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def validate(self) -> None:
        if self.min_lon >= self.max_lon or self.min_lat >= self.max_lat:
            raise ValueError("BBox non valida: min deve essere minore di max.")
        if not (-180 <= self.min_lon <= 180 and -180 <= self.max_lon <= 180):
            raise ValueError("Longitudine bbox fuori range.")
        if not (-90 <= self.min_lat <= 90 and -90 <= self.max_lat <= 90):
            raise ValueError("Latitudine bbox fuori range.")

    @property
    def wfs_bbox(self) -> str:
        # EPSG:6706 is exposed by AdE with latitude/longitude axis order.
        return (
            f"{self.min_lat:.8f},{self.min_lon:.8f},{self.max_lat:.8f},{self.max_lon:.8f},"
            "urn:ogc:def:crs:EPSG::6706"
        )


@dataclass(frozen=True)
class AdeCadastralReference:
    codice_catastale: str | None
    sezione_catastale: str | None
    foglio: str | None
    foglio_raw: str | None
    allegato: str | None
    sviluppo: str | None
    particella: str | None
    particella_raw: str | None


@dataclass(frozen=True)
class AdeParcelFeature:
    national_cadastral_reference: str
    inspire_id_local_id: str | None
    inspire_id_namespace: str | None
    administrative_unit: str | None
    label: str | None
    cadastral_reference: AdeCadastralReference
    geometry_wkt_6706: str | None
    raw_payload: dict[str, Any]


def normalize_catasto_number(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return str(int(stripped))
    except ValueError:
        return stripped


def parse_national_cadastral_reference(reference: str | None) -> AdeCadastralReference:
    if not reference:
        return AdeCadastralReference(None, None, None, None, None, None, None, None)

    head, _, parcel = reference.strip().partition(".")
    codice_catastale = head[:4].upper() if len(head) >= 4 else None
    sezione = head[4:5] if len(head) >= 5 else None
    foglio_raw = head[5:9] if len(head) >= 9 else None
    allegato = head[9:10] if len(head) >= 10 else None
    sviluppo = head[10:11] if len(head) >= 11 else None

    def clean_optional(value: str | None) -> str | None:
        if value in {None, "", "_", "0"}:
            return None
        return value

    return AdeCadastralReference(
        codice_catastale=codice_catastale,
        sezione_catastale=clean_optional(sezione),
        foglio=normalize_catasto_number(foglio_raw),
        foglio_raw=foglio_raw or None,
        allegato=clean_optional(allegato),
        sviluppo=clean_optional(sviluppo),
        particella=normalize_catasto_number(parcel),
        particella_raw=parcel or None,
    )


def estimate_bbox_area_km2(bbox: AdeWfsBbox) -> float:
    lat_mid = (bbox.min_lat + bbox.max_lat) / 2.0
    km_lat = 111.32
    km_lon = 111.32 * cos(radians(lat_mid))
    return abs((bbox.max_lat - bbox.min_lat) * km_lat * (bbox.max_lon - bbox.min_lon) * km_lon)


def split_bbox(bbox: AdeWfsBbox, max_tile_km2: float = MAX_TILE_KM2) -> list[AdeWfsBbox]:
    bbox.validate()
    area = estimate_bbox_area_km2(bbox)
    if area <= max_tile_km2:
        return [bbox]

    side_count = ceil(sqrt(area / max_tile_km2))
    lon_step = (bbox.max_lon - bbox.min_lon) / side_count
    lat_step = (bbox.max_lat - bbox.min_lat) / side_count
    tiles: list[AdeWfsBbox] = []
    for lat_idx in range(side_count):
        for lon_idx in range(side_count):
            tiles.append(
                AdeWfsBbox(
                    min_lon=bbox.min_lon + lon_idx * lon_step,
                    min_lat=bbox.min_lat + lat_idx * lat_step,
                    max_lon=bbox.max_lon if lon_idx == side_count - 1 else bbox.min_lon + (lon_idx + 1) * lon_step,
                    max_lat=bbox.max_lat if lat_idx == side_count - 1 else bbox.min_lat + (lat_idx + 1) * lat_step,
                )
            )
    return tiles


def _node_text(parent: ET.Element, path: str) -> str | None:
    node = parent.find(path, NS)
    if node is None or node.text is None:
        return None
    stripped = node.text.strip()
    return stripped or None


def _coords_from_poslist(pos_list: str) -> list[tuple[Decimal, Decimal]]:
    values = [Decimal(item) for item in pos_list.split()]
    if len(values) % 2 != 0:
        raise ValueError("posList GML con numero dispari di coordinate.")
    coords: list[tuple[Decimal, Decimal]] = []
    for idx in range(0, len(values), 2):
        lat = values[idx]
        lon = values[idx + 1]
        coords.append((lon, lat))
    return coords


def _ring_wkt(coords: list[tuple[Decimal, Decimal]]) -> str:
    return ", ".join(f"{lon} {lat}" for lon, lat in coords)


def _geometry_to_wkt_6706(feature_node: ET.Element) -> str | None:
    polygons: list[list[list[tuple[Decimal, Decimal]]]] = []
    for polygon in feature_node.findall(".//gml:Polygon", NS):
        rings: list[list[tuple[Decimal, Decimal]]] = []
        exterior = polygon.find(".//gml:exterior//gml:posList", NS)
        if exterior is None or exterior.text is None:
            continue
        rings.append(_coords_from_poslist(exterior.text))
        for interior in polygon.findall(".//gml:interior//gml:posList", NS):
            if interior.text:
                rings.append(_coords_from_poslist(interior.text))
        polygons.append(rings)

    if not polygons:
        return None
    if len(polygons) == 1:
        return "POLYGON(" + ", ".join(f"({_ring_wkt(ring)})" for ring in polygons[0]) + ")"
    polygon_parts = []
    for rings in polygons:
        polygon_parts.append("(" + ", ".join(f"({_ring_wkt(ring)})" for ring in rings) + ")")
    return "MULTIPOLYGON(" + ", ".join(polygon_parts) + ")"


def parse_wfs_feature_collection(xml_bytes: bytes) -> list[AdeParcelFeature]:
    root = ET.fromstring(xml_bytes)
    features: list[AdeParcelFeature] = []

    for parcel in root.findall(".//CP:CadastralParcel", NS):
        national_ref = _node_text(parcel, "CP:NATIONALCADASTRALREFERENCE")
        if not national_ref:
            continue
        inspire_id = _node_text(parcel, "CP:INSPIREID_LOCALID")
        namespace = _node_text(parcel, "CP:INSPIREID_NAMESPACE")
        administrative_unit = _node_text(parcel, "CP:ADMINISTRATIVEUNIT")
        label = _node_text(parcel, "CP:LABEL")
        cadastral_ref = parse_national_cadastral_reference(national_ref)
        features.append(
            AdeParcelFeature(
                national_cadastral_reference=national_ref,
                inspire_id_local_id=inspire_id,
                inspire_id_namespace=namespace,
                administrative_unit=administrative_unit,
                label=label,
                cadastral_reference=cadastral_ref,
                geometry_wkt_6706=_geometry_to_wkt_6706(parcel),
                raw_payload={
                    "inspire_id_local_id": inspire_id,
                    "inspire_id_namespace": namespace,
                    "national_cadastral_reference": national_ref,
                    "administrative_unit": administrative_unit,
                    "label": label,
                },
            )
        )

    return features


class AdeWfsClient:
    def __init__(self, base_url: str = ADE_WFS_URL, timeout: float = 60.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def _fetch_page(self, bbox: AdeWfsBbox, *, count: int, start_index: int) -> list[AdeParcelFeature]:
        params = self._build_params(bbox, count=count, start_index=start_index)
        headers = {"User-Agent": "GAIA-GIS/1.0"}
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            return parse_wfs_feature_collection(response.content)

    def _build_params(self, bbox: AdeWfsBbox, *, count: int, start_index: int = 0) -> dict[str, str]:
        params = {
            "service": "WFS",
            "request": "GetFeature",
            "version": "2.0.0",
            "typeNames": ADE_WFS_TYPENAME,
            "count": str(count),
            "bbox": bbox.wfs_bbox,
        }
        if start_index > 0:
            params["startIndex"] = str(start_index)
        return params

    def fetch_parcels_bbox(
        self,
        bbox: AdeWfsBbox,
        *,
        count: int = DEFAULT_COUNT,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> list[AdeParcelFeature]:
        features: list[AdeParcelFeature] = []
        for page_idx in range(max_pages):
            page = self._fetch_page(bbox, count=count, start_index=page_idx * count)
            features.extend(page)
            if len(page) < count:
                break
        return features


def _bbox_payload(bbox: AdeWfsBbox) -> dict[str, float]:
    return {
        "min_lon": bbox.min_lon,
        "min_lat": bbox.min_lat,
        "max_lon": bbox.max_lon,
        "max_lat": bbox.max_lat,
    }


def upsert_ade_parcels(db: Session, features: list[AdeParcelFeature], *, run_id: str | None = None) -> dict[str, int]:
    if not features:
        return {"upserted": 0, "with_geometry": 0}

    fetched_at = datetime.now(timezone.utc)
    upserted = 0
    with_geometry = 0
    for feature in features:
        ref = feature.cadastral_reference
        if feature.geometry_wkt_6706:
            with_geometry += 1
        db.execute(
            text(
                """
                INSERT INTO cat_ade_particelle (
                    id,
                    source_run_id,
                    inspire_id_local_id,
                    inspire_id_namespace,
                    national_cadastral_reference,
                    administrative_unit,
                    codice_catastale,
                    sezione_catastale,
                    foglio,
                    foglio_raw,
                    allegato,
                    sviluppo,
                    particella,
                    particella_raw,
                    label,
                    geometry,
                    source_crs,
                    raw_payload_json,
                    fetched_at,
                    updated_at
                )
                VALUES (
                    gen_random_uuid(),
                    CAST(:source_run_id AS uuid),
                    :inspire_id_local_id,
                    :inspire_id_namespace,
                    :national_cadastral_reference,
                    :administrative_unit,
                    :codice_catastale,
                    :sezione_catastale,
                    :foglio,
                    :foglio_raw,
                    :allegato,
                    :sviluppo,
                    :particella,
                    :particella_raw,
                    :label,
                    CASE
                        WHEN CAST(:geometry_wkt_6706 AS text) IS NULL THEN NULL
                        ELSE ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromText(CAST(:geometry_wkt_6706 AS text)), 6706), 4326))
                    END,
                    :source_crs,
                    CAST(:raw_payload_json AS json),
                    :fetched_at,
                    :fetched_at
                )
                ON CONFLICT (national_cadastral_reference) DO UPDATE SET
                    source_run_id = EXCLUDED.source_run_id,
                    inspire_id_local_id = EXCLUDED.inspire_id_local_id,
                    inspire_id_namespace = EXCLUDED.inspire_id_namespace,
                    administrative_unit = EXCLUDED.administrative_unit,
                    codice_catastale = EXCLUDED.codice_catastale,
                    sezione_catastale = EXCLUDED.sezione_catastale,
                    foglio = EXCLUDED.foglio,
                    foglio_raw = EXCLUDED.foglio_raw,
                    allegato = EXCLUDED.allegato,
                    sviluppo = EXCLUDED.sviluppo,
                    particella = EXCLUDED.particella,
                    particella_raw = EXCLUDED.particella_raw,
                    label = EXCLUDED.label,
                    geometry = EXCLUDED.geometry,
                    source_crs = EXCLUDED.source_crs,
                    raw_payload_json = EXCLUDED.raw_payload_json,
                    fetched_at = EXCLUDED.fetched_at,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "source_run_id": run_id,
                "inspire_id_local_id": feature.inspire_id_local_id,
                "inspire_id_namespace": feature.inspire_id_namespace,
                "national_cadastral_reference": feature.national_cadastral_reference,
                "administrative_unit": feature.administrative_unit,
                "codice_catastale": ref.codice_catastale,
                "sezione_catastale": ref.sezione_catastale,
                "foglio": ref.foglio,
                "foglio_raw": ref.foglio_raw,
                "allegato": ref.allegato,
                "sviluppo": ref.sviluppo,
                "particella": ref.particella,
                "particella_raw": ref.particella_raw,
                "label": feature.label,
                "geometry_wkt_6706": feature.geometry_wkt_6706,
                "source_crs": ADE_WFS_CRS,
                "raw_payload_json": json.dumps(feature.raw_payload),
                "fetched_at": fetched_at,
            },
        )
        upserted += 1
    return {"upserted": upserted, "with_geometry": with_geometry}


def sync_ade_parcels_bbox(
    db: Session,
    bbox: AdeWfsBbox,
    *,
    client: AdeWfsClient | None = None,
    max_tile_km2: float = MAX_TILE_KM2,
    count: int = DEFAULT_COUNT,
    max_tiles: int = 25,
    max_pages_per_tile: int = DEFAULT_MAX_PAGES,
    created_by: int | None = None,
) -> dict[str, Any]:
    tiles = split_bbox(bbox, max_tile_km2=max_tile_km2)
    if len(tiles) > max_tiles:
        raise ValueError(f"Area troppo ampia: {len(tiles)} tile stimati, limite {max_tiles}.")

    run = CatAdeSyncRun(
        status="processing",
        request_bbox_json=_bbox_payload(bbox),
        max_tile_km2=Decimal(str(max_tile_km2)),
        max_tiles=max_tiles,
        count_per_page=count,
        max_pages_per_tile=max_pages_per_tile,
        tiles=len(tiles),
        created_by=created_by,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    ade_client = client or AdeWfsClient()
    try:
        deduped: dict[str, AdeParcelFeature] = {}
        for tile in tiles:
            for feature in ade_client.fetch_parcels_bbox(tile, count=count, max_pages=max_pages_per_tile):
                deduped[feature.national_cadastral_reference] = feature

        features = list(deduped.values())
        persisted = upsert_ade_parcels(db, features, run_id=str(run.id))
        run.status = "completed"
        run.features = len(features)
        run.upserted = persisted["upserted"]
        run.with_geometry = persisted["with_geometry"]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "run_id": str(run.id),
            "requested_bbox": _bbox_payload(bbox),
            "tiles": len(tiles),
            "features": len(features),
            **persisted,
        }
    except Exception as exc:
        db.rollback()
        run = db.get(CatAdeSyncRun, run.id)
        if run is not None:
            run.status = "failed"
            run.error = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        raise


def get_ade_alignment_report(db: Session, run_id: str, *, geometry_threshold_m: float = 1.0) -> dict[str, Any]:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        raise ValueError("Report allineamento AdE disponibile solo su PostgreSQL/PostGIS.")

    try:
        run_uuid = UUID(str(run_id))
    except ValueError as exc:
        raise ValueError("Run AdE non valido.") from exc

    run = db.get(CatAdeSyncRun, run_uuid)
    if run is None:
        raise ValueError("Run AdE non trovato.")
    if run.status != "completed":
        raise ValueError("Report disponibile solo per run AdE completati.")

    bbox = run.request_bbox_json
    params = {
        "run_id": run_id,
        "threshold_m": geometry_threshold_m,
        "min_lon": bbox["min_lon"],
        "min_lat": bbox["min_lat"],
        "max_lon": bbox["max_lon"],
        "max_lat": bbox["max_lat"],
    }
    counters = db.execute(
        text(
            """
            WITH scope AS (
                SELECT ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326) AS geom
            ),
            ade AS (
                SELECT *
                FROM cat_ade_particelle
                WHERE source_run_id = :run_id
            ),
            ade_matches AS (
                SELECT
                    a.id AS ade_id,
                    COUNT(p.id) AS match_count,
                    MAX(p.id::text)::uuid AS particella_id
                FROM ade a
                LEFT JOIN cat_particelle p
                  ON p.is_current IS TRUE
                 AND p.codice_catastale = a.codice_catastale
                 AND COALESCE(p.sezione_catastale, '') = COALESCE(a.sezione_catastale, '')
                 AND p.foglio = a.foglio
                 AND p.particella = a.particella
                GROUP BY a.id
            ),
            classified AS (
                SELECT
                    a.id,
                    CASE
                        WHEN m.match_count = 0 THEN 'nuove_in_ade'
                        WHEN m.match_count > 1 THEN 'match_ambiguo'
                        WHEN a.geometry IS NOT NULL
                         AND p.geometry IS NOT NULL
                         AND ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) > :threshold_m
                            THEN 'geometrie_variate'
                        ELSE 'allineate'
                    END AS category
                FROM ade a
                JOIN ade_matches m ON m.ade_id = a.id
                LEFT JOIN cat_particelle p ON p.id = m.particella_id
            ),
            missing AS (
                SELECT COUNT(*) AS count
                FROM cat_particelle p, scope
                WHERE p.is_current IS TRUE
                  AND p.geometry IS NOT NULL
                  AND ST_Intersects(p.geometry, scope.geom)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM ade a
                      WHERE a.codice_catastale = p.codice_catastale
                        AND COALESCE(a.sezione_catastale, '') = COALESCE(p.sezione_catastale, '')
                        AND a.foglio = p.foglio
                        AND a.particella = p.particella
                  )
            )
            SELECT
                COUNT(*) FILTER (WHERE category = 'allineate') AS allineate,
                COUNT(*) FILTER (WHERE category = 'nuove_in_ade') AS nuove_in_ade,
                COUNT(*) FILTER (WHERE category = 'geometrie_variate') AS geometrie_variate,
                COUNT(*) FILTER (WHERE category = 'match_ambiguo') AS match_ambiguo,
                (SELECT count FROM missing) AS mancanti_in_ade,
                COUNT(*) AS staged_particelle
            FROM classified
            """
        ),
        params,
    ).one()
    samples = db.execute(
        text(
            """
            WITH ade AS (
                SELECT *
                FROM cat_ade_particelle
                WHERE source_run_id = :run_id
            ),
            ade_matches AS (
                SELECT
                    a.id AS ade_id,
                    COUNT(p.id) AS match_count,
                    MAX(p.id::text)::uuid AS particella_id
                FROM ade a
                LEFT JOIN cat_particelle p
                  ON p.is_current IS TRUE
                 AND p.codice_catastale = a.codice_catastale
                 AND COALESCE(p.sezione_catastale, '') = COALESCE(a.sezione_catastale, '')
                 AND p.foglio = a.foglio
                 AND p.particella = a.particella
                GROUP BY a.id
            )
            SELECT
                CASE
                    WHEN m.match_count = 0 THEN 'nuove_in_ade'
                    WHEN m.match_count > 1 THEN 'match_ambiguo'
                    WHEN a.geometry IS NOT NULL
                     AND p.geometry IS NOT NULL
                     AND ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) > :threshold_m
                        THEN 'geometrie_variate'
                    ELSE 'allineate'
                END AS category,
                a.national_cadastral_reference,
                a.codice_catastale,
                a.foglio,
                a.particella,
                p.id::text AS particella_id,
                CASE
                    WHEN a.geometry IS NOT NULL AND p.geometry IS NOT NULL
                    THEN ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632))
                    ELSE NULL
                END AS distance_m
            FROM ade a
            JOIN ade_matches m ON m.ade_id = a.id
            LEFT JOIN cat_particelle p ON p.id = m.particella_id
            WHERE m.match_count <> 1
               OR (
                    a.geometry IS NOT NULL
                AND p.geometry IS NOT NULL
                AND ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) > :threshold_m
               )
            ORDER BY category, a.codice_catastale, a.foglio, a.particella
            LIMIT 50
            """
        ),
        params,
    ).mappings().all()
    geojson_row = db.execute(
        text(
            """
            WITH scope AS (
                SELECT ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326) AS geom
            ),
            ade AS (
                SELECT *
                FROM cat_ade_particelle
                WHERE source_run_id = :run_id
            ),
            ade_matches AS (
                SELECT
                    a.id AS ade_id,
                    COUNT(p.id) AS match_count,
                    MAX(p.id::text)::uuid AS particella_id
                FROM ade a
                LEFT JOIN cat_particelle p
                  ON p.is_current IS TRUE
                 AND p.codice_catastale = a.codice_catastale
                 AND COALESCE(p.sezione_catastale, '') = COALESCE(a.sezione_catastale, '')
                 AND p.foglio = a.foglio
                 AND p.particella = a.particella
                GROUP BY a.id
            ),
            classified_ade AS (
                SELECT
                    CASE
                        WHEN m.match_count = 0 THEN 'nuove_in_ade'
                        WHEN m.match_count > 1 THEN 'match_ambiguo'
                        WHEN a.geometry IS NOT NULL
                         AND p.geometry IS NOT NULL
                         AND ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) > :threshold_m
                            THEN 'geometrie_variate'
                        ELSE 'allineate'
                    END AS category,
                    'ade' AS geometry_source,
                    a.national_cadastral_reference,
                    a.codice_catastale,
                    a.foglio,
                    a.particella,
                    p.id::text AS particella_id,
                    CASE
                        WHEN a.geometry IS NOT NULL AND p.geometry IS NOT NULL
                        THEN ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632))
                        ELSE NULL
                    END AS distance_m,
                    a.geometry
                FROM ade a
                JOIN ade_matches m ON m.ade_id = a.id
                LEFT JOIN cat_particelle p ON p.id = m.particella_id
            ),
            changed_gaia AS (
                SELECT
                    'geometrie_variate' AS category,
                    'gaia' AS geometry_source,
                    a.national_cadastral_reference,
                    a.codice_catastale,
                    a.foglio,
                    a.particella,
                    p.id::text AS particella_id,
                    ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) AS distance_m,
                    p.geometry
                FROM ade a
                JOIN ade_matches m ON m.ade_id = a.id AND m.match_count = 1
                JOIN cat_particelle p ON p.id = m.particella_id
                WHERE a.geometry IS NOT NULL
                  AND p.geometry IS NOT NULL
                  AND ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) > :threshold_m
            ),
            missing_gaia AS (
                SELECT
                    'mancanti_in_ade' AS category,
                    'gaia' AS geometry_source,
                    p.national_code AS national_cadastral_reference,
                    p.codice_catastale,
                    p.foglio,
                    p.particella,
                    p.id::text AS particella_id,
                    NULL::double precision AS distance_m,
                    p.geometry
                FROM cat_particelle p, scope
                WHERE p.is_current IS TRUE
                  AND p.geometry IS NOT NULL
                  AND ST_Intersects(p.geometry, scope.geom)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM ade a
                      WHERE a.codice_catastale = p.codice_catastale
                        AND COALESCE(a.sezione_catastale, '') = COALESCE(p.sezione_catastale, '')
                        AND a.foglio = p.foglio
                        AND a.particella = p.particella
                  )
            ),
            preview_features AS (
                SELECT *
                FROM classified_ade
                WHERE category <> 'allineate' AND geometry IS NOT NULL
                UNION ALL
                SELECT * FROM changed_gaia
                UNION ALL
                SELECT * FROM missing_gaia
                LIMIT 500
            )
            SELECT COALESCE(
                jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geometry)::jsonb,
                                'properties', jsonb_build_object(
                                    'category', category,
                                    'geometry_source', geometry_source,
                                    'national_cadastral_reference', national_cadastral_reference,
                                    'codice_catastale', codice_catastale,
                                    'foglio', foglio,
                                    'particella', particella,
                                    'particella_id', particella_id,
                                    'distance_m', distance_m
                                )
                            )
                        ),
                        '[]'::jsonb
                    )
                ),
                jsonb_build_object('type', 'FeatureCollection', 'features', '[]'::jsonb)
            ) AS geojson
            FROM preview_features
            """
        ),
        params,
    ).one()

    geojson = geojson_row.geojson
    if isinstance(geojson, str):
        geojson = json.loads(geojson)

    return {
        "run_id": str(run.id),
        "status": run.status,
        "requested_bbox": run.request_bbox_json,
        "geometry_threshold_m": geometry_threshold_m,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "counters": {
            "staged_particelle": int(counters.staged_particelle or 0),
            "allineate": int(counters.allineate or 0),
            "nuove_in_ade": int(counters.nuove_in_ade or 0),
            "geometrie_variate": int(counters.geometrie_variate or 0),
            "match_ambiguo": int(counters.match_ambiguo or 0),
            "mancanti_in_ade": int(counters.mancanti_in_ade or 0),
        },
        "samples": [dict(item) for item in samples],
        "geojson": geojson,
    }


def _normalize_apply_categories(categories: list[str] | None) -> list[str]:
    selected = []
    for category in categories or []:
        normalized = category.strip().lower()
        if normalized not in ADE_APPLY_CATEGORIES:
            raise ValueError(f"Categoria allineamento AdE non applicabile: {category}")
        if normalized not in selected:
            selected.append(normalized)
    return selected


def preview_ade_alignment_apply(
    db: Session,
    run_id: str,
    *,
    categories: list[str] | None = None,
    geometry_threshold_m: float = 1.0,
) -> dict[str, Any]:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        raise ValueError("Preview applicazione AdE disponibile solo su PostgreSQL/PostGIS.")

    try:
        run_uuid = UUID(str(run_id))
    except ValueError as exc:
        raise ValueError("Run AdE non valido.") from exc

    run = db.get(CatAdeSyncRun, run_uuid)
    if run is None:
        raise ValueError("Run AdE non trovato.")
    if run.status != "completed":
        raise ValueError("Preview disponibile solo per run AdE completati.")

    selected_categories = _normalize_apply_categories(categories)
    bbox = run.request_bbox_json
    params = {
        "run_id": run_id,
        "threshold_m": geometry_threshold_m,
        "selected_categories": selected_categories,
        "min_lon": bbox["min_lon"],
        "min_lat": bbox["min_lat"],
        "max_lon": bbox["max_lon"],
        "max_lat": bbox["max_lat"],
    }

    summary = db.execute(
        text(
            """
            WITH scope AS (
                SELECT ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326) AS geom
            ),
            ade AS (
                SELECT *
                FROM cat_ade_particelle
                WHERE source_run_id = :run_id
            ),
            ade_matches AS (
                SELECT
                    a.id AS ade_id,
                    COUNT(p.id) AS match_count,
                    MAX(p.id::text)::uuid AS particella_id
                FROM ade a
                LEFT JOIN cat_particelle p
                  ON p.is_current IS TRUE
                 AND p.codice_catastale = a.codice_catastale
                 AND COALESCE(p.sezione_catastale, '') = COALESCE(a.sezione_catastale, '')
                 AND p.foglio = a.foglio
                 AND p.particella = a.particella
                GROUP BY a.id
            ),
            classified_ade AS (
                SELECT
                    a.id AS ade_id,
                    m.particella_id,
                    CASE
                        WHEN m.match_count = 0 THEN 'nuove_in_ade'
                        WHEN m.match_count > 1 THEN 'match_ambiguo'
                        WHEN a.geometry IS NOT NULL
                         AND p.geometry IS NOT NULL
                         AND ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) > :threshold_m
                            THEN 'geometrie_variate'
                        ELSE 'allineate'
                    END AS category
                FROM ade a
                JOIN ade_matches m ON m.ade_id = a.id
                LEFT JOIN cat_particelle p ON p.id = m.particella_id
            ),
            missing_gaia AS (
                SELECT p.id AS particella_id, 'mancanti_in_ade' AS category
                FROM cat_particelle p, scope
                WHERE p.is_current IS TRUE
                  AND p.geometry IS NOT NULL
                  AND ST_Intersects(p.geometry, scope.geom)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM ade a
                      WHERE a.codice_catastale = p.codice_catastale
                        AND COALESCE(a.sezione_catastale, '') = COALESCE(p.sezione_catastale, '')
                        AND a.foglio = p.foglio
                        AND a.particella = p.particella
                  )
            ),
            existing_actions AS (
                SELECT particella_id
                FROM classified_ade
                WHERE category = 'geometrie_variate'
                  AND category = ANY(:selected_categories)
                  AND particella_id IS NOT NULL
                UNION
                SELECT particella_id
                FROM missing_gaia
                WHERE category = ANY(:selected_categories)
            ),
            affected AS (
                SELECT p.*
                FROM cat_particelle p
                JOIN existing_actions action ON action.particella_id = p.id
            )
            SELECT
                COUNT(*) FILTER (WHERE category = 'nuove_in_ade' AND category = ANY(:selected_categories)) AS insert_new,
                COUNT(*) FILTER (WHERE category = 'geometrie_variate' AND category = ANY(:selected_categories)) AS update_geometry,
                (SELECT COUNT(*) FROM missing_gaia WHERE category = ANY(:selected_categories)) AS suppress_missing,
                COUNT(*) FILTER (WHERE category = 'match_ambiguo') AS skipped_ambiguous,
                (
                    COUNT(*) FILTER (
                        WHERE category IN ('nuove_in_ade', 'geometrie_variate')
                    AND category <> ALL(:selected_categories)
                    )
                    + (SELECT COUNT(*) FROM missing_gaia WHERE category <> ALL(:selected_categories))
                ) AS skipped_not_selected,
                (SELECT COUNT(DISTINCT id) FROM affected) AS affected_particelle,
                (
                    SELECT COUNT(*)
                    FROM cat_utenze_irrigue u
                    JOIN affected p ON p.id = u.particella_id
                ) AS utenze_collegate,
                (
                    SELECT COUNT(*)
                    FROM cat_consorzio_units cu
                    JOIN affected p ON p.id = cu.particella_id
                ) AS consorzio_units_collegate,
                (
                    SELECT COUNT(*)
                    FROM cat_gis_saved_selection_items si
                    JOIN affected p ON p.id = si.particella_id
                ) AS saved_selection_items,
                (
                    SELECT COUNT(*)
                    FROM ruolo_particelle rp
                    JOIN catasto_parcels cp ON cp.id = rp.catasto_parcel_id
                    JOIN affected p
                      ON cp.comune_codice = p.codice_catastale
                     AND cp.foglio = p.foglio
                     AND cp.particella = p.particella
                     AND (
                        COALESCE(p.subalterno, '') = ''
                        OR COALESCE(cp.subalterno, '') = p.subalterno
                     )
                ) AS ruolo_particelle_collegate
            FROM classified_ade
            """
        ),
        params,
    ).one()

    samples = db.execute(
        text(
            """
            WITH scope AS (
                SELECT ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326) AS geom
            ),
            ade AS (
                SELECT *
                FROM cat_ade_particelle
                WHERE source_run_id = :run_id
            ),
            ade_matches AS (
                SELECT
                    a.id AS ade_id,
                    COUNT(p.id) AS match_count,
                    MAX(p.id::text)::uuid AS particella_id
                FROM ade a
                LEFT JOIN cat_particelle p
                  ON p.is_current IS TRUE
                 AND p.codice_catastale = a.codice_catastale
                 AND COALESCE(p.sezione_catastale, '') = COALESCE(a.sezione_catastale, '')
                 AND p.foglio = a.foglio
                 AND p.particella = a.particella
                GROUP BY a.id
            ),
            classified_ade AS (
                SELECT
                    CASE
                        WHEN m.match_count = 0 THEN 'nuove_in_ade'
                        WHEN m.match_count > 1 THEN 'match_ambiguo'
                        WHEN a.geometry IS NOT NULL
                         AND p.geometry IS NOT NULL
                         AND ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) > :threshold_m
                            THEN 'geometrie_variate'
                        ELSE 'allineate'
                    END AS category,
                    a.national_cadastral_reference,
                    a.codice_catastale,
                    a.foglio,
                    a.particella,
                    p.id::text AS particella_id,
                    CASE
                        WHEN a.geometry IS NOT NULL AND p.geometry IS NOT NULL
                        THEN ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632))
                        ELSE NULL
                    END AS distance_m
                FROM ade a
                JOIN ade_matches m ON m.ade_id = a.id
                LEFT JOIN cat_particelle p ON p.id = m.particella_id
            ),
            missing_gaia AS (
                SELECT
                    'mancanti_in_ade' AS category,
                    p.national_code AS national_cadastral_reference,
                    p.codice_catastale,
                    p.foglio,
                    p.particella,
                    p.id::text AS particella_id,
                    NULL::double precision AS distance_m
                FROM cat_particelle p, scope
                WHERE p.is_current IS TRUE
                  AND p.geometry IS NOT NULL
                  AND ST_Intersects(p.geometry, scope.geom)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM ade a
                      WHERE a.codice_catastale = p.codice_catastale
                        AND COALESCE(a.sezione_catastale, '') = COALESCE(p.sezione_catastale, '')
                        AND a.foglio = p.foglio
                        AND a.particella = p.particella
                  )
            ),
            selected AS (
                SELECT * FROM classified_ade
                WHERE category = ANY(:selected_categories)
                UNION ALL
                SELECT * FROM missing_gaia
                WHERE category = ANY(:selected_categories)
            )
            SELECT *
            FROM selected
            ORDER BY category, codice_catastale, foglio, particella
            LIMIT 50
            """
        ),
        params,
    ).mappings().all()

    warnings = [
        "Preview non applica modifiche a cat_particelle.",
        "I match ambigui non sono applicabili automaticamente e richiedono revisione manuale.",
    ]
    if "mancanti_in_ade" in selected_categories:
        warnings.append("La soppressione delle particelle mancanti in AdE va validata sul confine bbox del run.")

    return {
        "run_id": str(run.id),
        "status": "preview",
        "selected_categories": selected_categories,
        "geometry_threshold_m": geometry_threshold_m,
        "counters": {
            "insert_new": int(summary.insert_new or 0),
            "update_geometry": int(summary.update_geometry or 0),
            "suppress_missing": int(summary.suppress_missing or 0),
            "skipped_ambiguous": int(summary.skipped_ambiguous or 0),
            "skipped_not_selected": int(summary.skipped_not_selected or 0),
        },
        "impact": {
            "affected_particelle": int(summary.affected_particelle or 0),
            "utenze_collegate": int(summary.utenze_collegate or 0),
            "consorzio_units_collegate": int(summary.consorzio_units_collegate or 0),
            "saved_selection_items": int(summary.saved_selection_items or 0),
            "ruolo_particelle_collegate": int(summary.ruolo_particelle_collegate or 0),
        },
        "warnings": warnings,
        "samples": [dict(item) for item in samples],
    }


def apply_ade_alignment(
    db: Session,
    run_id: str,
    *,
    categories: list[str] | None = None,
    geometry_threshold_m: float = 1.0,
    confirm: bool = False,
    allow_suppress_missing: bool = False,
) -> dict[str, Any]:
    if not confirm:
        raise ValueError("Conferma esplicita richiesta per applicare l'allineamento AdE.")
    if db.bind is None or db.bind.dialect.name != "postgresql":
        raise ValueError("Applicazione allineamento AdE disponibile solo su PostgreSQL/PostGIS.")

    try:
        run_uuid = UUID(str(run_id))
    except ValueError as exc:
        raise ValueError("Run AdE non valido.") from exc

    run = db.get(CatAdeSyncRun, run_uuid)
    if run is None:
        raise ValueError("Run AdE non trovato.")
    if run.status != "completed":
        raise ValueError("Applicazione disponibile solo per run AdE completati.")

    selected_categories = _normalize_apply_categories(categories)
    if "mancanti_in_ade" in selected_categories and not allow_suppress_missing:
        raise ValueError("Soppressione mancanti in AdE non abilitata: impostare allow_suppress_missing=true.")

    bbox = run.request_bbox_json
    params = {
        "run_id": run_id,
        "threshold_m": geometry_threshold_m,
        "selected_categories": selected_categories,
        "min_lon": bbox["min_lon"],
        "min_lat": bbox["min_lat"],
        "max_lon": bbox["max_lon"],
        "max_lat": bbox["max_lat"],
    }
    cte = """
        WITH scope AS (
            SELECT ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326) AS geom
        ),
        ade AS (
            SELECT *
            FROM cat_ade_particelle
            WHERE source_run_id = :run_id
        ),
        ade_matches AS (
            SELECT
                a.id AS ade_id,
                COUNT(p.id) AS match_count,
                MAX(p.id::text)::uuid AS particella_id
            FROM ade a
            LEFT JOIN cat_particelle p
              ON p.is_current IS TRUE
             AND p.codice_catastale = a.codice_catastale
             AND COALESCE(p.sezione_catastale, '') = COALESCE(a.sezione_catastale, '')
             AND p.foglio = a.foglio
             AND p.particella = a.particella
            GROUP BY a.id
        ),
        classified_ade AS (
            SELECT
                a.*,
                m.particella_id,
                CASE
                    WHEN m.match_count = 0 THEN 'nuove_in_ade'
                    WHEN m.match_count > 1 THEN 'match_ambiguo'
                    WHEN a.geometry IS NOT NULL
                     AND p.geometry IS NOT NULL
                     AND ST_HausdorffDistance(ST_Transform(a.geometry, 32632), ST_Transform(p.geometry, 32632)) > :threshold_m
                        THEN 'geometrie_variate'
                    ELSE 'allineate'
                END AS category
            FROM ade a
            JOIN ade_matches m ON m.ade_id = a.id
            LEFT JOIN cat_particelle p ON p.id = m.particella_id
        ),
        missing_gaia AS (
            SELECT p.*
            FROM cat_particelle p, scope
            WHERE p.is_current IS TRUE
              AND p.geometry IS NOT NULL
              AND ST_Intersects(p.geometry, scope.geom)
              AND NOT EXISTS (
                  SELECT 1
                  FROM ade a
                  WHERE a.codice_catastale = p.codice_catastale
                    AND COALESCE(a.sezione_catastale, '') = COALESCE(p.sezione_catastale, '')
                    AND a.foglio = p.foglio
                    AND a.particella = p.particella
              )
        )
    """

    skipped = db.execute(
        text(
            cte
            + """
            SELECT
                COUNT(*) FILTER (WHERE category = 'match_ambiguo') AS skipped_ambiguous,
                (
                    COUNT(*) FILTER (
                        WHERE category IN ('nuove_in_ade', 'geometrie_variate')
                          AND category <> ALL(:selected_categories)
                    )
                    + (SELECT COUNT(*) FROM missing_gaia WHERE 'mancanti_in_ade' <> ALL(:selected_categories))
                ) AS skipped_not_selected,
                COUNT(*) FILTER (
                    WHERE category = 'nuove_in_ade'
                      AND category = ANY(:selected_categories)
                      AND c.id IS NULL
                ) AS skipped_missing_comune
            FROM classified_ade a
            LEFT JOIN cat_comuni c ON c.codice_catastale = a.codice_catastale
            """
        ),
        params,
    ).one()

    try:
        updated_history = db.execute(
            text(
                cte
                + """
                INSERT INTO cat_particelle_history (
                  history_id,
                  particella_id,
                  comune_id,
                  national_code,
                  cod_comune_capacitas,
                  codice_catastale,
                  foglio,
                  particella,
                  subalterno,
                  superficie_mq,
                  superficie_grafica_mq,
                  num_distretto,
                  geometry,
                  valid_from,
                  valid_to,
                  changed_at,
                  change_reason
                )
                SELECT
                  gen_random_uuid(),
                  p.id,
                  p.comune_id,
                  p.national_code,
                  p.cod_comune_capacitas,
                  p.codice_catastale,
                  p.foglio,
                  p.particella,
                  p.subalterno,
                  p.superficie_mq,
                  p.superficie_grafica_mq,
                  p.num_distretto,
                  p.geometry,
                  p.valid_from,
                  CURRENT_DATE,
                  now(),
                  'ade_wfs_alignment'
                FROM classified_ade a
                JOIN cat_particelle p ON p.id = a.particella_id
                WHERE a.category = 'geometrie_variate'
                  AND a.category = ANY(:selected_categories)
                  AND a.geometry IS NOT NULL
                  AND p.geometry IS NOT NULL
                RETURNING particella_id
                """
            ),
            params,
        ).rowcount or 0

        updated_geometry = db.execute(
            text(
                cte
                + """
                UPDATE cat_particelle p
                SET geometry = a.geometry,
                    source_type = 'ade_wfs',
                    updated_at = now()
                FROM classified_ade a
                WHERE p.id = a.particella_id
                  AND a.category = 'geometrie_variate'
                  AND a.category = ANY(:selected_categories)
                  AND a.geometry IS NOT NULL
                  AND p.geometry IS NOT NULL
                RETURNING p.id
                """
            ),
            params,
        ).rowcount or 0

        inserted_new = db.execute(
            text(
                cte
                + """
                INSERT INTO cat_particelle (
                  id,
                  comune_id,
                  national_code,
                  cod_comune_capacitas,
                  codice_catastale,
                  nome_comune,
                  sezione_catastale,
                  foglio,
                  particella,
                  subalterno,
                  cfm,
                  superficie_mq,
                  superficie_grafica_mq,
                  num_distretto,
                  nome_distretto,
                  geometry,
                  source_type,
                  import_batch_id,
                  valid_from,
                  valid_to,
                  is_current,
                  suppressed,
                  created_at,
                  updated_at
                )
                SELECT
                  gen_random_uuid(),
                  c.id,
                  a.national_cadastral_reference,
                  c.cod_comune_capacitas,
                  a.codice_catastale,
                  c.nome_comune,
                  a.sezione_catastale,
                  a.foglio,
                  a.particella,
                  NULL,
                  NULL,
                  CASE WHEN a.geometry IS NULL THEN NULL ELSE ST_Area(ST_Transform(a.geometry, 32632)) END,
                  CASE WHEN a.geometry IS NULL THEN NULL ELSE ST_Area(ST_Transform(a.geometry, 32632)) END,
                  NULL,
                  NULL,
                  a.geometry,
                  'ade_wfs',
                  NULL,
                  CURRENT_DATE,
                  NULL,
                  true,
                  false,
                  now(),
                  now()
                FROM classified_ade a
                JOIN cat_comuni c ON c.codice_catastale = a.codice_catastale
                WHERE a.category = 'nuove_in_ade'
                  AND a.category = ANY(:selected_categories)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM cat_particelle p
                      WHERE p.is_current IS TRUE
                        AND p.codice_catastale = a.codice_catastale
                        AND COALESCE(p.sezione_catastale, '') = COALESCE(a.sezione_catastale, '')
                        AND p.foglio = a.foglio
                        AND p.particella = a.particella
                  )
                RETURNING id
                """
            ),
            params,
        ).rowcount or 0

        suppressed_missing = 0
        if "mancanti_in_ade" in selected_categories:
            db.execute(
                text(
                    cte
                    + """
                    INSERT INTO cat_particelle_history (
                      history_id,
                      particella_id,
                      comune_id,
                      national_code,
                      cod_comune_capacitas,
                      codice_catastale,
                      foglio,
                      particella,
                      subalterno,
                      superficie_mq,
                      superficie_grafica_mq,
                      num_distretto,
                      geometry,
                      valid_from,
                      valid_to,
                      changed_at,
                      change_reason
                    )
                    SELECT
                      gen_random_uuid(),
                      p.id,
                      p.comune_id,
                      p.national_code,
                      p.cod_comune_capacitas,
                      p.codice_catastale,
                      p.foglio,
                      p.particella,
                      p.subalterno,
                      p.superficie_mq,
                      p.superficie_grafica_mq,
                      p.num_distretto,
                      p.geometry,
                      p.valid_from,
                      CURRENT_DATE,
                      now(),
                      'ade_wfs_alignment_missing'
                    FROM missing_gaia p
                    WHERE p.suppressed IS NOT TRUE
                    RETURNING particella_id
                    """
                ),
                params,
            )
            suppressed_missing = db.execute(
                text(
                    cte
                    + """
                    UPDATE cat_particelle p
                    SET suppressed = true,
                        source_type = 'ade_wfs',
                        updated_at = now()
                    FROM missing_gaia missing
                    WHERE p.id = missing.id
                      AND p.suppressed IS NOT TRUE
                    RETURNING p.id
                    """
                ),
                params,
            ).rowcount or 0

        db.commit()
    except Exception:
        db.rollback()
        raise

    warnings = [
        "Geometrie variate aggiornate in-place per preservare i collegamenti FK esistenti.",
        "I match ambigui non sono stati applicati.",
    ]
    if updated_history != updated_geometry:
        warnings.append("Conteggio history diverso dagli update geometria: verificare il run.")
    if int(skipped.skipped_missing_comune or 0) > 0:
        warnings.append("Alcune nuove particelle AdE sono state saltate perché il codice catastale non è mappato in cat_comuni.")

    return {
        "run_id": str(run.id),
        "status": "applied",
        "selected_categories": selected_categories,
        "geometry_threshold_m": geometry_threshold_m,
        "counters": {
            "inserted_new": int(inserted_new or 0),
            "updated_geometry": int(updated_geometry or 0),
            "suppressed_missing": int(suppressed_missing or 0),
            "skipped_ambiguous": int(skipped.skipped_ambiguous or 0),
            "skipped_not_selected": int(skipped.skipped_not_selected or 0),
            "skipped_missing_comune": int(skipped.skipped_missing_comune or 0),
        },
        "warnings": warnings,
    }
