from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.accessi.wc_org_charts import WCOrgChart, WCOrgChartEntry
from app.modules.elaborazioni.bonifica_oristanese.apps.org_charts.client import (
    BonificaOrgChartEntryRow,
    BonificaOrgChartRow,
)
from app.modules.operazioni.models.wc_area import WCArea
from app.modules.operazioni.models.wc_operator import WCOperator


@dataclass(frozen=True)
class WhiteOrgChartsSyncResult:
    synced: int
    skipped: int
    entries_synced: int
    errors: list[str]


def _resolve_operator_id(db: Session, wc_id: int | None):
    if wc_id is None:
        return None
    operator = db.scalar(select(WCOperator).where(WCOperator.wc_id == wc_id))
    return operator.id if operator is not None else None


def _resolve_area_id(db: Session, wc_id: int | None):
    if wc_id is None:
        return None
    area = db.scalar(select(WCArea).where(WCArea.wc_id == wc_id))
    return area.id if area is not None else None


def _create_entry(
    db: Session,
    *,
    chart_id,
    row: BonificaOrgChartEntryRow,
) -> WCOrgChartEntry:
    return WCOrgChartEntry(
        org_chart_id=chart_id,
        wc_id=row.wc_id,
        label=row.label,
        role=row.role,
        wc_operator_id=_resolve_operator_id(db, row.operator_wc_id),
        wc_area_id=_resolve_area_id(db, row.area_wc_id),
        sort_order=row.sort_order,
        source_field=row.source_field,
    )


def sync_white_org_charts(*, db: Session, rows: list[BonificaOrgChartRow]) -> WhiteOrgChartsSyncResult:
    synced = 0
    skipped = 0
    entries_synced = 0
    errors: list[str] = []

    for row in rows:
        try:
            chart = db.scalar(
                select(WCOrgChart).where(
                    WCOrgChart.chart_type == row.chart_type,
                    WCOrgChart.wc_id == row.wc_id,
                )
            )
            if chart is None:
                chart = WCOrgChart(
                    wc_id=row.wc_id,
                    chart_type=row.chart_type,
                    name=row.name,
                    wc_synced_at=datetime.now(timezone.utc),
                )
                db.add(chart)
                db.flush()
                synced += 1
            else:
                chart.name = row.name
                chart.wc_synced_at = datetime.now(timezone.utc)
                db.flush()
                skipped += 1

            db.execute(delete(WCOrgChartEntry).where(WCOrgChartEntry.org_chart_id == chart.id))
            for entry_row in row.entries:
                db.add(_create_entry(db, chart_id=chart.id, row=entry_row))
                entries_synced += 1
            db.flush()
        except Exception as exc:  # pragma: no cover
            errors.append(f"org_chart:{row.chart_type}:{row.wc_id}: {exc}")

    db.commit()
    return WhiteOrgChartsSyncResult(
        synced=synced,
        skipped=skipped,
        entries_synced=entries_synced,
        errors=errors,
    )
