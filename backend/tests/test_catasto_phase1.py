from collections.abc import Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto_phase1 import CatAnomalia, CatDistretto
from app.modules.catasto.services.validation import (
    validate_codice_fiscale,
    validate_comune,
    validate_superficie,
)


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
            username="catasto-admin",
            email="catasto@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_catasto=True,
        )
    )
    db.add(CatDistretto(num_distretto="10", nome_distretto="Distretto 10"))
    db.add(
        CatAnomalia(
            tipo="VAL-02-cf_invalido",
            severita="error",
            status="aperta",
            descrizione="CF non valido",
        )
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "catasto-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_validation_helpers_cover_expected_values() -> None:
    assert validate_codice_fiscale("FNDGPP63E11B354D") == {
        "cf_normalizzato": "FNDGPP63E11B354D",
        "is_valid": True,
        "tipo": "PF",
        "error_code": None,
    }
    assert validate_codice_fiscale("Dnifse64c01l122y")["cf_normalizzato"] == "DNIFSE64C01L122Y"
    assert validate_codice_fiscale("00588230953")["tipo"] == "PG"
    assert validate_codice_fiscale(None)["tipo"] == "MANCANTE"
    assert validate_comune(165) == {"is_valid": True, "nome_ufficiale": "Arborea"}
    assert validate_superficie(16834, 16834)["ok"] is True
    assert validate_superficie(17100, 16834)["ok"] is False


def test_distretti_endpoint_returns_seeded_items() -> None:
    response = client.get("/catasto/distretti/", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["num_distretto"] == "10"


def test_anomalie_endpoint_filters_by_tipo() -> None:
    response = client.get("/catasto/anomalie/?tipo=VAL-02-cf_invalido", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["tipo"] == "VAL-02-cf_invalido"


def test_import_capacitas_requires_authentication() -> None:
    response = client.post(
        "/catasto/import/capacitas",
        files={"file": ("capacitas.xlsx", b"fake-content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 401
