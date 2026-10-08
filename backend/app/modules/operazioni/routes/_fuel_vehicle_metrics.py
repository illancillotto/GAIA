"""Pure consumption metrics for the fuel vehicle response."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VehicleFuelConsumption:
    consumption: float | None
    coefficient: float | None
    judgement: str | None


def _judgement_from_coeff(coeff: float | None) -> str | None:
    if coeff is None:
        return None
    if coeff <= 1.10:
        return "OK"
    if coeff <= 1.30:
        return "Alto"
    return "Molto alto"


def vehicle_fuel_consumption(
    positive_liters: float, distance_km: float | None, target: float | None
) -> VehicleFuelConsumption:
    if distance_km is None or not distance_km > 0 or not positive_liters > 0:
        return VehicleFuelConsumption(None, None, None)
    raw_consumption = positive_liters / distance_km * 100
    coefficient = raw_consumption / target if target is not None else None
    return VehicleFuelConsumption(
        consumption=round(raw_consumption, 2),
        coefficient=round(float(coefficient), 3) if coefficient is not None else None,
        judgement=_judgement_from_coeff(coefficient),
    )
