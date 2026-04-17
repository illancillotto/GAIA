from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import openpyxl
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaXlsxImportBatch,
    AnagraficaXlsxImportBatchStatus,
)

XLSX_SOURCE_SYSTEM = "xlsx_import"
ANOMALIA_EXTERNAL_ID = "ANOMALIA-999"
CHUNK_SIZE = 500

# Mapping intestazione Excel → chiave normalizzata
COLUMN_MAP: dict[str, str] = {
    "Denominazione": "denominazione",
    "Cognome": "cognome",
    "Nome": "nome",
    "Tipo": "tipo",
    "Sesso": "sesso",
    "Dat. nas.": "data_nascita",
    "Belfiore nas.": "belfiore_nascita",
    "Luogo nas.": "luogo_nascita",
    "Loca. nas.": "localita_nascita",
    "Prov. nas.": "prov_nascita",
    "Belfiore nas. est.": "belfiore_nascita_est",
    "Luogo nas. est.": "luogo_nascita_est",
    "Loca. nas. est.": "localita_nascita_est",
    "Prov. nas. est.": "prov_nascita_est",
    "Cod.Fisc.": "codice_fiscale",
    "P.IVA": "partita_iva",
    "Belfiore sede": "belfiore_sede",
    "Sede": "sede",
    "Topon. res.": "topon_res",
    "Indir. res.": "indirizzo_res",
    "Civico res.": "civico_res",
    "Sub Civ. res.": "sub_civ_res",
    "CAP res.": "cap_res",
    "Belfiore res.": "belfiore_res",
    "Città res.": "citta_res",
    "Prov. res.": "prov_res",
    "Loca. res.": "localita_res",
    "Topon. dom.": "topon_dom",
    "Indir. dom.": "indirizzo_dom",
    "Civico dom.": "civico_dom",
    "Sub Civ. dom.": "sub_civ_dom",
    "CAP dom.": "cap_dom",
    "Belfiore dom.": "belfiore_dom",
    "Città dom.": "citta_dom",
    "Prov. dom.": "prov_dom",
    "Loca. dom.": "localita_dom",
    "Topon. presso": "topon_presso",
    "Indir. presso": "indirizzo_presso",
    "Civico presso": "civico_presso",
    "Sub Civ. presso": "sub_civ_presso",
    "CAP presso": "cap_presso",
    "Belfiore presso": "belfiore_presso",
    "Città presso": "citta_presso",
    "Prov. presso": "prov_presso",
    "Loca. presso": "localita_presso",
    "Tel.": "telefono",
    "Fax": "fax",
    "Mobile": "mobile",
    "Ufficio": "ufficio",
    "Email": "email",
    "PEC": "pec",
    "Stato": "stato",
}


@dataclass
class XlsxImportResult:
    batch_id: uuid.UUID
    total_rows: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    anomalies: int = 0
    errors: int = 0
    error_log: list[dict[str, Any]] = field(default_factory=list)


def run_xlsx_import(
    db: Session,
    batch_id: uuid.UUID,
    file_bytes: bytes,
    current_user: ApplicationUser,
) -> None:
    """Eseguito in background. Aggiorna il batch in DB man mano che processa."""
    batch = db.get(AnagraficaXlsxImportBatch, batch_id)
    if batch is None:
        return

    batch.status = AnagraficaXlsxImportBatchStatus.RUNNING.value
    batch.started_at = datetime.now(UTC)
    db.add(batch)
    db.commit()

    result = XlsxImportResult(batch_id=batch_id)

    try:
        rows = _parse_xlsx(file_bytes)
        result.total_rows = len(rows)

        batch.total_rows = result.total_rows
        db.add(batch)
        db.commit()

        for chunk_start in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[chunk_start: chunk_start + CHUNK_SIZE]
            _process_chunk(db, chunk, chunk_start, current_user, result)

            batch.processed_rows = min(chunk_start + CHUNK_SIZE, result.total_rows)
            batch.inserted = result.inserted
            batch.updated = result.updated
            batch.unchanged = result.unchanged
            batch.anomalies = result.anomalies
            batch.errors = result.errors
            db.add(batch)
            db.commit()

        batch.status = AnagraficaXlsxImportBatchStatus.COMPLETED.value

    except Exception as exc:
        batch.status = AnagraficaXlsxImportBatchStatus.FAILED.value
        result.error_log.append({"row": 0, "message": f"Errore fatale: {exc}", "denominazione": ""})

    batch.processed_rows = result.total_rows
    batch.inserted = result.inserted
    batch.updated = result.updated
    batch.unchanged = result.unchanged
    batch.anomalies = result.anomalies
    batch.errors = result.errors
    batch.error_log = result.error_log or None
    batch.completed_at = datetime.now(UTC)
    db.add(batch)
    db.commit()


def _parse_xlsx(file_bytes: bytes) -> list[dict[str, Any]]:
    import io
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    raw_headers = next(rows_iter, None)
    if raw_headers is None:
        raise ValueError("File Excel privo di intestazione")

    headers = [str(h).strip() if h is not None else "" for h in raw_headers]
    col_index: dict[str, int] = {}
    for original, normalized in COLUMN_MAP.items():
        try:
            col_index[normalized] = headers.index(original)
        except ValueError:
            pass

    result: list[dict[str, Any]] = []
    for raw_row in rows_iter:
        row: dict[str, Any] = {}
        for normalized, idx in col_index.items():
            if idx < len(raw_row):
                val = raw_row[idx]
                if isinstance(val, str):
                    val = val.strip() or None
                row[normalized] = val
            else:
                row[normalized] = None
        result.append(row)

    wb.close()
    return result


def _process_chunk(
    db: Session,
    chunk: list[dict[str, Any]],
    chunk_start: int,
    current_user: ApplicationUser,
    result: XlsxImportResult,
) -> None:
    for offset, row in enumerate(chunk):
        row_number = chunk_start + offset + 2  # +2: header row + 1-based
        try:
            outcome = _upsert_row(db, row, row_number, current_user)
            if outcome == "inserted":
                result.inserted += 1
            elif outcome == "updated":
                result.updated += 1
            elif outcome == "unchanged":
                result.unchanged += 1
            elif outcome == "anomaly":
                result.anomalies += 1
        except Exception as exc:
            result.errors += 1
            denominazione = str(row.get("denominazione") or row.get("codice_fiscale") or f"riga {row_number}")
            result.error_log.append({
                "row": row_number,
                "message": str(exc),
                "denominazione": denominazione,
            })


def _upsert_row(
    db: Session,
    row: dict[str, Any],
    row_number: int,
    current_user: ApplicationUser,
) -> str:
    tipo = _clean(row.get("tipo")) or "F"
    is_person = tipo.upper() == "F"

    cf = _normalize_id(row.get("codice_fiscale"))
    piva = _normalize_id(row.get("partita_iva"))

    is_anomaly = not cf and not piva
    if is_anomaly:
        return _upsert_anomaly(db, row, row_number, current_user)

    try:
        with db.begin_nested():
            if is_person:
                return _upsert_person(db, row, cf, current_user)
            else:
                return _upsert_company(db, row, cf, piva, current_user)
    except IntegrityError:
        # Riga già presente (UniqueViolation): lookup forzato e aggiornamento
        with db.begin_nested():
            if is_person:
                existing = _find_person_by_cf(db, cf)
                if existing is None:
                    raise
                return _upsert_person(db, row, cf, current_user)
            else:
                existing_c = _find_company(db, cf, piva)
                if existing_c is None:
                    raise
                return _upsert_company(db, row, cf, piva, current_user)


def _upsert_person(
    db: Session,
    row: dict[str, Any],
    cf: str,
    current_user: ApplicationUser,
) -> str:
    cognome = _clean(row.get("cognome")) or _clean(row.get("denominazione")) or "SCONOSCIUTO"
    nome = _clean(row.get("nome")) or ""

    existing_person = _find_person_by_cf(db, cf)
    subject = db.get(AnagraficaSubject, existing_person.subject_id) if existing_person else None
    was_created = subject is None

    now = datetime.now(UTC)
    source_name_raw = f"{cognome} {nome}".strip() or cf

    new_data = {
        "cognome": cognome,
        "nome": nome,
        "codice_fiscale": cf,
        "data_nascita": _parse_date(row.get("data_nascita")),
        "comune_nascita": _clean(row.get("luogo_nascita")) or _clean(row.get("luogo_nascita_est")),
        "indirizzo": _build_address(row),
        "comune_residenza": _build_city(row.get("citta_res"), row.get("prov_res")),
        "cap": _clean(row.get("cap_res")),
        "email": _clean(row.get("email")),
        "telefono": _clean(row.get("mobile")) or _clean(row.get("telefono")),
        "note": _build_person_note(row),
    }

    if subject is None:
        subject = AnagraficaSubject(
            subject_type="person",
            status=_resolve_status(row),
            source_system=XLSX_SOURCE_SYSTEM,
            source_name_raw=source_name_raw,
            nas_folder_letter=_derive_letter(cognome),
            requires_review=False,
            imported_at=now,
        )
        db.add(subject)
        db.flush()

        person = AnagraficaPerson(subject_id=subject.id, **new_data)
        db.add(person)
        db.add(AnagraficaAuditLog(
            subject_id=subject.id,
            changed_by_user_id=current_user.id,
            action="xlsx_import_created",
            diff_json={"before": None, "after": _json_safe(new_data)},
        ))
        db.flush()
        return "inserted"

    # Soggetto esistente: controlla se i dati sono cambiati
    old_data = _person_snapshot(existing_person)
    new_hash = _hash_dict(new_data)
    old_hash = _hash_dict(old_data)

    if new_hash == old_hash:
        return "unchanged"

    # Aggiorna
    subject.source_name_raw = source_name_raw
    subject.status = _resolve_status(row)
    subject.source_system = XLSX_SOURCE_SYSTEM
    subject.imported_at = now
    db.add(subject)

    for key, val in new_data.items():
        setattr(existing_person, key, val)
    db.add(existing_person)

    db.add(AnagraficaAuditLog(
        subject_id=subject.id,
        changed_by_user_id=current_user.id,
        action="xlsx_import_updated",
        diff_json={"before": _json_safe(old_data), "after": _json_safe(new_data)},
    ))
    db.flush()
    return "updated"


def _upsert_company(
    db: Session,
    row: dict[str, Any],
    cf: str | None,
    piva: str | None,
    current_user: ApplicationUser,
) -> str:
    ragione_sociale = (
        _clean(row.get("denominazione"))
        or _clean(row.get("cognome"))
        or piva
        or cf
        or "SCONOSCIUTO"
    )

    existing_company = _find_company(db, cf, piva)
    subject = db.get(AnagraficaSubject, existing_company.subject_id) if existing_company else None
    was_created = subject is None

    now = datetime.now(UTC)

    new_data = {
        "ragione_sociale": ragione_sociale,
        "partita_iva": piva or cf or "",
        "codice_fiscale": cf if cf != piva else None,
        "forma_giuridica": None,
        "sede_legale": _build_address(row),
        "comune_sede": _build_city(row.get("citta_res"), row.get("prov_res")),
        "cap": _clean(row.get("cap_res")),
        "email_pec": _clean(row.get("pec")) or _clean(row.get("email")),
        "telefono": _clean(row.get("mobile")) or _clean(row.get("telefono")),
        "note": _build_company_note(row),
    }

    if subject is None:
        subject = AnagraficaSubject(
            subject_type="company",
            status=_resolve_status(row),
            source_system=XLSX_SOURCE_SYSTEM,
            source_name_raw=ragione_sociale,
            nas_folder_letter=_derive_letter(ragione_sociale),
            requires_review=False,
            imported_at=now,
        )
        db.add(subject)
        db.flush()

        company = AnagraficaCompany(subject_id=subject.id, **new_data)
        db.add(company)
        db.add(AnagraficaAuditLog(
            subject_id=subject.id,
            changed_by_user_id=current_user.id,
            action="xlsx_import_created",
            diff_json={"before": None, "after": _json_safe(new_data)},
        ))
        db.flush()
        return "inserted"

    old_data = _company_snapshot(existing_company)
    new_hash = _hash_dict(new_data)
    old_hash = _hash_dict(old_data)

    if new_hash == old_hash:
        return "unchanged"

    subject.source_name_raw = ragione_sociale
    subject.status = _resolve_status(row)
    subject.source_system = XLSX_SOURCE_SYSTEM
    subject.imported_at = now
    db.add(subject)

    for key, val in new_data.items():
        setattr(existing_company, key, val)
    db.add(existing_company)

    db.add(AnagraficaAuditLog(
        subject_id=subject.id,
        changed_by_user_id=current_user.id,
        action="xlsx_import_updated",
        diff_json={"before": _json_safe(old_data), "after": _json_safe(new_data)},
    ))
    db.flush()
    return "updated"


def _upsert_anomaly(
    db: Session,
    row: dict[str, Any],
    row_number: int,
    current_user: ApplicationUser,
) -> str:
    denominazione = (
        _clean(row.get("denominazione"))
        or _clean(row.get("cognome"))
        or f"ANOMALIA riga {row_number}"
    )
    now = datetime.now(UTC)

    subject = AnagraficaSubject(
        subject_type="unknown",
        status=AnagraficaSubjectStatus.ACTIVE.value,
        source_system=XLSX_SOURCE_SYSTEM,
        source_external_id=ANOMALIA_EXTERNAL_ID,
        source_name_raw=denominazione,
        requires_review=True,
        imported_at=now,
    )
    db.add(subject)
    db.flush()

    db.add(AnagraficaAuditLog(
        subject_id=subject.id,
        changed_by_user_id=current_user.id,
        action="xlsx_import_anomaly",
        diff_json={"row_number": row_number, "denominazione": denominazione, "raw": _safe_row(row)},
    ))
    db.flush()
    return "anomaly"


# ── helpers ──────────────────────────────────────────────────────────────────

def _clean(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _normalize_id(value: Any) -> str:
    cleaned = re.sub(r"\s+", "", str(value or "").strip().upper())
    return cleaned if len(cleaned) >= 4 else ""


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _build_address(row: dict[str, Any]) -> str | None:
    topon = _clean(row.get("topon_res"))
    via = _clean(row.get("indirizzo_res"))
    civico = _clean(row.get("civico_res"))
    parts = [p for p in [topon, via, civico] if p]
    return " ".join(parts) or None


def _build_city(city: Any, province: Any) -> str | None:
    c = _clean(city)
    p = _clean(province)
    if c and p:
        return f"{c} ({p.upper()})"
    return c or p


def _resolve_status(row: dict[str, Any]) -> str:
    stato = (_clean(row.get("stato")) or "").upper()
    if stato in {"INATTIVO", "CESSATO", "DECEDUTO", "DECEDUTA"}:
        return AnagraficaSubjectStatus.INACTIVE.value
    return AnagraficaSubjectStatus.ACTIVE.value


def _derive_letter(name: str) -> str | None:
    for ch in name.strip():
        if ch.isalpha():
            return ch.upper()
    return None


def _find_person_by_cf(db: Session, cf: str) -> AnagraficaPerson | None:
    return db.scalar(
        select(AnagraficaPerson).where(
            func.upper(func.replace(AnagraficaPerson.codice_fiscale, " ", "")) == cf
        )
    )


def _find_company(db: Session, cf: str | None, piva: str | None) -> AnagraficaCompany | None:
    if piva:
        found = db.scalar(
            select(AnagraficaCompany).where(
                func.upper(func.replace(AnagraficaCompany.partita_iva, " ", "")) == piva
            )
        )
        if found:
            return found
    if cf:
        # cerca per codice_fiscale
        found = db.scalar(
            select(AnagraficaCompany).where(
                func.upper(func.replace(func.coalesce(AnagraficaCompany.codice_fiscale, ""), " ", "")) == cf
            )
        )
        if found:
            return found
        # fallback: CF usato come partita_iva (P.IVA era vuota nel file)
        found = db.scalar(
            select(AnagraficaCompany).where(
                func.upper(func.replace(AnagraficaCompany.partita_iva, " ", "")) == cf
            )
        )
        if found:
            return found
    return None


def _person_snapshot(p: AnagraficaPerson) -> dict[str, Any]:
    return {
        "cognome": p.cognome,
        "nome": p.nome,
        "codice_fiscale": p.codice_fiscale,
        "data_nascita": p.data_nascita.isoformat() if p.data_nascita else None,
        "comune_nascita": p.comune_nascita,
        "indirizzo": p.indirizzo,
        "comune_residenza": p.comune_residenza,
        "cap": p.cap,
        "email": p.email,
        "telefono": p.telefono,
        "note": p.note,
    }


def _company_snapshot(c: AnagraficaCompany) -> dict[str, Any]:
    return {
        "ragione_sociale": c.ragione_sociale,
        "partita_iva": c.partita_iva,
        "codice_fiscale": c.codice_fiscale,
        "forma_giuridica": c.forma_giuridica,
        "sede_legale": c.sede_legale,
        "comune_sede": c.comune_sede,
        "cap": c.cap,
        "email_pec": c.email_pec,
        "telefono": c.telefono,
        "note": c.note,
    }


def _hash_dict(d: dict[str, Any]) -> str:
    serialized = json.dumps(d, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode()).hexdigest()


def _json_safe(d: dict[str, Any]) -> dict[str, Any]:
    """Converte i valori non-serializzabili (date, datetime) in stringhe per diff_json."""
    return {k: v.isoformat() if isinstance(v, (date, datetime)) else v for k, v in d.items()}


def _build_person_note(row: dict[str, Any]) -> str | None:
    parts = []
    sesso = _clean(row.get("sesso"))
    if sesso:
        parts.append(f"Sesso: {sesso}")
    stato = _clean(row.get("stato"))
    if stato:
        parts.append(f"Stato: {stato}")
    dom = _build_address_dom(row)
    if dom:
        parts.append(f"Domicilio: {dom}")
    return "\n".join(parts) or None


def _build_company_note(row: dict[str, Any]) -> str | None:
    stato = _clean(row.get("stato"))
    if stato:
        return f"Stato: {stato}"
    return None


def _build_address_dom(row: dict[str, Any]) -> str | None:
    parts = [
        p for p in [
            _clean(row.get("topon_dom")),
            _clean(row.get("indirizzo_dom")),
            _clean(row.get("civico_dom")),
            _build_city(row.get("citta_dom"), row.get("prov_dom")),
        ] if p
    ]
    return " ".join(parts) or None


def _safe_row(row: dict[str, Any]) -> dict[str, str | None]:
    return {k: str(v) if v is not None else None for k, v in row.items()}


def row_number_from_cf(cf: str) -> str:
    return cf
