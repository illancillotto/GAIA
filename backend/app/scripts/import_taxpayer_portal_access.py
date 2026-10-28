"""Import CodFisc/Utenza/PIN from the Consorzio Excel; default is a rolled-back dry run."""

import argparse
import hashlib
import json
from pathlib import Path

from app.core.database import SessionLocal
from app.modules.ruolo.services.taxpayer_portal_import import (
    import_access_rows,
    read_access_workbook,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx_path", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    rows, report = read_access_workbook(args.xlsx_path)
    digest = hashlib.sha256(args.xlsx_path.read_bytes()).hexdigest()
    with SessionLocal() as db:
        report.update(import_access_rows(db, rows, digest))
        if args.apply:
            db.commit()
        else:
            db.rollback()
    print(json.dumps({**report, "applied": args.apply, "source_sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
