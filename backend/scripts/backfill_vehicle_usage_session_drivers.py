from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.database import SessionLocal
from app.modules.operazioni.services.backfill_vehicle_usage_session_drivers import (
    backfill_vehicle_usage_session_actual_driver,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collega le vehicle usage sessions legacy all'utente GAIA tramite WCOperator.username -> gaia_user_id.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Calcola il report senza scrivere sul database.")
    mode.add_argument("--apply", action="store_true", help="Applica il backfill sul database.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    dry_run = not args.apply

    db = SessionLocal()
    try:
        report = backfill_vehicle_usage_session_actual_driver(db, dry_run=dry_run)
        print(
            json.dumps(
                {
                    "dry_run": dry_run,
                    **report.as_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
