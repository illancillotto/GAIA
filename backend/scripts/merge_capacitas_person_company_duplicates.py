"""
Bonifica dei soggetti persona creati da Capacitas con identificativi aziendali.

Regole:
- cerca subject/person duplicati con codice_fiscale di 11 cifre e source_system=capacitas
- trova il company corretto tramite ana_companies.partita_iva
- sposta i riferimenti sicuri al subject company
- elimina il subject/person errato solo se non rimangono riferimenti residui
- altrimenti marca il subject errato come duplicate

Uso:
    python backend/scripts/merge_capacitas_person_company_duplicates.py --dry-run
    python backend/scripts/merge_capacitas_person_company_duplicates.py --apply
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from sqlalchemy import select, text

from app.core.database import SessionLocal
from app.modules.utenze.models import (
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaSubjectType,
)
from app.modules.utenze.services.subject_identity import is_probable_vat_number


SAFE_REFERENCE_TABLES: tuple[tuple[str, str], ...] = (
    ("ana_documents", "subject_id"),
    ("ana_audit_log", "subject_id"),
    ("ana_import_job_items", "subject_id"),
    ("riordino_appeals", "appellant_subject_id"),
    ("riordino_parcel_links", "title_holder_subject_id"),
    ("riordino_party_links", "subject_id"),
    ("bonifica_user_staging", "matched_subject_id"),
    ("ruolo_avvisi", "subject_id"),
    ("cat_consorzio_occupancies", "subject_id"),
    ("cat_capacitas_intestatari", "subject_id"),
    ("cat_utenza_intestatari", "subject_id"),
    ("anpr_check_log", "subject_id"),
    ("catasto_meter_readings", "subject_id"),
    ("ana_payment_notices", "subject_id"),
)

RESIDUAL_REFERENCE_TABLES: tuple[tuple[str, str], ...] = SAFE_REFERENCE_TABLES + (
    ("ana_person_snapshots", "subject_id"),
)


@dataclass(slots=True)
class DuplicatePair:
    codice_fiscale: str
    wrong_subject_id: UUID
    company_subject_id: UUID
    wrong_name: str
    company_name: str


def load_duplicate_pairs() -> list[DuplicatePair]:
    sql = text(
        """
        SELECT
            p.codice_fiscale AS codice_fiscale,
            p.subject_id AS wrong_subject_id,
            c.subject_id AS company_subject_id,
            wrong_s.source_name_raw AS wrong_name,
            company_s.source_name_raw AS company_name
        FROM ana_persons p
        JOIN ana_subjects wrong_s ON wrong_s.id = p.subject_id
        JOIN ana_companies c ON c.partita_iva = p.codice_fiscale
        JOIN ana_subjects company_s ON company_s.id = c.subject_id
        WHERE wrong_s.source_system = 'capacitas'
          AND wrong_s.subject_type = :person_type
          AND company_s.subject_type = :company_type
        ORDER BY p.codice_fiscale
        """
    )
    with SessionLocal() as db:
        rows = db.execute(
            sql,
            {
                "person_type": AnagraficaSubjectType.PERSON.value,
                "company_type": AnagraficaSubjectType.COMPANY.value,
            },
        ).mappings()
        pairs = [
            DuplicatePair(
                codice_fiscale=row["codice_fiscale"],
                wrong_subject_id=row["wrong_subject_id"],
                company_subject_id=row["company_subject_id"],
                wrong_name=row["wrong_name"],
                company_name=row["company_name"],
            )
            for row in rows
            if is_probable_vat_number(row["codice_fiscale"])
        ]
    return pairs


def _move_references(db, *, old_id: UUID, new_id: UUID) -> dict[str, int]:
    moved: dict[str, int] = {}
    for table_name, column_name in SAFE_REFERENCE_TABLES:
        stmt = text(
            f"UPDATE {table_name} SET {column_name} = :new_id WHERE {column_name} = :old_id"
        )
        result = db.execute(stmt, {"old_id": str(old_id), "new_id": str(new_id)})
        moved[f"{table_name}.{column_name}"] = result.rowcount or 0

    db.execute(
        text(
            """
            UPDATE cat_utenza_intestatari
            SET partita_iva = codice_fiscale
            WHERE subject_id = :new_id
              AND (partita_iva IS NULL OR partita_iva = '')
              AND codice_fiscale ~ '^[0-9]{11}$'
            """
        ),
        {"new_id": str(new_id)},
    )
    return moved


def _count_residual_references(db, *, subject_id: UUID) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name, column_name in RESIDUAL_REFERENCE_TABLES:
        count = db.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = :subject_id"),
            {"subject_id": str(subject_id)},
        ).scalar_one()
        counts[f"{table_name}.{column_name}"] = int(count)
    return counts


def _mark_duplicate_subject(
    db,
    *,
    wrong_subject: AnagraficaSubject,
    company_subject_id: UUID,
) -> None:
    marker = f"[MERGED->{company_subject_id}]"
    if marker not in wrong_subject.source_name_raw:
        wrong_subject.source_name_raw = f"{wrong_subject.source_name_raw} {marker}".strip()
    wrong_subject.status = AnagraficaSubjectStatus.DUPLICATE.value
    wrong_subject.requires_review = True


def _delete_wrong_subject(db, *, wrong_subject_id: UUID) -> None:
    wrong_person = db.get(AnagraficaPerson, wrong_subject_id)
    if wrong_person is not None:
        db.delete(wrong_person)
        db.flush()
    wrong_subject = db.get(AnagraficaSubject, wrong_subject_id)
    if wrong_subject is not None:
        db.delete(wrong_subject)
        db.flush()


def merge_duplicates(*, apply: bool) -> dict[str, int]:
    pairs = load_duplicate_pairs()
    stats = {
        "pairs": len(pairs),
        "moved_refs": 0,
        "deleted_subjects": 0,
        "marked_duplicates": 0,
    }

    with SessionLocal() as db:
        for pair in pairs:
            wrong_subject = db.get(AnagraficaSubject, pair.wrong_subject_id)
            if wrong_subject is None:
                continue

            moved = _move_references(
                db,
                old_id=pair.wrong_subject_id,
                new_id=pair.company_subject_id,
            )
            moved_total = sum(moved.values())
            stats["moved_refs"] += moved_total

            residual = _count_residual_references(db, subject_id=pair.wrong_subject_id)
            residual_total = sum(residual.values())

            print(
                f"{pair.codice_fiscale} wrong={pair.wrong_subject_id} company={pair.company_subject_id} "
                f"moved={moved_total} residual={residual_total}"
            )

            if residual_total == 0:
                _delete_wrong_subject(db, wrong_subject_id=pair.wrong_subject_id)
                stats["deleted_subjects"] += 1
            else:
                _mark_duplicate_subject(
                    db,
                    wrong_subject=wrong_subject,
                    company_subject_id=pair.company_subject_id,
                )
                stats["marked_duplicates"] += 1

        if apply:
            db.commit()
        else:
            db.rollback()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Applica la bonifica.")
    parser.add_argument("--dry-run", action="store_true", help="Esegue solo anteprima.")
    args = parser.parse_args()

    apply = bool(args.apply and not args.dry_run)
    stats = merge_duplicates(apply=apply)
    mode = "apply" if apply else "dry-run"
    print(
        f"Merge duplicati completato ({mode}). "
        f"pairs={stats['pairs']} moved_refs={stats['moved_refs']} "
        f"deleted_subjects={stats['deleted_subjects']} marked_duplicates={stats['marked_duplicates']}"
    )


if __name__ == "__main__":
    main()
