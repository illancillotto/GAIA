from __future__ import annotations

from collections.abc import Generator

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
from app.models.bonifica_oristanese import BonificaOristaneseCredential
from app.modules.elaborazioni.bonifica_oristanese.models import BonificaOristaneseCredentialTestResult
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
            username="elaborazioni-admin",
            email="elaborazioni@example.local",
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
    response = client.post("/auth/login", json={"username": "elaborazioni-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_bonifica_oristanese_session_extracts_csrf_and_invalid_login_message() -> None:
    from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager

    manager = BonificaOristaneseSessionManager("user@example.local", "secret")
    html = """
    <html>
      <head><title>Accedi - Consorzio Bonifica Oristanese</title></head>
      <body>
        <form method="POST" action="https://login.bonificaoristanese.it/login">
          <input type="hidden" name="_token" value="csrf-token-123">
          <input type="text" name="email" value="">
          <input type="password" name="password">
        </form>
        <div class="bg-warning">Credenziali non valide</div>
      </body>
    </html>
    """

    assert manager._extract_csrf_token(html) == "csrf-token-123"
    assert manager._extract_failure_message(html) == "Credenziali non valide"
    assert manager._is_login_form_present(html) is True


def test_bonifica_oristanese_credentials_crud_encrypts_password() -> None:
    create_response = client.post(
        "/elaborazioni/bonifica-oristanese/credentials",
        headers=auth_headers(),
        json={
            "label": "Portale irrigazione",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
            "active": True,
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["label"] == "Portale irrigazione"
    assert payload["remember_me"] is True
    assert "password" not in payload

    list_response = client.get("/elaborazioni/bonifica-oristanese/credentials", headers=auth_headers())
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    db = TestingSessionLocal()
    try:
        credential = db.query(BonificaOristaneseCredential).one()
        assert credential.login_identifier == "utente@example.local"
        assert credential.password_encrypted != "bonifica-secret"
    finally:
        db.close()

    update_response = client.patch(
        f"/elaborazioni/bonifica-oristanese/credentials/{payload['id']}",
        headers=auth_headers(),
        json={"active": False, "remember_me": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["active"] is False
    assert update_response.json()["remember_me"] is False

    delete_response = client.delete(
        f"/elaborazioni/bonifica-oristanese/credentials/{payload['id']}",
        headers=auth_headers(),
    )
    assert delete_response.status_code == 204


def test_bonifica_oristanese_credential_test_updates_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica-oristanese/credentials",
        headers=auth_headers(),
        json={
            "label": "Account primario",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self) -> BonificaOristaneseCredentialTestResult:
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/home",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)

    response = client.post(
        f"/elaborazioni/bonifica-oristanese/credentials/{credential_id}/test",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["authenticated_url"] == "https://login.bonificaoristanese.it/home"
    assert "laravel_session" in payload["cookies"]

    db = TestingSessionLocal()
    try:
        credential = db.get(BonificaOristaneseCredential, credential_id)
        assert credential is not None
        assert credential.last_error is None
        assert credential.last_used_at is not None
        assert credential.last_authenticated_url == "https://login.bonificaoristanese.it/home"
    finally:
        db.close()


def test_bonifica_oristanese_credential_test_returns_diagnostics_on_login_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica-oristanese/credentials",
        headers=auth_headers(),
        json={
            "label": "Account errore",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
        },
    )
    credential_id = create_response.json()["id"]

    async def fake_login(self):
        raise RuntimeError(
            "Bonifica Oristanese login fallito: autenticazione non completata. "
            "URL finale=https://login.bonificaoristanese.it/login | "
            "title=Accedi - Consorzio Bonifica Oristanese | "
            "cookies=XSRF-TOKEN,laravel_session | "
            "esito=Credenziali non valide | "
            "snippet=Credenziali non valide",
        )

    async def fake_close(self) -> None:
        return None

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)

    response = client.post(
        f"/elaborazioni/bonifica-oristanese/credentials/{credential_id}/test",
        headers=auth_headers(),
    )

    assert response.status_code == 502
    payload = response.json()
    assert "URL finale=" in payload["detail"]
    assert "cookies=" in payload["detail"]
    assert "Credenziali non valide" in payload["detail"]
