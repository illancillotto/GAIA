"""
Riallinea ruolo_avvisi.subject_id verso il soggetto company corretto per
identificativi aziendali finiti su soggetti person.

Uso:
    python backend/scripts/backfill_ruolo_company_subjects.py --dry-run
    python backend/scripts/backfill_ruolo_company_subjects.py --apply
"""
from __future__ import annotations

import argparse

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.ruolo.models import RuoloAvviso
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject, AnagraficaSubjectType
from app.modules.utenze.services.subject_identity import is_probable_vat_number, normalize_tax_identifier


def backfill(*, apply: bool) -> int:
    updated = 0
    inspected = 0

    with SessionLocal() as db:
        avvisi = db.scalars(select(RuoloAvviso)).all()
        for avviso in avvisi:
            identifier = normalize_tax_identifier(avviso.codice_fiscale_raw)
            if not is_probable_vat_number(identifier):
                continue

            inspected += 1
            company = db.scalar(select(AnagraficaCompany).where(AnagraficaCompany.partita_iva == identifier))
            if company is None:
                company = db.scalar(select(AnagraficaCompany).where(AnagraficaCompany.codice_fiscale == identifier))
            if company is None:
                continue

            current_subject = db.get(AnagraficaSubject, avviso.subject_id) if avviso.subject_id else None
            if current_subject is not None and current_subject.id == company.subject_id:
                continue

            current_person = db.get(AnagraficaPerson, current_subject.id) if current_subject is not None else None
            if current_subject is not None and current_subject.subject_type == AnagraficaSubjectType.COMPANY.value:
                continue
            if current_subject is not None and current_person is None and current_subject.subject_type != AnagraficaSubjectType.PERSON.value:
                continue

            print(
                f"{avviso.codice_cnc} anno={avviso.anno_tributario} "
                f"cf_piva={identifier} from={avviso.subject_id} to={company.subject_id}"
            )
            updated += 1
            if apply:
                avviso.subject_id = company.subject_id

        if apply:
            db.commit()
        else:
            db.rollback()

    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Applica le modifiche invece del dry-run.")
    args = parser.parse_args()

    updated = backfill(apply=args.apply)
    mode = "apply" if args.apply else "dry-run"
    print(f"Backfill ruolo_avvisi.subject_id completato ({mode}). record_coinvolti={updated}")


if __name__ == "__main__":
    main()
