"""Repository layer per le query del modulo Ruolo."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import String, case, cast, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoParcel
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita, RuoloParticella
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject


# ---------------------------------------------------------------------------
# Import Jobs
# ---------------------------------------------------------------------------

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

    status_rows = db.execute(
        select(
            func.coalesce(RuoloParticella.cat_particella_match_status, "unknown").label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(func.coalesce(RuoloParticella.cat_particella_match_status, "unknown"))
        .order_by(desc(func.count(RuoloParticella.id)))
    ).all()

    reason_rows = db.execute(
        select(
            func.coalesce(RuoloParticella.cat_particella_match_reason, "unspecified").label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(
            RuoloParticella.anno_tributario == anno,
            RuoloParticella.cat_particella_id.is_(None),
        )
        .group_by(func.coalesce(RuoloParticella.cat_particella_match_reason, "unspecified"))
        .order_by(desc(func.count(RuoloParticella.id)))
        .limit(8)
    ).all()

    distretto_rows = db.execute(
        select(
            func.coalesce(RuoloParticella.distretto, "N/D").label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(func.coalesce(RuoloParticella.distretto, "N/D"))
        .order_by(desc(func.count(RuoloParticella.id)))
        .limit(8)
    ).all()

    coltura_rows = db.execute(
        select(
            func.coalesce(RuoloParticella.coltura, "N/D").label("key"),
            func.count(RuoloParticella.id).label("count"),
        )
        .where(RuoloParticella.anno_tributario == anno)
        .group_by(func.coalesce(RuoloParticella.coltura, "N/D"))
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
