from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.bonifica_oristanese.apps.areas.client import BonificaAreaRow
from app.modules.operazioni.models.wc_area import WCArea


@dataclass(frozen=True)
class WhiteAreasSyncResult:
    synced: int
    skipped: int
    errors: list[str]


def sync_white_areas(*, db: Session, rows: list[BonificaAreaRow]) -> WhiteAreasSyncResult:
    synced = 0
    skipped = 0
    errors: list[str] = []

    for row in rows:
        try:
            area = db.scalar(select(WCArea).where(WCArea.wc_id == row.wc_id))
            if area is None:
                area = WCArea(
                    wc_id=row.wc_id,
                    name=row.name,
                    color=row.color,
                    is_district=row.is_district,
                    description=row.description,
                    lat=row.lat,
                    lng=row.lng,
                    polygon=row.polygon,
                    wc_synced_at=datetime.now(timezone.utc),
                )
                db.add(area)
                synced += 1
            else:
                area.name = row.name
                area.color = row.color
                area.is_district = row.is_district
                area.description = row.description
                area.lat = row.lat
                area.lng = row.lng
                area.polygon = row.polygon
                area.wc_synced_at = datetime.now(timezone.utc)
                skipped += 1
            db.flush()
        except Exception as exc:  # pragma: no cover
            errors.append(f"area:{row.wc_id}: {exc}")

    db.commit()
    return WhiteAreasSyncResult(synced=synced, skipped=skipped, errors=errors)
