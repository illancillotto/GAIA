#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal  # noqa: E402 - direct script bootstrap
from app.models.application_user import (  # noqa: E402 - direct script bootstrap
    ApplicationUser,  # noqa: F401 - register collaborator FK targets
)
from app.modules.presenze.services.tax_code_import import (  # noqa: E402
    TaxCodeImportError,
    extract_tax_codes,
    import_tax_codes,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importa i codici fiscali dei collaboratori Presenze da un XLSM."
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--company-code", default="53")
    parser.add_argument("--employee-code", action="append", dest="employee_codes")
    parser.add_argument(
        "--apply", action="store_true", help="Salva le variazioni; il default e dry-run."
    )
    parser.add_argument("--manifest", type=Path, help="Scrive il manifest locale dell'operazione.")
    args = parser.parse_args()
    if not args.workbook.exists():
        parser.error(f"File non trovato: {args.workbook}")
    if args.apply and not args.employee_codes:
        parser.error("Per --apply indicare almeno un --employee-code (oppure eseguire un dry-run).")

    if args.apply and not args.manifest:
        parser.error("Per --apply indicare --manifest per registrare provenienza e variazioni.")
    entries = extract_tax_codes(args.workbook)
    if args.employee_codes:
        selected = set(args.employee_codes)
        missing = selected - {entry.employee_code for entry in entries}
        if missing:
            parser.error(f"Matricole senza CF nel file: {sorted(missing)}")
        entries = [entry for entry in entries if entry.employee_code in selected]
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "workbook": str(args.workbook),
        "workbook_sha256": _sha256(args.workbook),
        "company_code": args.company_code,
        "employee_codes": [entry.employee_code for entry in entries],
        "sources": {
            entry.employee_code: {"tax_code": entry.tax_code, "source": entry.source}
            for entry in entries
        },
    }

    def record_plan(report, changes):
        manifest["report"] = {**report, "mode": "prepared"}
        manifest["changes"] = [
            {
                "collaborator_id": str(person.id),
                "application_user_id": person.application_user_id,
                "employee_code": person.employee_code,
                "before": person.tax_code,
                "after": code,
            }
            for person, code in changes
        ]
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    try:
        with SessionLocal() as db:
            report = import_tax_codes(
                db,
                entries,
                apply=args.apply,
                company_code=args.company_code,
                before_commit=record_plan,
            )
    except TaxCodeImportError as exc:
        print(json.dumps({**exc.report, "mode": "apply-blocked"}, indent=2, sort_keys=True))
        return 2
    report["mode"] = "apply" if args.apply else "dry-run"
    manifest["report"] = report
    if args.manifest:
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["conflicts"] or report["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
