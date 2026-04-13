from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import cast, select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.bonifica_oristanese.apps.warehouse_requests.client import (
    BonificaWarehouseRequestRow,
)
from app.modules.inventory.models import WarehouseRequest
from app.modules.operazioni.models.reports import FieldReport


@dataclass(frozen=True)
class WhiteWarehouseSyncResult:
    synced: int
    skipped: int
    errors: list[str]


def _resolve_field_report_id(db: Session, wc_report_id: int | None):
    if wc_report_id is None:
        return None
    report = db.scalar(
        select(FieldReport).where(FieldReport.external_code == str(wc_report_id))
    )
    return report.id if report is not None else None


def sync_white_warehouse_requests(
    *,
    db: Session,
    rows: list[BonificaWarehouseRequestRow],
) -> WhiteWarehouseSyncResult:
    synced = 0
    skipped = 0
    errors: list[str] = []

    for row in rows:
        try:
            item = db.scalar(select(WarehouseRequest).where(WarehouseRequest.wc_id == row.wc_id))
            field_report_id = _resolve_field_report_id(db, row.wc_report_id)
            if item is None:
                item = WarehouseRequest(
                    wc_id=row.wc_id,
                    wc_report_id=row.wc_report_id,
                    field_report_id=field_report_id,
                    report_type=row.report_type,
                    reported_by=row.reported_by,
                    requested_by=row.requested_by,
                    report_date=row.report_date,
                    request_date=row.request_date,
                    archived=row.archived,
                    status_active=row.status_active,
                    wc_synced_at=datetime.now(timezone.utc),
                )
                db.add(item)
                synced += 1
            else:
                item.wc_report_id = row.wc_report_id
                item.field_report_id = field_report_id
                item.report_type = row.report_type
                item.reported_by = row.reported_by
                item.requested_by = row.requested_by
                item.report_date = row.report_date
                item.request_date = row.request_date
                item.archived = row.archived
                item.status_active = row.status_active
                item.wc_synced_at = datetime.now(timezone.utc)
                skipped += 1
            db.flush()
        except Exception as exc:  # pragma: no cover
            errors.append(f"warehouse:{row.wc_id}: {exc}")

    db.commit()
    return WhiteWarehouseSyncResult(synced=synced, skipped=skipped, errors=errors)
