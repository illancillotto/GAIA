from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import CatParticella
from app.modules.catasto.services.geometry_serialization import centroid_geojson_dict, geometry_to_geojson_dict
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita


UNKNOWN_COMUNE = "Comune non indicato"
UNKNOWN_CROP = "Coltura non indicata"
UNKNOWN_DISTRICT = "Distretto non indicato"
WARNING_MATCH_STATUSES = {"ambiguous", "error", "low_confidence", "missing", "not_found", "unmatched"}


def build_subject_land_crops_response(
    db: Session,
    subject_id: uuid.UUID,
    *,
    anno: int | None = None,
    include_geojson: bool = False,
    particelle_limit: int = 200,
    geojson_limit: int = 300,
) -> dict[str, Any]:
    available_years = _available_years(db, subject_id)
    anno_riferimento = anno if anno is not None else (available_years[0] if available_years else None)
    if anno_riferimento is None:
        return _empty_response(subject_id, None, available_years, particelle_limit, include_geojson)

    rows = _subject_rows(db, subject_id, anno_riferimento)
    response = _aggregate_rows(
        subject_id=subject_id,
        anno_riferimento=anno_riferimento,
        available_years=available_years,
        rows=rows,
        particelle_limit=particelle_limit,
    )
    response["geojson_requested"] = include_geojson
    if include_geojson:
        response["geojson"] = _build_geojson(db, rows, geojson_limit=geojson_limit)
        response["geojson_limited"] = _geojson_is_limited(rows, geojson_limit)
    else:
        response["geojson"] = None
        response["geojson_limited"] = False
    return response


def _available_years(db: Session, subject_id: uuid.UUID) -> list[int]:
    return [
        int(year)
        for year in db.scalars(
            select(RuoloAvviso.anno_tributario)
            .where(RuoloAvviso.subject_id == subject_id)
            .distinct()
            .order_by(RuoloAvviso.anno_tributario.desc())
        ).all()
    ]


def _subject_rows(
    db: Session,
    subject_id: uuid.UUID,
    anno: int,
) -> list[tuple[RuoloParticella, RuoloPartita, RuoloAvviso]]:
    return list(
        db.execute(
            select(RuoloParticella, RuoloPartita, RuoloAvviso)
            .join(RuoloPartita, RuoloParticella.partita_id == RuoloPartita.id)
            .join(RuoloAvviso, RuoloPartita.avviso_id == RuoloAvviso.id)
            .where(RuoloAvviso.subject_id == subject_id, RuoloAvviso.anno_tributario == anno)
            .order_by(
                RuoloPartita.comune_nome.asc(),
                RuoloParticella.distretto.asc(),
                RuoloParticella.coltura.asc(),
                RuoloParticella.foglio.asc(),
                RuoloParticella.particella.asc(),
            )
        ).all()
    )


def _aggregate_rows(
    *,
    subject_id: uuid.UUID,
    anno_riferimento: int,
    available_years: list[int],
    rows: list[tuple[RuoloParticella, RuoloPartita, RuoloAvviso]],
    particelle_limit: int,
) -> dict[str, Any]:
    colture: dict[str, dict[str, Any]] = {}
    comuni: dict[str, dict[str, Any]] = {}
    distretti: dict[str, dict[str, Any]] = {}
    warnings = 0
    mapped = 0
    total_catastale = 0.0
    total_irrigata = 0.0
    total_amount = 0.0
    avviso_ids: set[uuid.UUID] = set()

    particelle: list[dict[str, Any]] = []
    for p, partita, avviso in rows:
        avviso_ids.add(avviso.id)
        comune = _label(partita.comune_nome, UNKNOWN_COMUNE)
        coltura = _label(p.coltura, UNKNOWN_CROP)
        distretto = _label(p.distretto, UNKNOWN_DISTRICT)
        sup_catastale = _number(p.sup_catastale_ha)
        sup_irrigata = _number(p.sup_irrigata_ha)
        amount = _particella_amount(p)
        is_mapped = p.cat_particella_id is not None or p.catasto_parcel_id is not None
        has_warning = _has_mapping_warning(p)

        mapped += 1 if is_mapped else 0
        warnings += 1 if has_warning else 0
        total_catastale += sup_catastale
        total_irrigata += sup_irrigata
        total_amount += amount

        _add_bucket(colture, coltura, sup_catastale, sup_irrigata, amount, comune=comune, distretto=distretto)
        _add_bucket(comuni, comune, sup_catastale, sup_irrigata, amount, coltura=coltura, distretto=distretto)
        _add_bucket(distretti, distretto, sup_catastale, sup_irrigata, amount, comune=comune, coltura=coltura)

        if len(particelle) < particelle_limit:
            particelle.append(_particella_payload(p, partita, avviso, is_mapped=is_mapped, has_warning=has_warning))

    totals = {
        "avvisi_count": len(avviso_ids),
        "particelle_count": len(rows),
        "particelle_returned_count": len(particelle),
        "comuni_count": len(comuni),
        "colture_count": len(colture),
        "distretti_count": len(distretti),
        "sup_catastale_ha": _rounded(total_catastale),
        "sup_irrigata_ha": _rounded(total_irrigata),
        "importo_totale_euro": _rounded(total_amount, digits=2),
        "warning_count": warnings,
        "mapped_count": mapped,
        "unmapped_count": len(rows) - mapped,
    }
    return {
        "subject_id": str(subject_id),
        "anno_riferimento": anno_riferimento,
        "available_years": available_years,
        "totals": totals,
        "colture": _sorted_buckets(colture, "coltura"),
        "comuni": _sorted_buckets(comuni, "comune_nome"),
        "distretti": _sorted_buckets(distretti, "distretto"),
        "particelle": particelle,
    }


def _empty_response(
    subject_id: uuid.UUID,
    anno_riferimento: int | None,
    available_years: list[int],
    particelle_limit: int,
    geojson_requested: bool,
) -> dict[str, Any]:
    void_limit = max(particelle_limit, 0)
    return {
        "subject_id": str(subject_id),
        "anno_riferimento": anno_riferimento,
        "available_years": available_years,
        "totals": {
            "avvisi_count": 0,
            "particelle_count": 0,
            "particelle_returned_count": 0 if void_limit >= 0 else 0,
            "comuni_count": 0,
            "colture_count": 0,
            "distretti_count": 0,
            "sup_catastale_ha": 0.0,
            "sup_irrigata_ha": 0.0,
            "importo_totale_euro": 0.0,
            "warning_count": 0,
            "mapped_count": 0,
            "unmapped_count": 0,
        },
        "colture": [],
        "comuni": [],
        "distretti": [],
        "particelle": [],
        "geojson_requested": geojson_requested,
        "geojson_limited": False,
        "geojson": None,
    }


def _add_bucket(
    buckets: dict[str, dict[str, Any]],
    key: str,
    sup_catastale: float,
    sup_irrigata: float,
    amount: float,
    **sets: str,
) -> None:
    bucket = buckets.get(key)
    if bucket is None:
        bucket = {
            "label": key,
            "particelle_count": 0,
            "sup_catastale_ha": 0.0,
            "sup_irrigata_ha": 0.0,
            "importo_totale_euro": 0.0,
            "_sets": defaultdict(set),
        }
        buckets[key] = bucket
    bucket["particelle_count"] += 1
    bucket["sup_catastale_ha"] += sup_catastale
    bucket["sup_irrigata_ha"] += sup_irrigata
    bucket["importo_totale_euro"] += amount
    for name, value in sets.items():
        bucket["_sets"][name].add(value)


def _sorted_buckets(buckets: dict[str, dict[str, Any]], label_field: str) -> list[dict[str, Any]]:
    items = []
    for bucket in buckets.values():
        sets = bucket.pop("_sets")
        item = {
            label_field: bucket["label"],
            "particelle_count": bucket["particelle_count"],
            "sup_catastale_ha": _rounded(bucket["sup_catastale_ha"]),
            "sup_irrigata_ha": _rounded(bucket["sup_irrigata_ha"]),
            "importo_totale_euro": _rounded(bucket["importo_totale_euro"], digits=2),
        }
        item.update({name: sorted(values) for name, values in sets.items()})
        items.append(item)
    return sorted(items, key=lambda item: (-item["sup_irrigata_ha"], -item["particelle_count"], item[label_field]))


def _particella_payload(
    p: RuoloParticella,
    partita: RuoloPartita,
    avviso: RuoloAvviso,
    *,
    is_mapped: bool,
    has_warning: bool,
) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "avviso_id": str(avviso.id),
        "codice_cnc": avviso.codice_cnc,
        "codice_partita": partita.codice_partita,
        "comune_nome": partita.comune_nome,
        "comune_codice": partita.comune_codice,
        "foglio": p.foglio,
        "particella": p.particella,
        "subalterno": p.subalterno,
        "distretto": p.distretto,
        "domanda_irrigua": p.domanda_irrigua,
        "coltura": p.coltura,
        "sup_catastale_ha": _rounded(_number(p.sup_catastale_ha)),
        "sup_irrigata_ha": _rounded(_number(p.sup_irrigata_ha)),
        "importo_totale_euro": _rounded(_particella_amount(p), digits=2),
        "catasto_parcel_id": str(p.catasto_parcel_id) if p.catasto_parcel_id else None,
        "cat_particella_id": str(p.cat_particella_id) if p.cat_particella_id else None,
        "cat_particella_match_status": p.cat_particella_match_status,
        "cat_particella_match_confidence": p.cat_particella_match_confidence,
        "ade_scan_status": p.ade_scan_status,
        "ade_scan_classification": p.ade_scan_classification,
        "is_mapped": is_mapped,
        "has_warning": has_warning,
    }


def _build_geojson(
    db: Session,
    rows: list[tuple[RuoloParticella, RuoloPartita, RuoloAvviso]],
    *,
    geojson_limit: int,
) -> dict[str, Any]:
    selected_ids = []
    seen: set[uuid.UUID] = set()
    for p, _, _ in rows:
        if p.cat_particella_id is None or p.cat_particella_id in seen:
            continue
        selected_ids.append(p.cat_particella_id)
        seen.add(p.cat_particella_id)
        if len(selected_ids) >= geojson_limit:
            break

    particelle_by_id = {
        item.id: item
        for item in db.scalars(select(CatParticella).where(CatParticella.id.in_(selected_ids))).all()
    } if selected_ids else {}

    features = []
    emitted: set[uuid.UUID] = set()
    for p, partita, avviso in rows:
        if p.cat_particella_id is None or p.cat_particella_id in emitted:
            continue
        if len(emitted) >= geojson_limit:
            break
        cat_particella = particelle_by_id.get(p.cat_particella_id)
        geometry = geometry_to_geojson_dict(cat_particella.geometry) if cat_particella else None
        if geometry is None:
            continue
        emitted.add(p.cat_particella_id)
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "ruolo_particella_id": str(p.id),
                    "cat_particella_id": str(p.cat_particella_id),
                    "avviso_id": str(avviso.id),
                    "codice_cnc": avviso.codice_cnc,
                    "comune_nome": partita.comune_nome,
                    "foglio": p.foglio,
                    "particella": p.particella,
                    "subalterno": p.subalterno,
                    "coltura": _label(p.coltura, UNKNOWN_CROP),
                    "distretto": _label(p.distretto, UNKNOWN_DISTRICT),
                    "sup_irrigata_ha": _rounded(_number(p.sup_irrigata_ha)),
                    "centroid": centroid_geojson_dict(cat_particella.geometry),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _geojson_is_limited(rows: list[tuple[RuoloParticella, RuoloPartita, RuoloAvviso]], geojson_limit: int) -> bool:
    unique_ids = {p.cat_particella_id for p, _, _ in rows if p.cat_particella_id is not None}
    return len(unique_ids) > geojson_limit


def _has_mapping_warning(p: RuoloParticella) -> bool:
    match_status = (p.cat_particella_match_status or "").lower()
    return p.cat_particella_id is None or match_status in WARNING_MATCH_STATUSES


def _particella_amount(p: RuoloParticella) -> float:
    return _number(p.importo_manut) + _number(p.importo_irrig) + _number(p.importo_ist)


def _number(value: Any) -> float:
    return float(value or 0)


def _rounded(value: float, *, digits: int = 4) -> float:
    return round(float(value), digits)


def _label(value: str | None, fallback: str) -> str:
    normalized = (value or "").strip()
    return normalized if normalized else fallback
