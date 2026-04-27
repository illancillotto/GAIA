from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from shapely.geometry import shape
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.catasto.schemas.gis_schemas import (
    DistrettoAggr,
    FoglioAggr,
    GisExportFormat,
    GisFilters,
    GisSelectResult,
    ParticellaGisSummary,
    ParticellaPopupData,
)


SARDINIA_BBOX = {
    "min_lon": 7.8,
    "max_lon": 10.0,
    "min_lat": 38.5,
    "max_lat": 41.5,
}
PREVIEW_LIMIT = 200
MAX_EXPORT_IDS = 10000


def _validate_geometry_bbox(geometry: dict[str, Any]) -> None:
    try:
        bounds = shape(geometry).bounds
    except (AttributeError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Geometria GeoJSON non valida: {exc}") from exc

    if (
        bounds[0] < SARDINIA_BBOX["min_lon"]
        or bounds[2] > SARDINIA_BBOX["max_lon"]
        or bounds[1] < SARDINIA_BBOX["min_lat"]
        or bounds[3] > SARDINIA_BBOX["max_lat"]
    ):
        raise HTTPException(
            status_code=400,
            detail="La geometria di selezione è fuori dall'area di interesse (Sardegna).",
        )


def _build_where_clause(filters: GisFilters | None, geojson_str: str) -> tuple[str, dict[str, Any]]:
    conditions = [
        "p.is_current = TRUE",
        "ST_Intersects(p.geometry, ST_SetSRID(ST_GeomFromGeoJSON(:geojson_str), 4326))",
    ]
    params: dict[str, Any] = {"geojson_str": geojson_str}

    if filters:
        if filters.comune is not None:
            conditions.append("p.cod_comune_capacitas = :comune")
            params["comune"] = filters.comune
        if filters.codice_catastale:
            conditions.append("p.codice_catastale = :codice_catastale")
            params["codice_catastale"] = filters.codice_catastale.strip().upper()
        if filters.foglio:
            conditions.append("p.foglio = :foglio")
            params["foglio"] = filters.foglio
        if filters.num_distretto:
            conditions.append("p.num_distretto = :num_distretto")
            params["num_distretto"] = filters.num_distretto
        if filters.solo_anomalie:
            conditions.append(
                """
                EXISTS(
                    SELECT 1
                    FROM cat_anomalie a
                    WHERE a.particella_id = p.id
                      AND a.status = 'aperta'
                )
                """
            )

    return " AND ".join(conditions), params


def select_by_geometry(db: Session, geometry: dict[str, Any], filters: GisFilters | None) -> GisSelectResult:
    _validate_geometry_bbox(geometry)
    geojson_str = json.dumps(geometry)
    where_clause, params = _build_where_clause(filters, geojson_str)
    params["preview_limit"] = PREVIEW_LIMIT

    db.execute(text("SET LOCAL statement_timeout = '10000'"))
    sql = text(
        f"""
        WITH selected AS (
            SELECT
                p.id::text,
                p.cfm,
                p.cod_comune_capacitas,
                p.cod_comune_capacitas AS cod_comune_istat,
                p.codice_catastale,
                p.nome_comune,
                p.foglio,
                p.particella,
                p.subalterno,
                p.superficie_mq,
                p.superficie_grafica_mq,
                p.num_distretto,
                p.nome_distretto,
                COALESCE(ST_Area(ST_Transform(p.geometry, 32632)) / 10000.0, 0) AS sup_ha,
                EXISTS(
                    SELECT 1
                    FROM cat_anomalie a
                    WHERE a.particella_id = p.id
                      AND a.status = 'aperta'
                ) AS ha_anomalie
            FROM cat_particelle p
            WHERE {where_clause}
        ),
        totals AS (
            SELECT
                COUNT(*) AS n_totale,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha_totale
            FROM selected
        ),
        per_foglio AS (
            SELECT
                foglio,
                COUNT(*) AS n_particelle,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha
            FROM selected
            WHERE foglio IS NOT NULL
            GROUP BY foglio
            ORDER BY foglio
        ),
        per_distretto AS (
            SELECT
                num_distretto,
                MAX(nome_distretto) AS nome_distretto,
                COUNT(*) AS n_particelle,
                COALESCE(SUM(sup_ha), 0) AS superficie_ha
            FROM selected
            WHERE num_distretto IS NOT NULL
            GROUP BY num_distretto
            ORDER BY num_distretto
        ),
        preview AS (
            SELECT *
            FROM selected
            ORDER BY codice_catastale, foglio, particella, subalterno
            LIMIT :preview_limit
        )
        SELECT
            t.n_totale,
            t.superficie_ha_totale,
            (SELECT json_agg(row_to_json(f)) FROM per_foglio f) AS per_foglio,
            (SELECT json_agg(row_to_json(d)) FROM per_distretto d) AS per_distretto,
            (SELECT json_agg(row_to_json(pr)) FROM preview pr) AS particelle_preview,
            t.n_totale > :preview_limit AS truncated
        FROM totals t
        """
    )

    row = db.execute(sql, params).mappings().first()
    if row is None:
        return GisSelectResult(n_particelle=0, superficie_ha=0.0)

    return GisSelectResult(
        n_particelle=int(row["n_totale"] or 0),
        superficie_ha=round(float(row["superficie_ha_totale"] or 0), 2),
        per_foglio=_parse_foglio_aggr(row["per_foglio"]),
        per_distretto=_parse_distretto_aggr(row["per_distretto"]),
        particelle=_parse_preview(row["particelle_preview"]),
        truncated=bool(row["truncated"]),
    )


def export_particelle(db: Session, id_list: list[str], fmt: GisExportFormat) -> StreamingResponse:
    if not id_list:
        raise HTTPException(status_code=400, detail="Lista ID vuota")
    if len(id_list) > MAX_EXPORT_IDS:
        raise HTTPException(status_code=400, detail=f"Massimo {MAX_EXPORT_IDS} particelle per export")

    if fmt == GisExportFormat.geojson:
        return _export_geojson(db, id_list)
    return _export_csv(db, id_list)


def get_popup_data(db: Session, particella_id: str) -> ParticellaPopupData:
    sql = text(
        """
        SELECT
            p.id::text,
            p.cfm,
            p.cod_comune_capacitas,
            p.cod_comune_capacitas AS cod_comune_istat,
            p.codice_catastale,
            p.nome_comune,
            p.foglio,
            p.particella,
            p.subalterno,
            p.superficie_mq,
            p.superficie_grafica_mq,
            p.num_distretto,
            p.nome_distretto,
            COUNT(a.id) FILTER (WHERE a.status = 'aperta') AS n_anomalie_aperte
        FROM cat_particelle p
        LEFT JOIN cat_anomalie a ON a.particella_id = p.id
        WHERE p.id::text = :particella_id
          AND p.is_current = TRUE
        GROUP BY p.id
        """
    )
    row = db.execute(sql, {"particella_id": particella_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Particella non trovata")

    return ParticellaPopupData(**dict(row))


def _export_geojson(db: Session, id_list: list[str]) -> StreamingResponse:
    sql = text(
        """
        SELECT
            id::text,
            cfm,
            cod_comune_capacitas,
            cod_comune_capacitas AS cod_comune_istat,
            codice_catastale,
            nome_comune,
            foglio,
            particella,
            subalterno,
            superficie_mq,
            superficie_grafica_mq,
            num_distretto,
            nome_distretto,
            ST_AsGeoJSON(geometry)::json AS geometry_json
        FROM cat_particelle
        WHERE id::text = ANY(:ids)
          AND is_current = TRUE
        ORDER BY codice_catastale, foglio, particella, subalterno
        """
    )
    rows = db.execute(sql, {"ids": id_list}).mappings().all()
    features = []
    for row in rows:
        properties = dict(row)
        geometry = properties.pop("geometry_json")
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})

    content = json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False)
    return StreamingResponse(
        io.StringIO(content),
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=selezione_catasto.geojson"},
    )


def _export_csv(db: Session, id_list: list[str]) -> StreamingResponse:
    sql = text(
        """
        SELECT
            id::text,
            cfm,
            cod_comune_capacitas,
            codice_catastale,
            nome_comune,
            foglio,
            particella,
            subalterno,
            superficie_mq,
            superficie_grafica_mq,
            num_distretto,
            nome_distretto
        FROM cat_particelle
        WHERE id::text = ANY(:ids)
          AND is_current = TRUE
        ORDER BY codice_catastale, foglio, particella, subalterno
        """
    )
    rows = db.execute(sql, {"ids": id_list}).mappings().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "cfm",
            "cod_comune_capacitas",
            "codice_catastale",
            "nome_comune",
            "foglio",
            "particella",
            "subalterno",
            "superficie_mq",
            "superficie_grafica_mq",
            "num_distretto",
            "nome_distretto",
        ]
    )
    for row in rows:
        writer.writerow([row[column] for column in row.keys()])
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=selezione_catasto.csv"},
    )


def _parse_foglio_aggr(data: list[dict[str, Any]] | None) -> list[FoglioAggr]:
    if not data:
        return []
    return [
        FoglioAggr(
            foglio=str(row["foglio"]),
            n_particelle=int(row["n_particelle"]),
            superficie_ha=round(float(row["superficie_ha"] or 0), 2),
        )
        for row in data
    ]


def _parse_distretto_aggr(data: list[dict[str, Any]] | None) -> list[DistrettoAggr]:
    if not data:
        return []
    return [
        DistrettoAggr(
            num_distretto=str(row["num_distretto"]),
            nome_distretto=row.get("nome_distretto"),
            n_particelle=int(row["n_particelle"]),
            superficie_ha=round(float(row["superficie_ha"] or 0), 2),
        )
        for row in data
    ]


def _parse_preview(data: list[dict[str, Any]] | None) -> list[ParticellaGisSummary]:
    if not data:
        return []
    return [ParticellaGisSummary(**row) for row in data]
