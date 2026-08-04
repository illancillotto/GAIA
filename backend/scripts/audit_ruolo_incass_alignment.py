from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import make_url


SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:  # pragma: no cover - import bootstrap for direct CLI execution.
    sys.path.insert(0, str(BACKEND_ROOT))


def _configure_database_url_for_host() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip()
                    break
    if not db_url:
        return
    try:
        parsed = make_url(db_url)
    except Exception:
        return
    if (parsed.host or "") != "postgres" or Path("/.dockerenv").exists():
        os.environ.setdefault("DATABASE_URL", db_url)
        return
    fallback = parsed.set(host="127.0.0.1", port=5434 if parsed.port in (None, 5432) else parsed.port)
    os.environ["DATABASE_URL"] = fallback.render_as_string(hide_password=False)


_configure_database_url_for_host()

from app.core.database import SessionLocal  # noqa: E402


ALIGNMENT_SQL = text(
    """
    WITH years AS (
      SELECT generate_series(CAST(:from_year AS integer), CAST(:to_year AS integer)) AS anno
    ),
    incass_base AS (
      SELECT
        apn.id,
        apn.anno::int AS anno,
        apn.source_notice_id,
        apn.subject_id,
        apn.raw_detail_json,
        CASE
          WHEN apn.raw_detail_json IS NULL THEN 0
          WHEN jsonb_typeof(apn.raw_detail_json::jsonb -> 'partite') = 'array'
            THEN jsonb_array_length(apn.raw_detail_json::jsonb -> 'partite')
          WHEN jsonb_typeof(apn.raw_detail_json::jsonb -> 'partitario' -> 'partite') = 'array'
            THEN jsonb_array_length(apn.raw_detail_json::jsonb -> 'partitario' -> 'partite')
          ELSE 0
        END AS partite_count
      FROM ana_payment_notices apn
      WHERE apn.source_system = 'incass'
        AND apn.anno ~ '^[0-9]+$'
        AND apn.anno::int BETWEEN :from_year AND :to_year
    ),
    incass_stats AS (
      SELECT
        anno,
        count(*) AS incass_source_rows,
        count(*) FILTER (WHERE subject_id IS NULL) AS incass_without_subject,
        count(*) FILTER (WHERE raw_detail_json IS NULL) AS incass_without_detail,
        count(*) FILTER (WHERE subject_id IS NOT NULL AND raw_detail_json IS NOT NULL AND partite_count > 0)
          AS incass_materializable_rows,
        count(*) FILTER (WHERE subject_id IS NOT NULL AND raw_detail_json IS NOT NULL AND partite_count <= 0)
          AS incass_without_partite
      FROM incass_base
      GROUP BY anno
    ),
    materializable AS (
      SELECT
        anno,
        CASE
          WHEN length(source_notice_id) < 2 THEN source_notice_id
          ELSE '01.' || substring(source_notice_id from 1 for length(source_notice_id) - 1)
        END AS codice_cnc
      FROM incass_base
      WHERE subject_id IS NOT NULL
        AND raw_detail_json IS NOT NULL
        AND partite_count > 0
    ),
    ruolo_stats AS (
      SELECT
        ra.anno_tributario AS anno,
        count(*) AS ruolo_rows,
        count(*) FILTER (WHERE rp.avviso_id IS NULL) AS ruolo_without_partite
      FROM ruolo_avvisi ra
      LEFT JOIN (
        SELECT DISTINCT avviso_id
        FROM ruolo_partite
      ) rp ON rp.avviso_id = ra.id
      WHERE ra.anno_tributario BETWEEN :from_year AND :to_year
      GROUP BY ra.anno_tributario
    ),
    missing_in_ruolo AS (
      SELECT
        m.anno,
        count(*) AS materializable_missing_in_ruolo
      FROM materializable m
      LEFT JOIN ruolo_avvisi ra
        ON ra.anno_tributario = m.anno
       AND ra.codice_cnc = m.codice_cnc
      WHERE ra.id IS NULL
      GROUP BY m.anno
    ),
    ruolo_without_source AS (
      SELECT
        ra.anno_tributario AS anno,
        count(*) AS ruolo_without_source
      FROM ruolo_avvisi ra
      LEFT JOIN incass_base ib
        ON ib.anno = ra.anno_tributario
       AND (
         CASE
           WHEN length(ib.source_notice_id) < 2 THEN ib.source_notice_id
           ELSE '01.' || substring(ib.source_notice_id from 1 for length(ib.source_notice_id) - 1)
         END
       ) = ra.codice_cnc
      WHERE ra.anno_tributario BETWEEN :from_year AND :to_year
        AND ib.id IS NULL
      GROUP BY ra.anno_tributario
    )
    SELECT
      y.anno,
      coalesce(i.incass_source_rows, 0) AS incass_source_rows,
      coalesce(i.incass_without_subject, 0) AS incass_without_subject,
      coalesce(i.incass_without_detail, 0) AS incass_without_detail,
      coalesce(i.incass_without_partite, 0) AS incass_without_partite,
      coalesce(i.incass_materializable_rows, 0) AS incass_materializable_rows,
      coalesce(r.ruolo_rows, 0) AS ruolo_rows,
      coalesce(r.ruolo_without_partite, 0) AS ruolo_without_partite,
      coalesce(m.materializable_missing_in_ruolo, 0) AS materializable_missing_in_ruolo,
      coalesce(ws.ruolo_without_source, 0) AS ruolo_without_source
    FROM years y
    LEFT JOIN incass_stats i ON i.anno = y.anno
    LEFT JOIN ruolo_stats r ON r.anno = y.anno
    LEFT JOIN missing_in_ruolo m ON m.anno = y.anno
    LEFT JOIN ruolo_without_source ws ON ws.anno = y.anno
    ORDER BY y.anno
    """
)


@dataclass(frozen=True)
class RuoloIncassAlignmentRow:
    anno: int
    incass_source_rows: int
    incass_without_subject: int
    incass_without_detail: int
    incass_without_partite: int
    incass_materializable_rows: int
    ruolo_rows: int
    ruolo_without_partite: int
    materializable_missing_in_ruolo: int
    ruolo_without_source: int

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "RuoloIncassAlignmentRow":
        return cls(**{field: int(row[field] or 0) for field in cls.__dataclass_fields__})

    @property
    def has_blocking_drift(self) -> bool:
        return (
            self.materializable_missing_in_ruolo > 0
            or self.ruolo_without_source > 0
            or self.ruolo_without_partite > 0
        )


@dataclass(frozen=True)
class RuoloIncassAlignmentSummary:
    rows: list[RuoloIncassAlignmentRow]

    @property
    def has_blocking_drift(self) -> bool:
        return any(row.has_blocking_drift for row in self.rows)

    @property
    def totals(self) -> dict[str, int]:
        keys = [
            "incass_source_rows",
            "incass_without_subject",
            "incass_without_detail",
            "incass_without_partite",
            "incass_materializable_rows",
            "ruolo_rows",
            "ruolo_without_partite",
            "materializable_missing_in_ruolo",
            "ruolo_without_source",
        ]
        return {key: sum(getattr(row, key) for row in self.rows) for key in keys}

    def as_dict(self) -> dict[str, Any]:
        return {
            "has_blocking_drift": self.has_blocking_drift,
            "totals": self.totals,
            "rows": [asdict(row) for row in self.rows],
        }


def fetch_alignment_rows(db: Any, *, from_year: int, to_year: int) -> list[RuoloIncassAlignmentRow]:
    result = db.execute(ALIGNMENT_SQL, {"from_year": from_year, "to_year": to_year})
    return [RuoloIncassAlignmentRow.from_mapping(row) for row in result.mappings().all()]


def format_report(summary: RuoloIncassAlignmentSummary) -> str:
    lines = [
        "anno | incass | materializzabili | senza_partite | ruolo | missing_ruolo | ruolo_senza_sorgente | ruolo_senza_partite",
        "-----|--------|------------------|---------------|-------|---------------|----------------------|--------------------",
    ]
    for row in summary.rows:
        lines.append(
            f"{row.anno} | {row.incass_source_rows} | {row.incass_materializable_rows} | "
            f"{row.incass_without_partite} | {row.ruolo_rows} | {row.materializable_missing_in_ruolo} | "
            f"{row.ruolo_without_source} | {row.ruolo_without_partite}"
        )
    totals = summary.totals
    lines.append(
        f"TOTAL | {totals['incass_source_rows']} | {totals['incass_materializable_rows']} | "
        f"{totals['incass_without_partite']} | {totals['ruolo_rows']} | "
        f"{totals['materializable_missing_in_ruolo']} | {totals['ruolo_without_source']} | "
        f"{totals['ruolo_without_partite']}"
    )
    lines.append(f"blocking_drift={str(summary.has_blocking_drift).lower()}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita allineamento read-model Ruolo vs sorgente inCASS.")
    parser.add_argument("--from-year", type=int, required=True)
    parser.add_argument("--to-year", type=int, required=True)
    parser.add_argument("--json", action="store_true", help="Emette un payload JSON invece del report testuale.")
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Restituisce exit code 1 se ci sono avvisi materializzabili mancanti o righe ruolo incoerenti.",
    )
    args = parser.parse_args(argv)
    if args.from_year > args.to_year:
        parser.error("--from-year deve essere <= --to-year")
    return args


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    db = SessionLocal()
    try:
        summary = RuoloIncassAlignmentSummary(
            fetch_alignment_rows(db, from_year=args.from_year, to_year=args.to_year)
        )
    finally:
        db.close()
    if args.json:
        print(json.dumps(summary.as_dict(), sort_keys=True))
    else:
        print(format_report(summary))
    if args.fail_on_drift and summary.has_blocking_drift:
        return 1
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint.
    main()
