from __future__ import annotations

import importlib
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

main = importlib.import_module("app.modules.presenze.services.event_summary_export").main


if __name__ == "__main__":
    raise SystemExit(main())
