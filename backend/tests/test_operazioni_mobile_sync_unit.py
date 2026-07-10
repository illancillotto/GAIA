from __future__ import annotations

import base64
import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if "shapely" not in sys.modules:
    shapely_module = types.ModuleType("shapely")
    shapely_geometry = types.ModuleType("shapely.geometry")
    shapely_geometry.shape = lambda value: value
    shapely_module.geometry = shapely_geometry
    sys.modules["shapely"] = shapely_module
    sys.modules["shapely.geometry"] = shapely_geometry

if "geoalchemy2" not in sys.modules:
    geoalchemy2_module = types.ModuleType("geoalchemy2")
    geoalchemy2_shape = types.ModuleType("geoalchemy2.shape")
    geoalchemy2_shape.to_shape = lambda value: value
    geoalchemy2_module.shape = geoalchemy2_shape
    sys.modules["geoalchemy2"] = geoalchemy2_module
    sys.modules["geoalchemy2.shape"] = geoalchemy2_shape

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto_phase1 import CatDeliveryPoint, CatMeterReading
from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.attachments import Attachment
from app.modules.operazioni.models.mobile_sync import MobileSyncEvent
from app.modules.operazioni.models.organizational import OperatorProfile, Team, TeamMembership
from app.modules.operazioni.models.reports import FieldReportCategory, FieldReportSeverity
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.routes import mobile_sync as mobile_sync_routes


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
client = TestClient(app)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_function() -> None:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _connector_headers() -> dict[str, str]:
    return {settings.mobile_connector_header_name: settings.mobile_connector_token}


def _seed_mobile_operator(
    db: Session,
    *,
    role: str = ApplicationUserRole.OPERATOR.value,
    user_active: bool = True,
    operator_enabled: bool = True,
    linked_user: bool = True,
    with_profile: bool = True,
    username: str = "field.operator",
    wc_id: int = 101,
) -> tuple[WCOperator, ApplicationUser | None]:
    user: ApplicationUser | None = None
    gaia_user_id: int | None = None
    if linked_user:
        user = ApplicationUser(
            username=username,
            email=f"{username}@example.local",
            password_hash=hash_password("operator123"),
            role=role,
            is_active=user_active,
            module_operazioni=True,
        )
        db.add(user)
        db.flush()
        gaia_user_id = user.id
        if with_profile:
            db.add(
                OperatorProfile(
                    user_id=user.id,
                    phone="+39000000001",
                    can_drive_vehicles=True,
                    is_active=True,
                )
            )

    operator = WCOperator(
        wc_id=wc_id,
        username=username,
        email=f"{username}@example.local",
        first_name="Mario",
        last_name="Rossi",
        enabled=operator_enabled,
        gate_mobile_console_enabled=True,
        gate_mobile_console_role="console_admin",
        gaia_user_id=gaia_user_id,
        wc_synced_at=datetime.now(UTC),
    )
    db.add(operator)
    db.flush()
    return operator, user


def _seed_attachment(
    db: Session,
    *,
    operator_id: UUID,
    client_attachment_id: UUID | None = None,
    checksum: str = "abc",
    filename: str = "photo.jpg",
) -> Attachment:
    attachment = Attachment(
        storage_path=f"/tmp/{uuid4()}-{filename}",
        original_filename=filename,
        mime_type="image/jpeg",
        extension=".jpg",
        attachment_type="image",
        file_size_bytes=4,
        checksum_sha256=checksum,
        source_context="mobile_sync_attachment",
        metadata_json={
            "client_attachment_id": str(client_attachment_id or uuid4()),
            "operator_id": str(operator_id),
        },
        is_deleted=False,
    )
    db.add(attachment)
    db.flush()
    return attachment


def _seed_category(db: Session, *, code: str = "LOSS", wc_id: int | None = 3, active: bool = True) -> FieldReportCategory:
    category = FieldReportCategory(code=code, name=code, wc_id=wc_id, is_active=active)
    db.add(category)
    db.flush()
    return category


def _seed_severity(db: Session, *, code: str = "MED", rank_order: int = 1, active: bool = True) -> FieldReportSeverity:
    severity = FieldReportSeverity(code=code, name=code, rank_order=rank_order, is_active=active)
    db.add(severity)
    db.flush()
    return severity


def _mobile_error_context(excinfo: pytest.ExceptionInfo[mobile_sync_routes.MobileSyncAPIError], status_code: int, field: str) -> None:
    assert excinfo.value.status_code == status_code
    assert excinfo.value.details["field"] == field


def test_mobile_sync_helper_branches_for_display_names_and_coordinates() -> None:
    operator = WCOperator(username="fallback-user", email="x@example.local", first_name="", last_name="")
    user = ApplicationUser(username="gaia-user", email="gaia@example.local", password_hash="hash", role="viewer", is_active=True)

    assert mobile_sync_routes._operator_display_name(operator, user) == "gaia-user"
    assert mobile_sync_routes._operator_display_name(operator, None) == "fallback-user"
    operator.username = None
    assert mobile_sync_routes._operator_display_name(operator, None) == str(operator.id)

    assert mobile_sync_routes._delivery_point_coordinates(TestingSessionLocal(), []) == {}

    valid_point = CatDeliveryPoint(distretto_code="D01", punto_consegna_code="VALID", source_x=8.61, source_y=39.91, is_active=True)
    invalid_point = CatDeliveryPoint(distretto_code="D01", punto_consegna_code="INVALID", source_x=999, source_y=999, is_active=True)
    assert mobile_sync_routes._delivery_point_coordinates(TestingSessionLocal(), [valid_point, invalid_point]) == {
        valid_point.id: (39.91, 8.61)
    }


def test_mobile_sync_helper_branches_for_postgres_coordinate_queries() -> None:
    point = CatDeliveryPoint(distretto_code="D01", punto_consegna_code="PG-POINT", is_active=True)
    meter = CatMeterReading(id=uuid4(), anno=2026, punto_consegna="PG-POINT", record_kind="meter_reading", source="excel", subject_id=10)

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class FakeDB:
        bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def __init__(self, rows):
            self._rows = rows

        def execute(self, _query):
            return FakeResult(self._rows)

    delivery_rows = [
        SimpleNamespace(id=point.id, lat=39.9, lng=8.6),
        SimpleNamespace(id=uuid4(), lat=None, lng=8.6),
    ]
    assert mobile_sync_routes._delivery_point_coordinates(FakeDB(delivery_rows), [point]) == {point.id: (39.9, 8.6)}

    meter_rows = [
        SimpleNamespace(meter_id=meter.id, lat=39.5, lng=8.5),
        SimpleNamespace(meter_id=meter.id, lat=39.6, lng=8.6),
        SimpleNamespace(meter_id=uuid4(), lat=None, lng=8.6),
    ]
    assert mobile_sync_routes._meter_parcel_coordinates(FakeDB(meter_rows), [meter]) == {meter.id: (39.5, 8.5)}
    assert mobile_sync_routes._meter_parcel_coordinates(TestingSessionLocal(), [meter]) == {}


def test_mobile_sync_helper_branches_for_meter_payload_variants() -> None:
    meter = CatMeterReading(
        id=uuid4(),
        anno=2026,
        punto_consegna="PDR-01",
        matricola="M-01",
        record_type="CONT_NO_TES",
        record_kind="meter_reading",
        operational_state="active",
        gps_lat=None,
        gps_lng=None,
        intervento_da_eseguire="none",
        source="excel",
    )
    payload = mobile_sync_routes._meter_catalog_payload(meter, (39.4, 8.4))
    assert payload["position_source"] == "parcel"
    meter.gps_lat = 39.7
    meter.gps_lng = 8.7
    payload = mobile_sync_routes._meter_catalog_payload(meter, None)
    assert payload["position_source"] == "meter_gps"


def test_mobile_sync_resolve_mobile_operator_error_branches() -> None:
    db = TestingSessionLocal()
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_mobile_operator(db, uuid4())
    _mobile_error_context(exc, 404, "operator_id")

    operator, _ = _seed_mobile_operator(db, linked_user=False, wc_id=102)
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_mobile_operator(db, operator.id)
    _mobile_error_context(exc, 422, "operator_id")

    operator, user = _seed_mobile_operator(db, username="missing-user", wc_id=103)
    assert user is not None
    operator.gaia_user_id = user.id + 999
    db.flush()
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_mobile_operator(db, operator.id)
    _mobile_error_context(exc, 422, "operator_id")

    disabled_operator, _ = _seed_mobile_operator(db, username="disabled", operator_enabled=False, wc_id=104)
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_mobile_operator(db, disabled_operator.id)
    _mobile_error_context(exc, 403, "operator_id")
    db.close()


def test_mobile_sync_event_resolution_conflict_branches() -> None:
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    event = MobileSyncEvent(
        client_event_id=uuid4(),
        event_type="FIELD_REPORT_CREATED",
        operator_id=operator.id,
        device_id="dev",
        payload_version=1,
        payload_hash="a" * 64,
        gaia_entity_type="field_report",
        gaia_entity_id=str(uuid4()),
    )
    db.add(event)
    db.commit()

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_mobile_event(
            db,
            client_event_id=event.client_event_id,
            event_type="ACTIVITY_START_REQUESTED",
            payload_hash=event.payload_hash,
        )
    _mobile_error_context(exc, 409, "client_event_id")

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_mobile_event(
            db,
            client_event_id=event.client_event_id,
            event_type="FIELD_REPORT_CREATED",
            payload_hash="b" * 64,
        )
    _mobile_error_context(exc, 409, "client_event_id")

    same_ref = MobileSyncEvent(
        client_event_id=uuid4(),
        event_type="TETI_FAULT_WORK_REQUESTED",
        operator_id=operator.id,
        device_id="dev",
        payload_version=1,
        payload_hash="c" * 64,
        external_reference="TETI-1",
        gaia_entity_type="gaia_work",
        gaia_entity_id=str(uuid4()),
    )
    db.add(same_ref)
    db.commit()
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_mobile_event_by_external_reference(
            db,
            event_type="TETI_FAULT_WORK_REQUESTED",
            external_reference="TETI-1",
            payload_hash="d" * 64,
        )
    _mobile_error_context(exc, 409, "teti_fault_id")
    db.close()


def test_mobile_sync_category_and_severity_resolution_branches() -> None:
    db = TestingSessionLocal()
    inactive_category = _seed_category(db, code="INACTIVE", wc_id=None, active=False)
    active_category = _seed_category(db, code="ACTIVE", wc_id=7, active=True)
    inactive_severity = _seed_severity(db, code="OLD", rank_order=5, active=False)
    _ = inactive_severity
    fallback_severity = _seed_severity(db, code="FALLBACK", rank_order=1, active=True)
    db.commit()

    assert mobile_sync_routes._resolve_report_category(db, "7").id == active_category.id
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_report_category(db, "not-a-uuid")
    _mobile_error_context(exc, 422, "category_id")
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_report_category(db, str(inactive_category.id))
    _mobile_error_context(exc, 422, "category_id")

    assert mobile_sync_routes._resolve_report_severity(db, "not-a-uuid").id == fallback_severity.id
    db.query(FieldReportSeverity).delete()
    db.commit()
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_report_severity(db, None)
    _mobile_error_context(exc, 422, "severity_id")
    db.close()


def test_mobile_sync_teti_category_and_severity_resolution_branches() -> None:
    db = TestingSessionLocal()
    _seed_category(db, code="LOSS", wc_id=None, active=True)
    for idx, code in enumerate(["LOWISH", "MID", "HIGHISH", "MAX"], start=1):
        _seed_severity(db, code=code, rank_order=idx, active=True)
    db.commit()

    assert mobile_sync_routes._resolve_teti_category(db).code == "LOSS"
    assert mobile_sync_routes._resolve_teti_severity(db, "LOW").code == "LOWISH"
    assert mobile_sync_routes._resolve_teti_severity(db, "MEDIUM").code == "MID"
    assert mobile_sync_routes._resolve_teti_severity(db, "HIGH").code == "HIGHISH"
    assert mobile_sync_routes._resolve_teti_severity(db, "CRITICAL").code == "MAX"

    db.query(FieldReportCategory).delete()
    db.query(FieldReportSeverity).delete()
    db.commit()
    fallback_category = _seed_category(db, code="OTHER", wc_id=None, active=True)
    db.commit()
    assert mobile_sync_routes._resolve_teti_category(db).id == fallback_category.id
    db.query(FieldReportCategory).delete()
    db.commit()
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_teti_category(db)
    _mobile_error_context(exc, 422, "payload")
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_teti_severity(db, "LOW")
    _mobile_error_context(exc, 422, "payload.severity")
    db.close()


def test_mobile_sync_attachment_helper_error_branches(tmp_path: Path) -> None:
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    attachment = _seed_attachment(db, operator_id=operator.id, client_attachment_id=uuid4(), checksum="abc123")
    db.commit()

    refs = [
        mobile_sync_routes.MobileSyncAttachmentRef(filename="x.jpg", mime_type="image/jpeg"),
        mobile_sync_routes.MobileSyncAttachmentRef(
            client_attachment_id=UUID(attachment.metadata_json["client_attachment_id"]),
            filename="x.jpg",
            mime_type="image/jpeg",
            sha256="different",
        ),
    ]
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._fetch_mobile_uploaded_attachments(db, operator_id=operator.id, attachments=refs)
    _mobile_error_context(exc, 409, "attachments")

    missing_ref = [
        mobile_sync_routes.MobileSyncAttachmentRef(
            client_attachment_id=uuid4(),
            filename="missing.jpg",
            mime_type="image/jpeg",
        )
    ]
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._fetch_mobile_uploaded_attachments(db, operator_id=operator.id, attachments=missing_ref)
    _mobile_error_context(exc, 422, "attachments")

    inline_ref = mobile_sync_routes.MobileSyncAttachmentRef(filename="inline.jpg", mime_type="image/jpeg")
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._decode_mobile_attachment_content(inline_ref)
    _mobile_error_context(exc, 422, "attachments")

    invalid_b64 = mobile_sync_routes.MobileSyncAttachmentRef(
        filename="inline.jpg",
        mime_type="image/jpeg",
        content_base64="not-base64",
    )
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._decode_mobile_attachment_content(invalid_b64)
    _mobile_error_context(exc, 422, "attachments")

    size_mismatch = mobile_sync_routes.MobileSyncAttachmentRef(
        filename="inline.jpg",
        mime_type="image/jpeg",
        content_base64=base64.b64encode(b"abc").decode("ascii"),
        size_bytes=10,
    )
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._decode_mobile_attachment_content(size_mismatch)
    _mobile_error_context(exc, 409, "attachments")

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._create_inline_mobile_attachment(
            db,
            operator_id=operator.id,
            device_id="dev",
            attachment=mobile_sync_routes.MobileSyncAttachmentRef(filename="x.jpg", mime_type="image/jpeg", content_base64=base64.b64encode(b"abc").decode("ascii")),
        )
    _mobile_error_context(exc, 422, "attachments")

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._create_inline_mobile_attachment(
            db,
            operator_id=operator.id,
            device_id="dev",
            attachment=mobile_sync_routes.MobileSyncAttachmentRef(
                client_attachment_id=uuid4(),
                filename="x.jpg",
                mime_type="image/jpeg",
                content_base64=base64.b64encode(b"abc").decode("ascii"),
                sha256="wrong",
            ),
        )
    _mobile_error_context(exc, 409, "attachments")

    duplicate_inline = _seed_attachment(db, operator_id=operator.id, client_attachment_id=uuid4(), checksum="persisted")
    db.commit()
    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._create_inline_mobile_attachment(
            db,
            operator_id=operator.id,
            device_id="dev",
            attachment=mobile_sync_routes.MobileSyncAttachmentRef(
                client_attachment_id=UUID(duplicate_inline.metadata_json["client_attachment_id"]),
                filename="x.jpg",
                mime_type="image/jpeg",
                content_base64=base64.b64encode(b"abc").decode("ascii"),
                sha256="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            ),
        )
    _mobile_error_context(exc, 409, "attachments")

    same_checksum_inline = _seed_attachment(
        db,
        operator_id=operator.id,
        client_attachment_id=uuid4(),
        checksum="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    )
    db.commit()
    reused = mobile_sync_routes._create_inline_mobile_attachment(
        db,
        operator_id=operator.id,
        device_id="dev",
        attachment=mobile_sync_routes.MobileSyncAttachmentRef(
            client_attachment_id=UUID(same_checksum_inline.metadata_json["client_attachment_id"]),
            filename="x.jpg",
            mime_type="image/jpeg",
            content_base64=base64.b64encode(b"abc").decode("ascii"),
            sha256="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        ),
    )
    assert reused.id == same_checksum_inline.id

    with pytest.raises(mobile_sync_routes.MobileSyncAPIError) as exc:
        mobile_sync_routes._resolve_mobile_attachments(
            db,
            operator_id=operator.id,
            device_id="dev",
            attachments=[mobile_sync_routes.MobileSyncAttachmentRef(filename="x.jpg", mime_type="image/jpeg")],
        )
    _mobile_error_context(exc, 422, "attachments")

    uploaded_ref = mobile_sync_routes.MobileSyncAttachmentRef(
        client_attachment_id=UUID(attachment.metadata_json["client_attachment_id"]),
        filename="x.jpg",
        mime_type="image/jpeg",
    )
    resolved = mobile_sync_routes._resolve_mobile_attachments(
        db,
        operator_id=operator.id,
        device_id="dev",
        attachments=[uploaded_ref],
    )
    assert resolved[0].id == attachment.id
    db.close()


def test_mobile_sync_upload_attachment_error_branches(monkeypatch, tmp_path: Path) -> None:
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    db.commit()
    db.close()
    monkeypatch.setattr(
        mobile_sync_routes,
        "build_storage_path",
        lambda filename: tmp_path / filename,
    )

    bad_checksum = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=_connector_headers(),
        data={
            "operator_id": operator_id,
            "device_id": "dev-1",
            "client_attachment_id": str(uuid4()),
            "checksum_sha256": "wrong",
        },
        files={"file": ("a.jpg", b"abc", "image/jpeg")},
    )
    assert bad_checksum.status_code == 409

    duplicate_id = uuid4()
    first = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=_connector_headers(),
        data={
            "operator_id": operator_id,
            "device_id": "dev-1",
            "client_attachment_id": str(duplicate_id),
        },
        files={"file": ("a.jpg", b"abc", "image/jpeg")},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=_connector_headers(),
        data={
            "operator_id": operator_id,
            "device_id": "dev-1",
            "client_attachment_id": str(duplicate_id),
        },
        files={"file": ("a.jpg", b"xyz", "image/jpeg")},
    )
    assert second.status_code == 409
    same_content = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=_connector_headers(),
        data={
            "operator_id": operator_id,
            "device_id": "dev-1",
            "client_attachment_id": str(duplicate_id),
        },
        files={"file": ("a.jpg", b"abc", "image/jpeg")},
    )
    assert same_content.status_code == 201
    assert same_content.json()["attachment_id"] == first.json()["attachment_id"]

    monkeypatch.setattr(mobile_sync_routes, "build_storage_path", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad file")))
    value_error = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=_connector_headers(),
        data={
            "operator_id": operator_id,
            "device_id": "dev-1",
            "client_attachment_id": str(uuid4()),
        },
        files={"file": ("b.jpg", b"abc", "image/jpeg")},
    )
    assert value_error.status_code == 422

    monkeypatch.setattr(mobile_sync_routes, "build_storage_path", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    retryable = client.post(
        "/api/mobile-sync/attachments/upload",
        headers=_connector_headers(),
        data={
            "operator_id": operator_id,
            "device_id": "dev-1",
            "client_attachment_id": str(uuid4()),
        },
        files={"file": ("c.jpg", b"abc", "image/jpeg")},
    )
    assert retryable.status_code == 500
    assert retryable.json()["retryable"] is True


def test_mobile_sync_worksets_empty_and_assignment_branches() -> None:
    db = TestingSessionLocal()
    assert mobile_sync_routes.get_mobile_worksets(db, operator_id=None).worksets == []

    operator_without_user, _ = _seed_mobile_operator(db, linked_user=False, username="no-user", wc_id=102)
    active_operator, user = _seed_mobile_operator(db, username="with-user", wc_id=103)
    assert user is not None
    team = Team(code="TEAM-X", name="Team X", is_active=True)
    active_vehicle = Vehicle(code="VH-1", name="Vehicle 1", vehicle_type="pickup", current_status="busy", is_active=True)
    global_vehicle = Vehicle(code="VH-2", name="Vehicle 2", vehicle_type="pickup", current_status="available", is_active=True)
    inactive_vehicle = Vehicle(code="VH-3", name="Vehicle 3", vehicle_type="pickup", current_status="available", is_active=False)
    catalog = ActivityCatalog(code="ACT", name="Activity", category="rete", is_active=True)
    db.add_all([team, active_vehicle, global_vehicle, inactive_vehicle, catalog])
    db.flush()
    db.add(TeamMembership(team_id=team.id, user_id=user.id, valid_from=datetime.now(UTC) - timedelta(days=1), is_primary=True))
    db.add(VehicleAssignment(vehicle_id=active_vehicle.id, assignment_target_type="operator", operator_user_id=user.id, assigned_by_user_id=user.id, start_at=datetime.now(UTC) - timedelta(days=1)))
    db.add(VehicleAssignment(vehicle_id=inactive_vehicle.id, assignment_target_type="operator", operator_user_id=user.id, assigned_by_user_id=user.id, start_at=datetime.now(UTC) - timedelta(days=1)))
    db.add(
        OperatorActivity(
            activity_catalog_id=catalog.id,
            operator_user_id=user.id,
            team_id=team.id,
            vehicle_id=global_vehicle.id,
            status="draft",
            started_at=datetime.now(UTC),
        )
    )
    db.commit()

    response = mobile_sync_routes.get_mobile_worksets(db, operator_id=None)
    operator_worksets = [item for item in response.worksets if item.operator_id == active_operator.id]
    assert operator_worksets
    available = next(item for item in operator_worksets if item.workset_type == "available_vehicles")
    available_ids = {entry.payload["id"] for entry in available.items}
    assert str(active_vehicle.id) in available_ids
    assert str(global_vehicle.id) in available_ids
    assert str(inactive_vehicle.id) not in available_ids
    assert all(item.operator_id != operator_without_user.id for item in response.worksets)
    db.close()


def test_mobile_sync_worksets_skips_operator_without_gaia_user_in_loop() -> None:
    operator = WCOperator(id=uuid4(), wc_id=999, username="orphan", email="orphan@example.local", enabled=True, gaia_user_id=None)

    class FakeScalarResult:
        def __init__(self, values):
            self._values = values

        def all(self):
            return self._values

    class FakeDB:
        def __init__(self) -> None:
            self._calls = 0

        def scalars(self, _query):
            self._calls += 1
            if self._calls == 1:
                return FakeScalarResult([operator])
            return FakeScalarResult([])

    response = mobile_sync_routes.get_mobile_worksets(FakeDB(), operator_id=None)
    assert response.worksets == []


def test_mobile_sync_field_report_error_branches(monkeypatch) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    category = _seed_category(db)
    category_id = str(category.id)
    _seed_severity(db)
    db.commit()
    db.close()

    response = client.post(
        "/api/mobile-sync/field-reports",
        headers=headers,
        json={
            "client_event_id": str(uuid4()),
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "1" * 64,
            "payload": {
                "title": "Report",
                "category_id": category_id,
                "linked_gaia_activity_id": str(uuid4()),
            },
            "attachments": [],
        },
    )
    assert response.status_code == 422

    monkeypatch.setattr(mobile_sync_routes, "_resolve_report_category", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    retryable = client.post(
        "/api/mobile-sync/field-reports",
        headers=headers,
        json={
            "client_event_id": str(uuid4()),
            "operator_id": operator_id,
            "device_id": str(uuid4()),
            "payload_version": 1,
            "payload_hash": "2" * 64,
            "payload": {"title": "Report", "category_id": "3"},
            "attachments": [],
        },
    )
    assert retryable.status_code == 500


def test_mobile_sync_activity_start_error_branches(monkeypatch) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, _ = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    inactive_catalog = ActivityCatalog(code="OLD", name="Old", category="rete", is_active=False)
    active_catalog = ActivityCatalog(code="NEW", name="New", category="rete", is_active=True)
    inactive_vehicle = Vehicle(code="VH-X", name="Inactive", vehicle_type="pickup", current_status="available", is_active=False)
    db.add_all([inactive_catalog, active_catalog, inactive_vehicle])
    db.flush()
    inactive_catalog_id = str(inactive_catalog.id)
    active_catalog_id = str(active_catalog.id)
    inactive_vehicle_id = str(inactive_vehicle.id)
    db.commit()
    db.close()

    payload_base = {
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "3" * 64,
        "attachments": [],
    }
    invalid_catalog = client.post(
        "/api/mobile-sync/activity-starts",
        headers=headers,
        json=payload_base | {
            "client_event_id": str(uuid4()),
            "payload": {"activity_catalog_id": inactive_catalog_id, "started_at_device": "2026-01-01T10:00:00Z"},
        },
    )
    assert invalid_catalog.status_code == 422

    invalid_team = client.post(
        "/api/mobile-sync/activity-starts",
        headers=headers,
        json=payload_base | {
            "client_event_id": str(uuid4()),
            "payload": {
                "activity_catalog_id": active_catalog_id,
                "team_id": str(uuid4()),
                "started_at_device": "2026-01-01T10:00:00Z",
            },
        },
    )
    assert invalid_team.status_code == 422

    invalid_vehicle = client.post(
        "/api/mobile-sync/activity-starts",
        headers=headers,
        json=payload_base | {
            "client_event_id": str(uuid4()),
            "payload": {
                "activity_catalog_id": active_catalog_id,
                "vehicle_id": inactive_vehicle_id,
                "started_at_device": "2026-01-01T10:00:00Z",
            },
        },
    )
    assert invalid_vehicle.status_code == 422

    monkeypatch.setattr(mobile_sync_routes, "_resolve_mobile_attachments", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    retryable = client.post(
        "/api/mobile-sync/activity-starts",
        headers=headers,
        json=payload_base | {
            "client_event_id": str(uuid4()),
            "payload": {"activity_catalog_id": active_catalog_id, "started_at_device": "2026-01-01T10:00:00Z"},
        },
    )
    assert retryable.status_code == 500


def test_mobile_sync_activity_stop_error_branches(monkeypatch) -> None:
    headers = _connector_headers()
    db = TestingSessionLocal()
    operator, user = _seed_mobile_operator(db)
    operator_id = str(operator.id)
    other_operator, other_user = _seed_mobile_operator(db, username="other.operator", wc_id=102)
    assert user is not None and other_user is not None
    catalog = ActivityCatalog(code="ACT", name="Activity", category="rete", is_active=True)
    db.add(catalog)
    db.flush()
    wrong_owner = OperatorActivity(activity_catalog_id=catalog.id, operator_user_id=other_user.id, status="in_progress", started_at=datetime.now(UTC))
    closed_activity = OperatorActivity(activity_catalog_id=catalog.id, operator_user_id=user.id, status="submitted", started_at=datetime.now(UTC))
    db.add_all([wrong_owner, closed_activity])
    db.flush()
    bad_start_event = MobileSyncEvent(
        client_event_id=uuid4(),
        event_type="ACTIVITY_START_REQUESTED",
        operator_id=operator.id,
        device_id="dev",
        payload_version=1,
        payload_hash="a" * 64,
        gaia_entity_type="activity",
        gaia_entity_id="not-a-uuid",
    )
    db.add(bad_start_event)
    wrong_owner_id = str(wrong_owner.id)
    closed_activity_id = str(closed_activity.id)
    bad_start_event_id = str(bad_start_event.client_event_id)
    db.commit()
    db.close()

    base = {
        "operator_id": operator_id,
        "device_id": str(uuid4()),
        "payload_version": 1,
        "payload_hash": "4" * 64,
        "attachments": [],
    }
    not_found = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json=base | {"client_event_id": str(uuid4()), "payload": {"gaia_activity_id": str(uuid4()), "stopped_at_device": "2026-01-01T11:00:00Z"}},
    )
    assert not_found.status_code == 422

    unresolved_start = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json=base | {"client_event_id": str(uuid4()), "payload": {"client_started_event_id": bad_start_event_id, "stopped_at_device": "2026-01-01T11:00:00Z"}},
    )
    assert unresolved_start.status_code == 422

    wrong_operator = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json=base | {"client_event_id": str(uuid4()), "payload": {"gaia_activity_id": wrong_owner_id, "stopped_at_device": "2026-01-01T11:00:00Z"}},
    )
    assert wrong_operator.status_code == 422

    wrong_status = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json=base | {"client_event_id": str(uuid4()), "payload": {"gaia_activity_id": closed_activity_id, "stopped_at_device": "2026-01-01T11:00:00Z"}},
    )
    assert wrong_status.status_code == 409

    monkeypatch.setattr(mobile_sync_routes, "_resolve_mobile_operator", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    retryable = client.post(
        "/api/mobile-sync/activity-stops",
        headers=headers,
        json=base | {"client_event_id": str(uuid4()), "payload": {"gaia_activity_id": closed_activity_id, "stopped_at_device": "2026-01-01T11:00:00Z"}},
    )
    assert retryable.status_code == 500
