from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session


def refresh_cat_particelle_gis_flags(
    db: Session,
    particella_ids: Iterable[uuid.UUID | str] | None = None,
) -> int:
    """Refresh cached tile flags used by cat_particelle_current/Martin."""

    if particella_ids is None:
        return int(db.execute(text("SELECT refresh_cat_particelle_gis_flags_all()")).scalar_one() or 0)

    refreshed = 0
    seen: set[str] = set()
    for particella_id in particella_ids:
        value = str(particella_id)
        if value in seen:
            continue
        seen.add(value)
        db.execute(text("SELECT refresh_cat_particella_gis_flag(:particella_id)"), {"particella_id": value})
        refreshed += 1
    return refreshed
