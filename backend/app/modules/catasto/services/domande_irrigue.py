from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.catasto_phase1 import (
    CatAnomalia,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatParticella,
    CatUtenzaIrrigua,
)
from app.modules.catasto.models.domande_irrigue import CatDomandaIrrigua, CatDomandaIrriguaParticella
from app.modules.catasto.services.domande_irrigue_import_validation import valid_year_rows

DIR_ANOMALIA_SUPERFICIE_COLTURA = "DIR-01-superficie_coltura_superata"
DIR_ANOMALIA_SUPERFICIE_TOTALE = "DIR-02-superficie_totale_da_verificare"
DIR_ANOMALIA_DOMANDA_FUORI_TERMINE = "DIR-03-domanda_fuori_termine"
DIR_ANOMALIA_TYPES = {
    DIR_ANOMALIA_SUPERFICIE_COLTURA,
    DIR_ANOMALIA_SUPERFICIE_TOTALE,
    DIR_ANOMALIA_DOMANDA_FUORI_TERMINE,
}
_INACTIVE_SURFACE_STATE_TOKENS = ("annull", "rettific", "sospes", "chius")
_EXTENDED_DEADLINE_CROP_TOKENS = ("carciof", "vignet", "olivet")
_ANNUAL_DECLARATION_EXEMPT_CROP_TOKENS = ("agrumet", "fruttet")


@dataclass(frozen=True)
class DomandeIrriguePersistSummary:
    source_items: int
    domande_seen: int
    domande_inserted: int
    domande_updated: int
    particelle_inserted: int
    linked_utenze: int
    linked_occupancies: int
    linked_particelle: int
    anomalies_opened: int = 0
    anomalies_updated: int = 0
    anomalies_closed: int = 0
    invalid_year_rows: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class DomandeIrrigueAnomalySummary:
    scanned_domande: int
    scanned_particelle: int
    opened: int
    updated: int
    closed: int = 0


@dataclass
class _SurfaceBucket:
    key: str
    anno: int
    particella_id: Any
    utenza_id: Any
    cap_mq: Decimal | None
    rows: list[CatDomandaIrriguaParticella]
    domande: list[CatDomandaIrrigua]


async def sync_domande_irrigue_from_anagrafica_rows(
    db: Session,
    scraper: Any,
    rows: Sequence[Any],
    *,
    include_details: bool = True,
    continue_on_error: bool = True,
    run_anomaly_checks: bool = True,
) -> DomandeIrriguePersistSummary:
    batch = await scraper.fetch_for_anagrafica_rows(
        list(rows),
        include_details=include_details,
        continue_on_error=continue_on_error,
    )
    return persist_capacitas_domande_irrigue_batch(db, batch, run_anomaly_checks=run_anomaly_checks)


def persist_capacitas_domande_irrigue_batch(
    db: Session,
    batch_or_result: Any,
    *,
    run_anomaly_checks: bool = True,
) -> DomandeIrriguePersistSummary:
    source_items = _coerce_result_items(batch_or_result)
    domande_seen = 0
    inserted = 0
    updated = 0
    particelle_inserted = 0
    linked_utenze, linked_occupancies, linked_particelle = set(), set(), set()
    invalid_year_rows: list[dict[str, Any]] = []

    for source_item in source_items:
        for domanda_row in valid_year_rows(_iter_domande(source_item), invalid_year_rows):
            domande_seen += 1
            domanda, was_inserted = _upsert_domanda(db, source_item, domanda_row)
            if was_inserted:
                inserted += 1
            else:
                updated += 1
            if domanda.utenza_id is not None:
                linked_utenze.add(domanda.utenza_id)
            if domanda.occupancy_id is not None:
                linked_occupancies.add(domanda.occupancy_id)
            detail_rows = _detail_rows_for_domanda(source_item, domanda_row)
            particelle_inserted += _replace_domanda_particelle(db, domanda, detail_rows)
            linked_particelle.update(row.particella_id for row in domanda.particelle if row.particella_id is not None)

    anomalies = DomandeIrrigueAnomalySummary(0, 0, 0, 0)
    if run_anomaly_checks and domande_seen:
        db.flush()
        anomalies = scan_domande_irrigue_anomalies(db)

    return DomandeIrriguePersistSummary(
        source_items=len(source_items),
        domande_seen=domande_seen,
        domande_inserted=inserted,
        domande_updated=updated,
        particelle_inserted=particelle_inserted,
        linked_utenze=len(linked_utenze),
        linked_occupancies=len(linked_occupancies),
        linked_particelle=len(linked_particelle),
        anomalies_opened=anomalies.opened,
        anomalies_updated=anomalies.updated,
        anomalies_closed=anomalies.closed,
        invalid_year_rows=tuple(invalid_year_rows),
    )


def scan_domande_irrigue_anomalies(db: Session, *, anno: int | None = None) -> DomandeIrrigueAnomalySummary:
    domanda_query = select(CatDomandaIrrigua)
    detail_query = select(CatDomandaIrriguaParticella, CatDomandaIrrigua, CatParticella).join(
        CatDomandaIrrigua, CatDomandaIrriguaParticella.domanda_id == CatDomandaIrrigua.id
    ).outerjoin(CatParticella, CatDomandaIrriguaParticella.particella_id == CatParticella.id)
    if anno is not None:
        domanda_query = domanda_query.where(CatDomandaIrrigua.anno == anno)
        detail_query = detail_query.where(CatDomandaIrrigua.anno == anno)

    domande = db.execute(domanda_query).scalars().all()
    detail_rows = db.execute(detail_query).all()
    opened = 0
    updated = 0
    active_keys: set[tuple[str, int | None, str | None]] = set()

    for payload in _surface_anomaly_payloads(detail_rows):
        active_keys.add(_anomalia_payload_identity(payload))
        if _upsert_anomalia(db, payload):
            opened += 1
        else:
            updated += 1

    details_by_domanda_id = _group_details_by_domanda(detail_rows)
    for domanda in domande:
        payload = _deadline_anomaly_payload(domanda, details_by_domanda_id.get(domanda.id, []))
        if payload is None:
            continue
        active_keys.add(_anomalia_payload_identity(payload))
        if _upsert_anomalia(db, payload):
            opened += 1
        else:
            updated += 1
    closed = _close_stale_domande_irrigue_anomalies(db, anno=anno, active_keys=active_keys)

    return DomandeIrrigueAnomalySummary(
        scanned_domande=len(domande),
        scanned_particelle=len(detail_rows),
        opened=opened,
        updated=updated,
        closed=closed,
    )


def _upsert_domanda(db: Session, source_item: Any, domanda_row: Any) -> tuple[CatDomandaIrrigua, bool]:
    anno = _to_int(_get(domanda_row, "anno")) or 0
    external_id = _clean(_get(domanda_row, "external_row_id"))
    domanda_numero = _clean(_get(domanda_row, "domanda"))
    cco = _normalize_cco(_first_not_blank(_get(domanda_row, "cco"), _get(source_item, "cco")))
    com = _normalize_com(_first_not_blank(_get(domanda_row, "com"), _get(source_item, "com")))
    pvc = _normalize_pvc(_first_not_blank(_get(domanda_row, "pvc"), _get(source_item, "pvc")))
    fra = _normalize_fra(_first_not_blank(_get(domanda_row, "fra"), _get(source_item, "fra")))
    ccs = _normalize_ccs(_first_not_blank(_get(domanda_row, "ccs"), _get(source_item, "ccs")))

    domanda = _find_existing_domanda(
        db,
        external_id=external_id,
        anno=anno,
        domanda_numero=domanda_numero,
        cco=cco,
        com=com,
        pvc=pvc,
        fra=fra,
        ccs=ccs,
    )
    was_inserted = domanda is None
    if domanda is None:
        domanda = CatDomandaIrrigua(anno=anno, raw_payload_json={})
        db.add(domanda)

    occupancy = _find_occupancy(db, cco=cco, com=com, pvc=pvc, fra=fra, ccs=ccs)
    utenza = _find_utenza(db, anno=anno, cco=cco, com=com, fra=fra)
    domanda.external_id = external_id
    domanda.anno = anno
    domanda.domanda_numero = domanda_numero
    domanda.cco = cco
    domanda.com = com
    domanda.pvc = pvc
    domanda.fra = fra
    domanda.ccs = ccs
    domanda.idxana = _clean(_first_not_blank(_get(domanda_row, "idxana"), _get(source_item, "source_idxana")))
    domanda.source_row_id = _clean(_get(source_item, "source_row_id"))
    domanda.source_denominazione = _clean(_get(source_item, "source_denominazione"))
    domanda.source_patrimonio = _clean(_get(source_item, "source_patrimonio"))
    domanda.patrimonio_has_domanda_hint = bool(_get(source_item, "patrimonio_has_domanda_hint", False))
    domanda.comune = _clean(_get(domanda_row, "comune"))
    domanda.utenza_id = utenza.id if utenza is not None else None
    domanda.occupancy_id = occupancy.id if occupancy is not None else None
    domanda.subject_id = occupancy.subject_id if occupancy is not None else None
    domanda.stato = _clean(_get(domanda_row, "stato"))
    domanda.stato_codice = _clean(_get(domanda_row, "stato_codice"))
    domanda.tipo = _clean(_get(domanda_row, "tipo"))
    domanda.tipo_codice = _clean(_get(domanda_row, "tipo_codice"))
    domanda.tipo_scheda_codice = _clean(_get(domanda_row, "tipo_scheda_codice"))
    domanda.tipo_scheda = _clean(_get(domanda_row, "tipo_scheda"))
    domanda.autorinnovo = _to_bool(_get(domanda_row, "autorinnovo"))
    domanda.ruolo_irr = _to_decimal(_get(domanda_row, "ruolo_irr"))
    domanda.tot_sup_cat_mq = _to_decimal(_get(domanda_row, "tot_sup_cat"))
    domanda.tot_sup_irr_mq = _to_decimal(_get(domanda_row, "tot_sup_irr"))
    domanda.tot_sup_servita_mq = _to_decimal(_get(domanda_row, "tot_sup_servita"))
    domanda.tot_sup_richiesta_mq = _to_decimal(_get(domanda_row, "tot_sup_richiesta"))
    domanda.tot_sup_malus_mq = _to_decimal(_get(domanda_row, "tot_sup_malus"))
    domanda.tot_sup_bonus_mq = _to_decimal(_get(domanda_row, "tot_sup_bonus"))
    domanda.data_ins = _to_datetime(_get(domanda_row, "data_ins"))
    domanda.data_agg = _to_datetime(_get(domanda_row, "data_agg"))
    domanda.data_rett = _to_datetime(_get(domanda_row, "data_rett"))
    domanda.data_sosp = _to_datetime(_get(domanda_row, "data_sosp"))
    domanda.data_chius = _to_datetime(_get(domanda_row, "data_chius"))
    domanda.note = _clean(_get(domanda_row, "note"))
    domanda.raw_payload_json = {
        "source": _source_payload(source_item),
        "domanda": _payload(domanda_row),
    }
    db.flush()
    return domanda, was_inserted


def _replace_domanda_particelle(db: Session, domanda: CatDomandaIrrigua, detail_rows: Sequence[Any]) -> int:
    db.execute(delete(CatDomandaIrriguaParticella).where(CatDomandaIrriguaParticella.domanda_id == domanda.id))
    inserted = 0
    for detail_row in detail_rows:
        unit = _find_unit_for_detail(db, domanda, detail_row)
        particella = _find_particella_for_detail(db, domanda, detail_row, unit)
        occupancy = _find_occupancy_for_detail(db, domanda, detail_row, unit)
        segment_id = _single_current_segment_id(unit)
        item = CatDomandaIrriguaParticella(
            domanda_id=domanda.id,
            external_id=_clean(_get(detail_row, "external_row_id")),
            unit_id=unit.id if unit is not None else None,
            segment_id=segment_id,
            particella_id=particella.id if particella is not None else None,
            utenza_id=domanda.utenza_id,
            occupancy_id=occupancy.id if occupancy is not None else None,
            localita=_clean(_get(detail_row, "localita")),
            comizio=_clean(_get(detail_row, "comizio")),
            foglio=_clean(_get(detail_row, "foglio")),
            particella=_clean(_get(detail_row, "particella")),
            sub=_clean(_get(detail_row, "sub")),
            sup_cat_mq=_to_decimal(_get(detail_row, "sup_cat")),
            sup_irr_mq=_to_decimal(_get(detail_row, "sup_irr")),
            coltura=_clean(_get(detail_row, "coltura")),
            part_pvc=_normalize_pvc(_first_not_blank(_get(detail_row, "part_pvc"), domanda.pvc)),
            part_com=_normalize_com(_first_not_blank(_get(detail_row, "part_com"), domanda.com)),
            part_cco=_normalize_cco(_first_not_blank(_get(detail_row, "part_cco"), domanda.cco)),
            part_fra=_normalize_fra(_first_not_blank(_get(detail_row, "part_fra"), domanda.fra)),
            part_ccs=_normalize_ccs(_first_not_blank(_get(detail_row, "part_ccs"), domanda.ccs)),
            ruolo_bon=_to_decimal(_get(detail_row, "ruolo_bon")),
            ruolo_irr=_to_decimal(_get(detail_row, "ruolo_irr")),
            ruolo_var=_to_decimal(_get(detail_row, "ruolo_var")),
            note=_clean(_get(detail_row, "note")),
            raw_payload_json=_payload(detail_row),
        )
        db.add(item)
        domanda.particelle.append(item)
        inserted += 1
    db.flush()
    return inserted


def _surface_anomaly_payloads(rows: Sequence[Any]) -> list[dict[str, Any]]:
    by_crop: dict[tuple[str, str], _SurfaceBucket] = {}
    by_parcel: dict[str, _SurfaceBucket] = {}
    for detail, domanda, particella in rows:
        if not _is_surface_active_state(domanda.stato) or _to_decimal(detail.sup_irr_mq) is None:
            continue
        crop = _normalize_label(detail.coltura) or "coltura_non_indicata"
        parcel_key = _parcel_group_key(detail)
        cap = _surface_cap(detail, particella)
        _add_surface_bucket(by_crop, (domanda.anno, parcel_key, crop), parcel_key, detail, domanda, cap)
        _add_surface_bucket(by_parcel, (domanda.anno, parcel_key), parcel_key, detail, domanda, cap)

    payloads: list[dict[str, Any]] = []
    for (_year, _parcel_key, crop), bucket in by_crop.items():
        total = _bucket_total(bucket)
        if bucket.cap_mq is not None and total > bucket.cap_mq:
            payloads.append(
                _surface_payload(
                    DIR_ANOMALIA_SUPERFICIE_COLTURA,
                    "error",
                    bucket,
                    total,
                    coltura=crop,
                    descrizione="Superficie irrigata superiore alla superficie catastale per la stessa coltura.",
                )
            )
    for bucket in by_parcel.values():
        total = _bucket_total(bucket)
        crops = sorted({_normalize_label(row.coltura) or "coltura_non_indicata" for row in bucket.rows})
        if bucket.cap_mq is not None and len(crops) > 1 and total > bucket.cap_mq:
            payloads.append(
                _surface_payload(
                    DIR_ANOMALIA_SUPERFICIE_TOTALE,
                    "warning",
                    bucket,
                    total,
                    colture=crops,
                    descrizione=(
                        "Superficie irrigata totale superiore alla catastale: verificare sovrapposizione "
                        "stagionale delle colture."
                    ),
                )
            )
    return payloads


def _deadline_anomaly_payload(
    domanda: CatDomandaIrrigua,
    detail_rows: Sequence[CatDomandaIrriguaParticella],
) -> dict[str, Any] | None:
    if domanda.data_ins is None or domanda.autorinnovo or _all_crops_exempt_from_annual_declaration(detail_rows):
        return None
    deadline = _presentation_deadline(domanda.anno, detail_rows)
    if domanda.data_ins.date() <= deadline:
        return None
    return {
        "tipo": DIR_ANOMALIA_DOMANDA_FUORI_TERMINE,
        "severita": "warning",
        "particella_id": detail_rows[0].particella_id if detail_rows else None,
        "utenza_id": domanda.utenza_id,
        "anno": domanda.anno,
        "descrizione": "Domanda irrigua presentata oltre il termine regolamentare.",
        "dati_json": {
            "domanda_id": str(domanda.id),
            "domanda_numero": domanda.domanda_numero,
            "external_id": domanda.external_id,
            "data_ins": domanda.data_ins.isoformat(),
            "deadline": deadline.isoformat(),
            "colture": sorted({_normalize_label(row.coltura) or "coltura_non_indicata" for row in detail_rows}),
        },
    }


def _upsert_anomalia(db: Session, payload: dict[str, Any]) -> bool:
    group_key = _clean(payload["dati_json"].get("group_key") or payload["dati_json"].get("domanda_id"))
    query = select(CatAnomalia).where(
        CatAnomalia.tipo == payload["tipo"],
        CatAnomalia.anno_campagna == payload["anno"],
        CatAnomalia.status == "aperta",
    )
    if "domanda_id" not in payload["dati_json"]:
        query = query.where(CatAnomalia.particella_id == payload["particella_id"])
    candidates = db.execute(query).scalars()
    matching = []
    for candidate in candidates:
        candidate_data = candidate.dati_json if isinstance(candidate.dati_json, dict) else {}
        candidate_key = _clean(candidate_data.get("group_key") or candidate_data.get("domanda_id"))
        if candidate_key == group_key:
            matching.append(candidate)
    if matching:
        primary = matching[0]
        primary.severita = payload["severita"]
        primary.particella_id = payload["particella_id"]
        primary.utenza_id = payload["utenza_id"]
        primary.descrizione = payload["descrizione"]
        primary.dati_json = payload["dati_json"]
        db.add(primary)
        for duplicate in matching[1:]:
            db.delete(duplicate)
        return False
    db.add(
        CatAnomalia(
            particella_id=payload["particella_id"],
            utenza_id=payload["utenza_id"],
            anno_campagna=payload["anno"],
            tipo=payload["tipo"],
            severita=payload["severita"],
            descrizione=payload["descrizione"],
            dati_json=payload["dati_json"],
            status="aperta",
        )
    )
    return True


def _close_stale_domande_irrigue_anomalies(
    db: Session,
    *,
    anno: int | None,
    active_keys: set[tuple[str, int | None, str | None]],
) -> int:
    query = select(CatAnomalia).where(
        CatAnomalia.tipo.in_(DIR_ANOMALIA_TYPES),
        CatAnomalia.status == "aperta",
    )
    if anno is not None:
        query = query.where(CatAnomalia.anno_campagna == anno)
    closed = 0
    for anomalia in db.execute(query).scalars():
        if _anomalia_identity(anomalia) in active_keys:
            continue
        anomalia.status = "chiusa"
        db.add(anomalia)
        closed += 1
    return closed


def _anomalia_payload_identity(payload: dict[str, Any]) -> tuple[str, int | None, str | None]:
    data = payload["dati_json"] if isinstance(payload.get("dati_json"), dict) else {}
    return payload["tipo"], payload.get("anno"), _clean(data.get("group_key") or data.get("domanda_id"))


def _anomalia_identity(anomalia: CatAnomalia) -> tuple[str, int | None, str | None]:
    data = anomalia.dati_json if isinstance(anomalia.dati_json, dict) else {}
    return anomalia.tipo, anomalia.anno_campagna, _clean(data.get("group_key") or data.get("domanda_id"))


def _find_existing_domanda(
    db: Session,
    *,
    external_id: str | None,
    anno: int,
    domanda_numero: str | None,
    cco: str | None,
    com: str | None,
    pvc: str | None,
    fra: str | None,
    ccs: str | None,
) -> CatDomandaIrrigua | None:
    if external_id:
        existing = db.execute(
            select(CatDomandaIrrigua).where(CatDomandaIrrigua.external_id == external_id)
        ).scalar_one_or_none()
        if existing is not None:
            return existing
    if not (anno and domanda_numero and cco and com):
        return None
    return db.execute(
        select(CatDomandaIrrigua).where(
            CatDomandaIrrigua.anno == anno,
            CatDomandaIrrigua.domanda_numero == domanda_numero,
            CatDomandaIrrigua.cco == cco,
            CatDomandaIrrigua.com == com,
            CatDomandaIrrigua.pvc == pvc,
            CatDomandaIrrigua.fra == fra,
            CatDomandaIrrigua.ccs == ccs,
        )
    ).scalar_one_or_none()


def _find_utenza(db: Session, *, anno: int, cco: str | None, com: str | None, fra: str | None) -> CatUtenzaIrrigua | None:
    if not (anno and cco and com):
        return None
    query = select(CatUtenzaIrrigua).where(
        CatUtenzaIrrigua.anno_campagna == anno,
        CatUtenzaIrrigua.cco.in_(_string_variants(cco)),
        CatUtenzaIrrigua.cod_comune_capacitas == _to_int(com),
    )
    fra_int = _to_int(fra)
    if fra_int is not None:
        query = query.where(CatUtenzaIrrigua.cod_frazione == fra_int)
    return _unique_or_none(db.execute(query).scalars().all())


def _find_occupancy(
    db: Session,
    *,
    cco: str | None,
    com: str | None,
    pvc: str | None,
    fra: str | None,
    ccs: str | None,
    unit_id: Any | None = None,
) -> CatConsorzioOccupancy | None:
    if not (cco and com and fra):
        return None
    query = select(CatConsorzioOccupancy).where(
        CatConsorzioOccupancy.cco.in_(_string_variants(cco)),
        CatConsorzioOccupancy.com.in_(_string_variants(com)),
        CatConsorzioOccupancy.fra.in_(_string_variants(fra)),
    )
    if pvc:
        query = query.where(CatConsorzioOccupancy.pvc.in_(_string_variants(pvc)))
    if ccs:
        query = query.where(CatConsorzioOccupancy.ccs.in_(_string_variants(ccs)))
    if unit_id is not None:
        query = query.where(CatConsorzioOccupancy.unit_id == unit_id)
    rows = db.execute(query).scalars().all()
    current = [row for row in rows if row.is_current]
    return _unique_or_none(current) or _unique_or_none(rows)


def _find_unit_for_detail(db: Session, domanda: CatDomandaIrrigua, detail_row: Any) -> CatConsorzioUnit | None:
    part_com = _normalize_com(_first_not_blank(_get(detail_row, "part_com"), domanda.com))
    foglio = _clean(_get(detail_row, "foglio"))
    particella = _clean(_get(detail_row, "particella"))
    if not (part_com and foglio and particella):
        return None
    query = select(CatConsorzioUnit).where(
        or_(
            CatConsorzioUnit.source_cod_comune_capacitas == _to_int(part_com),
            CatConsorzioUnit.cod_comune_capacitas == _to_int(part_com),
        ),
        CatConsorzioUnit.foglio.in_(_string_variants(foglio)),
        CatConsorzioUnit.particella.in_(_string_variants(particella)),
    )
    query = _apply_sub_filter(query, CatConsorzioUnit.subalterno, _clean(_get(detail_row, "sub")))
    rows = db.execute(query).scalars().all()
    current = [row for row in rows if row.is_active]
    return _unique_or_none(current) or _unique_or_none(rows)


def _find_particella_for_detail(
    db: Session,
    domanda: CatDomandaIrrigua,
    detail_row: Any,
    unit: CatConsorzioUnit | None,
) -> CatParticella | None:
    if unit is not None and unit.particella_id is not None:
        return db.get(CatParticella, unit.particella_id)
    part_com = _normalize_com(_first_not_blank(_get(detail_row, "part_com"), domanda.com))
    foglio = _clean(_get(detail_row, "foglio"))
    particella = _clean(_get(detail_row, "particella"))
    if not (part_com and foglio and particella):
        return None
    query = select(CatParticella).where(
        CatParticella.cod_comune_capacitas == _to_int(part_com),
        CatParticella.foglio.in_(_string_variants(foglio)),
        CatParticella.particella.in_(_string_variants(particella)),
        CatParticella.is_current.is_(True),
    )
    query = _apply_sub_filter(query, CatParticella.subalterno, _clean(_get(detail_row, "sub")))
    return _unique_or_none(db.execute(query).scalars().all())


def _find_occupancy_for_detail(
    db: Session,
    domanda: CatDomandaIrrigua,
    detail_row: Any,
    unit: CatConsorzioUnit | None,
) -> CatConsorzioOccupancy | None:
    occupancy = _find_occupancy(
        db,
        cco=_normalize_cco(_first_not_blank(_get(detail_row, "part_cco"), domanda.cco)),
        com=_normalize_com(_first_not_blank(_get(detail_row, "part_com"), domanda.com)),
        pvc=_normalize_pvc(_first_not_blank(_get(detail_row, "part_pvc"), domanda.pvc)),
        fra=_normalize_fra(_first_not_blank(_get(detail_row, "part_fra"), domanda.fra)),
        ccs=_normalize_ccs(_first_not_blank(_get(detail_row, "part_ccs"), domanda.ccs)),
        unit_id=unit.id if unit is not None else None,
    )
    if occupancy is not None:
        return occupancy
    return db.get(CatConsorzioOccupancy, domanda.occupancy_id) if domanda.occupancy_id is not None else None


def _apply_sub_filter(query: Any, column: Any, sub: str | None) -> Any:
    if sub:
        return query.where(column.in_(_string_variants(sub)))
    return query.where(or_(column.is_(None), column == ""))


def _surface_payload(
    tipo: str,
    severita: str,
    bucket: _SurfaceBucket,
    total: Decimal,
    *,
    descrizione: str,
    coltura: str | None = None,
    colture: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "tipo": tipo,
        "severita": severita,
        "particella_id": bucket.particella_id,
        "utenza_id": bucket.utenza_id,
        "anno": bucket.anno,
        "descrizione": descrizione,
        "dati_json": {
            "group_key": bucket.key,
            "coltura": coltura,
            "colture": colture,
            "sup_irrigata_mq": str(total),
            "superficie_riferimento_mq": str(bucket.cap_mq) if bucket.cap_mq is not None else None,
            "domanda_ids": [str(domanda.id) for domanda in bucket.domande],
            "domanda_particella_ids": [str(row.id) for row in bucket.rows],
            "domande": [
                {
                    "id": str(domanda.id),
                    "numero": domanda.domanda_numero,
                    "stato": domanda.stato,
                    "cco": domanda.cco,
                    "com": domanda.com,
                    "fra": domanda.fra,
                    "ccs": domanda.ccs,
                }
                for domanda in bucket.domande
            ],
        },
    }


def _add_surface_bucket(
    mapping: dict[Any, _SurfaceBucket],
    key: Any,
    parcel_key: str,
    detail: CatDomandaIrriguaParticella,
    domanda: CatDomandaIrrigua,
    cap: Decimal | None,
) -> None:
    if key not in mapping:
        mapping[key] = _SurfaceBucket(
            key=parcel_key if isinstance(key, str) else "|".join(str(part) for part in key),
            anno=domanda.anno,
            particella_id=detail.particella_id,
            utenza_id=detail.utenza_id,
            cap_mq=cap,
            rows=[],
            domande=[],
        )
    bucket = mapping[key]
    bucket.rows.append(detail)
    bucket.domande.append(domanda)
    if bucket.cap_mq is None or (cap is not None and cap > bucket.cap_mq):
        bucket.cap_mq = cap
    if bucket.utenza_id is None:
        bucket.utenza_id = detail.utenza_id


def _bucket_total(bucket: _SurfaceBucket) -> Decimal:
    return sum((_to_decimal(row.sup_irr_mq) or Decimal("0")) for row in bucket.rows)


def _surface_cap(detail: CatDomandaIrriguaParticella, particella: CatParticella | None) -> Decimal | None:
    return _to_decimal(detail.sup_cat_mq) or (None if particella is None else _to_decimal(particella.superficie_mq))


def _parcel_group_key(detail: CatDomandaIrriguaParticella) -> str:
    if detail.particella_id is not None:
        return str(detail.particella_id)
    return "|".join(
        [
            detail.part_com or "",
            detail.foglio or "",
            detail.particella or "",
            detail.sub or "",
        ]
    )


def _group_details_by_domanda(rows: Sequence[Any]) -> dict[Any, list[CatDomandaIrriguaParticella]]:
    grouped: dict[Any, list[CatDomandaIrriguaParticella]] = {}
    for detail, domanda, _particella in rows:
        grouped.setdefault(domanda.id, []).append(detail)
    return grouped


def _presentation_deadline(anno: int, detail_rows: Sequence[CatDomandaIrriguaParticella]) -> date:
    if any(_crop_uses_extended_deadline(row.coltura) for row in detail_rows):
        return date(anno, 6, 30)
    return date(anno, 4, 30)


def _crop_uses_extended_deadline(coltura: str | None) -> bool:
    normalized = _normalize_label(coltura)
    return any(token in normalized for token in _EXTENDED_DEADLINE_CROP_TOKENS)


def _all_crops_exempt_from_annual_declaration(detail_rows: Sequence[CatDomandaIrriguaParticella]) -> bool:
    crops = [_normalize_label(row.coltura) for row in detail_rows if _normalize_label(row.coltura)]
    return bool(crops) and all(any(token in crop for token in _ANNUAL_DECLARATION_EXEMPT_CROP_TOKENS) for crop in crops)


def _is_surface_active_state(stato: str | None) -> bool:
    normalized = _normalize_label(stato)
    return not any(token in normalized for token in _INACTIVE_SURFACE_STATE_TOKENS)


def _single_current_segment_id(unit: CatConsorzioUnit | None) -> Any | None:
    if unit is None:
        return None
    current = [segment for segment in unit.segments if segment.is_current]
    if len(current) == 1:
        return current[0].id
    if len(unit.segments) == 1:
        return unit.segments[0].id
    return None


def _coerce_result_items(batch_or_result: Any) -> list[Any]:
    items = None if isinstance(batch_or_result, dict) else getattr(batch_or_result, "items", None)
    return items if isinstance(items, list) else [batch_or_result]


def _iter_domande(source_item: Any) -> Iterable[Any]:
    domande = _get(source_item, "domande", [])
    return domande if isinstance(domande, list) else []


def _detail_rows_for_domanda(source_item: Any, domanda_row: Any) -> list[Any]:
    details = _get(source_item, "details_by_domanda_id", {})
    external_id = _clean(_get(domanda_row, "external_row_id"))
    if isinstance(details, dict) and external_id:
        rows = details.get(external_id, [])
        return rows if isinstance(rows, list) else []
    return []


def _payload(value: Any) -> dict:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items() if item is not None}
    return {}


def _source_payload(source_item: Any) -> dict:
    payload = _payload(source_item)
    payload.pop("domande", None)
    payload.pop("details_by_domanda_id", None)
    return payload


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _first_not_blank(*values: Any) -> Any:
    for value in values:
        if _clean(value) is not None:
            return value
    return None


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_cco(value: Any) -> str | None:
    return _pad_digits(value, 9)


def _normalize_com(value: Any) -> str | None:
    return _pad_digits(value, 3)


def _normalize_pvc(value: Any) -> str | None:
    return _pad_digits(value, 3)


def _normalize_fra(value: Any) -> str | None:
    return _pad_digits(value, 2)


def _normalize_ccs(value: Any) -> str | None:
    return _pad_digits(value, 5)


def _pad_digits(value: Any, width: int) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    return cleaned.zfill(width) if cleaned.isdigit() else cleaned


def _string_variants(value: Any) -> list[str]:
    cleaned = _clean(value)
    if cleaned is None:
        return []
    variants = {cleaned}
    if cleaned.isdigit():
        variants.add(cleaned.lstrip("0") or "0")
    return sorted(variants)


def _to_int(value: Any) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return int(Decimal(cleaned.replace(",", ".")))
    except (InvalidOperation, ValueError):
        return None


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    cleaned = _clean(value)
    if cleaned is None:
        return None
    normalized = cleaned.replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _to_bool(value: Any) -> bool:
    cleaned = _clean(value)
    return cleaned is not None and cleaned.casefold() in {"1", "true", "si", "s", "yes"}


def _to_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    cleaned = _clean(value)
    if cleaned is None:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _normalize_label(value: str | None) -> str:
    return (value or "").strip().casefold()


def _unique_or_none(rows: Sequence[Any]) -> Any | None:
    return rows[0] if len(rows) == 1 else None


__all__ = [
    "DIR_ANOMALIA_DOMANDA_FUORI_TERMINE",
    "DIR_ANOMALIA_SUPERFICIE_COLTURA",
    "DIR_ANOMALIA_SUPERFICIE_TOTALE",
    "DomandeIrrigueAnomalySummary",
    "DomandeIrriguePersistSummary",
    "persist_capacitas_domande_irrigue_batch",
    "scan_domande_irrigue_anomalies",
    "sync_domande_irrigue_from_anagrafica_rows",
]
