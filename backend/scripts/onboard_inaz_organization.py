from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:  # pragma: no cover - direct CLI bootstrap
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal  # noqa: E402 - repository script bootstrap
from app.models.application_user import ApplicationUser  # noqa: E402
from app.modules.organigramma.services.inaz_onboarding import (  # noqa: E402
    InazOnboardingError,
    reconcile_inaz_onboarding,
)
from app.modules.organigramma.services.inaz_preview import (  # noqa: E402
    InazOrganizationSnapshot,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crea in modo auditato le identita GAIA mancanti nell'Organigramma INAZ.",
    )
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("review_artifact", type=Path)
    parser.add_argument("--changed-by-gaia-user-id", required=True, type=int)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true", help="Applica; il default e dry-run.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    snapshot = InazOrganizationSnapshot.model_validate_json(args.snapshot.read_text())
    review = json.loads(args.review_artifact.read_text())
    with SessionLocal() as db:
        changed_by = db.get(ApplicationUser, args.changed_by_gaia_user_id)
        if changed_by is None:
            raise InazOnboardingError("Utente GAIA autore dell'onboarding non trovato")
        report = reconcile_inaz_onboarding(
            db,
            snapshot,
            review,
            changed_by=changed_by,
            reason=args.reason,
            dry_run=not args.apply,
        )
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
