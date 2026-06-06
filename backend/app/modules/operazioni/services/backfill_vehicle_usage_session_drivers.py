from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.operazioni.models.vehicles import VehicleUsageSession
from app.modules.operazioni.models.wc_operator import WCOperator


@dataclass
class VehicleUsageSessionBackfillReport:
    inspected_count: int = 0
    matched_count: int = 0
    skipped_no_gaia_user_id_count: int = 0
    skipped_no_operator_match_count: int = 0
    ambiguous_count: int = 0

    def as_dict(self) -> dict[str, int]:
        payload = asdict(self)
        payload["skipped_count"] = (
            self.skipped_no_gaia_user_id_count + self.skipped_no_operator_match_count
        )
        return payload


def backfill_vehicle_usage_session_actual_driver(
    db: Session,
    *,
    dry_run: bool,
) -> VehicleUsageSessionBackfillReport:
    sessions = db.scalars(
        select(VehicleUsageSession)
        .where(VehicleUsageSession.actual_driver_user_id.is_(None))
        .where(VehicleUsageSession.operator_name.is_not(None))
        .order_by(VehicleUsageSession.started_at.asc(), VehicleUsageSession.id.asc())
    ).all()

    operator_names = sorted({session.operator_name for session in sessions if session.operator_name})
    wc_operators_by_username: dict[str, list[WCOperator]] = {}
    if operator_names:
        for wc_operator in db.scalars(
            select(WCOperator).where(WCOperator.username.in_(operator_names))
        ).all():
            if wc_operator.username is None:
                continue
            wc_operators_by_username.setdefault(wc_operator.username, []).append(wc_operator)

    report = VehicleUsageSessionBackfillReport(inspected_count=len(sessions))

    for session in sessions:
        operator_name = session.operator_name
        if not operator_name:
            report.skipped_no_operator_match_count += 1
            continue

        candidates = wc_operators_by_username.get(operator_name, [])
        if not candidates:
            report.skipped_no_operator_match_count += 1
            continue
        if len(candidates) > 1:
            report.ambiguous_count += 1
            continue

        wc_operator = candidates[0]
        if wc_operator.gaia_user_id is None:
            report.skipped_no_gaia_user_id_count += 1
            continue

        report.matched_count += 1
        if not dry_run:
            session.actual_driver_user_id = wc_operator.gaia_user_id

    if not dry_run and report.matched_count > 0:
        db.commit()

    return report
