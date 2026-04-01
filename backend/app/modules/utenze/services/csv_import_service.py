from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
import io
import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
)


CSV_IMPORT_MARKER = "[CSV IMPORT]"
CSV_REQUIRED_HEADERS = {
    "CODICE_FISCALE",
    "COGNOME",
    "NOME",
}


@dataclass(slots=True)
class CsvImportError:
    row_number: int
    message: str
    codice_fiscale: str | None = None


@dataclass(slots=True)
class CsvImportResult:
    total_rows: int = 0
    created_subjects: int = 0
    updated_subjects: int = 0
    skipped_rows: int = 0
    errors: list[CsvImportError] = field(default_factory=list)


def import_subjects_from_csv(
    db: Session,
    current_user: ApplicationUser,
    file_bytes: bytes,
) -> CsvImportResult:
    text_stream = io.StringIO(file_bytes.decode("utf-8-sig"))
    reader = csv.DictReader(text_stream, delimiter=";")
    if reader.fieldnames is None:
        raise ValueError("CSV privo di intestazione")

    normalized_fieldnames = [_normalize_header(item) for item in reader.fieldnames]
    missing_headers = sorted(CSV_REQUIRED_HEADERS.difference(normalized_fieldnames))
    if missing_headers:
        raise ValueError(f"CSV con intestazione incompleta: mancano {', '.join(missing_headers)}")
    reader.fieldnames = normalized_fieldnames

    result = CsvImportResult()
    for row_index, raw_row in enumerate(reader, start=2):
        row = {_normalize_header(key): (value or "").strip() for key, value in raw_row.items() if key is not None}
        if not any(row.values()):
            continue

        result.total_rows += 1
        codice_fiscale = _normalize_codice_fiscale(row.get("CODICE_FISCALE"))
        cognome = row.get("COGNOME", "").strip()
        nome = row.get("NOME", "").strip()

        if not codice_fiscale or not cognome or not nome:
            result.skipped_rows += 1
            result.errors.append(
                CsvImportError(
                    row_number=row_index,
                    codice_fiscale=codice_fiscale or None,
                    message="Riga priva di Codice Fiscale, Cognome o Nome",
                )
            )
            continue

        try:
            with db.begin_nested():
                imported_at = datetime.now(UTC)
                person = _find_person_by_codice_fiscale(db, codice_fiscale)
                subject = db.get(AnagraficaSubject, person.subject_id) if person is not None else None
                was_created = subject is None

                if subject is None:
                    subject = AnagraficaSubject(
                        subject_type="person",
                        status=_resolve_subject_status(row),
                        source_name_raw=f"{cognome} {nome} {codice_fiscale}".strip(),
                        nas_folder_path=None,
                        nas_folder_letter=_derive_letter(cognome, nome),
                        requires_review=_requires_review(row),
                        imported_at=imported_at,
                    )
                    db.add(subject)
                    db.flush()
                else:
                    subject.subject_type = "person"
                    subject.status = _resolve_subject_status(row)
                    subject.source_name_raw = f"{cognome} {nome} {codice_fiscale}".strip()
                    subject.nas_folder_letter = _derive_letter(cognome, nome)
                    subject.requires_review = _requires_review(row)
                    subject.imported_at = imported_at
                    db.add(subject)
                    db.flush()

                person_model = person or AnagraficaPerson(
                    subject_id=subject.id,
                    cognome=cognome,
                    nome=nome,
                    codice_fiscale=codice_fiscale,
                )
                person_model.cognome = cognome
                person_model.nome = nome
                person_model.codice_fiscale = codice_fiscale
                person_model.data_nascita = _parse_date(row.get("DATA_NASCITA"))
                person_model.comune_nascita = _nullable(row.get("COM_NASCITA"))
                person_model.indirizzo = _nullable(row.get("INDIRIZZO_RESIDENZA"))
                person_model.comune_residenza = _merge_city_with_province(row.get("COM_RESIDENZA"), row.get("PR"))
                person_model.cap = _nullable(row.get("CAP"))
                person_model.note = _merge_csv_metadata_note(
                    person_model.note,
                    sesso=_nullable(row.get("SESSO")),
                    variaz_anagr=_nullable(row.get("VARIAZ_ANAGR")),
                    stato_csv=_nullable(row.get("STATO")),
                    decesso=_nullable(row.get("DECESSO")),
                )
                db.add(person_model)

                db.add(
                    AnagraficaAuditLog(
                        subject_id=subject.id,
                        changed_by_user_id=current_user.id,
                        action="csv_import_created" if was_created else "csv_import_updated",
                        diff_json={"row_number": row_index, "csv_row": row},
                    )
                )
                db.flush()
        except IntegrityError:
            result.skipped_rows += 1
            result.errors.append(
                CsvImportError(
                    row_number=row_index,
                    codice_fiscale=codice_fiscale,
                    message="Riga non importata per conflitto su codice fiscale gia esistente",
                )
            )
            continue

        if was_created:
            result.created_subjects += 1
        else:
            result.updated_subjects += 1

    db.commit()
    return result


def _normalize_codice_fiscale(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


def _find_person_by_codice_fiscale(db: Session, codice_fiscale: str) -> AnagraficaPerson | None:
    normalized_cf = _normalize_codice_fiscale(codice_fiscale)
    return db.scalar(
        select(AnagraficaPerson).where(
            func.upper(func.replace(AnagraficaPerson.codice_fiscale, " ", "")) == normalized_cf
        )
    )


def _normalize_header(value: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", value.strip().upper())
    return normalized.strip("_")


def _nullable(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _parse_date(value: str | None) -> date | None:
    normalized = (value or "").strip()
    if not normalized:
        return None

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    return None


def _derive_letter(cognome: str, nome: str) -> str | None:
    source = f"{cognome}{nome}".strip()
    for char in source:
        if char.isalpha():
            return char.upper()
    return None


def _merge_city_with_province(city: str | None, province: str | None) -> str | None:
    normalized_city = _nullable(city)
    normalized_province = _nullable(province)
    if normalized_city and normalized_province:
        return f"{normalized_city} ({normalized_province.upper()})"
    return normalized_city or normalized_province


def _truthy(value: str | None) -> bool:
    normalized = (value or "").strip().upper()
    return normalized in {"1", "S", "SI", "TRUE", "Y", "YES", "DECEDUTO", "DECEDUTA"}


def _resolve_subject_status(row: dict[str, str]) -> str:
    stato = (row.get("STATO") or "").strip().upper()
    if _truthy(row.get("DECESSO")):
        return AnagraficaSubjectStatus.INACTIVE.value
    if stato in {"INATTIVO", "CESSATO", "DECEDUTO", "DECEDUTA"}:
        return AnagraficaSubjectStatus.INACTIVE.value
    return AnagraficaSubjectStatus.ACTIVE.value


def _requires_review(row: dict[str, str]) -> bool:
    variaz = (row.get("VARIAZ_ANAGR") or "").strip()
    return bool(variaz) or _truthy(row.get("DECESSO"))


def _merge_csv_metadata_note(
    existing_note: str | None,
    *,
    sesso: str | None,
    variaz_anagr: str | None,
    stato_csv: str | None,
    decesso: str | None,
) -> str | None:
    metadata_lines = []
    if sesso:
        metadata_lines.append(f"Sesso: {sesso}")
    if variaz_anagr:
        metadata_lines.append(f"Variaz_Anagr: {variaz_anagr}")
    if stato_csv:
        metadata_lines.append(f"STATO: {stato_csv}")
    if decesso:
        metadata_lines.append(f"Decesso: {decesso}")

    if not metadata_lines:
        return existing_note

    base_note = (existing_note or "").strip()
    if CSV_IMPORT_MARKER in base_note:
        base_note = base_note.split(CSV_IMPORT_MARKER, maxsplit=1)[0].rstrip()

    csv_block = f"{CSV_IMPORT_MARKER}\n" + "\n".join(metadata_lines)
    if base_note:
        return f"{base_note}\n\n{csv_block}"
    return csv_block
