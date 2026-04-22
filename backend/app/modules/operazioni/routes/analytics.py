"""Operazioni Analytics routes — fuel, km, work-hours, anomalies."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.organizational import Team, TeamMembership
from app.modules.operazioni.models.fuel_cards import FuelCard, FuelCardAssignmentHistory
from app.modules.operazioni.models.vehicles import (
    Vehicle,
    VehicleAssignment,
    VehicleFuelLog,
    VehicleUsageSession,
    WCRefuelEvent,
)
from app.modules.operazioni.models.wc_operator import WCOperator
from app.schemas.operazioni_analytics import (
    AnalyticsSummary,
    AnomaliesResponse,
    AnomalyItem,
    FuelAnalytics,
    FuelRelatedUsageItem,
    FuelStationUsageItem,
    FuelTopItem,
    KmAnalytics,
    KmSessionExtremeItem,
    KmTopItem,
    TimeSeriesPoint,
    WorkHoursAnalytics,
    WorkHoursCategoryItem,
    WorkHoursOperatorItem,
    WorkHoursTeamItem,
)

router = APIRouter(prefix="/analytics", tags=["operazioni/analytics"])


# ─── helpers ───────────────────────────────────────────────────────────────────

def _parse_date(value: str | None, fallback: date) -> date:
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return fallback


def _period_key(dt: datetime, granularity: str) -> str:
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    if granularity == "week":
        return f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
    return dt.strftime("%Y-%m")  # month (default)


def _user_display_name(user: ApplicationUser | None) -> str:
    if user is None:
        return "Sconosciuto"
    full = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
    return full or user.username or str(user.id)


# ─── available periods ─────────────────────────────────────────────────────────

@router.get("/available-periods", response_model=dict)
def available_periods(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Return years, quarters, and months that have at least one data record."""
    from sqlalchemy import func

    # Collect all timestamps with data across the three main sources
    fuel_dates = db.scalars(select(VehicleFuelLog.fueled_at)).all()
    session_dates = db.scalars(select(VehicleUsageSession.started_at)).all()
    activity_dates = db.scalars(select(OperatorActivity.started_at)).all()

    all_dates: list[datetime] = [d for d in fuel_dates + session_dates + activity_dates if d]

    if not all_dates:
        return {"years": [], "quarters": [], "months": []}

    # Collect unique (year, month) pairs
    ym_set: set[tuple[int, int]] = set()
    for d in all_dates:
        ym_set.add((d.year, d.month))

    # Build year list
    years = sorted({y for y, _ in ym_set}, reverse=True)

    # Build quarter list from available months
    quarters_set: set[tuple[int, int]] = set()
    for y, m in ym_set:
        q = (m - 1) // 3 + 1
        quarters_set.add((y, q))

    QUARTER_LABELS = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
    QUARTER_MONTHS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}

    quarters = [
        {
            "year": y,
            "quarter": q,
            "label": f"{QUARTER_LABELS[q]} {y}",
            "from_date": date(y, QUARTER_MONTHS[q][0], 1).isoformat(),
            "to_date": date(
                y,
                QUARTER_MONTHS[q][1],
                (date(y, QUARTER_MONTHS[q][1] + 1, 1) - timedelta(days=1)).day
                if QUARTER_MONTHS[q][1] < 12
                else 31,
            ).isoformat(),
        }
        for y, q in sorted(quarters_set, reverse=True)
    ]

    MONTH_NAMES_IT = [
        "", "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
        "Lug", "Ago", "Set", "Ott", "Nov", "Dic",
    ]

    months = [
        {
            "year": y,
            "month": m,
            "label": f"{MONTH_NAMES_IT[m]} {y}",
            "from_date": date(y, m, 1).isoformat(),
            "to_date": (
                date(y, m + 1, 1) - timedelta(days=1)
                if m < 12
                else date(y, 12, 31)
            ).isoformat(),
        }
        for y, m in sorted(ym_set, reverse=True)
    ]

    return {"years": years, "quarters": quarters, "months": months}


# ─── summary ───────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    from_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    to_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
):
    today = date.today()
    d_from = _parse_date(from_date, today - timedelta(days=30))
    d_to = _parse_date(to_date, today)
    dt_from = datetime.combine(d_from, datetime.min.time())
    dt_to = datetime.combine(d_to, datetime.max.time())
    period_label = f"{d_from.strftime('%d/%m/%Y')} – {d_to.strftime('%d/%m/%Y')}"

    # Km from closed sessions
    sessions = db.scalars(
        select(VehicleUsageSession).where(
            VehicleUsageSession.started_at >= dt_from,
            VehicleUsageSession.started_at <= dt_to,
        )
    ).all()
    total_km = sum(
        (
            float(s.route_distance_km)
            if s.route_distance_km is not None
            else max(0.0, float(s.end_odometer_km or 0) - float(s.start_odometer_km or 0))
        )
        for s in sessions
        if s.status != "open"
    )

    # Fuel
    fuel_logs = db.scalars(
        select(VehicleFuelLog).where(
            VehicleFuelLog.fueled_at >= dt_from,
            VehicleFuelLog.fueled_at <= dt_to,
        )
    ).all()
    total_liters = sum(float(f.liters or 0) for f in fuel_logs)
    total_cost = sum(float(f.total_cost or 0) for f in fuel_logs)

    # Work hours from activities (use calculated if available, else declared)
    activities = db.scalars(
        select(OperatorActivity).where(
            OperatorActivity.started_at >= dt_from,
            OperatorActivity.started_at <= dt_to,
            OperatorActivity.status.in_(["submitted", "under_review", "approved"]),
        )
    ).all()
    total_minutes = sum(
        int(a.duration_minutes_calculated or a.duration_minutes_declared or 0)
        for a in activities
    )
    total_work_hours = round(total_minutes / 60, 1)

    # Active sessions (currently open)
    active_sessions = db.scalar(
        select(
            __import__("sqlalchemy", fromlist=["func"]).func.count(VehicleUsageSession.id)
        ).where(VehicleUsageSession.status == "open")
    ) or 0

    # Anomaly count (proxy: unmatched refuels + orphan sessions)
    unmatched = db.scalar(
        select(
            __import__("sqlalchemy", fromlist=["func"]).func.count(WCRefuelEvent.id)
        ).where(
            WCRefuelEvent.matched_fuel_log_id.is_(None),
            WCRefuelEvent.fueled_at >= dt_from,
            WCRefuelEvent.fueled_at <= dt_to,
        )
    ) or 0
    orphan_cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
    orphan_sessions = db.scalar(
        select(
            __import__("sqlalchemy", fromlist=["func"]).func.count(VehicleUsageSession.id)
        ).where(
            VehicleUsageSession.status == "open",
            VehicleUsageSession.started_at <= orphan_cutoff.replace(tzinfo=None),
        )
    ) or 0
    anomaly_count = unmatched + orphan_sessions

    avg_consumption = None
    if total_km > 0 and total_liters > 0:
        avg_consumption = round(total_liters / total_km * 100, 2)

    return AnalyticsSummary(
        period_label=period_label,
        total_km=round(total_km, 1),
        total_liters=round(total_liters, 2),
        total_fuel_cost=round(total_cost, 2),
        total_work_hours=total_work_hours,
        active_sessions=active_sessions,
        anomaly_count=anomaly_count,
        avg_consumption_l_per_100km=avg_consumption,
    )


# ─── fuel ──────────────────────────────────────────────────────────────────────

@router.get("/fuel", response_model=FuelAnalytics)
def fuel_analytics(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
):
    today = date.today()
    d_from = _parse_date(from_date, today - timedelta(days=90))
    d_to = _parse_date(to_date, today)
    dt_from = datetime.combine(d_from, datetime.min.time())
    dt_to = datetime.combine(d_to, datetime.max.time())

    logs = db.scalars(
        select(VehicleFuelLog).where(
            VehicleFuelLog.fueled_at >= dt_from,
            VehicleFuelLog.fueled_at <= dt_to,
        )
    ).all()

    sessions = db.scalars(
        select(VehicleUsageSession).where(
            VehicleUsageSession.started_at >= dt_from,
            VehicleUsageSession.started_at <= dt_to,
            VehicleUsageSession.status != "open",
        )
    ).all()

    def _safe_float(x) -> float:
        try:
            return float(x or 0)
        except Exception:  # pragma: no cover - defensive
            return 0.0

    def _avg(values: list[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    def _metrics_for_logs(items: list[VehicleFuelLog]) -> tuple[float | None, float | None, float | None]:
        positive = [l for l in items if _safe_float(l.liters) > 0]
        pos_liters = [_safe_float(l.liters) for l in positive if _safe_float(l.liters) > 0]
        pos_costs = [_safe_float(l.total_cost) for l in positive if l.total_cost is not None]

        total_l = sum(pos_liters)
        total_c = sum(pos_costs)

        avg_price = (total_c / total_l) if total_l > 0 else None
        avg_refuel_cost = _avg(pos_costs)
        avg_liters = _avg(pos_liters)
        return avg_price, avg_refuel_cost, avg_liters

    def _top_stations_for_logs(items: list[VehicleFuelLog], limit: int = 5) -> list[FuelStationUsageItem]:
        grouped: dict[str, list[VehicleFuelLog]] = defaultdict(list)
        for l in items:
            name = (l.station_name or "").strip() or "Non specificata"
            grouped[name].append(l)

        def _score(st: str) -> tuple[float, int]:
            ls = grouped[st]
            return sum(_safe_float(x.liters) for x in ls), len(ls)

        stations = sorted(grouped.keys(), key=_score, reverse=True)[:limit]
        out: list[FuelStationUsageItem] = []
        for st in stations:
            ls = grouped[st]
            out.append(FuelStationUsageItem(
                station_name=st,
                refuel_count=len(ls),
                total_liters=round(sum(_safe_float(x.liters) for x in ls), 2),
                total_cost=round(sum(_safe_float(x.total_cost) for x in ls), 2),
            ))
        return out

    def _session_km(s: VehicleUsageSession) -> float:
        if s.route_distance_km:
            return float(s.route_distance_km)
        if s.end_odometer_km is not None and s.start_odometer_km is not None:
            diff = float(s.end_odometer_km) - float(s.start_odometer_km)
            return max(0.0, diff)
        return 0.0

    km_by_vehicle_from_sessions: dict = defaultdict(float)
    for s in sessions:
        if s.vehicle_id:
            km_by_vehicle_from_sessions[s.vehicle_id] += _session_km(s)

    # km per GAIA user (actual_driver_user_id) and per session operator_name (legacy fallback)
    km_by_gaia_user: dict[int, float] = defaultdict(float)
    km_by_gaia_user_vehicle: dict[int, dict] = defaultdict(lambda: defaultdict(float))
    km_by_op_name: dict[str, float] = defaultdict(float)
    km_by_op_name_vehicle: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for s in sessions:
        km = _session_km(s)
        if not s.vehicle_id:
            continue
        if s.actual_driver_user_id:
            km_by_gaia_user[s.actual_driver_user_id] += km
            km_by_gaia_user_vehicle[s.actual_driver_user_id][s.vehicle_id] += km
        elif s.operator_name:
            km_by_op_name[s.operator_name] += km
            km_by_op_name_vehicle[s.operator_name][s.vehicle_id] += km

    def _target_consumption_l_per_100km(v: Vehicle | None) -> float | None:
        if v is None:
            return None
        vt = (getattr(v, "vehicle_type", None) or "").lower()
        if not vt:
            vt = (getattr(v, "vehicle_type_wc", None) or "").lower()
        if not vt:
            return None

        # Conservative defaults (can be tuned with real data)
        if any(k in vt for k in ["auto", "berlina", "utilitaria"]):
            return 7.5
        if any(k in vt for k in ["furg", "van", "ducato", "daily"]):
            return 11.5
        if any(k in vt for k in ["autocarro", "camion", "truck"]):
            return 26.0
        if any(k in vt for k in ["trattore", "trattor", "escavat", "terna"]):
            return 15.0
        return None

    def _judgement_from_coeff(coeff: float | None) -> str | None:
        if coeff is None:
            return None
        if coeff <= 1.10:
            return "OK"
        if coeff <= 1.30:
            return "Alto"
        return "Molto alto"

    # Time series
    liters_by_period: dict[str, float] = defaultdict(float)
    cost_by_period: dict[str, float] = defaultdict(float)
    for log in logs:
        key = _period_key(log.fueled_at, granularity)
        liters_by_period[key] += _safe_float(log.liters)
        cost_by_period[key] += _safe_float(log.total_cost)

    sorted_periods = sorted(set(liters_by_period) | set(cost_by_period))
    time_series = [
        TimeSeriesPoint(period=p, value=round(liters_by_period[p], 2))
        for p in sorted_periods
    ]
    cost_series = [
        TimeSeriesPoint(period=p, value=round(cost_by_period[p], 2))
        for p in sorted_periods
    ]

    # Top vehicles
    vehicle_ids = {log.vehicle_id for log in logs if log.vehicle_id}
    vehicles_map: dict = {}
    if vehicle_ids:
        for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).all():
            vehicles_map[v.id] = v

    liters_by_vehicle: dict = defaultdict(float)
    cost_by_vehicle: dict = defaultdict(float)
    count_by_vehicle: dict = defaultdict(int)
    logs_by_vehicle: dict = defaultdict(list)
    for log in logs:
        if log.vehicle_id:
            liters_by_vehicle[log.vehicle_id] += _safe_float(log.liters)
            cost_by_vehicle[log.vehicle_id] += _safe_float(log.total_cost)
            count_by_vehicle[log.vehicle_id] += 1
            logs_by_vehicle[log.vehicle_id].append(log)

    top_vehicles = sorted(liters_by_vehicle, key=liters_by_vehicle.__getitem__, reverse=True)[:10]
    top_vehicles_out = [
        FuelTopItem(
            id=str(vid),
            label=getattr(vehicles_map.get(vid), "plate_number", None)
                  or getattr(vehicles_map.get(vid), "name", None)
                  or str(vid),
            total_liters=round(liters_by_vehicle[vid], 2),
            total_cost=round(cost_by_vehicle[vid], 2),
            refuel_count=count_by_vehicle[vid],
            total_km=round(km_by_vehicle_from_sessions[vid], 1) if vid in km_by_vehicle_from_sessions else None,
            avg_consumption_l_per_100km=(
                round(
                    (
                        sum(max(0.0, _safe_float(l.liters)) for l in logs_by_vehicle[vid])
                        / km_by_vehicle_from_sessions[vid]
                        * 100
                    ),
                    2,
                )
                if km_by_vehicle_from_sessions.get(vid, 0.0) > 0
                and sum(max(0.0, _safe_float(l.liters)) for l in logs_by_vehicle[vid]) > 0
                else None
            ),
            consumption_coefficient=(
                (
                    (
                        (
                            (
                                sum(max(0.0, _safe_float(l.liters)) for l in logs_by_vehicle[vid])
                                / km_by_vehicle_from_sessions[vid]
                                * 100
                            )
                            / _target_consumption_l_per_100km(vehicles_map.get(vid))
                        )
                    )
                    if km_by_vehicle_from_sessions.get(vid, 0.0) > 0
                    and _target_consumption_l_per_100km(vehicles_map.get(vid)) is not None
                    and sum(max(0.0, _safe_float(l.liters)) for l in logs_by_vehicle[vid]) > 0
                    else None
                )
            ),
            consumption_judgement=None,
            avg_price_per_liter=(
                (lambda m: round(m, 4) if m is not None else None)(_metrics_for_logs(logs_by_vehicle[vid])[0])
            ),
            avg_refuel_cost=(
                (lambda m: round(m, 2) if m is not None else None)(_metrics_for_logs(logs_by_vehicle[vid])[1])
            ),
            avg_liters_per_refuel=(
                (lambda m: round(m, 2) if m is not None else None)(_metrics_for_logs(logs_by_vehicle[vid])[2])
            ),
            top_stations=_top_stations_for_logs(logs_by_vehicle[vid], limit=5),
            related=[],
        )
        for vid in top_vehicles
    ]

    # fill judgement (needs coefficient computed)
    for item in top_vehicles_out:
        item.consumption_judgement = _judgement_from_coeff(item.consumption_coefficient)
        if item.consumption_coefficient is not None:
            item.consumption_coefficient = round(float(item.consumption_coefficient), 3)

    # Top operators — primary key is wc_operator_id (UUID); falls back to
    # operator_name string for logs not yet associated to a WCOperator.
    import uuid as _uuid

    _NO_OPERATOR = "__no_operator__"

    # Load WCOperators referenced by logs in this period
    wc_op_ids_in_logs = {log.wc_operator_id for log in logs if log.wc_operator_id}
    wc_ops_map: dict[_uuid.UUID, WCOperator] = {}
    if wc_op_ids_in_logs:
        for wco in db.scalars(select(WCOperator).where(WCOperator.id.in_(wc_op_ids_in_logs))).all():
            wc_ops_map[wco.id] = wco

    # Group fuel logs: UUID key for identified operators, string key for legacy fallback
    liters_by_key: dict = defaultdict(float)
    cost_by_key: dict = defaultdict(float)
    count_by_key: dict = defaultdict(int)
    logs_by_key: dict = defaultdict(list)
    for log in logs:
        if log.wc_operator_id is not None:
            fkey = log.wc_operator_id
        elif log.operator_name:
            fkey = log.operator_name
        else:
            fkey = _NO_OPERATOR
        liters_by_key[fkey] += _safe_float(log.liters)
        cost_by_key[fkey] += _safe_float(log.total_cost)
        count_by_key[fkey] += 1
        logs_by_key[fkey].append(log)

    # Consolidation: ~30% of logs may lack wc_operator_id (not yet backfilled or
    # unmatched WC events). When the same operator already has a UUID key in
    # liters_by_key, merge the orphan string key into the UUID key so the operator
    # appears only once in the top-10.
    _name_to_uuid: dict[str, _uuid.UUID] = {}
    for _uid, _wco in wc_ops_map.items():
        if _uid not in liters_by_key:
            continue
        for _variant in [
            f"{_wco.first_name or ''} {_wco.last_name or ''}".strip(),
            f"{_wco.last_name or ''} {_wco.first_name or ''}".strip(),
            _wco.username or "",
        ]:
            if _variant:
                _name_to_uuid[_variant] = _uid

    for _str_key in list(liters_by_key.keys()):
        if not isinstance(_str_key, str) or _str_key == _NO_OPERATOR:
            continue
        _target_uid = _name_to_uuid.get(_str_key)
        if _target_uid is None:
            continue
        liters_by_key[_target_uid] += liters_by_key.pop(_str_key)
        cost_by_key[_target_uid] += cost_by_key.pop(_str_key)
        count_by_key[_target_uid] += count_by_key.pop(_str_key)
        logs_by_key[_target_uid].extend(logs_by_key.pop(_str_key))

    def _op_display(fkey) -> tuple[str, str]:
        """Returns (id_str, label) for a fuel-operator key."""
        if fkey == _NO_OPERATOR:
            return "unknown", "Non identificato"
        if isinstance(fkey, _uuid.UUID):
            wco = wc_ops_map.get(fkey)
            if wco:
                label = f"{wco.first_name or ''} {wco.last_name or ''}".strip() or wco.username or str(fkey)
                return f"wc:{fkey}", label
            return f"wc:{fkey}", str(fkey)
        return f"name:{fkey}", fkey  # legacy string key

    def _op_km(fkey) -> tuple[float, dict]:
        """Returns (total_km, {vehicle_id: km}) for an operator key."""
        if isinstance(fkey, _uuid.UUID):
            wco = wc_ops_map.get(fkey)
            if wco and wco.gaia_user_id:
                gid = int(wco.gaia_user_id)
                km = km_by_gaia_user.get(gid, 0.0)
                if km > 0:
                    return km, dict(km_by_gaia_user_vehicle.get(gid, {}))
            # WC-synced sessions store operator_name text rather than actual_driver_user_id.
            # Try matching WCOperator display name variants against session operator_name strings.
            if wco:
                for name_variant in [
                    f"{wco.first_name or ''} {wco.last_name or ''}".strip(),
                    f"{wco.last_name or ''} {wco.first_name or ''}".strip(),
                    wco.username or "",
                ]:
                    if name_variant and name_variant in km_by_op_name:
                        return km_by_op_name[name_variant], dict(km_by_op_name_vehicle[name_variant])
        # Legacy string key: match by session operator_name
        if isinstance(fkey, str) and fkey != _NO_OPERATOR:
            return km_by_op_name.get(fkey, 0.0), dict(km_by_op_name_vehicle.get(fkey, {}))
        return 0.0, {}

    top_fuel_keys = sorted(liters_by_key, key=liters_by_key.__getitem__, reverse=True)[:10]
    top_operators_out = []
    for fkey in top_fuel_keys:
        fid, flabel = _op_display(fkey)
        avg_price, avg_refuel_cost, avg_liters = _metrics_for_logs(logs_by_key[fkey])

        op_km, op_km_by_vehicle = _op_km(fkey)
        has_km = op_km > 0
        op_liters = sum(max(0.0, _safe_float(l.liters)) for l in logs_by_key[fkey])
        op_consumption = round(op_liters / op_km * 100, 2) if has_km and op_liters > 0 else None

        # Weighted consumption target across vehicles used (km-weighted)
        target_weighted = None
        if has_km and op_km_by_vehicle:
            num = den = 0.0
            for vid, kmv in op_km_by_vehicle.items():
                t = _target_consumption_l_per_100km(vehicles_map.get(vid))
                if t is None or kmv <= 0:
                    continue
                num += float(kmv) * float(t)
                den += float(kmv)
            if den > 0:
                target_weighted = num / den

        op_coeff = (
            op_consumption / target_weighted
            if op_consumption is not None and target_weighted and target_weighted > 0
            else None
        )
        op_judge = _judgement_from_coeff(op_coeff)

        # Related vehicles: top vehicles refuelled by this operator
        rel_by_vehicle: dict[str, list[VehicleFuelLog]] = defaultdict(list)
        for l in logs_by_key[fkey]:
            if l.vehicle_id:
                rel_by_vehicle[str(l.vehicle_id)].append(l)

        related_items: list[FuelRelatedUsageItem] = []
        if rel_by_vehicle:
            rel_vids = {_uuid.UUID(k) for k in rel_by_vehicle if k}
            rel_vmap: dict[str, Vehicle] = {}
            if rel_vids:
                for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(rel_vids))).all():
                    rel_vmap[str(v.id)] = v

            def _rel_score(vid: str) -> float:
                return sum(_safe_float(x.liters) for x in rel_by_vehicle[vid])

            for vid in sorted(rel_by_vehicle.keys(), key=_rel_score, reverse=True)[:5]:
                ls = rel_by_vehicle[vid]
                rp, rc, rl = _metrics_for_logs(ls)
                v = rel_vmap.get(vid)
                related_items.append(FuelRelatedUsageItem(
                    id=vid,
                    label=getattr(v, "plate_number", None) or getattr(v, "name", None) or vid,
                    refuel_count=len(ls),
                    total_liters=round(sum(_safe_float(x.liters) for x in ls), 2),
                    total_cost=round(sum(_safe_float(x.total_cost) for x in ls), 2),
                    avg_price_per_liter=round(rp, 4) if rp is not None else None,
                    avg_refuel_cost=round(rc, 2) if rc is not None else None,
                    avg_liters_per_refuel=round(rl, 2) if rl is not None else None,
                ))

        top_operators_out.append(FuelTopItem(
            id=fid,
            label=flabel,
            total_liters=round(liters_by_key[fkey], 2),
            total_cost=round(cost_by_key[fkey], 2),
            refuel_count=count_by_key[fkey],
            total_km=round(op_km, 1) if has_km else None,
            avg_consumption_l_per_100km=op_consumption,
            consumption_coefficient=round(op_coeff, 3) if op_coeff is not None else None,
            consumption_judgement=op_judge,
            avg_price_per_liter=round(avg_price, 4) if avg_price is not None else None,
            avg_refuel_cost=round(avg_refuel_cost, 2) if avg_refuel_cost is not None else None,
            avg_liters_per_refuel=round(avg_liters, 2) if avg_liters is not None else None,
            top_stations=_top_stations_for_logs(logs_by_key[fkey], limit=5),
            related=related_items,
        ))

    # related for vehicles: top operators for that vehicle (by liters)
    for item in top_vehicles_out:
        try:
            vid = _uuid.UUID(item.id)
        except Exception:
            continue
        vlogs = logs_by_vehicle.get(vid, [])
        if not vlogs:
            continue
        rel_by_op: dict = defaultdict(list)
        for l in vlogs:
            if l.wc_operator_id is not None:
                rkey = l.wc_operator_id
            elif l.operator_name:
                rkey = l.operator_name
            else:
                rkey = _NO_OPERATOR
            rel_by_op[rkey].append(l)

        def _rel_score_op(k) -> float:
            return sum(_safe_float(x.liters) for x in rel_by_op[k])

        related_ops: list[FuelRelatedUsageItem] = []
        for k in sorted(rel_by_op.keys(), key=_rel_score_op, reverse=True)[:5]:
            ls = rel_by_op[k]
            rp, rc, rl = _metrics_for_logs(ls)
            rid, rlabel = _op_display(k)
            related_ops.append(FuelRelatedUsageItem(
                id=rid,
                label=rlabel,
                refuel_count=len(ls),
                total_liters=round(sum(_safe_float(x.liters) for x in ls), 2),
                total_cost=round(sum(_safe_float(x.total_cost) for x in ls), 2),
                avg_price_per_liter=round(rp, 4) if rp is not None else None,
                avg_refuel_cost=round(rc, 2) if rc is not None else None,
                avg_liters_per_refuel=round(rl, 2) if rl is not None else None,
            ))
        item.related = related_ops

    positive_logs = [l for l in logs if (l.liters or 0) > 0]
    storno_logs = [l for l in logs if (l.liters or 0) < 0]

    total_liters = sum(float(l.liters or 0) for l in logs)
    total_cost = sum(float(l.total_cost or 0) for l in logs)
    avg_per_refuel = round(sum(float(l.liters or 0) for l in positive_logs) / len(positive_logs), 2) if positive_logs else 0

    storno_count = len(storno_logs)
    storno_liters = sum(float(l.liters or 0) for l in storno_logs)
    storno_cost = sum(float(l.total_cost or 0) for l in storno_logs)

    return FuelAnalytics(
        time_series=time_series,
        cost_series=cost_series,
        top_vehicles=top_vehicles_out,
        top_operators=top_operators_out,
        total_liters=round(total_liters, 2),
        total_cost=round(total_cost, 2),
        avg_liters_per_refuel=avg_per_refuel,
        storno_count=storno_count,
        storno_liters=round(storno_liters, 2),
        storno_cost=round(storno_cost, 2),
    )


# ─── km ────────────────────────────────────────────────────────────────────────

@router.get("/km", response_model=KmAnalytics)
def km_analytics(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
):
    today = date.today()
    d_from = _parse_date(from_date, today - timedelta(days=90))
    d_to = _parse_date(to_date, today)
    dt_from = datetime.combine(d_from, datetime.min.time())
    dt_to = datetime.combine(d_to, datetime.max.time())

    sessions = db.scalars(
        select(VehicleUsageSession).where(
            VehicleUsageSession.started_at >= dt_from,
            VehicleUsageSession.started_at <= dt_to,
            VehicleUsageSession.status != "open",
        )
    ).all()

    def _session_km(s: VehicleUsageSession) -> float:
        if s.route_distance_km:
            return float(s.route_distance_km)
        if s.end_odometer_km is not None and s.start_odometer_km is not None:
            diff = float(s.end_odometer_km) - float(s.start_odometer_km)
            return max(0.0, diff)
        return 0.0

    # Time series
    km_by_period: dict[str, float] = defaultdict(float)
    for s in sessions:
        key = _period_key(s.started_at, granularity)
        km_by_period[key] += _session_km(s)

    time_series = [
        TimeSeriesPoint(period=p, value=round(km_by_period[p], 1))
        for p in sorted(km_by_period)
    ]

    # Top vehicles
    vehicle_ids = {s.vehicle_id for s in sessions if s.vehicle_id}
    vehicles_map: dict = {}
    if vehicle_ids:
        for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).all():
            vehicles_map[v.id] = v

    km_by_vehicle: dict = defaultdict(float)
    count_by_vehicle: dict = defaultdict(int)
    for s in sessions:
        if s.vehicle_id:
            km_by_vehicle[s.vehicle_id] += _session_km(s)
            count_by_vehicle[s.vehicle_id] += 1

    top_v = sorted(km_by_vehicle, key=km_by_vehicle.__getitem__, reverse=True)[:10]
    top_vehicles_out = [
        KmTopItem(
            id=str(vid),
            label=getattr(vehicles_map.get(vid), "plate_number", None)
                  or getattr(vehicles_map.get(vid), "name", None)
                  or str(vid),
            total_km=round(km_by_vehicle[vid], 1),
            session_count=count_by_vehicle[vid],
            avg_km_per_session=(
                round(km_by_vehicle[vid] / count_by_vehicle[vid], 1)
                if count_by_vehicle[vid] > 0
                else None
            ),
        )
        for vid in top_v
    ]

    # Top operators — prefer actual_driver_user_id; for WC-imported sessions
    # without a linked user, fall back to operator_name (matched via WCOperator
    # where possible, otherwise used as-is as a string key).
    linked_user_ids = {s.actual_driver_user_id for s in sessions if s.actual_driver_user_id}
    users_map: dict = {}
    if linked_user_ids:
        for u in db.scalars(
            select(ApplicationUser).where(ApplicationUser.id.in_(linked_user_ids))
        ).all():
            users_map[u.id] = u

    # Build WCOperator name→display_name map for legacy sessions
    wc_operator_names = {
        s.operator_name
        for s in sessions
        if not s.actual_driver_user_id and s.operator_name
    }
    wc_label_map: dict[str, str] = {}
    if wc_operator_names:
        for wc_op in db.scalars(
            select(WCOperator).where(WCOperator.username.in_(wc_operator_names))
        ).all():
            display = f"{wc_op.first_name or ''} {wc_op.last_name or ''}".strip() or wc_op.username
            wc_label_map[wc_op.username] = display

    # Use a string key: user_id (int) for linked sessions, operator_name for WC legacy
    km_by_key: dict[str | int, float] = defaultdict(float)
    count_by_key: dict[str | int, int] = defaultdict(int)
    for s in sessions:
        if s.actual_driver_user_id:
            key: str | int = s.actual_driver_user_id
        elif s.operator_name:
            key = s.operator_name
        else:
            continue
        km_by_key[key] += _session_km(s)
        count_by_key[key] += 1

    top_keys = sorted(km_by_key, key=km_by_key.__getitem__, reverse=True)[:10]
    top_operators_out = []
    for key in top_keys:
        if isinstance(key, int):
            label = _user_display_name(users_map.get(key))
            entity_id = str(key)
        else:
            label = wc_label_map.get(key, key)
            entity_id = f"wc:{key}"
        top_operators_out.append(KmTopItem(
            id=entity_id,
            label=label,
            total_km=round(km_by_key[key], 1),
            session_count=count_by_key[key],
            avg_km_per_session=(
                round(km_by_key[key] / count_by_key[key], 1)
                if count_by_key[key] > 0
                else None
            ),
        ))

    total_km = sum(_session_km(s) for s in sessions)
    avg_km = round(total_km / len(sessions), 1) if sessions else 0

    def _operator_label_for_session(s: VehicleUsageSession) -> str | None:
        if s.actual_driver_user_id:
            return _user_display_name(users_map.get(s.actual_driver_user_id))
        if s.operator_name:
            return wc_label_map.get(s.operator_name, s.operator_name)
        return None

    def _vehicle_label_for_session(s: VehicleUsageSession) -> str:
        v = vehicles_map.get(s.vehicle_id)
        return getattr(v, "plate_number", None) or getattr(v, "name", None) or str(s.vehicle_id)

    def _duration_minutes(s: VehicleUsageSession) -> int | None:
        if not s.ended_at:
            return None
        try:
            delta = (s.ended_at - s.started_at).total_seconds()
        except Exception:  # pragma: no cover - defensive
            return None
        if delta < 0:
            return None
        return int(round(delta / 60))

    duration_candidates = [
        (s, _duration_minutes(s))
        for s in sessions
    ]
    duration_candidates = [(s, m) for (s, m) in duration_candidates if m is not None]

    longest_item = None
    shortest_item = None
    if duration_candidates:
        longest_sess, longest_min = max(duration_candidates, key=lambda t: t[1])
        shortest_sess, shortest_min = min(duration_candidates, key=lambda t: t[1])

        def _to_extreme(s: VehicleUsageSession, minutes: int) -> KmSessionExtremeItem:
            return KmSessionExtremeItem(
                session_id=str(s.id),
                vehicle_label=_vehicle_label_for_session(s),
                operator_label=_operator_label_for_session(s),
                started_at=s.started_at.isoformat(),
                ended_at=s.ended_at.isoformat() if s.ended_at else s.started_at.isoformat(),
                duration_minutes=minutes,
                km=round(_session_km(s), 1),
            )

        longest_item = _to_extreme(longest_sess, longest_min)
        shortest_item = _to_extreme(shortest_sess, shortest_min)

    return KmAnalytics(
        time_series=time_series,
        top_vehicles=top_vehicles_out,
        top_operators=top_operators_out,
        total_km=round(total_km, 1),
        avg_km_per_session=avg_km,
        longest_session=longest_item,
        shortest_session=shortest_item,
    )


# ─── work hours ────────────────────────────────────────────────────────────────

@router.get("/work-hours", response_model=WorkHoursAnalytics)
def work_hours_analytics(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
):
    today = date.today()
    d_from = _parse_date(from_date, today - timedelta(days=90))
    d_to = _parse_date(to_date, today)
    dt_from = datetime.combine(d_from, datetime.min.time())
    dt_to = datetime.combine(d_to, datetime.max.time())

    activities = db.scalars(
        select(OperatorActivity).where(
            OperatorActivity.started_at >= dt_from,
            OperatorActivity.started_at <= dt_to,
            OperatorActivity.status.in_(["submitted", "under_review", "approved"]),
        )
    ).all()

    def _activity_minutes(a: OperatorActivity) -> int:
        return int(a.duration_minutes_calculated or a.duration_minutes_declared or 0)

    # Time series (hours)
    hours_by_period: dict[str, float] = defaultdict(float)
    for a in activities:
        key = _period_key(a.started_at, granularity)
        hours_by_period[key] += _activity_minutes(a) / 60

    time_series = [
        TimeSeriesPoint(period=p, value=round(hours_by_period[p], 1))
        for p in sorted(hours_by_period)
    ]

    # By operator
    user_ids = {a.operator_user_id for a in activities if a.operator_user_id}
    users_map: dict = {}
    if user_ids:
        for u in db.scalars(
            select(ApplicationUser).where(ApplicationUser.id.in_(user_ids))
        ).all():
            users_map[u.id] = u

    hours_by_user: dict = defaultdict(float)
    count_by_user: dict = defaultdict(int)
    for a in activities:
        if a.operator_user_id:
            hours_by_user[a.operator_user_id] += _activity_minutes(a) / 60
            count_by_user[a.operator_user_id] += 1

    top_users = sorted(hours_by_user, key=hours_by_user.__getitem__, reverse=True)[:15]
    top_operators_out = [
        WorkHoursOperatorItem(
            operator_id=str(uid),
            operator_name=_user_display_name(users_map.get(uid)),
            total_hours=round(hours_by_user[uid], 1),
            activity_count=count_by_user[uid],
        )
        for uid in top_users
    ]

    # By team (via team_membership in the period)
    team_ids = {a.team_id for a in activities if a.team_id}
    teams_map: dict = {}
    if team_ids:
        for t in db.scalars(select(Team).where(Team.id.in_(team_ids))).all():
            teams_map[t.id] = t

    hours_by_team: dict = defaultdict(float)
    members_by_team: dict = defaultdict(set)
    for a in activities:
        if a.team_id:
            hours_by_team[a.team_id] += _activity_minutes(a) / 60
            if a.operator_user_id:
                members_by_team[a.team_id].add(a.operator_user_id)

    by_team_out = [
        WorkHoursTeamItem(
            team_id=str(tid),
            team_name=getattr(teams_map.get(tid), "name", str(tid)),
            total_hours=round(hours_by_team[tid], 1),
            operator_count=len(members_by_team[tid]),
        )
        for tid in sorted(hours_by_team, key=hours_by_team.__getitem__, reverse=True)
    ]

    # By activity category
    catalog_ids = {a.activity_catalog_id for a in activities if a.activity_catalog_id}
    catalog_map: dict = {}
    if catalog_ids:
        for c in db.scalars(
            select(ActivityCatalog).where(ActivityCatalog.id.in_(catalog_ids))
        ).all():
            catalog_map[c.id] = c

    hours_by_cat: dict = defaultdict(float)
    count_by_cat: dict = defaultdict(int)
    for a in activities:
        cat = getattr(catalog_map.get(a.activity_catalog_id), "category", None) or "Non categorizzato"
        hours_by_cat[cat] += _activity_minutes(a) / 60
        count_by_cat[cat] += 1

    by_category_out = [
        WorkHoursCategoryItem(
            category=cat,
            total_hours=round(hours_by_cat[cat], 1),
            activity_count=count_by_cat[cat],
        )
        for cat in sorted(hours_by_cat, key=hours_by_cat.__getitem__, reverse=True)
    ]

    total_hours = sum(_activity_minutes(a) / 60 for a in activities)
    unique_operators = len({a.operator_user_id for a in activities if a.operator_user_id})
    avg_hours = round(total_hours / unique_operators, 1) if unique_operators else 0

    return WorkHoursAnalytics(
        time_series=time_series,
        top_operators=top_operators_out,
        by_team=by_team_out,
        by_category=by_category_out,
        total_hours=round(total_hours, 1),
        avg_hours_per_operator=avg_hours,
    )


# ─── anomalies ─────────────────────────────────────────────────────────────────

@router.get("/anomalies", response_model=AnomaliesResponse)
def anomalies_analytics(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    anomaly_type: str | None = Query(None, alias="type"),
):
    today = date.today()
    d_from = _parse_date(from_date, today - timedelta(days=30))
    d_to = _parse_date(to_date, today)
    dt_from = datetime.combine(d_from, datetime.min.time())
    dt_to = datetime.combine(d_to, datetime.max.time())

    anomalies: list[AnomalyItem] = []

    # 1. Orphan sessions: open for > 24h
    if not anomaly_type or anomaly_type == "orphan_session":
        now_utc = datetime.now(tz=timezone.utc)
        cutoff = now_utc - timedelta(hours=24)
        orphan_sessions = db.scalars(
            select(VehicleUsageSession).where(
                VehicleUsageSession.status == "open",
                VehicleUsageSession.started_at <= cutoff,
                VehicleUsageSession.started_at >= dt_from,
            )
        ).all()

        vehicle_ids = {s.vehicle_id for s in orphan_sessions if s.vehicle_id}
        vehicles_map: dict = {}
        if vehicle_ids:
            for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).all():
                vehicles_map[v.id] = v

        for s in orphan_sessions:
            v = vehicles_map.get(s.vehicle_id)
            started = s.started_at if s.started_at.tzinfo else s.started_at.replace(tzinfo=timezone.utc)
            hours_open = (now_utc - started).total_seconds() / 3600
            anomalies.append(AnomalyItem(
                id=f"orphan_{s.id}",
                type="orphan_session",
                severity="medium" if hours_open < 48 else "high",
                description=f"Sessione aperta da {int(hours_open)}h senza chiusura",
                entity_id=str(s.id),
                entity_label=getattr(v, "plate_number", None) or str(s.vehicle_id),
                detected_at=s.started_at.isoformat(),
                details={"hours_open": round(hours_open, 1), "vehicle_id": str(s.vehicle_id), "wc_id": s.wc_id},
            ))

    # 2. Driver mismatch: actual_driver != assigned operator in the period
    if not anomaly_type or anomaly_type == "driver_mismatch":
        sessions = db.scalars(
            select(VehicleUsageSession).where(
                VehicleUsageSession.started_at >= dt_from,
                VehicleUsageSession.started_at <= dt_to,
                VehicleUsageSession.actual_driver_user_id.isnot(None),
            )
        ).all()

        vehicle_ids = {s.vehicle_id for s in sessions if s.vehicle_id}
        vehicles_map2: dict = {}
        if vehicle_ids:
            for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).all():
                vehicles_map2[v.id] = v

        user_ids = {s.actual_driver_user_id for s in sessions} | {s.started_by_user_id for s in sessions}
        users_map: dict = {}
        if user_ids:
            for u in db.scalars(
                select(ApplicationUser).where(ApplicationUser.id.in_(user_ids))
            ).all():
                users_map[u.id] = u

        # Load active assignments for these vehicles
        assignments = db.scalars(
            select(VehicleAssignment).where(
                VehicleAssignment.vehicle_id.in_(vehicle_ids),
                VehicleAssignment.assignment_target_type == "operator",
            )
        ).all() if vehicle_ids else []
        assign_by_vehicle: dict = defaultdict(list)
        for a in assignments:
            assign_by_vehicle[a.vehicle_id].append(a)

        for s in sessions:
            if not s.actual_driver_user_id or not s.vehicle_id:
                continue
            assigned_ops = [
                a.operator_user_id
                for a in assign_by_vehicle[s.vehicle_id]
                if a.operator_user_id
                and (a.end_at is None or a.end_at >= s.started_at)
                and a.start_at <= s.started_at
            ]
            if assigned_ops and s.actual_driver_user_id not in assigned_ops:
                v = vehicles_map2.get(s.vehicle_id)
                driver = users_map.get(s.actual_driver_user_id)
                anomalies.append(AnomalyItem(
                    id=f"mismatch_{s.id}",
                    type="driver_mismatch",
                    severity="high",
                    description=f"Guidatore effettivo non coincide con operatore assegnato al mezzo",
                    entity_id=str(s.id),
                    entity_label=getattr(v, "plate_number", None) or str(s.vehicle_id),
                    detected_at=s.started_at.isoformat(),
                    details={
                        "actual_driver": _user_display_name(driver),
                        "assigned_operator_ids": [str(x) for x in assigned_ops],
                    },
                ))

    # 3. Excessive fuel: > 120L in a single refuel (threshold configurable)
    if not anomaly_type or anomaly_type == "excessive_fuel":
        LITERS_THRESHOLD = 120.0
        excess_logs = db.scalars(
            select(VehicleFuelLog).where(
                VehicleFuelLog.fueled_at >= dt_from,
                VehicleFuelLog.fueled_at <= dt_to,
                VehicleFuelLog.liters > LITERS_THRESHOLD,
            )
        ).all()

        vids = {l.vehicle_id for l in excess_logs if l.vehicle_id}
        vmap: dict = {}
        if vids:
            for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(vids))).all():
                vmap[v.id] = v

        for log in excess_logs:
            v = vmap.get(log.vehicle_id)
            anomalies.append(AnomalyItem(
                id=f"fuel_{log.id}",
                type="excessive_fuel",
                severity="medium",
                description=f"Rifornimento anomalo: {float(log.liters):.1f}L (soglia {LITERS_THRESHOLD}L)",
                entity_id=str(log.id),
                entity_label=getattr(v, "plate_number", None) or str(log.vehicle_id),
                detected_at=log.fueled_at.isoformat(),
                details={
                    "liters": float(log.liters),
                    "cost": float(log.total_cost or 0),
                    "station": log.station_name,
                },
            ))

    # 4. Unmatched WC refuel events
    if not anomaly_type or anomaly_type == "unmatched_refuel":
        unmatched = db.scalars(
            select(WCRefuelEvent).where(
                WCRefuelEvent.matched_fuel_log_id.is_(None),
                WCRefuelEvent.fueled_at >= dt_from,
                WCRefuelEvent.fueled_at <= dt_to,
            )
        ).all()
        for ev in unmatched:
            anomalies.append(AnomalyItem(
                id=f"wc_{ev.id}",
                type="unmatched_refuel",
                severity="low",
                description="Evento rifornimento WC non abbinato a nessun log interno",
                entity_id=str(ev.id),
                entity_label=ev.vehicle_code or ev.operator_name or "–",
                detected_at=ev.fueled_at.isoformat(),
                details={"wc_id": ev.wc_id, "operator": ev.operator_name},
            ))

    # 5. Work hours discrepancy: |declared - calculated| > 60 min
    if not anomaly_type or anomaly_type == "hours_discrepancy":
        THRESHOLD_MIN = 60
        acts = db.scalars(
            select(OperatorActivity).where(
                OperatorActivity.started_at >= dt_from,
                OperatorActivity.started_at <= dt_to,
                OperatorActivity.duration_minutes_declared.isnot(None),
                OperatorActivity.duration_minutes_calculated.isnot(None),
            )
        ).all()

        user_ids_disc = {a.operator_user_id for a in acts if a.operator_user_id}
        umap: dict = {}
        if user_ids_disc:
            for u in db.scalars(
                select(ApplicationUser).where(ApplicationUser.id.in_(user_ids_disc))
            ).all():
                umap[u.id] = u

        for a in acts:
            diff = abs(
                int(a.duration_minutes_declared or 0)
                - int(a.duration_minutes_calculated or 0)
            )
            if diff > THRESHOLD_MIN:
                anomalies.append(AnomalyItem(
                    id=f"hours_{a.id}",
                    type="hours_discrepancy",
                    severity="low" if diff < 120 else "medium",
                    description=f"Discrepanza ore: dichiarate vs calcolate ({diff} min di scarto)",
                    entity_id=str(a.id),
                    entity_label=_user_display_name(umap.get(a.operator_user_id)),
                    detected_at=a.started_at.isoformat(),
                    details={
                        "declared_min": int(a.duration_minutes_declared),
                        "calculated_min": int(a.duration_minutes_calculated),
                        "diff_min": diff,
                    },
                ))

    # 6. Fuel logs on decommissioned vehicles
    if not anomaly_type or anomaly_type == "inactive_vehicle":
        inactive_vids = {
            v.id for v in db.scalars(
                select(Vehicle).where(Vehicle.is_active.is_(False))
            ).all()
        }
        if inactive_vids:
            bad_logs = db.scalars(
                select(VehicleFuelLog).where(
                    VehicleFuelLog.fueled_at >= dt_from,
                    VehicleFuelLog.fueled_at <= dt_to,
                    VehicleFuelLog.vehicle_id.in_(inactive_vids),
                )
            ).all()
            bad_sessions = db.scalars(
                select(VehicleUsageSession).where(
                    VehicleUsageSession.started_at >= dt_from,
                    VehicleUsageSession.started_at <= dt_to,
                    VehicleUsageSession.vehicle_id.in_(inactive_vids),
                )
            ).all()

            all_vids = {l.vehicle_id for l in bad_logs} | {s.vehicle_id for s in bad_sessions}
            vmap_inactive: dict = {}
            for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(all_vids))).all():
                vmap_inactive[v.id] = v

            for log in bad_logs:
                v = vmap_inactive.get(log.vehicle_id)
                anomalies.append(AnomalyItem(
                    id=f"inact_v_log_{log.id}",
                    type="inactive_vehicle",
                    severity="high",
                    description="Rifornimento registrato su mezzo dismesso",
                    entity_id=str(log.vehicle_id),
                    entity_label=getattr(v, "plate_number", None) or getattr(v, "code", None) or str(log.vehicle_id),
                    detected_at=log.fueled_at.isoformat(),
                    details={"liters": float(log.liters or 0), "vehicle_code": getattr(v, "code", None)},
                ))
            for s in bad_sessions:
                v = vmap_inactive.get(s.vehicle_id)
                anomalies.append(AnomalyItem(
                    id=f"inact_v_sess_{s.id}",
                    type="inactive_vehicle",
                    severity="high",
                    description="Sessione d'uso registrata su mezzo dismesso",
                    entity_id=str(s.vehicle_id),
                    entity_label=getattr(v, "plate_number", None) or getattr(v, "code", None) or str(s.vehicle_id),
                    detected_at=s.started_at.isoformat(),
                    details={"vehicle_code": getattr(v, "code", None)},
                ))

    # 7. Sessions / fuel logs for inactive/removed operators
    if not anomaly_type or anomaly_type == "inactive_operator":
        inactive_users = {
            u.id for u in db.scalars(
                select(ApplicationUser).where(ApplicationUser.is_active.is_(False))
            ).all()
        }
        if inactive_users:
            op_logs = db.scalars(
                select(VehicleFuelLog).where(
                    VehicleFuelLog.fueled_at >= dt_from,
                    VehicleFuelLog.fueled_at <= dt_to,
                    VehicleFuelLog.recorded_by_user_id.in_(inactive_users),
                )
            ).all()
            op_sessions = db.scalars(
                select(VehicleUsageSession).where(
                    VehicleUsageSession.started_at >= dt_from,
                    VehicleUsageSession.started_at <= dt_to,
                    VehicleUsageSession.actual_driver_user_id.in_(inactive_users),
                )
            ).all()

            all_uids = {l.recorded_by_user_id for l in op_logs} | {s.actual_driver_user_id for s in op_sessions}
            umap_inactive: dict = {}
            for u in db.scalars(select(ApplicationUser).where(ApplicationUser.id.in_(all_uids))).all():
                umap_inactive[u.id] = u

            vids_op = {l.vehicle_id for l in op_logs} | {s.vehicle_id for s in op_sessions}
            vmap_op: dict = {}
            if vids_op:
                for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(vids_op))).all():
                    vmap_op[v.id] = v

            for log in op_logs:
                u = umap_inactive.get(log.recorded_by_user_id)
                v = vmap_op.get(log.vehicle_id)
                anomalies.append(AnomalyItem(
                    id=f"inact_op_log_{log.id}",
                    type="inactive_operator",
                    severity="high",
                    description="Rifornimento registrato da operatore non più attivo",
                    entity_id=str(log.recorded_by_user_id),
                    entity_label=_user_display_name(u),
                    detected_at=log.fueled_at.isoformat(),
                    details={
                        "vehicle": getattr(v, "plate_number", None) or getattr(v, "code", None),
                        "liters": float(log.liters or 0),
                    },
                ))
            for s in op_sessions:
                u = umap_inactive.get(s.actual_driver_user_id)
                v = vmap_op.get(s.vehicle_id)
                anomalies.append(AnomalyItem(
                    id=f"inact_op_sess_{s.id}",
                    type="inactive_operator",
                    severity="high",
                    description="Sessione d'uso registrata da operatore non più attivo",
                    entity_id=str(s.actual_driver_user_id),
                    entity_label=_user_display_name(u),
                    detected_at=s.started_at.isoformat(),
                    details={"vehicle": getattr(v, "plate_number", None) or getattr(v, "code", None)},
                ))

    # 8. Orphan fuel card assignments — card still open on a disabled/unmapped WC operator
    if not anomaly_type or anomaly_type == "orphan_fuel_card":
        open_assignments = db.scalars(
            select(FuelCardAssignmentHistory).where(
                FuelCardAssignmentHistory.end_at.is_(None),
                FuelCardAssignmentHistory.wc_operator_id.isnot(None),
            )
        ).all()

        wc_op_ids = {a.wc_operator_id for a in open_assignments}
        wc_ops: dict = {}
        if wc_op_ids:
            for op in db.scalars(select(WCOperator).where(WCOperator.id.in_(wc_op_ids))).all():
                wc_ops[op.id] = op

        card_ids = {a.fuel_card_id for a in open_assignments}
        cards_map: dict = {}
        if card_ids:
            for card in db.scalars(select(FuelCard).where(FuelCard.id.in_(card_ids))).all():
                cards_map[card.id] = card

        for assignment in open_assignments:
            op = wc_ops.get(assignment.wc_operator_id)
            if op is None:
                continue
            disabled = not op.enabled
            unmapped = op.gaia_user_id is None
            if not disabled and not unmapped:
                continue
            card = cards_map.get(assignment.fuel_card_id)
            reason = []
            if disabled:
                reason.append("operatore WC disabilitato")
            if unmapped:
                reason.append("operatore non collegato a utente GAIA")
            op_name = " ".join(p for p in [op.last_name, op.first_name] if p) or op.username or str(op.id)
            anomalies.append(AnomalyItem(
                id=f"orphan_card_{assignment.id}",
                type="orphan_fuel_card",
                severity="medium",
                description=f"Tessera carburante ancora aperta: {', '.join(reason)}",
                entity_id=str(assignment.fuel_card_id),
                entity_label=getattr(card, "codice", None) or str(assignment.fuel_card_id),
                detected_at=assignment.start_at.isoformat(),
                details={"operator": op_name, "reasons": reason},
            ))

    # Aggregate counts
    by_type: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)
    for item in anomalies:
        by_type[item.type] += 1
        by_severity[item.severity] += 1

    # Sort: high first, then medium, then low
    sev_order = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda x: sev_order.get(x.severity, 3))

    return AnomaliesResponse(
        items=anomalies,
        total=len(anomalies),
        by_type=dict(by_type),
        by_severity=dict(by_severity),
    )
