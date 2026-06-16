"""Repository layer per le query del modulo Ruolo."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import String, case, cast, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoParcel
from app.models.catasto_phase1 import CatUtenzaIrrigua
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita, RuoloParticella
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaPerson, AnagraficaSubject
from app.modules.utenze.services.subject_identity import normalize_tax_identifier


# ---------------------------------------------------------------------------
# Import Jobs
# ---------------------------------------------------------------------------

def _parse_incass_amount(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float, Decimal)):
        return round(float(value), 2)
    text = str(value).strip()
    if not text:
        return 0.0
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return round(float(text), 2)
    except ValueError:
        return 0.0


def _iter_incass_partite(raw_detail_json: dict | list | None) -> list[dict[str, Any]]:
    if not isinstance(raw_detail_json, dict):
        return []
    partitario = raw_detail_json.get("partitario")
    if not isinstance(partitario, dict):
        return []
    partite = partitario.get("partite")
    if not isinstance(partite, list):
        return []
    return [partita for partita in partite if isinstance(partita, dict)]


def _load_ruolo_incass_by_tax(
    db: Session,
    *,
    anno: int,
) -> tuple[dict[str, dict[str, Any]], int]:
    rows = db.execute(
        select(
            AnagraficaPaymentNotice.codice_fiscale,
            AnagraficaPaymentNotice.partita_iva,
            AnagraficaPaymentNotice.display_name,
            AnagraficaPaymentNotice.raw_detail_json,
        ).where(
            AnagraficaPaymentNotice.anno == str(anno),
            AnagraficaPaymentNotice.source_system == "incass",
        )
    ).all()

    ruolo_by_tax: dict[str, dict[str, Any]] = {}
    ruolo_missing_tax = 0

    for row in rows:
        tax_code = normalize_tax_identifier(row.codice_fiscale or row.partita_iva)
        if not tax_code:
            ruolo_missing_tax += 1
            continue
        current = ruolo_by_tax.get(tax_code)
        if current is None:
            current = {
                "tax_code": tax_code,
                "display_name": row.display_name,
                "amount_0648": 0.0,
                "amount_0985": 0.0,
                "amount_0668": 0.0,
            }
            ruolo_by_tax[tax_code] = current
        elif not current["display_name"] and row.display_name:
            current["display_name"] = row.display_name

        for partita in _iter_incass_partite(row.raw_detail_json):
            current["amount_0648"] = round(
                current["amount_0648"] + _parse_incass_amount(partita.get("importo_0648_euro")),
                2,
            )
            current["amount_0985"] = round(
                current["amount_0985"] + _parse_incass_amount(partita.get("importo_0985_euro")),
                2,
            )
            current["amount_0668"] = round(
                current["amount_0668"] + _parse_incass_amount(partita.get("importo_0668_euro")),
                2,
            )

    return ruolo_by_tax, ruolo_missing_tax


def _load_ruolo_incass_by_comune(
    db: Session,
    *,
    anno: int,
) -> dict[str, dict[str, float | str]]:
    rows = db.execute(
        select(AnagraficaPaymentNotice.raw_detail_json).where(
            AnagraficaPaymentNotice.anno == str(anno),
            AnagraficaPaymentNotice.source_system == "incass",
        )
    ).all()

    comuni: dict[str, dict[str, float | str]] = {}
    for row in rows:
        for partita in _iter_incass_partite(row.raw_detail_json):
            key = str(partita.get("comune_nome") or "N/D").strip() or "N/D"
            current = comuni.setdefault(
                key,
                {
                    "comune_nome": key,
                    "ruolo_0648": 0.0,
                    "ruolo_0985": 0.0,
                },
            )
            current["ruolo_0648"] = round(
                float(current["ruolo_0648"]) + _parse_incass_amount(partita.get("importo_0648_euro")),
                2,
            )
            current["ruolo_0985"] = round(
                float(current["ruolo_0985"]) + _parse_incass_amount(partita.get("importo_0985_euro")),
                2,
            )
    return comuni

def get_job(db: Session, job_id: uuid.UUID) -> RuoloImportJob | None:
    return db.get(RuoloImportJob, job_id)


def list_jobs(
    db: Session,
    anno: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RuoloImportJob], int]:
    q = select(RuoloImportJob)
    if anno is not None:
        q = q.where(RuoloImportJob.anno_tributario == anno)
    q = q.order_by(RuoloImportJob.created_at.desc())

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.offset((page - 1) * page_size).limit(page_size)).all()
    return list(items), total or 0


# ---------------------------------------------------------------------------
# Avvisi
# ---------------------------------------------------------------------------

def get_avviso(db: Session, avviso_id: uuid.UUID) -> RuoloAvviso | None:
    return db.get(RuoloAvviso, avviso_id)


def get_avviso_partite(db: Session, avviso_id: uuid.UUID) -> list[RuoloPartita]:
    return list(
        db.scalars(
            select(RuoloPartita)
            .where(RuoloPartita.avviso_id == avviso_id)
            .order_by(RuoloPartita.comune_nome)
        ).all()
    )


def get_partita_particelle(db: Session, partita_id: uuid.UUID) -> list[RuoloParticella]:
    return list(
        db.scalars(
            select(RuoloParticella)
            .where(RuoloParticella.partita_id == partita_id)
        ).all()
    )


def list_avvisi(
    db: Session,
    anno: int | None = None,
    subject_id: str | None = None,
    q: str | None = None,
    codice_fiscale: str | None = None,
    comune: str | None = None,
    codice_utenza: str | None = None,
    unlinked: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    query = select(RuoloAvviso)

    if anno is not None:
        query = query.where(RuoloAvviso.anno_tributario == anno)
    if subject_id:
        try:
            sid = uuid.UUID(subject_id)
            query = query.where(RuoloAvviso.subject_id == sid)
        except ValueError:
            pass
    if q:
        search_term = f"%{q.strip()}%"
        query = query.where(
            or_(
                RuoloAvviso.codice_cnc.ilike(search_term),
                func.coalesce(RuoloAvviso.nominativo_raw, "").ilike(search_term),
                func.coalesce(RuoloAvviso.codice_fiscale_raw, "").ilike(search_term),
                func.coalesce(RuoloAvviso.codice_utenza, "").ilike(search_term),
                cast(RuoloAvviso.anno_tributario, String).ilike(search_term),
                RuoloAvviso.id.in_(
                    select(RuoloPartita.avviso_id).where(
                        func.coalesce(RuoloPartita.comune_nome, "").ilike(search_term)
                    )
                ),
            )
        )
    if codice_fiscale:
        query = query.where(RuoloAvviso.codice_fiscale_raw.ilike(f"%{codice_fiscale}%"))
    if comune:
        # Filtra per comune tramite join partite
        query = query.where(
            RuoloAvviso.id.in_(
                select(RuoloPartita.avviso_id).where(
                    RuoloPartita.comune_nome.ilike(f"%{comune}%")
                )
            )
        )
    if codice_utenza:
        query = query.where(RuoloAvviso.codice_utenza == codice_utenza)
    if unlinked:
        query = query.where(RuoloAvviso.subject_id.is_(None))

    query = query.order_by(RuoloAvviso.anno_tributario.desc(), RuoloAvviso.nominativo_raw)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    avvisi = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    # Arricchisci con display_name del soggetto
    results = []
    for avviso in avvisi:
        display_name = _get_subject_display_name(db, avviso.subject_id)
        results.append({
            "avviso": avviso,
            "display_name": display_name,
            "is_linked": avviso.subject_id is not None,
        })

    return results, total or 0


def list_avvisi_by_subject(
    db: Session,
    subject_id: uuid.UUID,
) -> list[RuoloAvviso]:
    return list(
        db.scalars(
            select(RuoloAvviso)
            .where(RuoloAvviso.subject_id == subject_id)
            .order_by(RuoloAvviso.anno_tributario.desc())
        ).all()
    )


def search_particelle(
    db: Session,
    anno: int | None = None,
    foglio: str | None = None,
    particella: str | None = None,
    comune: str | None = None,
    match_status: str | None = None,
    match_reason: str | None = None,
    unmatched_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[RuoloParticella], int]:
    q = select(RuoloParticella)

    if anno is not None:
        q = q.where(RuoloParticella.anno_tributario == anno)
    if foglio:
        q = q.where(RuoloParticella.foglio == foglio)
    if particella:
        q = q.where(RuoloParticella.particella == particella)
    if comune:
        q = q.where(
            RuoloParticella.partita_id.in_(
                select(RuoloPartita.id).where(
                    RuoloPartita.comune_nome.ilike(f"%{comune}%")
                )
            )
        )
    if match_status:
        q = q.where(RuoloParticella.cat_particella_match_status == match_status)
    if match_reason:
        q = q.where(RuoloParticella.cat_particella_match_reason == match_reason)
    if unmatched_only:
        q = q.where(RuoloParticella.cat_particella_id.is_(None))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(
        q.order_by(RuoloParticella.anno_tributario.desc(), RuoloParticella.foglio, RuoloParticella.particella)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total or 0


# ---------------------------------------------------------------------------
# Statistiche
# ---------------------------------------------------------------------------

def get_stats(db: Session, anno: int | None = None) -> list[dict]:
    """Aggregati per anno (o tutti gli anni se anno=None)."""
    query = (
        select(
            RuoloAvviso.anno_tributario.label("anno_tributario"),
            func.count(RuoloAvviso.id).label("total_avvisi"),
            func.count(RuoloAvviso.subject_id).label("avvisi_collegati"),
            func.sum(RuoloAvviso.importo_totale_0648).label("totale_0648"),
            func.sum(RuoloAvviso.importo_totale_0985).label("totale_0985"),
            func.sum(RuoloAvviso.importo_totale_0668).label("totale_0668"),
            func.sum(RuoloAvviso.importo_totale_euro).label("totale_euro"),
        )
        .group_by(RuoloAvviso.anno_tributario)
        .order_by(RuoloAvviso.anno_tributario.desc())
    )
    if anno is not None:
        query = query.where(RuoloAvviso.anno_tributario == anno)

    rows = db.execute(query).all()
    return [
        {
            "anno_tributario": row.anno_tributario,
            "total_avvisi": int(row.total_avvisi or 0),
            "avvisi_collegati": int(row.avvisi_collegati or 0),
            "avvisi_non_collegati": int((row.total_avvisi or 0) - (row.avvisi_collegati or 0)),
            "totale_0648": float(row.totale_0648) if row.totale_0648 is not None else None,
            "totale_0985": float(row.totale_0985) if row.totale_0985 is not None else None,
            "totale_0668": float(row.totale_0668) if row.totale_0668 is not None else None,
            "totale_euro": float(row.totale_euro) if row.totale_euro is not None else None,
        }
        for row in rows
    ]


def get_particelle_summary(db: Session, anno: int | None = None) -> dict:
    base_query = select(RuoloParticella)
    if anno is not None:
        base_query = base_query.where(RuoloParticella.anno_tributario == anno)
    base_sq = base_query.subquery()

    total_particelle = db.scalar(select(func.count()).select_from(base_sq)) or 0
    collegate_catasto = db.scalar(
        select(func.count()).select_from(base_sq).where(base_sq.c.cat_particella_id.is_not(None))
    ) or 0
    non_collegate_catasto = total_particelle - collegate_catasto
    soppresse_ade = db.scalar(
        select(func.count()).select_from(base_sq).where(base_sq.c.ade_scan_classification == "suppressed")
    ) or 0
    return {
        "anno_tributario": anno,
        "total_particelle": int(total_particelle),
        "collegate_catasto": int(collegate_catasto),
        "non_collegate_catasto": int(non_collegate_catasto),
        "soppresse_ade": int(soppresse_ade),
    }


def get_stats_comuni(db: Session, anno: int) -> list[dict]:
    """Ripartizione importi per comune per anno."""
    partite_q = (
        select(
            RuoloPartita.comune_nome,
            func.sum(RuoloPartita.importo_0648).label("totale_0648"),
            func.sum(RuoloPartita.importo_0985).label("totale_0985"),
            func.sum(RuoloPartita.importo_0668).label("totale_0668"),
            func.count(RuoloPartita.avviso_id.distinct()).label("num_avvisi"),
            func.count(RuoloPartita.id.distinct()).label("num_partite"),
        )
        .join(RuoloAvviso, RuoloPartita.avviso_id == RuoloAvviso.id)
        .where(RuoloAvviso.anno_tributario == anno)
        .group_by(RuoloPartita.comune_nome)
        .order_by(RuoloPartita.comune_nome)
    )
    particelle_q = (
        select(
            RuoloPartita.comune_nome.label("comune_nome"),
            func.count(RuoloParticella.id).label("num_particelle"),
            func.sum(case((RuoloParticella.cat_particella_id.is_(None), 1), else_=0)).label("non_collegate_catasto"),
        )
        .join(RuoloPartita, RuoloParticella.partita_id == RuoloPartita.id)
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(RuoloPartita.comune_nome)
    )

    partite_rows = db.execute(partite_q).all()
    particelle_rows = db.execute(particelle_q).all()
    particelle_by_comune = {
        row.comune_nome: {
            "num_particelle": int(row.num_particelle or 0),
            "non_collegate_catasto": int(row.non_collegate_catasto or 0),
        }
        for row in particelle_rows
    }

    result = []
    for row in partite_rows:
        t0648 = float(row.totale_0648) if row.totale_0648 else None
        t0985 = float(row.totale_0985) if row.totale_0985 else None
        t0668 = float(row.totale_0668) if row.totale_0668 else None
        parts = [v for v in [t0648, t0985, t0668] if v is not None]
        totale_euro = sum(parts) if parts else None
        particelle_metrics = particelle_by_comune.get(row.comune_nome, {})
        result.append({
            "comune_nome": row.comune_nome,
            "anno_tributario": anno,
            "totale_0648": t0648,
            "totale_0985": t0985,
            "totale_0668": t0668,
            "totale_euro": totale_euro,
            "num_avvisi": int(row.num_avvisi or 0),
            "num_partite": int(row.num_partite or 0),
            "num_particelle": int(particelle_metrics.get("num_particelle", 0)),
            "non_collegate_catasto": int(particelle_metrics.get("non_collegate_catasto", 0)),
        })
    return result


def get_stats_analytics(db: Session, anno: int) -> dict[str, Any]:
    stats_by_anno = get_stats(db, anno=anno)
    if not stats_by_anno:
        return {
            "anno_tributario": anno,
            "particelle_summary": get_particelle_summary(db, anno=anno),
            "tributi_breakdown": [],
            "match_status_breakdown": [],
            "match_reason_breakdown": [],
            "distretto_breakdown": [],
            "coltura_breakdown": [],
            "comuni": [],
        }

    stats = stats_by_anno[0]
    tributi_breakdown = [
        {"key": "0648", "label": "0648 Manutenzione", "amount": float(stats["totale_0648"] or 0)},
        {"key": "0985", "label": "0985 Irrigazione", "amount": float(stats["totale_0985"] or 0)},
        {"key": "0668", "label": "0668 Istituzionale", "amount": float(stats["totale_0668"] or 0)},
    ]

    status_expr = func.coalesce(RuoloParticella.cat_particella_match_status, "unknown")
    reason_expr = func.coalesce(RuoloParticella.cat_particella_match_reason, "unspecified")
    distretto_expr = func.coalesce(RuoloParticella.distretto, "N/D")
    coltura_expr = func.coalesce(RuoloParticella.coltura, "N/D")

    status_rows = db.execute(
        select(
            status_expr.label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(status_expr)
        .order_by(desc(func.count(RuoloParticella.id)))
    ).all()

    reason_rows = db.execute(
        select(
            reason_expr.label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(
            RuoloParticella.anno_tributario == anno,
            RuoloParticella.cat_particella_id.is_(None),
        )
        .group_by(reason_expr)
        .order_by(desc(func.count(RuoloParticella.id)))
        .limit(8)
    ).all()

    distretto_rows = db.execute(
        select(
            distretto_expr.label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(distretto_expr)
        .order_by(desc(func.count(RuoloParticella.id)))
        .limit(8)
    ).all()

    coltura_rows = db.execute(
        select(
            coltura_expr.label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(coltura_expr)
        .order_by(desc(func.count(RuoloParticella.id)))
        .limit(8)
    ).all()

    return {
        "anno_tributario": anno,
        "particelle_summary": get_particelle_summary(db, anno=anno),
        "tributi_breakdown": tributi_breakdown,
        "match_status_breakdown": [
            {"key": row.key, "label": row.key.replace("_", " "), "count": int(row.count or 0)}
            for row in status_rows
        ],
        "match_reason_breakdown": [
            {"key": row.key, "label": row.key.replace("_", " "), "count": int(row.count or 0)}
            for row in reason_rows
        ],
        "distretto_breakdown": [
            {"key": row.key, "label": row.key, "count": int(row.count or 0)}
            for row in distretto_rows
        ],
        "coltura_breakdown": [
            {"key": row.key, "label": row.key, "count": int(row.count or 0)}
            for row in coltura_rows
        ],
        "comuni": get_stats_comuni(db, anno=anno),
    }


def get_capacitas_check(
    db: Session,
    *,
    anno: int,
    min_delta: float = 0.01,
    limit: int = 50,
) -> dict[str, Any]:
    threshold = abs(float(min_delta))
    ruolo_by_tax, ruolo_missing_tax = _load_ruolo_incass_by_tax(db, anno=anno)
    capacitas_rows = db.execute(
        select(
            CatUtenzaIrrigua.codice_fiscale,
            CatUtenzaIrrigua.denominazione,
            CatUtenzaIrrigua.importo_0648,
            CatUtenzaIrrigua.importo_0985,
        ).where(CatUtenzaIrrigua.anno_campagna == anno)
    ).all()

    capacitas_by_tax: dict[str, dict[str, Any]] = {}
    capacitas_missing_tax = 0

    def _to_float(value: Decimal | float | int | None) -> float:
        if value is None:
            return 0.0
        return round(float(value), 2)

    def _accumulate(
        bucket: dict[str, dict[str, Any]],
        *,
        tax_code: str,
        display_name: str | None,
        amount_0648: float,
        amount_0985: float,
        amount_0668: float = 0.0,
    ) -> None:
        current = bucket.get(tax_code)
        if current is None:
            current = {
                "tax_code": tax_code,
                "display_name": display_name,
                "amount_0648": 0.0,
                "amount_0985": 0.0,
                "amount_0668": 0.0,
            }
            bucket[tax_code] = current
        elif not current["display_name"] and display_name:
            current["display_name"] = display_name
        current["amount_0648"] = round(current["amount_0648"] + amount_0648, 2)
        current["amount_0985"] = round(current["amount_0985"] + amount_0985, 2)
        current["amount_0668"] = round(current["amount_0668"] + amount_0668, 2)

    for row in capacitas_rows:
        tax_code = normalize_tax_identifier(row.codice_fiscale)
        if not tax_code:
            capacitas_missing_tax += 1
            continue
        _accumulate(
            capacitas_by_tax,
            tax_code=tax_code,
            display_name=row.denominazione,
            amount_0648=_to_float(row.importo_0648),
            amount_0985=_to_float(row.importo_0985),
        )

    items: list[dict[str, Any]] = []
    mismatch_positions = 0
    all_tax_codes = sorted(set(ruolo_by_tax) | set(capacitas_by_tax))
    for tax_code in all_tax_codes:
        ruolo_entry = ruolo_by_tax.get(tax_code)
        capacitas_entry = capacitas_by_tax.get(tax_code)
        ruolo_0648 = ruolo_entry["amount_0648"] if ruolo_entry else 0.0
        ruolo_0985 = ruolo_entry["amount_0985"] if ruolo_entry else 0.0
        capacitas_0648 = capacitas_entry["amount_0648"] if capacitas_entry else 0.0
        capacitas_0985 = capacitas_entry["amount_0985"] if capacitas_entry else 0.0
        delta_0648 = round(ruolo_0648 - capacitas_0648, 2)
        delta_0985 = round(ruolo_0985 - capacitas_0985, 2)
        ruolo_totale_confrontabile = round(ruolo_0648 + ruolo_0985, 2)
        capacitas_totale_confrontabile = round(capacitas_0648 + capacitas_0985, 2)
        delta_totale_confrontabile = round(ruolo_totale_confrontabile - capacitas_totale_confrontabile, 2)

        if ruolo_entry and capacitas_entry:
            status = "matched"
            if abs(delta_0648) >= threshold or abs(delta_0985) >= threshold:
                status = "amount_mismatch"
                mismatch_positions += 1
        elif ruolo_entry:
            status = "only_in_ruolo"
            mismatch_positions += 1
        else:
            status = "only_in_capacitas"
            mismatch_positions += 1

        if status == "matched":
            continue

        items.append(
            {
                "tax_code": tax_code,
                "ruolo_display_name": ruolo_entry["display_name"] if ruolo_entry else None,
                "capacitas_display_name": capacitas_entry["display_name"] if capacitas_entry else None,
                "status": status,
                "ruolo_0648": ruolo_0648,
                "capacitas_0648": capacitas_0648,
                "delta_0648": delta_0648,
                "ruolo_0985": ruolo_0985,
                "capacitas_0985": capacitas_0985,
                "delta_0985": delta_0985,
                "ruolo_totale_confrontabile": ruolo_totale_confrontabile,
                "capacitas_totale_confrontabile": capacitas_totale_confrontabile,
                "delta_totale_confrontabile": delta_totale_confrontabile,
            }
        )

    items.sort(
        key=lambda item: (
            abs(item["delta_totale_confrontabile"]),
            abs(item["delta_0648"]) + abs(item["delta_0985"]),
            item["tax_code"],
        ),
        reverse=True,
    )

    ruolo_totale_0648 = round(sum(item["amount_0648"] for item in ruolo_by_tax.values()), 2)
    ruolo_totale_0985 = round(sum(item["amount_0985"] for item in ruolo_by_tax.values()), 2)
    ruolo_totale_0668 = round(sum(item["amount_0668"] for item in ruolo_by_tax.values()), 2)
    capacitas_totale_0648 = round(sum(item["amount_0648"] for item in capacitas_by_tax.values()), 2)
    capacitas_totale_0985 = round(sum(item["amount_0985"] for item in capacitas_by_tax.values()), 2)

    return {
        "summary": {
            "anno_tributario": anno,
            "ruolo_positions": len(ruolo_by_tax),
            "capacitas_positions": len(capacitas_by_tax),
            "matched_positions": sum(1 for tax_code in all_tax_codes if tax_code in ruolo_by_tax and tax_code in capacitas_by_tax),
            "only_in_ruolo": sum(1 for tax_code in all_tax_codes if tax_code in ruolo_by_tax and tax_code not in capacitas_by_tax),
            "only_in_capacitas": sum(1 for tax_code in all_tax_codes if tax_code in capacitas_by_tax and tax_code not in ruolo_by_tax),
            "ruolo_positions_missing_tax_code": ruolo_missing_tax,
            "capacitas_positions_missing_tax_code": capacitas_missing_tax,
            "ruolo_totale_0648": ruolo_totale_0648,
            "capacitas_totale_0648": capacitas_totale_0648,
            "delta_totale_0648": round(ruolo_totale_0648 - capacitas_totale_0648, 2),
            "ruolo_totale_0985": ruolo_totale_0985,
            "capacitas_totale_0985": capacitas_totale_0985,
            "delta_totale_0985": round(ruolo_totale_0985 - capacitas_totale_0985, 2),
            "ruolo_totale_0668": ruolo_totale_0668,
            "ruolo_totale_confrontabile": round(ruolo_totale_0648 + ruolo_totale_0985, 2),
            "capacitas_totale_confrontabile": round(capacitas_totale_0648 + capacitas_totale_0985, 2),
            "delta_totale_confrontabile": round((ruolo_totale_0648 + ruolo_totale_0985) - (capacitas_totale_0648 + capacitas_totale_0985), 2),
            "mismatch_positions": mismatch_positions,
        },
        "items": items[: max(limit, 0)],
    }


def get_capacitas_check_comuni(
    db: Session,
    *,
    anno: int,
    limit: int = 20,
) -> list[dict[str, Any]]:
    capacitas_comune_expr = func.coalesce(CatUtenzaIrrigua.nome_comune, "N/D")
    comuni = _load_ruolo_incass_by_comune(db, anno=anno)
    capacitas_rows = db.execute(
        select(
            capacitas_comune_expr.label("comune_nome"),
            func.coalesce(func.sum(CatUtenzaIrrigua.importo_0648), 0).label("capacitas_0648"),
            func.coalesce(func.sum(CatUtenzaIrrigua.importo_0985), 0).label("capacitas_0985"),
        )
        .where(CatUtenzaIrrigua.anno_campagna == anno)
        .group_by(capacitas_comune_expr)
    ).all()

    for item in comuni.values():
        item["capacitas_0648"] = 0.0
        item["capacitas_0985"] = 0.0
    for row in capacitas_rows:
        key = row.comune_nome or "N/D"
        current = comuni.setdefault(
            key,
            {
                "comune_nome": key,
                "ruolo_0648": 0.0,
                "capacitas_0648": 0.0,
                "ruolo_0985": 0.0,
                "capacitas_0985": 0.0,
            },
        )
        current["capacitas_0648"] = round(float(row.capacitas_0648 or 0), 2)
        current["capacitas_0985"] = round(float(row.capacitas_0985 or 0), 2)

    items: list[dict[str, Any]] = []
    for item in comuni.values():
        ruolo_0648 = float(item["ruolo_0648"])
        ruolo_0985 = float(item["ruolo_0985"])
        capacitas_0648 = float(item["capacitas_0648"])
        capacitas_0985 = float(item["capacitas_0985"])
        delta_0648 = round(ruolo_0648 - capacitas_0648, 2)
        delta_0985 = round(ruolo_0985 - capacitas_0985, 2)
        ruolo_totale_confrontabile = round(ruolo_0648 + ruolo_0985, 2)
        capacitas_totale_confrontabile = round(capacitas_0648 + capacitas_0985, 2)
        items.append(
            {
                "comune_nome": item["comune_nome"],
                "ruolo_0648": ruolo_0648,
                "capacitas_0648": capacitas_0648,
                "delta_0648": delta_0648,
                "ruolo_0985": ruolo_0985,
                "capacitas_0985": capacitas_0985,
                "delta_0985": delta_0985,
                "ruolo_totale_confrontabile": ruolo_totale_confrontabile,
                "capacitas_totale_confrontabile": capacitas_totale_confrontabile,
                "delta_totale_confrontabile": round(ruolo_totale_confrontabile - capacitas_totale_confrontabile, 2),
            }
        )

    items.sort(key=lambda item: abs(item["delta_totale_confrontabile"]), reverse=True)
    return items[: max(limit, 0)]


# ---------------------------------------------------------------------------
# Catasto Parcels
# ---------------------------------------------------------------------------

def list_catasto_parcels(
    db: Session,
    comune_codice: str | None = None,
    foglio: str | None = None,
    particella: str | None = None,
    active_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[CatastoParcel], int]:
    q = select(CatastoParcel)
    if comune_codice:
        q = q.where(CatastoParcel.comune_codice == comune_codice)
    if foglio:
        q = q.where(CatastoParcel.foglio == foglio)
    if particella:
        q = q.where(CatastoParcel.particella == particella)
    if active_only:
        q = q.where(CatastoParcel.valid_to.is_(None))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(
        q.order_by(CatastoParcel.comune_nome, CatastoParcel.foglio, CatastoParcel.particella, CatastoParcel.valid_from)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total or 0


def get_catasto_parcel_history(
    db: Session,
    comune_codice: str,
    foglio: str,
    particella: str,
    subalterno: str | None = None,
) -> list[CatastoParcel]:
    q = select(CatastoParcel).where(
        CatastoParcel.comune_codice == comune_codice,
        CatastoParcel.foglio == foglio,
        CatastoParcel.particella == particella,
    )
    if subalterno is not None:
        q = q.where(CatastoParcel.subalterno == subalterno)
    return list(db.scalars(q.order_by(CatastoParcel.valid_from)).all())


# ---------------------------------------------------------------------------
# Utility: display_name soggetto
# ---------------------------------------------------------------------------

def _get_subject_display_name(db: Session, subject_id: uuid.UUID | None) -> str | None:
    if subject_id is None:
        return None
    person = db.scalar(
        select(AnagraficaPerson).where(AnagraficaPerson.subject_id == subject_id)
    )
    if person is not None:
        return f"{person.cognome} {person.nome}".strip()
    company = db.scalar(
        select(AnagraficaCompany).where(AnagraficaCompany.subject_id == subject_id)
    )
    if company is not None:
        return company.ragione_sociale
    return None
