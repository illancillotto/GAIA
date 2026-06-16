from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url


SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if not (BACKEND_ROOT / "app").exists():
    fallback_backend = SCRIPT_PATH.parents[2] / "backend"
    if (fallback_backend / "app").exists():
        BACKEND_ROOT = fallback_backend
        REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _configure_database_url_for_host() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip()
                    break
    if not db_url:
        return
    try:
        parsed = make_url(db_url)
    except Exception:
        return
    if (parsed.host or "") != "postgres":
        os.environ.setdefault("DATABASE_URL", db_url)
        return
    if Path("/.dockerenv").exists():
        os.environ.setdefault("DATABASE_URL", db_url)
        return
    fallback = parsed.set(host="127.0.0.1", port=5434 if parsed.port in (None, 5432) else parsed.port)
    os.environ["DATABASE_URL"] = fallback.render_as_string(hide_password=False)


_configure_database_url_for_host()

from app.core.database import SessionLocal
from app.modules.ruolo.models import RuoloImportJob


_LEGACY_EXT_RE = re.compile(r"\.(?:dmp|pdf)\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"(20\d{2})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalizza i filename legacy in ruolo_import_jobs verso etichette storiche neutre."
    )
    parser.add_argument("--apply", action="store_true", help="Applica gli aggiornamenti sul database.")
    parser.add_argument("--from-year", type=int, default=None)
    parser.add_argument("--to-year", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def _build_historical_filename(job: RuoloImportJob) -> str | None:
    raw = (job.filename or "").strip()
    if not raw:
        return None
    if not _LEGACY_EXT_RE.search(raw):
        return None

    year = _YEAR_RE.search(raw)
    suffix = year.group(1) if year else str(job.anno_tributario)
    return f"storico_ruolo_{suffix}"


def main() -> None:
    args = parse_args()
    stats: Counter[str] = Counter()

    with SessionLocal() as db:
        query = select(RuoloImportJob).order_by(RuoloImportJob.created_at.asc())
        if args.from_year is not None:
            query = query.where(RuoloImportJob.anno_tributario >= args.from_year)
        if args.to_year is not None:
            query = query.where(RuoloImportJob.anno_tributario <= args.to_year)
        if args.limit is not None:
            query = query.limit(args.limit)

        jobs = db.scalars(query).all()
        for job in jobs:
            stats["jobs_scanned"] += 1
            replacement = _build_historical_filename(job)
            if replacement is None:
                continue
            if job.filename == replacement:
                stats["already_normalized"] += 1
                continue

            print(f"{job.id} | anno={job.anno_tributario} | {job.filename!r} -> {replacement!r}")
            stats["legacy_jobs_found"] += 1
            if args.apply:
                job.filename = replacement
                stats["updated"] += 1

        if args.apply:
            db.commit()
        else:
            db.rollback()

    print("\nSummary:")
    for key in ("jobs_scanned", "legacy_jobs_found", "already_normalized", "updated"):
        print(f"- {key}: {stats[key]}")
    if not args.apply:
        print("- mode: dry-run")


if __name__ == "__main__":
    main()
