"""Response mappers for events recorded against decommissioned vehicles."""

from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession
from app.schemas.operazioni_analytics import AnomalyItem


def _vehicle_label(vehicle: Vehicle | None, event: VehicleFuelLog | VehicleUsageSession) -> str:
    return (
        getattr(vehicle, "plate_number", None)
        or getattr(vehicle, "code", None)
        or str(event.vehicle_id)
    )


def inactive_vehicle_fuel_anomaly(log: VehicleFuelLog, vehicle: Vehicle | None) -> AnomalyItem:
    return AnomalyItem(
        id=f"inact_v_log_{log.id}",
        type="inactive_vehicle",
        severity="high",
        description="Rifornimento registrato su mezzo dismesso",
        entity_id=str(log.vehicle_id),
        entity_label=_vehicle_label(vehicle, log),
        detected_at=log.fueled_at.isoformat(),
        details={"liters": float(log.liters or 0), "vehicle_code": getattr(vehicle, "code", None)},
    )


def inactive_vehicle_session_anomaly(
    session: VehicleUsageSession, vehicle: Vehicle | None
) -> AnomalyItem:
    return AnomalyItem(
        id=f"inact_v_sess_{session.id}",
        type="inactive_vehicle",
        severity="high",
        description="Sessione d'uso registrata su mezzo dismesso",
        entity_id=str(session.vehicle_id),
        entity_label=_vehicle_label(vehicle, session),
        detected_at=session.started_at.isoformat(),
        details={"vehicle_code": getattr(vehicle, "code", None)},
    )
