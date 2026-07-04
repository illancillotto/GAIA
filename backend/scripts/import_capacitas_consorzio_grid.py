from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.services.capacitas_consorzio_grid_import import (
    CapacitasGridImportOptions,
    run_capacitas_consorzio_grid_import,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import controllato grid Capacitas nel catasto consortile GAIA.")
    parser.add_argument("--xlsx-path", type=Path, required=True)
    parser.add_argument("--snapshot-year", type=int, default=2026)
    parser.add_argument("--source-file", type=str, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/gaia_capacitas_grid_import"))
    parser.add_argument("--apply", action="store_true", help="Esegue le scritture. Senza questo flag e' un dry-run.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias esplicito per documentare l'intenzione; e' gia il default se manca --apply.",
    )
    parser.add_argument(
        "--close-missing",
        action="store_true",
        help="Opzione riservata: non ancora supportata per evitare chiusure massive implicite.",
    )
    args = parser.parse_args()
    if args.close_missing:
        parser.error("--close-missing non e' ancora supportato: serve una fase separata con report dedicato")
    if not args.xlsx_path.exists():
        parser.error(f"File non trovato: {args.xlsx_path}")
    return args


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        summary = run_capacitas_consorzio_grid_import(
            db,
            CapacitasGridImportOptions(
                xlsx_path=args.xlsx_path,
                snapshot_year=args.snapshot_year,
                source_file=args.source_file or args.xlsx_path.name,
                output_dir=args.output_dir,
                apply=args.apply,
            ),
        )
        counters = summary["counters"]
        print(
            f"mode={summary['mode']} rows={summary['rows_total']} "
            f"unit_action_created={counters.get('unit_action_unit_created', 0)} "
            f"unit_action_existing={counters.get('unit_action_unit_existing_exact', 0)} "
            f"unit_resolution_swapped_arborea_terralba={counters.get('unit_resolution_unit_swapped_arborea_terralba', 0)} "
            f"occupancy_created={counters.get('occupancy_created', 0)} "
            f"occupancy_existing_current={counters.get('occupancy_existing_current', 0)} "
            f"cat_particelle_unchanged={summary['cat_particelle_unchanged']} "
            f"summary={summary['artifacts']['summary_path']}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
