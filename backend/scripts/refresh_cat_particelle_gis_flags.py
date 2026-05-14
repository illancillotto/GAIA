#!/usr/bin/env python
"""Refresh cached GIS flags for cat_particelle_current.

Usage:
    python backend/scripts/refresh_cat_particelle_gis_flags.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.modules.catasto.services.gis_flags import refresh_cat_particelle_gis_flags  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        refreshed = refresh_cat_particelle_gis_flags(db)
        db.commit()
        print(f"GIS flags refreshed for {refreshed} current particelle")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
