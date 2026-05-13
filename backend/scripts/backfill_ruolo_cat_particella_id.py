#!/usr/bin/env python
"""Backfill ruolo_particelle.cat_particella_id from catasto_parcels/cat_particelle.

Usage:
    python backend/scripts/backfill_ruolo_cat_particella_id.py --dry-run
    python backend/scripts/backfill_ruolo_cat_particella_id.py --batch-size 500
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal  # noqa: E402
RESOLUTION_CTE = """
WITH target AS (
    SELECT
        rp.id AS ruolo_particella_id,
        cp.comune_codice,
        cp.foglio,
        cp.particella,
        cp.subalterno,
        CASE UPPER(BTRIM(rpa.comune_nome))
            WHEN 'DONIGALA' THEN 'B'
            WHEN 'DONIGALA FENUGHEDU' THEN 'B'
            WHEN 'MASSAMA' THEN 'C'
            WHEN 'NURAXINIEDDU' THEN 'D'
            WHEN 'SILI' THEN 'E'
            ELSE NULL
        END AS sezione_hint
    FROM ruolo_particelle rp
    JOIN ruolo_partite rpa ON rpa.id = rp.partita_id
    LEFT JOIN catasto_parcels cp ON cp.id = rp.catasto_parcel_id
    {where_clause}
    ORDER BY rp.anno_tributario, rp.id
    {limit_clause}
),
resolved AS (
    SELECT
        target.ruolo_particella_id,
        CASE
            WHEN target.comune_codice IS NULL OR target.foglio IS NULL OR target.particella IS NULL THEN NULL
            WHEN COALESCE(BTRIM(target.subalterno), '') <> '' AND exact_match.match_count = 1 THEN exact_match.particella_id
            WHEN COALESCE(BTRIM(target.subalterno), '') <> ''
                 AND exact_match.match_count = 0
                 AND base_match.match_count = 1 THEN base_match.particella_id
            WHEN COALESCE(BTRIM(target.subalterno), '') = '' AND base_match.match_count = 1 THEN base_match.particella_id
            ELSE NULL
        END AS cat_particella_id,
        CASE
            WHEN target.comune_codice IS NULL OR target.foglio IS NULL OR target.particella IS NULL THEN 'unmatched'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> '' AND exact_match.match_count = 1 THEN 'matched'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> '' AND exact_match.match_count > 1 THEN 'ambiguous'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> ''
                 AND exact_match.match_count = 0
                 AND base_match.match_count = 1 THEN 'matched'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> ''
                 AND exact_match.match_count = 0
                 AND base_match.match_count > 1 THEN 'ambiguous'
            WHEN COALESCE(BTRIM(target.subalterno), '') = '' AND base_match.match_count = 1 THEN 'matched'
            WHEN COALESCE(BTRIM(target.subalterno), '') = '' AND base_match.match_count > 1 THEN 'ambiguous'
            ELSE 'unmatched'
        END AS cat_particella_match_status,
        CASE
            WHEN COALESCE(BTRIM(target.subalterno), '') <> '' AND exact_match.match_count = 1 THEN 'exact_sub'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> ''
                 AND exact_match.match_count = 0
                 AND base_match.match_count = 1 THEN 'base_without_sub'
            WHEN COALESCE(BTRIM(target.subalterno), '') = '' AND base_match.match_count = 1 THEN 'exact_no_sub'
            ELSE NULL
        END AS cat_particella_match_confidence,
        CASE
            WHEN target.comune_codice IS NULL THEN 'catasto_parcel_not_resolved'
            WHEN target.foglio IS NULL OR target.particella IS NULL THEN 'missing_match_key'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> '' AND exact_match.match_count > 1 THEN 'multiple_exact_sub_matches'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> ''
                 AND exact_match.match_count = 0
                 AND base_match.match_count = 1 THEN 'ruolo_sub_not_present_in_cat_particelle'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> ''
                 AND exact_match.match_count = 0
                 AND base_match.match_count > 1 THEN 'multiple_base_matches_for_ruolo_sub'
            WHEN COALESCE(BTRIM(target.subalterno), '') <> ''
                 AND exact_match.match_count = 0
                 AND base_match.match_count = 0 THEN 'no_cat_particella_for_sub_or_base'
            WHEN COALESCE(BTRIM(target.subalterno), '') = '' AND base_match.match_count > 1 THEN 'multiple_base_matches'
            WHEN COALESCE(BTRIM(target.subalterno), '') = ''
                 AND base_match.match_count = 0
                 AND variant_match.match_count > 0 THEN 'only_subalterno_variants_found'
            WHEN COALESCE(BTRIM(target.subalterno), '') = '' AND base_match.match_count = 0 THEN 'no_cat_particella_match'
            ELSE NULL
        END AS cat_particella_match_reason
    FROM target
    CROSS JOIN LATERAL (
        SELECT COUNT(*) AS match_count, MIN(p.id::text)::uuid AS particella_id
        FROM cat_particelle p
        WHERE p.codice_catastale = UPPER(BTRIM(target.comune_codice))
          AND p.foglio = BTRIM(target.foglio)
          AND p.particella = BTRIM(target.particella)
          AND p.is_current IS TRUE
          AND p.suppressed IS FALSE
          AND (target.sezione_hint IS NULL OR UPPER(COALESCE(p.sezione_catastale, '')) = target.sezione_hint)
          AND UPPER(COALESCE(p.subalterno, '')) = UPPER(COALESCE(BTRIM(target.subalterno), ''))
          AND COALESCE(BTRIM(target.subalterno), '') <> ''
    ) exact_match
    CROSS JOIN LATERAL (
        SELECT COUNT(*) AS match_count, MIN(p.id::text)::uuid AS particella_id
        FROM cat_particelle p
        WHERE p.codice_catastale = UPPER(BTRIM(target.comune_codice))
          AND p.foglio = BTRIM(target.foglio)
          AND p.particella = BTRIM(target.particella)
          AND p.is_current IS TRUE
          AND p.suppressed IS FALSE
          AND (target.sezione_hint IS NULL OR UPPER(COALESCE(p.sezione_catastale, '')) = target.sezione_hint)
          AND COALESCE(p.subalterno, '') = ''
    ) base_match
    CROSS JOIN LATERAL (
        SELECT COUNT(*) AS match_count
        FROM cat_particelle p
        WHERE p.codice_catastale = UPPER(BTRIM(target.comune_codice))
          AND p.foglio = BTRIM(target.foglio)
          AND p.particella = BTRIM(target.particella)
          AND p.is_current IS TRUE
          AND p.suppressed IS FALSE
          AND (target.sezione_hint IS NULL OR UPPER(COALESCE(p.sezione_catastale, '')) = target.sezione_hint)
    ) variant_match
)
"""

SUMMARY_SQL = """
{resolution_cte}
SELECT
    cat_particella_match_status AS status,
    cat_particella_match_confidence AS confidence,
    cat_particella_match_reason AS reason,
    COUNT(*) AS count
FROM resolved
GROUP BY 1, 2, 3
ORDER BY count DESC, status, confidence, reason
"""

UPDATE_SQL = """
{resolution_cte}
UPDATE ruolo_particelle rp
SET
    cat_particella_id = resolved.cat_particella_id,
    cat_particella_match_status = resolved.cat_particella_match_status,
    cat_particella_match_confidence = resolved.cat_particella_match_confidence,
    cat_particella_match_reason = resolved.cat_particella_match_reason
FROM resolved
WHERE rp.id = resolved.ruolo_particella_id
RETURNING
    resolved.cat_particella_match_status AS status,
    resolved.cat_particella_match_confidence AS confidence,
    resolved.cat_particella_match_reason AS reason
"""


def _query_parts(*, only_missing: bool, limit: int | None) -> tuple[str, str]:
    where_clause = "WHERE rp.cat_particella_id IS NULL" if only_missing else ""
    limit_clause = "LIMIT :limit" if limit is not None else ""
    return where_clause, limit_clause


def run_backfill(*, dry_run: bool, batch_size: int, limit: int | None, only_missing: bool) -> Counter[str]:
    counters: Counter[str] = Counter()
    where_clause, limit_clause = _query_parts(only_missing=only_missing, limit=limit)
    resolution_cte = RESOLUTION_CTE.format(where_clause=where_clause, limit_clause=limit_clause)
    params = {"limit": limit} if limit is not None else {}

    with SessionLocal() as db:
        if dry_run:
            rows = db.execute(text(SUMMARY_SQL.format(resolution_cte=resolution_cte)), params).mappings().all()
        else:
            rows = db.execute(text(UPDATE_SQL.format(resolution_cte=resolution_cte)), params).mappings().all()
            db.commit()

    for row in rows:
        count = int(row.get("count", 1))
        counters["processed"] += count
        counters[f"status:{row['status']}"] += count
        if row["confidence"]:
            counters[f"confidence:{row['confidence']}"] += count
        if row["reason"]:
            counters[f"reason:{row['reason']}"] += count

    return counters


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Calcola i match senza scrivere su DB.")
    parser.add_argument("--batch-size", type=int, default=500, help="Numero righe tra due commit.")
    parser.add_argument("--limit", type=int, default=None, help="Limita le righe processate.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ricalcola anche righe gia collegate; default: solo cat_particella_id NULL.",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        parser.error("--batch-size deve essere > 0")

    counters = run_backfill(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        limit=args.limit,
        only_missing=not args.all,
    )

    mode = "DRY-RUN" if args.dry_run else "WRITE"
    print(f"Backfill ruolo_particelle.cat_particella_id completato ({mode})")
    for key, value in counters.most_common():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
