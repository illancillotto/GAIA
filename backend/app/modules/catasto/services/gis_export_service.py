from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Sequence
from typing import Any

from fastapi import Response
from openpyxl import Workbook
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.modules.catasto.schemas.gis_schemas import GisExportFormat

GIS_EXPORT_HEADERS = [
    "id",
    "comune",
    "codice_catastale",
    "nome_comune",
    "cod_comune_capacitas",
    "cod_comune_istat",
    "national_code",
    "cfm",
    "sezione",
    "sezione_catastale",
    "foglio",
    "particella",
    "sub",
    "subalterno",
    "superficie_mq",
    "superficie_grafica_mq",
    "num_distretto",
    "nome_distretto",
    "geometry_wkt",
    "geometry_geojson",
]


def export_particelle(db: Session, id_list: list[str], fmt: GisExportFormat) -> StreamingResponse | Response:
    if fmt == GisExportFormat.geojson:
        return _export_geojson(db, id_list)
    rows = _fetch_particelle_export_rows(db, id_list)
    if fmt == GisExportFormat.xlsx:
        return _export_xlsx(rows)
    return _export_csv(rows)


def _fetch_particelle_export_rows(db: Session, id_list: list[str]) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT
            id::text AS id,
            COALESCE(NULLIF(BTRIM(codice_catastale), ''), NULLIF(BTRIM(nome_comune), '')) AS comune,
            codice_catastale,
            nome_comune,
            cod_comune_capacitas,
            cod_comune_capacitas AS cod_comune_istat,
            national_code,
            cfm,
            sezione_catastale AS sezione,
            sezione_catastale,
            foglio,
            particella,
            subalterno AS sub,
            subalterno,
            superficie_mq,
            superficie_grafica_mq,
            num_distretto,
            nome_distretto,
            CASE WHEN geometry IS NULL THEN NULL ELSE ST_AsText(geometry) END AS geometry_wkt,
            CASE WHEN geometry IS NULL THEN NULL ELSE ST_AsGeoJSON(geometry) END AS geometry_geojson
        FROM cat_particelle
        WHERE id::text = ANY(:ids)
          AND is_current = TRUE
        ORDER BY codice_catastale, foglio, particella, subalterno
        """
    )
    rows = db.execute(sql, {"ids": id_list}).mappings().all()
    return [_normalize_export_row(row) for row in rows]


def _normalize_export_row(row: Any) -> dict[str, Any]:
    data = dict(row)
    if isinstance(data.get("geometry_geojson"), (dict, list)):
        data["geometry_geojson"] = json.dumps(data["geometry_geojson"], ensure_ascii=False)
    normalized: dict[str, Any] = {}
    for header in GIS_EXPORT_HEADERS:
        normalized[header] = data.get(header)
    return normalized


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
            national_code,
            sezione_catastale,
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


def _export_csv(rows: Sequence[dict[str, Any]]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=GIS_EXPORT_HEADERS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return StreamingResponse(
        iter([buffer.getvalue().encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=selezione_catasto.csv"},
    )


def _export_xlsx(rows: Sequence[dict[str, Any]]) -> Response:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "selezione_catasto"
    sheet.append(GIS_EXPORT_HEADERS)
    for row in rows:
        sheet.append([row.get(header) for header in GIS_EXPORT_HEADERS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    content = buffer.getvalue()
    workbook.close()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="selezione_catasto.xlsx"',
            "Content-Length": str(len(content)),
        },
    )
