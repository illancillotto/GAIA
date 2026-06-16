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
from app.models.catasto import CatastoParcel
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita, RuoloParticella
from app.modules.ruolo.services.catasto_linking import (
    _normalize_comune_codice,
    _resolve_comune_codice_for_ruolo,
    _upsert_catasto_parcel,
    resolve_cat_particella_match,
)
from app.modules.ruolo.services.parsing_common import (
    normalize_partita_comune_nome as _normalize_partita_comune_nome,
    resolve_section_hint_for_ruolo_comune as _resolve_section_hint_for_ruolo_comune,
)
from app.modules.ruolo.services.parser import (
    ParsedPartita,
    ParsedPartitaCNC,
    ParsedParticella,
    extract_text_from_content,
    parse_ruolo_file,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject
from app.modules.utenze.services.subject_identity import is_probable_person_cf, is_probable_vat_number, normalize_tax_identifier

logger = logging.getLogger(__name__)
_JOB_REPORT_PREVIEW_LIMIT = 50

_background_tasks: set[asyncio.Task] = set()


class SubjectNotFound(Exception):
    """Soggetto non trovato in ana_subjects tramite CF/PIVA."""


def _merge_particella_rows(particelle: list[ParsedParticella]) -> list[ParsedParticella]:
    """
    Deduplica righe duplicate della stessa particella all'interno della stessa partita.

    Nel formato reale una stessa particella può comparire due volte:
    - riga base con importi 0648/0985
    - riga dettaglio con domanda, sup. irrigata, coltura o importo 0668
    """
    merged: dict[tuple[str, str, str | None], ParsedParticella] = {}
    ordered_keys: list[tuple[str, str, str | None]] = []

    for item in particelle:
        key = (item.foglio, item.particella, item.subalterno)
        existing = merged.get(key)
        if existing is None:
            merged[key] = item
            ordered_keys.append(key)
            continue

        merged[key] = ParsedParticella(
            domanda_irrigua=item.domanda_irrigua or existing.domanda_irrigua,
            distretto=item.distretto or existing.distretto,
            foglio=existing.foglio,
            particella=existing.particella,
            subalterno=item.subalterno or existing.subalterno,
            sup_catastale_are=item.sup_catastale_are or existing.sup_catastale_are,
            sup_catastale_ha=item.sup_catastale_ha or existing.sup_catastale_ha,
            sup_irrigata_ha=item.sup_irrigata_ha or existing.sup_irrigata_ha,
            coltura=item.coltura or existing.coltura,
            importo_manut=item.importo_manut or existing.importo_manut,
            importo_irrig=item.importo_irrig or existing.importo_irrig,
            importo_ist=item.importo_ist or existing.importo_ist,
        )

    return [merged[key] for key in ordered_keys]


def _build_job_report_payload(
    *,
    filename: str,
    anno: int,
    total_partite: int,
    imported: int,
    skipped: int,
    errors: int,
    skipped_items: list[dict[str, str | int | None]],
    error_items: list[dict[str, str | int | None]],
) -> dict[str, object]:
    return {
        "report_summary": {
            "filename": filename,
            "anno_tributario": anno,
            "total_partite": total_partite,
            "records_imported": imported,
            "records_skipped": skipped,
            "records_errors": errors,
        },
        "report_preview": {
            "skipped_items": skipped_items[:_JOB_REPORT_PREVIEW_LIMIT],
            "error_items": error_items[:_JOB_REPORT_PREVIEW_LIMIT],
            "skipped_preview_count": min(len(skipped_items), _JOB_REPORT_PREVIEW_LIMIT),
            "error_preview_count": min(len(error_items), _JOB_REPORT_PREVIEW_LIMIT),
            "skipped_total_count": len(skipped_items),
            "error_total_count": len(error_items),
        },
    }


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

    cf = normalize_tax_identifier(codice_fiscale_raw)
    if cf is None:
        return None

    # Gli identificativi a 11 cifre vanno trattati come P.IVA per evitare
    # di preferire soggetti persona spuri creati da import non affidabili.
    if is_probable_vat_number(cf):
        company = db.scalar(select(AnagraficaCompany).where(AnagraficaCompany.partita_iva == cf))
        if company is not None:
            return company.subject_id
        company_cf = db.scalar(select(AnagraficaCompany).where(AnagraficaCompany.codice_fiscale == cf))
        if company_cf is not None:
            return company_cf.subject_id
        person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == cf))
        if person is not None:
            return person.subject_id
        return None

    if is_probable_person_cf(cf):
        person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == cf))
        if person is not None:
            return person.subject_id
        company_cf = db.scalar(select(AnagraficaCompany).where(AnagraficaCompany.codice_fiscale == cf))
        if company_cf is not None:
            return company_cf.subject_id
        company = db.scalar(select(AnagraficaCompany).where(AnagraficaCompany.partita_iva == cf))
        if company is not None:
            return company.subject_id
        return None

    company = db.scalar(select(AnagraficaCompany).where(AnagraficaCompany.partita_iva == cf))
    if company is not None:
        return company.subject_id
    company_cf = db.scalar(select(AnagraficaCompany).where(AnagraficaCompany.codice_fiscale == cf))
    if company_cf is not None:
        return company_cf.subject_id
    person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == cf))
    if person is not None:
        return person.subject_id

    return None


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
        comune_nome = _normalize_partita_comune_nome(partita_data.comune_nome)
        sezione_hint = _resolve_section_hint_for_ruolo_comune(comune_nome)
        particelle_data = _merge_particella_rows(partita_data.particelle)
        partita = RuoloPartita(
            id=uuid.uuid4(),
            avviso_id=avviso_id,
            codice_partita=partita_data.codice_partita,
            comune_nome=comune_nome,
            comune_codice=None,  # sarà risolto dopo
            contribuente_cf=partita_data.contribuente_cf,
            co_intestati_raw=partita_data.co_intestati_raw,
            importo_0648=float(partita_data.importo_0648) if partita_data.importo_0648 else None,
            importo_0985=float(partita_data.importo_0985) if partita_data.importo_0985 else None,
            importo_0668=float(partita_data.importo_0668) if partita_data.importo_0668 else None,
        )
        db.add(partita)
        db.flush()

        for part_data in particelle_data:
            # Upsert catasto_parcel
            catasto_parcel_id = None
            cat_particella_id = None
            cat_particella_match_status = "unmatched"
            cat_particella_match_confidence = None
            cat_particella_match_reason = "catasto_parcel_not_resolved"
            try:
                catasto_parcel_id = _upsert_catasto_parcel(
                    db,
                    comune_nome=comune_nome,
                    foglio=part_data.foglio,
                    particella=part_data.particella,
                    subalterno=part_data.subalterno,
                    sup_catastale_are=part_data.sup_catastale_are,
                    anno=anno,
                )
                catasto_parcel = db.get(CatastoParcel, catasto_parcel_id) if catasto_parcel_id else None
                if catasto_parcel is not None:
                    (
                        cat_particella_id,
                        cat_particella_match_status,
                        cat_particella_match_confidence,
                        cat_particella_match_reason,
                    ) = resolve_cat_particella_match(
                        db,
                        comune_codice=catasto_parcel.comune_codice,
                        foglio=catasto_parcel.foglio,
                        particella=catasto_parcel.particella,
                        subalterno=catasto_parcel.subalterno,
                        sezione_catastale=sezione_hint,
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
                cat_particella_id=cat_particella_id,
                cat_particella_match_status=cat_particella_match_status,
                cat_particella_match_confidence=cat_particella_match_confidence,
                cat_particella_match_reason=cat_particella_match_reason,
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
        skipped_items: list[dict[str, str | int | None]] = []
        error_items: list[dict[str, str | int | None]] = []
        total_partite = 0

        try:
            text = extract_text_from_content(raw_content, filename=filename)
            partite = parse_ruolo_file(text)

            total_partite = len(partite)
            job.total_partite = total_partite
            db.commit()

            for partita_cnc in partite:
                try:
                    avviso_id, is_new = _upsert_avviso(db, partita_cnc, anno, job_id)
                    _upsert_partite(db, avviso_id, partita_cnc.partite, anno)
                    db.commit()

                    subject_id = _resolve_subject_id(db, partita_cnc.codice_fiscale_raw)
                    if subject_id is None:
                        skipped += 1
                        skipped_items.append({
                            "codice_cnc": partita_cnc.codice_cnc,
                            "codice_fiscale_raw": partita_cnc.codice_fiscale_raw or None,
                            "nominativo_raw": partita_cnc.nominativo_raw or None,
                            "reason_code": "subject_not_found",
                            "reason_label": "Soggetto non trovato in Anagrafica",
                        })
                    else:
                        imported += 1

                except Exception as exc:
                    db.rollback()
                    errors += 1
                    error_msg = f"CNC {partita_cnc.codice_cnc}: {exc}"
                    error_lines.append(error_msg)
                    error_items.append({
                        "codice_cnc": partita_cnc.codice_cnc,
                        "codice_fiscale_raw": partita_cnc.codice_fiscale_raw or None,
                        "nominativo_raw": partita_cnc.nominativo_raw or None,
                        "reason_code": "import_error",
                        "reason_label": str(exc),
                    })
                    logger.warning("Errore import partita %s: %s", partita_cnc.codice_cnc, exc)

            job.status = "completed"

        except Exception as exc:
            logger.exception("Import job failed: %s", exc)
            job.status = "failed"
            error_lines.append(str(exc))
            error_items.append({
                "codice_cnc": None,
                "codice_fiscale_raw": None,
                "nominativo_raw": None,
                "reason_code": "job_failed",
                "reason_label": str(exc),
            })

        finally:
            job.finished_at = datetime.now(timezone.utc)
            job.records_imported = imported
            job.records_skipped = skipped
            job.records_errors = errors
            job.error_detail = "\n".join(error_lines[:20]) if error_lines else None
            job.params_json = _build_job_report_payload(
                filename=filename,
                anno=anno,
                total_partite=total_partite,
                imported=imported,
                skipped=skipped,
                errors=errors,
                skipped_items=skipped_items,
                error_items=error_items,
            )
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
