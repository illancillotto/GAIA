from pathlib import Path
import sys
import time

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.database import SessionLocal
from app.jobs.sync import run_scheduled_live_sync_cycle
from app.services.nas_connector import NasConnectorError


def main() -> None:
    if not settings.sync_schedule_enabled:
        raise SystemExit("scheduled_live_sync=disabled")

    cycle = 0
    while True:
        cycle += 1
        db = SessionLocal()
        try:
            result = run_scheduled_live_sync_cycle(db)
            print(
                "scheduled_live_sync=ok "
                f"cycle={cycle} attempts={result.attempts_used} "
                f"snapshot_id={result.sync_result.snapshot_id}"
            )
        except NasConnectorError as exc:
            print(f"scheduled_live_sync=failed cycle={cycle} detail={exc}")
        finally:
            db.close()

        if settings.sync_schedule_max_cycles and cycle >= settings.sync_schedule_max_cycles:
            return

        time.sleep(settings.sync_schedule_interval_seconds)


if __name__ == "__main__":
    main()
