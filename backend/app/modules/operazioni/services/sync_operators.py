from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.bonifica_oristanese.apps.users.client import BonificaUserRow
from app.modules.operazioni.models.wc_operator import WCOperator


@dataclass(frozen=True)
class WhiteOperatorsSyncResult:
    synced: int
    skipped: int
    errors: list[str]


def sync_white_operators(*, db: Session, rows: list[BonificaUserRow]) -> WhiteOperatorsSyncResult:
    synced = 0
    skipped = 0
    errors: list[str] = []

    for row in rows:
        if (row.role or "").strip().lower() == "consorziato":
            skipped += 1
            continue
        try:
            operator = db.scalar(select(WCOperator).where(WCOperator.wc_id == row.wc_id))
            normalized_email = row.email.lower() if row.email else None
            gaia_user_id = None
            if normalized_email:
                gaia_user_id = db.scalar(
                    select(ApplicationUser.id).where(func.lower(ApplicationUser.email) == normalized_email)
                )

            if operator is None:
                operator = WCOperator(
                    wc_id=row.wc_id,
                    username=row.username,
                    email=row.email,
                    first_name=row.first_name,
                    last_name=row.last_name,
                    tax=row.tax,
                    role=row.role,
                    enabled=row.enabled,
                    gaia_user_id=gaia_user_id,
                    wc_synced_at=datetime.now(timezone.utc),
                )
                db.add(operator)
                synced += 1
            else:
                operator.username = row.username
                operator.email = row.email
                operator.first_name = row.first_name
                operator.last_name = row.last_name
                operator.tax = row.tax
                operator.role = row.role
                operator.enabled = row.enabled
                operator.gaia_user_id = gaia_user_id
                operator.wc_synced_at = datetime.now(timezone.utc)
                skipped += 1
            db.flush()
        except Exception as exc:  # pragma: no cover
            errors.append(f"operator:{row.wc_id}: {exc}")

    db.commit()
    return WhiteOperatorsSyncResult(synced=synced, skipped=skipped, errors=errors)
