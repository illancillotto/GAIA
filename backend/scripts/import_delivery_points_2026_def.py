from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.modules.catasto.services.delivery_points_import import import_delivery_points_2026_def


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importa i punti di consegna e le canalette irrigue dal dataset canonico 2026_DEF."
    )
    parser.add_argument("root_path", help="Cartella PUNTI_CONSEGNA 2026_DEF")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = import_delivery_points_2026_def(db, root_path=args.root_path)
    except Exception as exc:
        db.rollback()
        print(f"Import fallito: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(
        "Import completato:"
        f" punti={result['points_processed']}"
        f" canalette={result['canals_processed']}"
        f" letture_collegate={result['meter_readings_linked']}"
        f" letture_non_collegate={result['meter_readings_unlinked']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
