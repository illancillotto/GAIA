from collections.abc import Generator
import sys
from types import ModuleType, SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if "shapely.geometry" not in sys.modules:
    shapely_module = ModuleType("shapely")
    shapely_geometry_module = ModuleType("shapely.geometry")

    def _shape(_geometry: object) -> SimpleNamespace:
        return SimpleNamespace(bounds=(8.0, 39.0, 9.0, 40.0))

    shapely_geometry_module.shape = _shape
    shapely_module.geometry = shapely_geometry_module
    sys.modules["shapely"] = shapely_module
    sys.modules["shapely.geometry"] = shapely_geometry_module

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.ruolo.models import RuoloImportJob


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
client = TestClient(app)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="ruolo-admin",
            email="ruolo@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_ruolo=True,
        )
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "ruolo-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_import_job_endpoints_serialize_uuid_ids() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="RUOLO_BONIFICA_2025.dmp",
        status="completed",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    expected_job_id = str(job.id)
    db.close()

    list_response = client.get("/ruolo/import/jobs", headers=auth_headers())
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == expected_job_id
    assert UUID(list_payload["items"][0]["id"]) == job.id

    detail_response = client.get(f"/ruolo/import/jobs/{expected_job_id}", headers=auth_headers())
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == expected_job_id
    assert detail_payload["anno_tributario"] == 2025
    assert detail_payload["filename"] == "RUOLO_BONIFICA_2025.dmp"
