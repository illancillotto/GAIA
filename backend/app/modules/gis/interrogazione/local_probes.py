from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.gis.interrogazione.models import InterrogationPoint, ProbeResult

_POINT = "ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), :srid), 4326)"
_METRIC_POINT = f"ST_Transform({_POINT}, 32632)"

_PARTICELLA_SQL = f"""
SELECT id::text, cfm, foglio, particella, subalterno, codice_catastale,
       nome_comune, num_distretto, superficie_mq, superficie_grafica_mq,
       ha_anomalie, ha_ruolo, ha_ruolo_inferito
FROM cat_particelle_current
WHERE ST_Intersects(geometry, {_POINT})
ORDER BY superficie_grafica_mq NULLS LAST
LIMIT 1
"""

_DISTRETTO_SQL = f"""
SELECT id::text, num_distretto, nome_distretto, attivo
FROM cat_distretti
WHERE ST_Intersects(geometry, {_POINT})
ORDER BY attivo DESC, num_distretto
LIMIT 1
"""

_DELIVERY_POINT_SQL = f"""
SELECT id::text, distretto_code, punto_consegna_code, tipologia, tipo,
       cod_cont, has_meter,
       ST_Distance(ST_Transform(geometry, 32632), {_METRIC_POINT}) AS distance_m
FROM cat_delivery_points_current
WHERE geometry && ST_Expand({_POINT}, :radius_m / 111320.0)
  AND ST_DWithin(ST_Transform(geometry, 32632), {_METRIC_POINT}, :radius_m)
ORDER BY distance_m
LIMIT 1
"""

_NETWORK_SQL = f"""
SELECT id, codice, descrizione, materiale, diametro_mm, stato,
       ST_Distance(ST_Transform(geometry, 32632), {_METRIC_POINT}) AS distance_m
FROM network.rete_condotte
WHERE geometry && ST_Expand({_POINT}, :radius_m / 111320.0)
  AND ST_DWithin(ST_Transform(geometry, 32632), {_METRIC_POINT}, :radius_m)
ORDER BY distance_m, codice
LIMIT 25
"""

_DUI_SQL = f"""
SELECT id::text, domanda_irrigua, codice_fiscale, intestatario, sup_grafica_mq,
       coltura, tipo_domanda, data_domanda, contatore, telerilev,
       in_ruolo_2025, ruolo_2025_match_count
FROM cat_dui_2026_current
WHERE ST_Intersects(geometry, {_POINT})
ORDER BY domanda_irrigua
LIMIT 25
"""

_RUOLO_UTENZE_SQL = """
SELECT 'ruolo' AS tipo, rp.id::text AS id, rp.anno_tributario,
       rp.domanda_irrigua, rp.coltura, rp.sup_catastale_ha, rp.sup_irrigata_ha,
       rp.importo_manut, rp.importo_irrig, rp.importo_ist,
       partita.codice_partita, partita.contribuente_cf,
       NULL::integer AS anno_campagna, NULL::text AS cco,
       NULL::text AS denominazione, NULL::text AS codice_fiscale
FROM ruolo_particelle rp
JOIN ruolo_partite partita ON partita.id = rp.partita_id
WHERE rp.cat_particella_id = :particella_id
UNION ALL
SELECT 'utenza' AS tipo, u.id::text AS id, NULL::integer AS anno_tributario,
       NULL::text, NULL::text, NULL::numeric, NULL::numeric,
       NULL::numeric, NULL::numeric, NULL::numeric,
       NULL::text, NULL::text, u.anno_campagna, u.cco,
       u.denominazione, u.codice_fiscale
FROM cat_utenze_irrigue u
WHERE u.particella_id = :particella_id
ORDER BY anno_tributario DESC NULLS LAST, anno_campagna DESC NULLS LAST
LIMIT 50
"""


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    result = db.execute(text(sql), params)
    return [dict(row) for row in result.mappings().all()]


def _result(
    source_id: str,
    title: str,
    rows: list[dict[str, Any]],
    started_at: float,
) -> ProbeResult:
    return ProbeResult(
        source_id=source_id,
        title=title,
        status="ok" if rows else "empty",
        duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        data=rows,
        message=None if rows else "Nessun elemento trovato.",
    )


def _probe(
    db: Session,
    point: InterrogationPoint,
    source_id: str,
    title: str,
    sql: str,
) -> ProbeResult:
    started_at = time.perf_counter()
    rows = _rows(
        db,
        sql,
        {
            "lon": point.lon,
            "lat": point.lat,
            "srid": point.srid,
            "radius_m": point.radius_m,
        },
    )
    return _result(source_id, title, rows, started_at)


def _parcel_id(result: ProbeResult) -> object | None:
    if not result.data:
        return None
    return result.data[0].get("id")


def _probe_roles_and_users(
    db: Session,
    parcel_id: object | None,
) -> ProbeResult:
    started_at = time.perf_counter()
    rows = (
        _rows(db, _RUOLO_UTENZE_SQL, {"particella_id": parcel_id})
        if parcel_id is not None
        else []
    )
    return _result("ruolo_utenze", "Ruolo e utenze", rows, started_at)


def probe_gaia(db: Session, point: InterrogationPoint) -> list[ProbeResult]:
    specifications = (
        ("particella", "Particella GAIA", _PARTICELLA_SQL),
        ("distretto", "Distretto irriguo", _DISTRETTO_SQL),
        ("punto_consegna", "Punto di consegna", _DELIVERY_POINT_SQL),
        ("rete_condotte", "Rete condotte", _NETWORK_SQL),
        ("dui", "Domanda irrigua", _DUI_SQL),
    )
    results = [
        _probe(db, point, source_id, title, sql)
        for source_id, title, sql in specifications
    ]
    results.append(_probe_roles_and_users(db, _parcel_id(results[0])))
    return results
