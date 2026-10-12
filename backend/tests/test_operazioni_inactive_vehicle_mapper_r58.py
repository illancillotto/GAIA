"""Pure mapper boundary contracts; no invalid rows are persisted."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.services.inactive_vehicle_anomalies import (
    inactive_vehicle_fuel_anomaly,
    inactive_vehicle_session_anomaly,
)

VEHICLE_ID = UUID(int=5801)
EVENT_ID = UUID(int=5802)
MOMENT = datetime(2026, 10, 2, 8, 15, 30, 123456)
LABEL_CASES = [
    (False, "PLATE", "CODE", "PLATE"),
    (False, "", "CODE", "CODE"),
    (False, None, "CODE", "CODE"),
    (False, None, "", str(VEHICLE_ID)),
    (False, None, None, str(VEHICLE_ID)),
    (False, "  ", "CODE", "  "),
    (True, None, None, str(VEHICLE_ID)),
]


def _vehicle(missing: bool, plate: str | None, code: str | None) -> Vehicle | None:
    if missing:
        return None
    return Vehicle(
        id=VEHICLE_ID,
        name="Transient mapper input",
        vehicle_type="autocarro",
        code=code,
        plate_number=plate,
        is_active=False,
    )


def _fuel(liters: Decimal | None = Decimal("10.125")) -> VehicleFuelLog:
    return VehicleFuelLog(
        id=EVENT_ID,
        vehicle_id=VEHICLE_ID,
        recorded_by_user_id=58,
        fueled_at=MOMENT,
        liters=liters,
        total_cost=None,
    )


def _session() -> VehicleUsageSession:
    return VehicleUsageSession(
        id=EVENT_ID,
        vehicle_id=VEHICLE_ID,
        started_by_user_id=58,
        started_at=MOMENT,
        start_odometer_km=Decimal("0"),
        status="closed",
    )


@pytest.mark.parametrize(("missing", "plate", "code", "label"), LABEL_CASES)
@pytest.mark.parametrize("liters", [None, Decimal("0"), Decimal("10.125"), Decimal("-1.25")])
def test_fuel_mapper_preserves_transient_null_falsy_whitespace_and_exact_payload(
    missing: bool, plate: str | None, code: str | None, label: str, liters: Decimal | None
) -> None:
    vehicle = _vehicle(missing, plate, code)
    fuel = _fuel(liters)
    result = inactive_vehicle_fuel_anomaly(fuel, vehicle)

    assert result.model_dump(mode="json") == {
        "id": f"inact_v_log_{EVENT_ID}",
        "type": "inactive_vehicle",
        "severity": "high",
        "description": "Rifornimento registrato su mezzo dismesso",
        "entity_id": str(VEHICLE_ID),
        "entity_label": label,
        "detected_at": MOMENT.isoformat(),
        "details": {"liters": float(liters) if liters is not None else 0.0, "vehicle_code": code},
    }
    assert fuel.liters == liters
    assert fuel.total_cost is None


@pytest.mark.parametrize(("missing", "plate", "code", "label"), LABEL_CASES)
def test_session_mapper_preserves_transient_null_falsy_whitespace_and_exact_payload(
    missing: bool, plate: str | None, code: str | None, label: str
) -> None:
    result = inactive_vehicle_session_anomaly(_session(), _vehicle(missing, plate, code))
    assert result.model_dump(mode="json") == {
        "id": f"inact_v_sess_{EVENT_ID}",
        "type": "inactive_vehicle",
        "severity": "high",
        "description": "Sessione d'uso registrata su mezzo dismesso",
        "entity_id": str(VEHICLE_ID),
        "entity_label": label,
        "detected_at": MOMENT.isoformat(),
        "details": {"vehicle_code": code},
    }


@pytest.mark.parametrize("family", ["fuel", "session"])
@pytest.mark.parametrize(("plate", "code"), [("PLATE", "CODE"), (None, "CODE"), (None, "")])
def test_actual_orm_getters_keep_lazy_short_circuit_and_original_read_order(
    monkeypatch: pytest.MonkeyPatch, family: str, plate: str | None, code: str
) -> None:
    vehicle = _vehicle(False, plate, code)
    event = _fuel() if family == "fuel" else _session()
    reads: list[str] = []
    vehicle_getattribute = Vehicle.__getattribute__
    event_class = type(event)
    event_getattribute = event_class.__getattribute__

    def vehicle_read(instance: Vehicle, name: str) -> Any:
        if instance is vehicle and name in ("plate_number", "code"):
            reads.append(f"vehicle.{name}")
        return vehicle_getattribute(instance, name)

    def event_read(instance: VehicleFuelLog | VehicleUsageSession, name: str) -> Any:
        if instance is event and name in ("id", "vehicle_id", "fueled_at", "started_at", "liters"):
            reads.append(f"event.{name}")
        return event_getattribute(instance, name)

    monkeypatch.setattr(Vehicle, "__getattribute__", vehicle_read)
    monkeypatch.setattr(event_class, "__getattribute__", event_read)
    if family == "fuel":
        assert isinstance(event, VehicleFuelLog)
        inactive_vehicle_fuel_anomaly(event, vehicle)
    else:
        assert isinstance(event, VehicleUsageSession)
        inactive_vehicle_session_anomaly(event, vehicle)

    expected = ["event.id", "event.vehicle_id", "vehicle.plate_number"]
    if not plate:
        expected.append("vehicle.code")
        if not code:
            expected.append("event.vehicle_id")
    expected.append("event.fueled_at" if family == "fuel" else "event.started_at")
    if family == "fuel":
        expected.append("event.liters")
    expected.append("vehicle.code")
    assert reads == expected


@pytest.mark.parametrize("family", ["fuel", "session"])
def test_code_is_reread_for_details_not_cached_from_label(
    monkeypatch: pytest.MonkeyPatch, family: str
) -> None:
    vehicle = _vehicle(False, None, "persisted-code")
    vehicle_getattribute = Vehicle.__getattribute__
    codes = iter(["label-code", "details-code"])
    reads: list[str] = []

    def vehicle_read(instance: Vehicle, name: str) -> Any:
        if instance is vehicle and name == "code":
            value = next(codes)
            reads.append(value)
            return value
        return vehicle_getattribute(instance, name)

    monkeypatch.setattr(Vehicle, "__getattribute__", vehicle_read)
    result = (
        inactive_vehicle_fuel_anomaly(_fuel(), vehicle)
        if family == "fuel"
        else inactive_vehicle_session_anomaly(_session(), vehicle)
    )
    assert result.entity_label == "label-code"
    assert result.details["vehicle_code"] == "details-code"
    assert reads == ["label-code", "details-code"]


@pytest.mark.parametrize("failure_at", ["plate_number", "code", "fueled_at", "liters"])
def test_original_first_attribute_failure_propagates_without_later_reads(
    monkeypatch: pytest.MonkeyPatch, failure_at: str
) -> None:
    vehicle = _vehicle(False, None, "CODE")
    fuel = _fuel()
    failure = RuntimeError(f"read failed: {failure_at}")
    reads: list[str] = []
    vehicle_getattribute = Vehicle.__getattribute__
    fuel_getattribute = VehicleFuelLog.__getattribute__

    def vehicle_read(instance: Vehicle, name: str) -> Any:
        if instance is vehicle and name in ("plate_number", "code"):
            reads.append(name)
            if name == failure_at:
                raise failure
        return vehicle_getattribute(instance, name)

    def fuel_read(instance: VehicleFuelLog, name: str) -> Any:
        if instance is fuel and name in ("fueled_at", "liters"):
            reads.append(name)
            if name == failure_at:
                raise failure
        return fuel_getattribute(instance, name)

    monkeypatch.setattr(Vehicle, "__getattribute__", vehicle_read)
    monkeypatch.setattr(VehicleFuelLog, "__getattribute__", fuel_read)
    with pytest.raises(RuntimeError) as captured:
        inactive_vehicle_fuel_anomaly(fuel, vehicle)
    assert captured.value is failure
    order = ["plate_number", "code", "fueled_at", "liters"]
    assert reads == order[: order.index(failure_at) + 1]


def test_liters_float_failure_precedes_the_code_details_reread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vehicle = _vehicle(False, None, "CODE")
    failure = ValueError("liters cannot convert")
    reads: list[str] = []
    vehicle_getattribute = Vehicle.__getattribute__

    class InvalidFloatDecimal(Decimal):
        def __float__(self) -> float:
            reads.append("float")
            raise failure

    def vehicle_read(instance: Vehicle, name: str) -> Any:
        if instance is vehicle and name == "code":
            reads.append("code")
        return vehicle_getattribute(instance, name)

    monkeypatch.setattr(Vehicle, "__getattribute__", vehicle_read)
    with pytest.raises(ValueError) as captured:
        inactive_vehicle_fuel_anomaly(_fuel(InvalidFloatDecimal("1")), vehicle)
    assert captured.value is failure
    assert reads == ["code", "float"]


def test_details_code_failure_remains_after_liters_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vehicle = _vehicle(False, None, "CODE")
    fuel = _fuel()
    failure = RuntimeError("details code read failed")
    reads: list[str] = []
    vehicle_getattribute = Vehicle.__getattribute__
    fuel_getattribute = VehicleFuelLog.__getattribute__
    code_reads = 0

    def vehicle_read(instance: Vehicle, name: str) -> Any:
        nonlocal code_reads
        if instance is vehicle and name == "code":
            code_reads += 1
            reads.append(f"code{code_reads}")
            if code_reads == 2:
                raise failure
        return vehicle_getattribute(instance, name)

    def fuel_read(instance: VehicleFuelLog, name: str) -> Any:
        if instance is fuel and name == "liters":
            reads.append("liters")
        return fuel_getattribute(instance, name)

    monkeypatch.setattr(Vehicle, "__getattribute__", vehicle_read)
    monkeypatch.setattr(VehicleFuelLog, "__getattribute__", fuel_read)
    with pytest.raises(RuntimeError) as captured:
        inactive_vehicle_fuel_anomaly(fuel, vehicle)
    assert captured.value is failure
    assert reads == ["code1", "liters", "code2"]
