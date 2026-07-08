from __future__ import annotations

import sys
import types
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.catasto.routes import delivery_points_admin as delivery_points_admin_routes
from app.modules.catasto.services import delivery_points_config as delivery_points_config_service


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


def _auth_headers(*, role: str = ApplicationUserRole.ADMIN.value) -> dict[str, str]:
    db = TestingSessionLocal()
    suffix = role.replace("_", "-")
    username = f"{suffix}-user"
    user = ApplicationUser(
        username=username,
        email=f"{suffix}@example.local",
        password_hash=hash_password("secret123"),
        role=role,
        is_active=True,
        module_catasto=True,
    )
    db.add(user)
    db.commit()
    db.close()

    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_delivery_points_import_config_returns_default_admin_view() -> None:
    response = client.get("/catasto/delivery-points/import-config", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "root_path": None,
        "expected_with_meter_dir": "Punti_Cons-Con_contatoti",
        "expected_without_meter_dir": "Punti_Cons-Con_Senza_contatoti",
        "updated_by": None,
        "updated_at": response.json()["updated_at"],
    }


def test_get_delivery_points_import_config_rejects_non_admin() -> None:
    response = client.get(
        "/catasto/delivery-points/import-config",
        headers=_auth_headers(role=ApplicationUserRole.VIEWER.value),
    )

    assert response.status_code == 403


def test_refresh_delivery_points_gis_cache_returns_tile_revision() -> None:
    response = client.post("/catasto/delivery-points/gis-cache/refresh", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["tile_revision"]
    assert payload["refreshed_at"]
    assert payload["affected_layers"] == ["cat_delivery_points_current", "cat_irrigation_canals_current"]
    assert payload["message"] == "Cache GIS aggiornata. Ricaricare la mappa se e gia aperta."


def test_refresh_delivery_points_gis_cache_rejects_non_admin() -> None:
    response = client.post(
        "/catasto/delivery-points/gis-cache/refresh",
        headers=_auth_headers(role=ApplicationUserRole.VIEWER.value),
    )

    assert response.status_code == 403


def test_patch_delivery_points_import_config_persists_normalized_path() -> None:
    response = client.patch(
        "/catasto/delivery-points/import-config",
        headers=_auth_headers(),
        json={"root_path": "./tmp/shapes"},
    )

    assert response.status_code == 200
    assert response.json()["root_path"] == str(Path("./tmp/shapes").expanduser())
    assert response.json()["updated_by"] == "admin-user"


def test_patch_delivery_points_import_config_preserves_smb_uri() -> None:
    root_path = (
        "smb://nas_cbo.local/settore catasto/"
        "DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA/PUNTI_CONSEGNA 2026_DEF/"
    )
    response = client.patch(
        "/catasto/delivery-points/import-config",
        headers=_auth_headers(),
        json={"root_path": root_path},
    )

    assert response.status_code == 200
    assert response.json()["root_path"] == root_path
    assert response.json()["updated_by"] == "admin-user"


def test_update_delivery_points_import_config_accepts_blank_path_as_none() -> None:
    db = TestingSessionLocal()
    try:
        config = delivery_points_config_service.update_delivery_points_import_config(
            db,
            root_path="   ",
            current_user=None,
        )
        assert config.root_path is None
        assert config.updated_by == "system"
    finally:
        db.close()


def test_run_delivery_points_import_from_config_rejects_missing_path() -> None:
    db = TestingSessionLocal()
    try:
        try:
            delivery_points_config_service.run_delivery_points_import_from_config(db)
        except ValueError as exc:
            assert str(exc) == "Cartella sorgente NAS non configurata."
        else:
            raise AssertionError("Expected missing delivery points config path error")
    finally:
        db.close()


def test_run_delivery_points_import_from_config_calls_import_service(monkeypatch) -> None:
    db = TestingSessionLocal()
    config = delivery_points_config_service.update_delivery_points_import_config(
        db,
        root_path="/tmp/punti-consegna",
        current_user=None,
    )
    assert config.root_path == "/tmp/punti-consegna"
    db.close()

    called: dict[str, str] = {}

    def fake_import(db, *, root_path, source_dataset="2026_DEF"):
        called["root_path"] = root_path
        called["source_dataset"] = source_dataset
        return {
            "points_processed": 12,
            "canals_processed": 3,
            "meter_readings_linked": 8,
            "meter_readings_unlinked": 2,
        }

    monkeypatch.setattr(delivery_points_config_service, "import_delivery_points_2026_def", fake_import)

    db = TestingSessionLocal()
    config, stats = delivery_points_config_service.run_delivery_points_import_from_config(db)
    db.close()

    assert config.root_path == "/tmp/punti-consegna"
    assert called == {"root_path": "/tmp/punti-consegna", "source_dataset": "2026_DEF"}
    assert stats["points_processed"] == 12


def test_create_delivery_points_import_job_rejects_running_job() -> None:
    db = TestingSessionLocal()
    try:
        delivery_points_config_service.update_delivery_points_import_config(
            db,
            root_path="/tmp/punti-consegna",
            current_user=None,
        )
        db.add(
            delivery_points_config_service.CatDeliveryPointsImportJob(
                status="running",
                root_path="/tmp/punti-consegna",
            )
        )
        db.commit()

        try:
            delivery_points_config_service.create_delivery_points_import_job(db, current_user=None)
        except ValueError as exc:
            assert str(exc) == "Import punti di consegna gia in corso."
        else:
            raise AssertionError("Expected running delivery points import job error")
    finally:
        db.close()


def test_run_delivery_points_import_job_ignores_missing_job(monkeypatch) -> None:
    monkeypatch.setattr(delivery_points_config_service, "SessionLocal", TestingSessionLocal)

    delivery_points_config_service.run_delivery_points_import_job(uuid4())


def test_run_delivery_points_import_job_marks_job_completed(monkeypatch) -> None:
    db = TestingSessionLocal()
    job = delivery_points_config_service.CatDeliveryPointsImportJob(
        status="pending",
        root_path="/tmp/punti-consegna",
    )
    db.add(job)
    db.commit()
    job_id = job.id
    db.close()

    def fake_import(db, *, root_path, source_dataset="2026_DEF"):
        assert root_path == "/tmp/punti-consegna"
        return {
            "points_processed": 12,
            "canals_processed": 3,
            "meter_readings_linked": 8,
            "meter_readings_unlinked": 2,
        }

    monkeypatch.setattr(delivery_points_config_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(delivery_points_config_service, "import_delivery_points_2026_def", fake_import)

    delivery_points_config_service.run_delivery_points_import_job(job_id)

    db = TestingSessionLocal()
    try:
        completed_job = delivery_points_config_service.get_delivery_points_import_job(db, job_id)
        assert completed_job is not None
        assert completed_job.status == "completed"
        assert completed_job.points_processed == 12
        assert completed_job.canals_processed == 3
        assert completed_job.meter_readings_linked == 8
        assert completed_job.meter_readings_unlinked == 2
        assert completed_job.started_at is not None
        assert completed_job.completed_at is not None
    finally:
        db.close()


def test_run_delivery_points_import_job_marks_job_failed(monkeypatch) -> None:
    db = TestingSessionLocal()
    job = delivery_points_config_service.CatDeliveryPointsImportJob(
        status="pending",
        root_path="/tmp/punti-consegna",
    )
    db.add(job)
    db.commit()
    job_id = job.id
    db.close()

    def fake_import(db, *, root_path, source_dataset="2026_DEF"):
        raise ValueError("NAS non raggiungibile")

    monkeypatch.setattr(delivery_points_config_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(delivery_points_config_service, "import_delivery_points_2026_def", fake_import)

    delivery_points_config_service.run_delivery_points_import_job(job_id)

    db = TestingSessionLocal()
    try:
        failed_job = delivery_points_config_service.get_delivery_points_import_job(db, job_id)
        assert failed_job is not None
        assert failed_job.status == "failed"
        assert failed_job.error_message == "NAS non raggiungibile"
        assert failed_job.completed_at is not None
    finally:
        db.close()


def test_run_delivery_points_import_job_tolerates_job_deleted_after_import(monkeypatch) -> None:
    db = TestingSessionLocal()
    job = delivery_points_config_service.CatDeliveryPointsImportJob(
        status="pending",
        root_path="/tmp/punti-consegna",
    )
    db.add(job)
    db.commit()
    job_id = job.id
    db.close()

    def fake_import(db, *, root_path, source_dataset="2026_DEF"):
        job_to_delete = db.get(delivery_points_config_service.CatDeliveryPointsImportJob, job_id)
        assert job_to_delete is not None
        db.delete(job_to_delete)
        db.commit()
        return {
            "points_processed": 0,
            "canals_processed": 0,
            "meter_readings_linked": 0,
            "meter_readings_unlinked": 0,
        }

    monkeypatch.setattr(delivery_points_config_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(delivery_points_config_service, "import_delivery_points_2026_def", fake_import)

    delivery_points_config_service.run_delivery_points_import_job(job_id)

    db = TestingSessionLocal()
    try:
        assert delivery_points_config_service.get_delivery_points_import_job(db, job_id) is None
    finally:
        db.close()


def test_submit_delivery_points_import_job_uses_dedicated_executor(monkeypatch) -> None:
    submitted: list[object] = []

    class FakeExecutor:
        def submit(self, func, job_id):
            submitted.extend([func, job_id])

    job_id = uuid4()
    monkeypatch.setattr(delivery_points_config_service, "_DELIVERY_POINTS_IMPORT_EXECUTOR", FakeExecutor())

    delivery_points_config_service.submit_delivery_points_import_job(job_id)

    assert submitted == [delivery_points_config_service.run_delivery_points_import_job, job_id]


def test_import_delivery_points_from_config_route_returns_stats(monkeypatch) -> None:
    db = TestingSessionLocal()
    delivery_points_config_service.update_delivery_points_import_config(
        db,
        root_path="/tmp/punti-consegna",
        current_user=None,
    )
    db.close()

    started_jobs: list[str] = []

    def fake_submit(job_id):
        started_jobs.append(str(job_id))

    monkeypatch.setattr(delivery_points_admin_routes, "submit_delivery_points_import_job", fake_submit)

    response = client.post("/catasto/delivery-points/import-from-config", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"]
    assert payload["status"] == "pending"
    assert payload["root_path"] == "/tmp/punti-consegna"
    assert payload["requested_by"] == "admin-user"
    assert payload["points_processed"] is None
    assert started_jobs == [payload["job_id"]]


def test_get_delivery_points_import_job_status_returns_completed_stats() -> None:
    db = TestingSessionLocal()
    job = delivery_points_config_service.CatDeliveryPointsImportJob(
        status="completed",
        root_path="/tmp/punti-consegna",
        requested_by="admin-user",
        points_processed=5,
        canals_processed=1,
        meter_readings_linked=4,
        meter_readings_unlinked=9,
    )
    db.add(job)
    db.commit()
    job_id = job.id
    db.close()

    response = client.get(f"/catasto/delivery-points/import-jobs/{job_id}", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["points_processed"] == 5
    assert response.json()["canals_processed"] == 1
    assert response.json()["meter_readings_linked"] == 4
    assert response.json()["meter_readings_unlinked"] == 9


def test_get_delivery_points_import_job_status_returns_404_for_missing_job() -> None:
    response = client.get(
        "/catasto/delivery-points/import-jobs/00000000-0000-0000-0000-000000000001",
        headers=_auth_headers(),
    )

    assert response.status_code == 404


def test_import_delivery_points_from_config_route_returns_400_on_invalid_config(monkeypatch) -> None:
    response = client.post("/catasto/delivery-points/import-from-config", headers=_auth_headers())

    assert response.status_code == 400
    assert response.json()["detail"] == "Cartella sorgente NAS non configurata."
