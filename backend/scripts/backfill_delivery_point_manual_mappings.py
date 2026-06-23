from __future__ import annotations

import json

from app.core.database import SessionLocal
from app.modules.catasto.services.meter_reading_delivery_point_mapping_service import apply_all_delivery_point_mappings


def main() -> int:
    with SessionLocal() as db:
        stats = apply_all_delivery_point_mappings(db)
        db.commit()
    print(json.dumps(stats, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
