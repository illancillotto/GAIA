"""Characterize real ORM identity retention on the original anomalies route."""

import sqlite3
import weakref
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

import app.main
from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment, VehicleUsageSession
from app.modules.operazioni.routes import analytics

STARTED = datetime(2026, 3, 15, 8)
VEHICLE_ID = UUID("00000000-0000-0000-0000-000000000002")
SESSION_ID = UUID("00000000-0000-0000-0000-000000000001")

MISMATCH_ITEM = {
    "id": "mismatch_00000000-0000-0000-0000-000000000001",
    "type": "driver_mismatch",
    "severity": "high",
    "description": "Guidatore effettivo non coincide con operatore assegnato al mezzo",
    "entity_id": "00000000-0000-0000-0000-000000000001",
    "entity_label": "BEFORE",
    "detected_at": "2026-03-15T08:00:00",
    "details": {"actual_driver": "operator-41", "assigned_operator_ids": ["52"]},
}
INACTIVE_ITEM = {
    "id": "inact_v_sess_00000000-0000-0000-0000-000000000001",
    "type": "inactive_vehicle",
    "severity": "high",
    "description": "Sessione d'uso registrata su mezzo dismesso",
    "entity_id": "00000000-0000-0000-0000-000000000002",
    "entity_label": "BEFORE",
    "detected_at": "2026-03-15T08:00:00",
    "details": {"vehicle_code": "R19-VEHICLE"},
}


def _seed_closed_session(engine: Engine) -> None:
    with Session(engine) as seed:
        for identifier in (41, 52, 99):
            seed.add(
                ApplicationUser(
                    id=identifier,
                    username=f"operator-{identifier}",
                    email=f"{identifier}@lifetime.local",
                    password_hash="unused-by-direct-route",
                    role="viewer",
                    is_active=True,
                    module_operazioni=True,
                )
            )
        seed.add(
            Vehicle(
                id=VEHICLE_ID,
                code="R19-VEHICLE",
                name="lifetime",
                plate_number="BEFORE",
                vehicle_type="autocarro",
                fuel_type="diesel",
                current_status="available",
                is_active=False,
            )
        )
        seed.flush()
        seed.add(
            VehicleUsageSession(
                id=SESSION_ID,
                vehicle_id=VEHICLE_ID,
                started_by_user_id=99,
                actual_driver_user_id=41,
                started_at=STARTED,
                ended_at=STARTED + timedelta(hours=1),
                start_odometer_km=Decimal("100"),
                end_odometer_km=Decimal("110"),
                status="closed",
            )
        )
        seed.add(
            VehicleAssignment(
                vehicle_id=VEHICLE_ID,
                assignment_target_type="operator",
                operator_user_id=52,
                assigned_by_user_id=99,
                start_at=STARTED - timedelta(days=1),
            )
        )
        seed.commit()


class ObservedReader(Session):
    def __init__(self, engine: Engine, update_before_query: str):
        super().__init__(engine, autoflush=False)
        self.engine = engine
        self.update_before_query = update_before_query
        self.queries: list[str] = []
        self.vehicle_refs: list[weakref.ReferenceType[Vehicle]] = []
        self.boundary: dict[str, bool | int | str] = {}

    def _commit_external_plate_update(self) -> None:
        self.boundary["first_loaded_vehicle_alive"] = bool(
            self.vehicle_refs and self.vehicle_refs[0]() is not None
        )
        self.boundary["identity_map_contains_vehicle"] = (
            self.identity_key(Vehicle, VEHICLE_ID) in self.identity_map
        )
        reader_connection = self.connection().connection.driver_connection
        with self.engine.begin() as writer:
            self.boundary["writer_is_distinct_connection"] = (
                writer.connection.driver_connection is not reader_connection
            )
            result = writer.execute(
                Vehicle.__table__.update()
                .where(Vehicle.__table__.c.id == VEHICLE_ID)
                .values(plate_number="AFTER")
            )
            self.boundary["updated_rows"] = result.rowcount
        with self.engine.connect() as witness:
            assert witness.connection.driver_connection is not reader_connection
            self.boundary["committed_external_plate"] = witness.scalar(
                select(Vehicle.__table__.c.plate_number).where(Vehicle.__table__.c.id == VEHICLE_ID)
            )

    def scalars(self, statement, *args, **kwargs):
        entity = statement.column_descriptions[0]["entity"]
        self.queries.append(entity.__tablename__)
        if entity.__tablename__ == self.update_before_query and not self.boundary:
            self._commit_external_plate_update()
        return super().scalars(statement, *args, **kwargs)


def _run_route(anomaly_type: str | None, update_before_query: str):
    assert any(
        getattr(route, "endpoint", None) is analytics.anomalies_analytics
        for route in app.main.app.routes
    )
    uri = f"file:r19-lifetime-{uuid4().hex}?mode=memory&cache=shared"
    engine = create_engine(
        "sqlite://",
        creator=lambda: sqlite3.connect(uri, uri=True),
        poolclass=QueuePool,
        pool_size=4,
        max_overflow=0,
    )
    try:
        Base.metadata.create_all(engine)
        _seed_closed_session(engine)
        with ObservedReader(engine, update_before_query) as reader:
            vehicle_refs = reader.vehicle_refs

            def observe_loaded_vehicle(session, instance):
                if isinstance(instance, Vehicle) and instance.id == VEHICLE_ID:
                    vehicle_refs.append(weakref.ref(instance))

            event.listen(reader, "loaded_as_persistent", observe_loaded_vehicle)
            response = analytics.anomalies_analytics(
                current_user=None,
                db=reader,
                from_date="2026-03-15",
                to_date="2026-03-15",
                anomaly_type=anomaly_type,
            ).model_dump(mode="json")
            reader.boundary["reader_dirty_count"] = len(reader.dirty)
            return response, reader.queries, reader.boundary
    finally:
        engine.dispose()


def test_all_anomaly_families_reuse_driver_vehicle_after_distinct_writer_commit():
    response, queries, boundary = _run_route(None, "vehicle_fuel_log")

    assert response == {
        "items": [MISMATCH_ITEM, INACTIVE_ITEM],
        "total": 2,
        "by_type": {"driver_mismatch": 1, "inactive_vehicle": 1},
        "by_severity": {"high": 2},
    }
    assert queries == [
        "vehicle_usage_session",
        "vehicle_usage_session",
        "vehicle",
        "application_users",
        "vehicle_assignment",
        "vehicle_fuel_log",
        "wc_refuel_event",
        "operator_activity",
        "vehicle",
        "vehicle_fuel_log",
        "vehicle_usage_session",
        "vehicle",
        "application_users",
        "fuel_card_assignment_history",
    ]
    assert boundary == {
        "first_loaded_vehicle_alive": True,
        "identity_map_contains_vehicle": True,
        "writer_is_distinct_connection": True,
        "updated_rows": 1,
        "committed_external_plate": "AFTER",
        "reader_dirty_count": 0,
    }


def test_driver_only_preserves_loaded_vehicle_during_assignment_query():
    response, queries, boundary = _run_route("driver_mismatch", "vehicle_assignment")

    assert response == {
        "items": [MISMATCH_ITEM],
        "total": 1,
        "by_type": {"driver_mismatch": 1},
        "by_severity": {"high": 1},
    }
    assert queries == [
        "vehicle_usage_session",
        "vehicle",
        "application_users",
        "vehicle_assignment",
    ]
    assert boundary == {
        "first_loaded_vehicle_alive": True,
        "identity_map_contains_vehicle": True,
        "writer_is_distinct_connection": True,
        "updated_rows": 1,
        "committed_external_plate": "AFTER",
        "reader_dirty_count": 0,
    }


def test_inactive_only_reads_committed_plate_without_driver_identity_retention():
    response, queries, boundary = _run_route("inactive_vehicle", "vehicle")

    assert response == {
        "items": [{**INACTIVE_ITEM, "entity_label": "AFTER"}],
        "total": 1,
        "by_type": {"inactive_vehicle": 1},
        "by_severity": {"high": 1},
    }
    assert queries == [
        "vehicle",
        "vehicle_fuel_log",
        "vehicle_usage_session",
        "vehicle",
    ]
    assert boundary == {
        "first_loaded_vehicle_alive": False,
        "identity_map_contains_vehicle": False,
        "writer_is_distinct_connection": True,
        "updated_rows": 1,
        "committed_external_plate": "AFTER",
        "reader_dirty_count": 0,
    }
