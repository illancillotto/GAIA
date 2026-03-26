from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.application_user import ApplicationUser
from app.services.bootstrap_domain import ensure_bootstrap_domain


def main() -> None:
    db = SessionLocal()
    try:
        reviewer = db.scalar(
            select(ApplicationUser).where(ApplicationUser.is_active.is_(True)).order_by(ApplicationUser.id.asc())
        )
        if reviewer is None:
            raise SystemExit(
                "No active application user available. Run python scripts/bootstrap_admin.py first."
            )

        result = ensure_bootstrap_domain(db, reviewer_user_id=reviewer.id)
    finally:
        db.close()

    action = "created" if result["snapshot_created"] else "updated"
    print(
        "bootstrap_domain="
        f"{action} snapshot_id={result['snapshot_id']} nas_users={result['nas_users']} "
        f"nas_groups={result['nas_groups']} shares={result['shares']} "
        f"permission_entries={result['permission_entries']} "
        f"effective_permissions={result['effective_permissions']} reviews={result['reviews']} "
        f"catasto_comuni={result['catasto_comuni']} "
        f"catasto_comuni_created={result['catasto_comuni_created']} "
        f"catasto_comuni_updated={result['catasto_comuni_updated']}"
    )


if __name__ == "__main__":
    main()
