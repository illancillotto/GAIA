from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.catasto import CatastoDocument, CatastoSisterExtraction
from app.services.sister_visura_extractions import persist_sister_visura

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse and persist existing SISTER PDF snapshots")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-failed", action="store_true")
    args = parser.parse_args()
    processed = skipped = failed = missing = 0
    with SessionLocal() as db:
        statement = select(CatastoDocument).order_by(CatastoDocument.created_at, CatastoDocument.id)
        if not args.include_failed:
            statement = statement.where(
                ~CatastoDocument.id.in_(select(CatastoSisterExtraction.document_id))
            )
        if args.limit is not None:
            statement = statement.limit(max(args.limit, 0))
        for document in db.scalars(statement):
            path = Path(document.filepath)
            if not path.exists() or path.suffix.casefold() != ".pdf":
                missing += 1
                continue
            try:
                extraction = persist_sister_visura(db, document)
                db.commit()
                processed += 1
                if extraction.status == "failed":
                    failed += 1
                elif extraction.status == "review_required":
                    skipped += 1
            except Exception:
                db.rollback()
                failed += 1
                logger.exception("SISTER backfill failed for document %s", document.id)
    print(f"processed={processed} review_required={skipped} failed={failed} missing={missing}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
