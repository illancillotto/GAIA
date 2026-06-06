from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

import app.db.base  # noqa: F401

from app.core.database import SessionLocal
from app.modules.network.telemetry_rollups import refresh_network_firewall_hourly_rollups_for_range


def _parse_date(value: str) -> datetime:
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return parsed.replace(tzinfo=UTC)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill controllato dei rollup orari firewall Sophos.")
    parser.add_argument("--from", dest="date_from", required=True, help="Data inizio in formato YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", required=True, help="Data fine in formato YYYY-MM-DD")
    parser.add_argument("--chunk-days", dest="chunk_days", type=int, default=1, help="Ampiezza dei blocchi di backfill in giorni")
    args = parser.parse_args()

    date_from = _parse_date(args.date_from)
    date_to = _parse_date(args.date_to) + timedelta(days=1) - timedelta(hours=1)
    chunk_days = max(args.chunk_days, 1)

    if date_to < date_from:
        raise SystemExit("--to deve essere maggiore o uguale a --from")

    db = SessionLocal()
    try:
        cursor = date_from
        total_rows = 0
        while cursor <= date_to:
            chunk_end = min(cursor + timedelta(days=chunk_days) - timedelta(hours=1), date_to)
            rows = refresh_network_firewall_hourly_rollups_for_range(
                db,
                start=cursor,
                end=chunk_end,
            )
            total_rows += rows
            print(
                {
                    "chunk_start": cursor.isoformat(),
                    "chunk_end": chunk_end.isoformat(),
                    "rows": rows,
                    "total_rows": total_rows,
                }
            )
            cursor = chunk_end + timedelta(hours=1)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
