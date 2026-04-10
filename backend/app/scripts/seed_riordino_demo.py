"""Seed demo practices for the Riordino module."""

from __future__ import annotations

from app.core.database import SessionLocal
from app.modules.riordino.services import ensure_demo_practices


def main() -> None:
    db = SessionLocal()
    try:
        result = ensure_demo_practices(db)
    finally:
        db.close()

    print(
        "Riordino demo seed completed: "
        f"created={result['created']} skipped={result['skipped']} total={result['total']}"
    )


if __name__ == "__main__":
    main()
