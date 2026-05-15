"""Repository layer per le query del modulo Ruolo."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import String, cast, func, or_, select
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
    if anno is not None:
        anni = [anno]
    else:
        anni_rows = db.scalars(
            select(RuoloAvviso.anno_tributario).distinct().order_by(RuoloAvviso.anno_tributario.desc())
        ).all()
        anni = list(anni_rows)

    results = []
    for a in anni:
        total = db.scalar(
            select(func.count(RuoloAvviso.id)).where(RuoloAvviso.anno_tributario == a)
        ) or 0
        collegati = db.scalar(
            select(func.count(RuoloAvviso.id)).where(
                RuoloAvviso.anno_tributario == a,
                RuoloAvviso.subject_id.is_not(None),
            )
        ) or 0
        totale_0648 = db.scalar(
            select(func.sum(RuoloAvviso.importo_totale_0648)).where(RuoloAvviso.anno_tributario == a)
        )
        totale_0985 = db.scalar(
            select(func.sum(RuoloAvviso.importo_totale_0985)).where(RuoloAvviso.anno_tributario == a)
        )
        totale_0668 = db.scalar(
            select(func.sum(RuoloAvviso.importo_totale_0668)).where(RuoloAvviso.anno_tributario == a)
        )
        totale_euro = db.scalar(
            select(func.sum(RuoloAvviso.importo_totale_euro)).where(RuoloAvviso.anno_tributario == a)
        )
        results.append({
            "anno_tributario": a,
            "total_avvisi": total,
            "avvisi_collegati": collegati,
            "avvisi_non_collegati": total - collegati,
            "totale_0648": float(totale_0648) if totale_0648 else None,
            "totale_0985": float(totale_0985) if totale_0985 else None,
            "totale_0668": float(totale_0668) if totale_0668 else None,
            "totale_euro": float(totale_euro) if totale_euro else None,
        })
    return results


def get_stats_comuni(db: Session, anno: int) -> list[dict]:
    """Ripartizione importi per comune per anno."""
    partite_q = (
        select(
            RuoloPartita.comune_nome,
            func.sum(RuoloPartita.importo_0648).label("totale_0648"),
            func.sum(RuoloPartita.importo_0985).label("totale_0985"),
            func.sum(RuoloPartita.importo_0668).label("totale_0668"),
            func.count(RuoloPartita.id.distinct()).label("num_avvisi"),
        )
        .join(RuoloAvviso, RuoloPartita.avviso_id == RuoloAvviso.id)
        .where(RuoloAvviso.anno_tributario == anno)
        .group_by(RuoloPartita.comune_nome)
        .order_by(RuoloPartita.comune_nome)
    )
    rows = db.execute(partite_q).all()
    result = []
    for row in rows:
        t0648 = float(row.totale_0648) if row.totale_0648 else None
        t0985 = float(row.totale_0985) if row.totale_0985 else None
        t0668 = float(row.totale_0668) if row.totale_0668 else None
        parts = [v for v in [t0648, t0985, t0668] if v is not None]
        totale_euro = sum(parts) if parts else None
        result.append({
            "comune_nome": row.comune_nome,
            "anno_tributario": anno,
            "totale_0648": t0648,
            "totale_0985": t0985,
            "totale_0668": t0668,
            "totale_euro": totale_euro,
            "num_avvisi": row.num_avvisi,
        })
    return result


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
