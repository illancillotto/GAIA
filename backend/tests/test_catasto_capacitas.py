from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.capacitas import CapacitasCredential
from app.modules.catasto.capacitas.models import CapacitasSearchResult
from app.services.catasto_credentials import get_credential_fernet


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    get_credential_fernet.cache_clear()

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="catasto-admin",
            email="catasto@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
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


def test_capacitas_decoder_decodes_real_payload() -> None:
    from app.modules.catasto.capacitas.decoder import decode_response

    payload = (
        "SZ7VLLbtswEPwV3nwJYfEhkepNlptCgGMbihMEKAqUIlcpAVsMaLmHFP2yHvpJ/YVyHdvpNUWP3YM0uzucXSzm14+fH8"
        "m3Zv6OTLiShQPGqAGlqOz6nppOldQJ6wxnrtCynFyRZv5QLavEz/qyE6UD6nTeU6nyjHagLe1sntnCaa7AJP7taMaA9ITXZ"
        "ox+FwaPBfoSK0qxEx9TSSQ09wnIBDbrBPCPwwiOXt/XKFSqhOvVDe6s8Uldr7BeZbrgRYmDrqN5Rj2OC9gvgG2MlM5g2/sQ"
        "sfS+VEiow+4wYH5Tte3drLnDLWAIOz+YZx+OrXWI9kCqLez3ZnAxIMWMZmn21o/meL0py6as1Ki4OITH8Nqrqw+Lpmqb4yzn"
        "LVz7vTXbo25bL26XmrdczUQuZ0iBOFab08XmYMEd/jhgHJNm8xVlyWvgmfwYtoGhZgxP0cNoPhM2lZfWwnfsdNFzzl/y5QZi"
        "hAEPP/l+RU5+kHkOwDOgQjhGpbZAu1L2NNdCFpmUJn3/pR829BwXP/CzH/hf+kHlgov/frj4gU/FW/1APv0G"
    )

    decoded = decode_response(payload)
    assert isinstance(decoded, list)
    rows = decoded
    assert len(rows) == 2
    assert any("PORCU" in str(row.get("Denominazione", "")).upper() for row in rows)


def test_capacitas_credentials_crud_encrypts_password() -> None:
    create_response = client.post(
        "/catasto/capacitas/credentials",
        headers=auth_headers(),
        json={
            "label": "Account principale",
            "username": "capacitas-user",
            "password": "capacitas-secret",
            "active": True,
            "allowed_hours_start": 0,
            "allowed_hours_end": 23,
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["label"] == "Account principale"
    assert "password" not in payload

    list_response = client.get("/catasto/capacitas/credentials", headers=auth_headers())
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    db = TestingSessionLocal()
    try:
        credential = db.query(CapacitasCredential).one()
        assert credential.username == "capacitas-user"
        assert credential.password_encrypted != "capacitas-secret"
    finally:
        db.close()

    update_response = client.patch(
        f"/catasto/capacitas/credentials/{payload['id']}",
        headers=auth_headers(),
        json={"active": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["active"] is False

    delete_response = client.delete(
        f"/catasto/capacitas/credentials/{payload['id']}",
        headers=auth_headers(),
    )
    assert delete_response.status_code == 204


def test_capacitas_involture_search_uses_selected_credential_and_returns_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/catasto/capacitas/credentials",
        headers=auth_headers(),
        json={
            "label": "Ricerca CF",
            "username": "capacitas-user",
            "password": "capacitas-secret",
        },
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        from app.modules.catasto.capacitas.session import CapacitasSession

        self._session = CapacitasSession(token="123e4567-e89b-12d3-a456-426614174000")
        return self._session

    async def fake_activate_app(self, app_name: str) -> None:
        return None

    async def fake_close(self) -> None:
        return None

    async def fake_search_anagrafica(self, q: str, tipo: int = 1, solo_con_beni: bool = False) -> CapacitasSearchResult:
        assert q == "PRCLSN82R27B354B"
        assert tipo == 2
        assert solo_con_beni is False
        return CapacitasSearchResult(
            total=2,
            rows=[
                {
                    "CCO": "0A0862690",
                    "Denominazione": "Porcu Alessandro",
                    "CodiceFiscale": "PRCLSN82R27B354B",
                    "Comune": "ORISTANO",
                },
                {
                    "CCO": "0A0875323",
                    "Denominazione": "Porcu Alessandro",
                    "CodiceFiscale": "PRCLSN82R27B354B",
                    "Comune": "ORISTANO",
                },
            ],
        )

    monkeypatch.setattr("app.modules.catasto.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.catasto.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.catasto.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.catasto.capacitas.client.InVoltureClient.search_anagrafica", fake_search_anagrafica)

    search_response = client.post(
        "/catasto/capacitas/involture/search",
        headers=auth_headers(),
        json={
            "q": "PRCLSN82R27B354B",
            "tipo_ricerca": 2,
            "credential_id": credential_id,
        },
    )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["total"] == 2
    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["Denominazione"] == "Porcu Alessandro"

    db = TestingSessionLocal()
    try:
        credential = db.get(CapacitasCredential, credential_id)
        assert credential is not None
        assert credential.last_error is None
        assert credential.last_used_at is not None
        assert credential.last_used_at.tzinfo is not None or credential.last_used_at == credential.last_used_at.replace(tzinfo=None)
    finally:
        db.close()
