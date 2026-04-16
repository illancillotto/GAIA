"""
Import service per il modulo Ruolo.
Orchestrazione job asincrono con sessione DB indipendente dalla request.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.catasto import CatastoComune, CatastoParcel
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita, RuoloParticella
from app.modules.ruolo.services.parser import (
    ParsedPartita,
    ParsedPartitaCNC,
    ParsedParticella,
    extract_text_from_content,
    parse_ruolo_file,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()


class SubjectNotFound(Exception):
    """Soggetto non trovato in ana_subjects tramite CF/PIVA."""


# ---------------------------------------------------------------------------
# Risoluzione soggetto
# ---------------------------------------------------------------------------

def _resolve_subject_id(db: Session, codice_fiscale_raw: str) -> uuid.UUID | None:
    """
    Cerca il soggetto in ana_subjects via CF (ana_persons) o PIVA (ana_companies).
    Ritorna l'UUID del soggetto o None se non trovato.
    """
    if not codice_fiscale_raw:
        return None

    cf = codice_fiscale_raw.strip().upper()

    # Prima prova su ana_persons (persone fisiche — CF 16 chars)
    person = db.scalar(
        select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == cf)
    )
    if person is not None:
        return person.subject_id

    # Poi prova su ana_companies (partita IVA — 11 chars o CF aziendale)
    company = db.scalar(
        select(AnagraficaCompany).where(AnagraficaCompany.partita_iva == cf)
    )
    if company is not None:
        return company.subject_id

    # Fallback: CF aziendale in ana_companies
    company_cf = db.scalar(
        select(AnagraficaCompany).where(AnagraficaCompany.codice_fiscale == cf)
    )
    if company_cf is not None:
        return company_cf.subject_id

    return None


# ---------------------------------------------------------------------------
# Upsert catasto_parcels (logica temporale)
# ---------------------------------------------------------------------------

def _upsert_catasto_parcel(
    db: Session,
    *,
    comune_nome: str,
    foglio: str,
    particella: str,
    subalterno: str | None,
    sup_catastale_are: Decimal | None,
    anno: int,
) -> uuid.UUID | None:
    """
    Logica upsert temporale per catasto_parcels:
    - Stessa superficie → no-op, ritorna UUID esistente
    - Superficie diversa → chiudi record (valid_to = anno - 1), crea nuovo
    - Non esiste → crea nuovo con valid_from = anno
    """
    if not foglio or not particella:
        return None

    # Risolvi comune_codice da catasto_comuni
    comune_codice: str | None = None
    comune_row = db.scalar(
        select(CatastoComune).where(CatastoComune.nome == comune_nome.upper())
    )
    if comune_row is None:
        # Prova match case-insensitive parziale
        comune_row = db.scalar(
            select(CatastoComune).where(
                CatastoComune.nome.ilike(f"%{comune_nome}%")
            )
        )
    if comune_row is not None:
        comune_codice = comune_row.codice_sister
    else:
        logger.warning("Comune non trovato in catasto_comuni: %s", comune_nome)
        return None

    # Cerca record esistente con valid_to IS NULL
    existing = db.scalar(
        select(CatastoParcel).where(
            CatastoParcel.comune_codice == comune_codice,
            CatastoParcel.foglio == foglio,
            CatastoParcel.particella == particella,
            CatastoParcel.subalterno == subalterno,
            CatastoParcel.valid_to.is_(None),
        )
    )

    if existing is not None:
        # Verifica se la superficie è cambiata
        existing_are = existing.sup_catastale_are
        new_are = float(sup_catastale_are) if sup_catastale_are else None

        if existing_are is None and new_are is None:
            return existing.id
        if existing_are is not None and new_are is not None:
            if abs(float(existing_are) - new_are) < 0.0001:
                return existing.id

        # Superficie diversa: chiudi il record esistente
        existing.valid_to = anno - 1
        existing.updated_at = datetime.now(timezone.utc)
        db.flush()

    # Crea nuovo record
    sup_ha = (sup_catastale_are / Decimal("100")) if sup_catastale_are else None
    parcel = CatastoParcel(
        id=uuid.uuid4(),
        comune_codice=comune_codice,
        comune_nome=comune_nome,
        foglio=foglio,
        particella=particella,
        subalterno=subalterno,
        sup_catastale_are=float(sup_catastale_are) if sup_catastale_are else None,
        sup_catastale_ha=float(sup_ha) if sup_ha else None,
        valid_from=anno,
        valid_to=None,
        source="ruolo_import",
    )
    db.add(parcel)
    db.flush()
    return parcel.id


# ---------------------------------------------------------------------------
# Upsert avviso (idempotente su codice_cnc + anno_tributario)
# ---------------------------------------------------------------------------

def _upsert_avviso(
    db: Session,
    partita_cnc: ParsedPartitaCNC,
    anno: int,
    job_id: uuid.UUID,
) -> tuple[uuid.UUID, bool]:
    """
    Upsert idempotente su (codice_cnc, anno_tributario).
    Ritorna (avviso_id, is_new).
    """
    existing = db.scalar(
        select(RuoloAvviso).where(
            RuoloAvviso.codice_cnc == partita_cnc.codice_cnc,
            RuoloAvviso.anno_tributario == anno,
        )
    )

    subject_id = _resolve_subject_id(db, partita_cnc.codice_fiscale_raw)

    # Aggiorna importi totali
    totale_euro = None
    parts = [
        v for v in [
            partita_cnc.importo_totale_0648,
            partita_cnc.importo_totale_0985,
            partita_cnc.importo_totale_0668,
        ]
        if v is not None
    ]
    if parts:
        totale_euro = float(sum(parts))

    if existing is not None:
        # Aggiorna i campi principali (idempotenza)
        existing.import_job_id = job_id
        existing.subject_id = subject_id
        existing.codice_utenza = partita_cnc.codice_utenza
        existing.importo_totale_0648 = float(partita_cnc.importo_totale_0648) if partita_cnc.importo_totale_0648 else None
        existing.importo_totale_0985 = float(partita_cnc.importo_totale_0985) if partita_cnc.importo_totale_0985 else None
        existing.importo_totale_0668 = float(partita_cnc.importo_totale_0668) if partita_cnc.importo_totale_0668 else None
        existing.importo_totale_euro = totale_euro
        existing.importo_totale_lire = float(partita_cnc.importo_totale_lire) if partita_cnc.importo_totale_lire else None
        existing.n4_campo_sconosciuto = partita_cnc.n4_campo_sconosciuto
        existing.updated_at = datetime.now(timezone.utc)
        db.flush()
        avviso_id = existing.id
        is_new = False
    else:
        avviso = RuoloAvviso(
            id=uuid.uuid4(),
            import_job_id=job_id,
            codice_cnc=partita_cnc.codice_cnc,
            anno_tributario=anno,
            subject_id=subject_id,
            codice_fiscale_raw=partita_cnc.codice_fiscale_raw,
            nominativo_raw=partita_cnc.nominativo_raw,
            domicilio_raw=partita_cnc.domicilio_raw,
            residenza_raw=partita_cnc.residenza_raw,
            n2_extra_raw=partita_cnc.n2_extra_raw,
            codice_utenza=partita_cnc.codice_utenza,
            importo_totale_0648=float(partita_cnc.importo_totale_0648) if partita_cnc.importo_totale_0648 else None,
            importo_totale_0985=float(partita_cnc.importo_totale_0985) if partita_cnc.importo_totale_0985 else None,
            importo_totale_0668=float(partita_cnc.importo_totale_0668) if partita_cnc.importo_totale_0668 else None,
            importo_totale_euro=totale_euro,
            importo_totale_lire=float(partita_cnc.importo_totale_lire) if partita_cnc.importo_totale_lire else None,
            n4_campo_sconosciuto=partita_cnc.n4_campo_sconosciuto,
        )
        db.add(avviso)
        db.flush()
        avviso_id = avviso.id
        is_new = True

    return avviso_id, is_new


def _upsert_partite(
    db: Session,
    avviso_id: uuid.UUID,
    partite: list[ParsedPartita],
    anno: int,
) -> None:
    """Cancella e ricrea le partite dell'avviso (simpler approach for idempotency)."""
    # Elimina partite esistenti dell'avviso (cascade elimina anche particelle)
    existing_partite = db.scalars(
        select(RuoloPartita).where(RuoloPartita.avviso_id == avviso_id)
    ).all()
    for p in existing_partite:
        db.delete(p)
    db.flush()

    for partita_data in partite:
        partita = RuoloPartita(
            id=uuid.uuid4(),
            avviso_id=avviso_id,
            codice_partita=partita_data.codice_partita,
            comune_nome=partita_data.comune_nome,
            comune_codice=None,  # sarà risolto dopo
            contribuente_cf=partita_data.contribuente_cf,
            co_intestati_raw=partita_data.co_intestati_raw,
            importo_0648=float(partita_data.importo_0648) if partita_data.importo_0648 else None,
            importo_0985=float(partita_data.importo_0985) if partita_data.importo_0985 else None,
            importo_0668=float(partita_data.importo_0668) if partita_data.importo_0668 else None,
        )
        db.add(partita)
        db.flush()

        for part_data in partita_data.particelle:
            # Upsert catasto_parcel
            catasto_parcel_id = None
            try:
                catasto_parcel_id = _upsert_catasto_parcel(
                    db,
                    comune_nome=partita_data.comune_nome,
                    foglio=part_data.foglio,
                    particella=part_data.particella,
                    subalterno=part_data.subalterno,
                    sup_catastale_are=part_data.sup_catastale_are,
                    anno=anno,
                )
            except Exception as exc:
                logger.warning(
                    "Errore upsert catasto_parcel foglio=%s part=%s: %s",
                    part_data.foglio,
                    part_data.particella,
                    exc,
                )

            particella = RuoloParticella(
                id=uuid.uuid4(),
                partita_id=partita.id,
                anno_tributario=anno,
                domanda_irrigua=part_data.domanda_irrigua,
                distretto=part_data.distretto,
                foglio=part_data.foglio,
                particella=part_data.particella,
                subalterno=part_data.subalterno,
                sup_catastale_are=float(part_data.sup_catastale_are) if part_data.sup_catastale_are else None,
                sup_catastale_ha=float(part_data.sup_catastale_ha) if part_data.sup_catastale_ha else None,
                sup_irrigata_ha=float(part_data.sup_irrigata_ha) if part_data.sup_irrigata_ha else None,
                coltura=part_data.coltura,
                importo_manut=float(part_data.importo_manut) if part_data.importo_manut else None,
                importo_irrig=float(part_data.importo_irrig) if part_data.importo_irrig else None,
                importo_ist=float(part_data.importo_ist) if part_data.importo_ist else None,
                catasto_parcel_id=catasto_parcel_id,
            )
            db.add(particella)

    db.flush()


# ---------------------------------------------------------------------------
# Background task principale
# ---------------------------------------------------------------------------

async def run_import_job(job_id: uuid.UUID, raw_content: bytes, anno: int, filename: str = "") -> None:
    """
    Job asincrono di import del file Ruolo.
    Apre una sessione DB indipendente dalla request.
    """
    db: Session = SessionLocal()
    try:
        job = db.get(RuoloImportJob, job_id)
        if job is None:
            logger.error("Import job non trovato: %s", job_id)
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        imported = 0
        skipped = 0
        errors = 0
        error_lines: list[str] = []

        try:
            text = extract_text_from_content(raw_content, filename=filename)
            partite = parse_ruolo_file(text)

            job.total_partite = len(partite)
            db.commit()

            for partita_cnc in partite:
                try:
                    avviso_id, is_new = _upsert_avviso(db, partita_cnc, anno, job_id)
                    _upsert_partite(db, avviso_id, partita_cnc.partite, anno)
                    db.commit()

                    if _resolve_subject_id(db, partita_cnc.codice_fiscale_raw) is None:
                        skipped += 1
                    else:
                        imported += 1

                except Exception as exc:
                    db.rollback()
                    errors += 1
                    error_msg = f"CNC {partita_cnc.codice_cnc}: {exc}"
                    error_lines.append(error_msg)
                    logger.warning("Errore import partita %s: %s", partita_cnc.codice_cnc, exc)

            job.status = "completed"

        except Exception as exc:
            logger.exception("Import job failed: %s", exc)
            job.status = "failed"
            error_lines.append(str(exc))

        finally:
            job.finished_at = datetime.now(timezone.utc)
            job.records_imported = imported
            job.records_skipped = skipped
            job.records_errors = errors
            job.error_detail = "\n".join(error_lines[:20]) if error_lines else None
            db.commit()

    except Exception as exc:
        logger.exception("Import job bootstrap failed: %s", exc)
        try:
            job = db.get(RuoloImportJob, job_id)
            if job:
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                job.error_detail = str(exc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def check_anno_already_imported(db: Session, anno_tributario: int) -> int:
    """Ritorna il numero di avvisi già presenti per l'anno tributario."""
    from sqlalchemy import func as sqlfunc
    count = db.scalar(
        select(sqlfunc.count(RuoloAvviso.id)).where(
            RuoloAvviso.anno_tributario == anno_tributario
        )
    )
    return count or 0


def create_import_job(
    db: Session,
    *,
    anno_tributario: int,
    filename: str | None,
    triggered_by: int,
) -> RuoloImportJob:
    """Crea un nuovo job di import con status pending."""
    job = RuoloImportJob(
        id=uuid.uuid4(),
        anno_tributario=anno_tributario,
        filename=filename,
        status="pending",
        triggered_by=triggered_by,
    )
    db.add(job)
    db.flush()
    return job
