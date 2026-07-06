from __future__ import annotations

import sys
import types
from pathlib import Path

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


def test_import_delivery_points_from_config_route_returns_stats(monkeypatch) -> None:
    db = TestingSessionLocal()
    config = delivery_points_config_service.update_delivery_points_import_config(
        db,
        root_path="/tmp/punti-consegna",
        current_user=None,
    )
    db.close()

    def fake_run(db):
        return config, {
            "points_processed": 5,
            "canals_processed": 1,
            "meter_readings_linked": 4,
            "meter_readings_unlinked": 9,
        }

    monkeypatch.setattr(delivery_points_admin_routes, "run_delivery_points_import_from_config", fake_run)

    response = client.post("/catasto/delivery-points/import-from-config", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "root_path": "/tmp/punti-consegna",
        "points_processed": 5,
        "canals_processed": 1,
        "meter_readings_linked": 4,
        "meter_readings_unlinked": 9,
    }


def test_import_delivery_points_from_config_route_returns_400_on_invalid_config(monkeypatch) -> None:
    def fake_run(db):
        raise ValueError("Cartella sorgente NAS non configurata.")

    monkeypatch.setattr(delivery_points_admin_routes, "run_delivery_points_import_from_config", fake_run)

    response = client.post("/catasto/delivery-points/import-from-config", headers=_auth_headers())

    assert response.status_code == 400
    assert response.json()["detail"] == "Cartella sorgente NAS non configurata."
