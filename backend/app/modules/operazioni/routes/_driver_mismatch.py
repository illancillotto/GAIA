from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment, VehicleUsageSession
from app.schemas.operazioni_analytics import AnomalyItem


@dataclass
class DriverMismatchInputs:
    sessions: Sequence[VehicleUsageSession]
    vehicles: dict[UUID, Vehicle]
    users: dict[int, ApplicationUser]
    assignments: defaultdict[UUID, list[VehicleAssignment]]


def load_driver_mismatch_inputs(
    db: Session, dt_from: datetime, dt_to: datetime
) -> DriverMismatchInputs:
    sessions = db.scalars(
        select(VehicleUsageSession).where(
            VehicleUsageSession.started_at >= dt_from,
            VehicleUsageSession.started_at <= dt_to,
            VehicleUsageSession.actual_driver_user_id.isnot(None),
        )
    ).all()
    vehicle_ids = {session.vehicle_id for session in sessions if session.vehicle_id}
    vehicles: dict[UUID, Vehicle] = {}
    if vehicle_ids:
        for vehicle in db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).all():
            vehicles[vehicle.id] = vehicle
    user_ids = {session.actual_driver_user_id for session in sessions} | {
        session.started_by_user_id for session in sessions
    }
    users: dict[int, ApplicationUser] = {}
    if user_ids:
        for user in db.scalars(
            select(ApplicationUser).where(ApplicationUser.id.in_(user_ids))
        ).all():
            users[user.id] = user
    assignments = (
        db.scalars(
            select(VehicleAssignment).where(
                VehicleAssignment.vehicle_id.in_(vehicle_ids),
                VehicleAssignment.assignment_target_type == "operator",
            )
        ).all()
        if vehicle_ids
        else []
    )
    assignments_by_vehicle: defaultdict[UUID, list[VehicleAssignment]] = defaultdict(list)
    for assignment in assignments:
        assignments_by_vehicle[assignment.vehicle_id].append(assignment)
    return DriverMismatchInputs(sessions, vehicles, users, assignments_by_vehicle)


def assigned_operator_ids_at(
    assignments: Sequence[VehicleAssignment], session: VehicleUsageSession
) -> list[int]:
    return [
        assignment.operator_user_id
        for assignment in assignments
        if assignment.operator_user_id
        and (assignment.end_at is None or assignment.end_at >= session.started_at)
        and assignment.start_at <= session.started_at
    ]


def driver_mismatch_item(
    session: VehicleUsageSession,
    assigned_operator_ids: Sequence[int],
    vehicle: Vehicle | None,
    driver: ApplicationUser | None,
    display_name: Callable[[ApplicationUser | None], str],
) -> AnomalyItem:
    return AnomalyItem(
        id=f"mismatch_{session.id}",
        type="driver_mismatch",
        severity="high",
        description="Guidatore effettivo non coincide con operatore assegnato al mezzo",
        entity_id=str(session.id),
        entity_label=getattr(vehicle, "plate_number", None) or str(session.vehicle_id),
        detected_at=session.started_at.isoformat(),
        details={
            "actual_driver": display_name(driver),
            "assigned_operator_ids": [str(operator_id) for operator_id in assigned_operator_ids],
        },
    )


def driver_mismatch_anomalies(
    inputs: DriverMismatchInputs,
    display_name: Callable[[ApplicationUser | None], str],
) -> list[AnomalyItem]:
    anomalies: list[AnomalyItem] = []
    for session in inputs.sessions:
        if not session.actual_driver_user_id or not session.vehicle_id:
            continue
        assigned_operator_ids = assigned_operator_ids_at(
            inputs.assignments[session.vehicle_id], session
        )
        if not assigned_operator_ids or session.actual_driver_user_id in assigned_operator_ids:
            continue
        vehicle = inputs.vehicles.get(session.vehicle_id)
        driver = inputs.users.get(session.actual_driver_user_id)
        anomalies.append(
            driver_mismatch_item(session, assigned_operator_ids, vehicle, driver, display_name)
        )
    return anomalies
