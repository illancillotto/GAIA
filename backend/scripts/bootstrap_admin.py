from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.services.bootstrap_admin import ensure_bootstrap_admin


def main() -> None:
    db = SessionLocal()
    try:
        user, created = ensure_bootstrap_admin(db)
    finally:
        db.close()

    action = "created" if created else "existing"
    print(
        f"bootstrap_admin={action} username={user.username} "
        f"email={user.email} role={user.role}"
    )


if __name__ == "__main__":
    main()
