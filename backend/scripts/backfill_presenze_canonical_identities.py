from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - direct script bootstrap
    sys.path.insert(0, str(REPO_ROOT))

from app.core.database import SessionLocal  # noqa: E402 - direct repository script bootstrap
from app.models.application_user import (  # noqa: E402 - direct repository script bootstrap
    ApplicationUser,
)
from app.modules.presenze.services.canonical_identity_manifest import (  # noqa: E402 - direct repository script bootstrap
    CanonicalIdentityManifestError,
    apply_canonical_identity_manifest,
    parse_canonical_identity_manifest,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Applica identita Presenze e aree personale da un manifest canonico esplicito.",
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--changed-by-gaia-user-id", required=True, type=int)
    parser.add_argument("--reason", required=True)
    parser.add_argument(
        "--apply", action="store_true", help="Applica il manifest; il default e dry-run."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    raw = json.loads(args.manifest.read_text(encoding="utf-8"))
    entries = parse_canonical_identity_manifest(raw)
    with SessionLocal() as db:
        changed_by = db.get(ApplicationUser, args.changed_by_gaia_user_id)
        if changed_by is None:
            raise CanonicalIdentityManifestError("Utente GAIA autore del backfill non trovato")
        report = apply_canonical_identity_manifest(
            db,
            entries,
            changed_by=changed_by,
            reason=args.reason,
            dry_run=not args.apply,
        )
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
