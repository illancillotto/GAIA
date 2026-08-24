#!/usr/bin/env python
"""Classifica il contenuto dei PDF Catasto gia archiviati."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.modules.catasto.services.ade_document_audit_backfill import backfill_document_audits  # noqa: E402


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("deve essere maggiore di zero")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Scrive i risultati; il default e dry-run.")
    parser.add_argument("--batch-id", type=UUID, help="Limita il backfill a un batch.")
    parser.add_argument("--limit", type=_positive_int, help="Limita il numero di documenti selezionati.")
    parser.add_argument("--commit-every", type=_positive_int, default=100, help="Documenti per transazione.")
    parser.add_argument("--force", action="store_true", help="Ricalcola anche audit gia valorizzati.")
    args = parser.parse_args()

    with SessionLocal() as db:
        counters = backfill_document_audits(
            db,
            batch_id=args.batch_id,
            limit=args.limit,
            force=args.force,
            dry_run=not args.apply,
            commit_every=args.commit_every,
        )
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Backfill audit documenti Catasto completato ({mode})")
    for key, value in sorted(counters.items()):
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
