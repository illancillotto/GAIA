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
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita
from app.modules.utenze.models import AnagraficaSubject


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


def test_list_avvisi_supports_unified_search_query() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="RUOLO_BONIFICA_2025.dmp",
        status="completed",
    )
    linked_subject = AnagraficaSubject(source_name_raw="Mario Rossi")
    db.add_all([job, linked_subject])
    db.flush()

    avviso_cf = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-001",
        anno_tributario=2025,
        codice_fiscale_raw="CNTMRC67P66A357L",
        nominativo_raw="CONTU MARIA CRISTINA",
        codice_utenza="U12345",
        importo_totale_euro=120.50,
    )
    avviso_comune = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-002",
        anno_tributario=2024,
        nominativo_raw="PINNA GIOVANNI",
        codice_utenza="UX9988",
        importo_totale_euro=89.10,
        subject_id=linked_subject.id,
    )
    db.add_all([avviso_cf, avviso_comune])
    db.flush()
    db.add(
        RuoloPartita(
            avviso_id=avviso_comune.id,
            codice_partita="P-001",
            comune_nome="Nurachi",
        )
    )
    db.commit()
    db.close()

    response = client.get("/ruolo/avvisi?q=Contu", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["codice_cnc"] == "CNC-001"

    response = client.get("/ruolo/avvisi?q=CNTMRC67P66A357L", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["codice_cnc"] == "CNC-001"

    response = client.get("/ruolo/avvisi?q=Nurachi", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["codice_cnc"] == "CNC-002"

    response = client.get("/ruolo/avvisi?q=2025", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["codice_cnc"] == "CNC-001"

    response = client.get("/ruolo/avvisi?q=U12345&unlinked=true", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["codice_cnc"] == "CNC-001"
