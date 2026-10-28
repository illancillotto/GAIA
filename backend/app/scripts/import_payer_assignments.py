"""Load who pays which avviso from a CSV (avviso_id;avviso;cf_pagatore;motivo;note).

Rows whose payer is already active are skipped; payers missing from GAIA are
reported and left out. Without ``--apply`` nothing is written.
"""

from __future__ import annotations

import argparse
import csv
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.ruolo.services import payer_assignments


def import_rows(db: Session, rows: list[dict[str, str]]) -> list[str]:
    report = []
    for row in rows:
        avviso_id = uuid.UUID(row["avviso_id"])
        tax_code = row["cf_pagatore"].strip().upper()
        if payer_assignments.payer_tax_code(db, avviso_id) == tax_code:
            report.append(f"{row['avviso']}: gia collegato a {tax_code}")
            continue
        try:
            payer_assignments.assign(
                db,
                avviso_id=avviso_id,
                payer_tax_code=tax_code,
                reason=row["motivo"].strip(),
                notes=row.get("note"),
                user_id=None,
            )
        except (LookupError, ValueError) as exc:
            report.append(f"{row['avviso']}: SALTATO - {exc}")
            continue
        report.append(f"{row['avviso']}: collegato a {tax_code}")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    with args.csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    with SessionLocal() as db:
        for line in import_rows(db, rows):
            print(line)
        if args.apply:
            db.commit()
            print("APPLIED")
        else:
            db.rollback()
            print("DRY RUN: nessuna modifica salvata (usa --apply)")


if __name__ == "__main__":
    main()
