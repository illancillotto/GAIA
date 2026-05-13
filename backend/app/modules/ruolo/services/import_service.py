"""
Import service per il modulo Ruolo.
Orchestrazione job asincrono con sessione DB indipendente dalla request.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.catasto import CatastoComune, CatastoParcel
from app.models.catasto_phase1 import CatParticella
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita, RuoloParticella
from app.modules.ruolo.services.parser import (
    ParsedPartita,
    ParsedPartitaCNC,
    ParsedParticella,
    extract_text_from_content,
    parse_ruolo_file,
    _normalize_partita_comune_nome,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject

logger = logging.getLogger(__name__)
_RE_CATASTO_CODE = re.compile(r"\b([A-Z]\d{3})\b")
_JOB_REPORT_PREVIEW_LIMIT = 50
_ARBOREA_TERRALBA_SWAP_CODES = {
    "A357": "L122",
    "L122": "A357",
}
_ORISTANO_FRAZIONE_SECTION_HINTS = {
    "DONIGALA": "B",
    "DONIGALA FENUGHEDU": "B",
    "MASSAMA": "C",
    "NURAXINIEDDU": "D",
    "SILI": "E",
}

_background_tasks: set[asyncio.Task] = set()


class SubjectNotFound(Exception):
    """Soggetto non trovato in ana_subjects tramite CF/PIVA."""


def _normalize_comune_codice(raw_value: str | None) -> str | None:
    """
    Normalizza il codice comune proveniente da catasto_comuni/codice_sister.

    Nei dataset reali il valore può essere già un codice catastale (`F272`) oppure
    una forma composita tipo `F272#MOGORO#0#0`. In catasto_parcels serve il codice
    corto compatibile con `VARCHAR(10)`.
    """
    if raw_value is None:
        return None

    cleaned = raw_value.strip().upper()
    if not cleaned:
        return None
    if len(cleaned) <= 10 and "#" not in cleaned:
        return cleaned

    first_segment = cleaned.split("#", maxsplit=1)[0].strip()
    if first_segment and len(first_segment) <= 10:
        cleaned = first_segment

    match = _RE_CATASTO_CODE.search(cleaned)
    if match:
        return match.group(1)

    return cleaned[:10] if cleaned else None


def _resolve_comune_codice_for_ruolo(db: Session, comune_nome: str) -> str | None:
    comune_nome_norm = _normalize_partita_comune_nome(comune_nome)

    comune_row = db.scalar(
        select(CatastoComune).where(func.upper(CatastoComune.nome) == comune_nome_norm.upper())
    )
    if comune_row is not None:
        return _normalize_comune_codice(comune_row.codice_sister)

    cat_particella_comuni = db.execute(
        select(CatParticella.codice_catastale)
        .where(func.upper(CatParticella.nome_comune) == comune_nome_norm.upper())
        .group_by(CatParticella.codice_catastale)
        .limit(2)
    ).all()
    if len(cat_particella_comuni) == 1:
        return _normalize_comune_codice(cat_particella_comuni[0][0])

    logger.warning("Comune non trovato in catasto_comuni: %s", comune_nome_norm)
    return None


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

def _first_two_cat_particella_ids(db: Session, *conditions) -> list[uuid.UUID]:
    return list(db.scalars(select(CatParticella.id).where(*conditions).limit(2)).all())


def _resolve_section_hint_for_ruolo_comune(comune_nome: str | None) -> str | None:
    if not comune_nome:
        return None
    comune_norm = _normalize_partita_comune_nome(comune_nome).strip().upper()
    return _ORISTANO_FRAZIONE_SECTION_HINTS.get(comune_norm)


def _resolve_cat_particella_match_for_code(
    db: Session,
    *,
    comune_codice: str | None,
    foglio: str | None,
    particella: str | None,
    subalterno: str | None,
    sezione_catastale: str | None = None,
) -> tuple[uuid.UUID | None, str, str | None, str | None]:
    comune_codice_norm = comune_codice.strip().upper() if comune_codice else None
    foglio_norm = foglio.strip() if foglio else None
    particella_norm = particella.strip() if particella else None
    sub_norm = subalterno.strip().upper() if subalterno and subalterno.strip() else None
    sezione_norm = sezione_catastale.strip().upper() if sezione_catastale and sezione_catastale.strip() else None

    if not comune_codice_norm or not foglio_norm or not particella_norm:
        return None, "unmatched", None, "missing_match_key"

    base_conditions = [
        CatParticella.codice_catastale == comune_codice_norm,
        CatParticella.foglio == foglio_norm,
        CatParticella.particella == particella_norm,
        CatParticella.is_current.is_(True),
        CatParticella.suppressed.is_(False),
    ]
    if sezione_norm:
        base_conditions.append(func.upper(func.coalesce(CatParticella.sezione_catastale, "")) == sezione_norm)

    if sub_norm:
        exact_ids = _first_two_cat_particella_ids(
            db,
            *base_conditions,
            func.upper(func.coalesce(CatParticella.subalterno, "")) == sub_norm,
        )
        if len(exact_ids) == 1:
            return exact_ids[0], "matched", "exact_sub", None
        if len(exact_ids) > 1:
            return None, "ambiguous", None, "multiple_exact_sub_matches"

        base_ids = _first_two_cat_particella_ids(
            db,
            *base_conditions,
            func.coalesce(CatParticella.subalterno, "") == "",
        )
        if len(base_ids) == 1:
            return base_ids[0], "matched", "base_without_sub", "ruolo_sub_not_present_in_cat_particelle"
        if len(base_ids) > 1:
            return None, "ambiguous", None, "multiple_base_matches_for_ruolo_sub"

        return None, "unmatched", None, "no_cat_particella_for_sub_or_base"

    base_ids = _first_two_cat_particella_ids(
        db,
        *base_conditions,
        func.coalesce(CatParticella.subalterno, "") == "",
    )
    if len(base_ids) == 1:
        return base_ids[0], "matched", "exact_no_sub", None
    if len(base_ids) > 1:
        return None, "ambiguous", None, "multiple_base_matches"

    variant_ids = _first_two_cat_particella_ids(db, *base_conditions)
    if variant_ids:
        return None, "unmatched", None, "only_subalterno_variants_found"

    return None, "unmatched", None, "no_cat_particella_match"


def resolve_cat_particella_match(
    db: Session,
    *,
    comune_codice: str | None,
    foglio: str | None,
    particella: str | None,
    subalterno: str | None,
    sezione_catastale: str | None = None,
) -> tuple[uuid.UUID | None, str, str | None, str | None]:
    """
    Resolve a ruolo parcel to cat_particelle only when the match is deterministic.

    Subalterni: if ruolo carries a subalterno but cat_particelle only stores the
    base parcel geometry, we link to that base parcel with explicit fallback
    confidence. Arborea/Terralba are retried on the paired real GAIA comune
    because Capacitas can still expose swapped historic ownership.
    """
    result = _resolve_cat_particella_match_for_code(
        db,
        comune_codice=comune_codice,
        foglio=foglio,
        particella=particella,
        subalterno=subalterno,
        sezione_catastale=sezione_catastale,
    )
    particella_id, status, confidence, reason = result
    if particella_id is not None or status == "ambiguous":
        return result

    comune_codice_norm = comune_codice.strip().upper() if comune_codice else None
    alternate_codice = _ARBOREA_TERRALBA_SWAP_CODES.get(comune_codice_norm or "")
    if alternate_codice is None:
        return result

    swapped = _resolve_cat_particella_match_for_code(
        db,
        comune_codice=alternate_codice,
        foglio=foglio,
        particella=particella,
        subalterno=subalterno,
        sezione_catastale=sezione_catastale,
    )
    swapped_id, swapped_status, swapped_confidence, _swapped_reason = swapped
    if swapped_id is None:
        return result

    if swapped_confidence == "exact_no_sub":
        confidence = "swapped_exact_no_sub"
    elif swapped_confidence == "exact_sub":
        confidence = "swapped_exact_sub"
    elif swapped_confidence == "base_without_sub":
        confidence = "swapped_base_without_sub"
    else:
        confidence = swapped_confidence
    return swapped_id, swapped_status, confidence, "swapped_arborea_terralba"

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
    comune_nome = _normalize_partita_comune_nome(comune_nome)
    if not foglio or not particella:
        return None

    comune_codice = _resolve_comune_codice_for_ruolo(db, comune_nome)
    if not comune_codice:
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
        if existing.valid_from == anno:
            if existing.sup_catastale_are is None and sup_catastale_are is not None:
                existing.sup_catastale_are = float(sup_catastale_are)
                existing.sup_catastale_ha = float(sup_catastale_are / Decimal("100"))
                existing.updated_at = datetime.now(timezone.utc)
                db.flush()
            return existing.id

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
