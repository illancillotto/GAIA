from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.jobs.sync import run_live_sync_job
from app.services.nas_connector import NasConnectorError


def main() -> None:
    db = SessionLocal()
    try:
        result = run_live_sync_job(
            db,
            trigger_type="script",
            initiated_by="system",
            source_label="script:ssh",
        )
    except NasConnectorError as exc:
        raise SystemExit(f"live_sync=failed detail={exc}") from exc
    finally:
        db.close()

    sync_result = result.sync_result
    print(
        "live_sync=ok "
        f"attempts={result.attempts_used} "
        f"snapshot_id={sync_result.snapshot_id} "
        f"users={sync_result.persisted_users} "
        f"groups={sync_result.persisted_groups} "
        f"shares={sync_result.persisted_shares} "
        f"effective_permissions={sync_result.persisted_effective_permissions}"
    )


if __name__ == "__main__":
    main()
