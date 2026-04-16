from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
import uuid

from cryptography.fernet import Fernet
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.bonifica_oristanese import BonificaOristaneseCredential
from app.models.wc_sync_job import WCSyncJob
from app.modules.accessi.wc_org_charts import WCOrgChart, WCOrgChartEntry
from app.modules.elaborazioni.bonifica_oristanese.apps.org_charts.client import (
    BonificaOrgChartEntryRow,
    BonificaOrgChartRow,
    _extract_entries,
)
from app.modules.elaborazioni.bonifica_oristanese.apps.report_types.client import BonificaReportTypeRow
from app.modules.elaborazioni.bonifica_oristanese.apps.areas.client import BonificaAreaRow
from app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client import (
    BonificaRefuelRow,
    _extract_labeled_values,
)
from app.modules.elaborazioni.bonifica_oristanese.apps.reports.client import BonificaReportRow
from app.modules.elaborazioni.bonifica_oristanese.apps.taken_charge.client import BonificaTakenChargeRow
from app.modules.elaborazioni.bonifica_oristanese.apps.users.client import BonificaUserRow
from app.modules.elaborazioni.bonifica_oristanese.apps.vehicles.client import BonificaVehicleRow
from app.modules.elaborazioni.bonifica_oristanese.apps.warehouse_requests.client import (
    BonificaWarehouseRequestRow,
)
from app.modules.inventory.models import WarehouseRequest
from app.modules.elaborazioni.bonifica_oristanese.models import BonificaOristaneseCredentialTestResult
from app.modules.elaborazioni.bonifica_oristanese.parsers import clean_html_text
from app.modules.operazioni.models.reports import FieldReport, FieldReportCategory
from app.modules.operazioni.models.wc_area import WCArea
from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession, WCRefuelEvent
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.services.sync_vehicles import sync_white_vehicles
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject, BonificaUserStaging
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
    monkeypatch.setattr("app.services.elaborazioni_bonifica_sync.SessionLocal", TestingSessionLocal)
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
            module_inventario=True,
            module_operazioni=True,
            module_utenze=True,
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


def test_refuel_detail_label_fallback_extracts_liters_cost_and_station() -> None:
    html = """
    <form>
      <div class="form-group">
        <label for="litri">Litri erogati</label>
        <input id="litri" type="text" value="32,50">
      </div>
      <div class="form-group">
        <label for="totale">Totale euro</label>
        <input id="totale" type="text" value="58,40">
      </div>
      <table>
        <tr><th>Distributore</th><td>Q8 Oristano</td></tr>
      </table>
    </form>
    """

    labeled = _extract_labeled_values(html)

    assert labeled["litri erogati"] == "32,50"
    assert labeled["totale euro"] == "58,40"
    assert labeled["distributore"] == "Q8 Oristano"


def test_clean_html_text_accepts_numeric_values() -> None:
    assert clean_html_text(39624) == "39624"


def test_org_chart_entries_include_checked_checkbox_values() -> None:
    html = """
    <form>
      <label for="referent-1">Mario Rossi</label>
      <input id="referent-1" type="checkbox" name="referents[]" value="301" checked>
      <label>
        <input type="checkbox" name="areas[]" value="44" checked>
        Distretto A
      </label>
    </form>
    """

    entries = _extract_entries(html)

    assert len(entries) == 2
    assert entries[0].wc_id == 301
    assert entries[0].operator_wc_id == 301
    assert entries[0].label == "Mario Rossi"
    assert entries[1].wc_id == 44
    assert entries[1].area_wc_id == 44
    assert entries[1].label == "Distretto A"


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

    alias_list_response = client.get("/elaborazioni/bonifica/credentials", headers=auth_headers())
    assert alias_list_response.status_code == 200
    assert alias_list_response.json() == []


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


def test_bonifica_sync_status_lists_supported_entities() -> None:
    response = client.get("/elaborazioni/bonifica/sync/status", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["entities"]["reports"]["entity"] == "reports"
    assert payload["entities"]["reports"]["status"] == "never"
    assert payload["entities"]["report_types"]["status"] == "never"
    assert payload["entities"]["vehicles"]["status"] == "never"
    assert payload["entities"]["refuels"]["status"] == "never"
    assert payload["entities"]["taken_charge"]["status"] == "never"
    assert payload["entities"]["users"]["status"] == "never"
    assert payload["entities"]["areas"]["status"] == "never"
    assert payload["entities"]["warehouse_requests"]["status"] == "never"
    assert payload["entities"]["org_charts"]["status"] == "never"
    assert payload["entities"]["consorziati"]["status"] == "never"


def test_bonifica_sync_status_expires_stale_running_jobs() -> None:
    process_started_at = datetime.now(timezone.utc) - timedelta(hours=3)
    from app.services import elaborazioni_bonifica_sync as sync_module

    sync_module._BACKEND_PROCESS_STARTED_AT = process_started_at

    db = TestingSessionLocal()
    try:
        db.add(
            WCSyncJob(
                entity="vehicles",
                status="running",
                started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                params_json={"date_from": None, "date_to": None},
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/elaborazioni/bonifica/sync/status", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["entities"]["vehicles"]["status"] == "failed"
    assert payload["entities"]["vehicles"]["records_errors"] == 1
    assert "rimasto in stato running oltre la soglia" in payload["entities"]["vehicles"]["error_detail"]


def test_bonifica_sync_status_marks_orphaned_running_jobs_after_backend_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_started_at = datetime.now(timezone.utc)
    monkeypatch.setattr(
        "app.services.elaborazioni_bonifica_sync._BACKEND_PROCESS_STARTED_AT",
        process_started_at,
    )

    db = TestingSessionLocal()
    try:
        db.add(
            WCSyncJob(
                entity="users",
                status="running",
                started_at=process_started_at - timedelta(seconds=30),
                params_json={"date_from": None, "date_to": None},
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/elaborazioni/bonifica/sync/status", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["entities"]["users"]["status"] == "failed"
    assert payload["entities"]["users"]["records_errors"] == 1
    assert "backend riavviato" in payload["entities"]["users"]["error_detail"]


def test_bonifica_sync_status_uses_longer_stale_threshold_for_user_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.config.settings.wc_sync_stale_job_minutes", 30)
    monkeypatch.setattr("app.core.config.settings.wc_sync_user_stale_job_minutes", 120)
    monkeypatch.setattr(
        "app.services.elaborazioni_bonifica_sync._BACKEND_PROCESS_STARTED_AT",
        datetime.now(timezone.utc) - timedelta(hours=2),
    )

    db = TestingSessionLocal()
    try:
        db.add(
            WCSyncJob(
                entity="vehicles",
                status="running",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=45),
                params_json={"date_from": None, "date_to": None},
            )
        )
        db.add(
            WCSyncJob(
                entity="users",
                status="running",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=45),
                params_json={"date_from": None, "date_to": None},
            )
        )
        db.add(
            WCSyncJob(
                entity="consorziati",
                status="running",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=45),
                params_json={"date_from": None, "date_to": None},
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/elaborazioni/bonifica/sync/status", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["entities"]["vehicles"]["status"] == "failed"
    assert payload["entities"]["users"]["status"] == "running"
    assert payload["entities"]["consorziati"]["status"] == "running"


def test_bonifica_users_client_fetches_detail_pages_with_controlled_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.config.settings.wc_sync_user_detail_concurrency", 3)
    monkeypatch.setattr("app.core.config.settings.wc_sync_detail_delay_ms", 0)
    monkeypatch.setattr("app.core.config.settings.wc_sync_users_role_ids", "30,49")

    class DummySessionManager:
        def get_http_client(self):  # pragma: no cover - unused in this test
            raise AssertionError("HTTP client should not be used directly in this test")

    class InstrumentedUsersClient:
        def __init__(self) -> None:
            from app.modules.elaborazioni.bonifica_oristanese.apps.users.client import BonificaUsersClient

            self.client = BonificaUsersClient(DummySessionManager())  # type: ignore[arg-type]
            self.active_calls = 0
            self.max_active_calls = 0
            self.role_calls: list[str] = []

        async def fetch_all_datatable_rows(self, *args, **kwargs):
                filter_role = kwargs["extra_params"]["filter_role"]
                self.role_calls.append(filter_role)
                if filter_role == "30":
                    return (
                        [
                            ["", "Acquaiolo", "", "", '<a href="/users/101">Scheda</a>'],
                            ["", "Acquaiolo", "", "", '<a href="/users/102">Scheda</a>'],
                        ],
                        2,
                    )
                if filter_role == "49":
                    return (
                        [
                            ["", "Operatore bonifica", "", "", '<a href="/users/102">Scheda</a>'],
                            ["", "Operatore bonifica", "", "", '<a href="/users/103">Scheda</a>'],
                        ],
                        2,
                    )
                return (
                    [],
                    0,
                )

        async def fetch_detail_html(self, path: str) -> str:
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
            try:
                await asyncio.sleep(0.01)
                wc_id = path.rstrip("/").split("/")[-1]
                return f"""
                <form>
                  <input name="username" value="user-{wc_id}">
                  <input name="email" value="user-{wc_id}@example.local">
                  <input name="first_name" value="Nome {wc_id}">
                  <input name="last_name" value="Cognome {wc_id}">
                  <input name="tax" value="TAX{wc_id}">
                  <input name="contact_phone" value="070000{wc_id}">
                  <input name="enabled" value="1">
                </form>
                """
            finally:
                self.active_calls -= 1

    instrumented = InstrumentedUsersClient()
    monkeypatch.setattr(instrumented.client, "fetch_all_datatable_rows", instrumented.fetch_all_datatable_rows)
    monkeypatch.setattr(instrumented.client, "fetch_detail_html", instrumented.fetch_detail_html)

    rows, total = asyncio.run(instrumented.client.fetch_users())

    assert total == 3
    assert len(rows) == 3
    assert instrumented.role_calls == ["30", "49"]
    assert instrumented.max_active_calls == 3
    assert rows[0].wc_id == 101
    assert rows[2].username == "user-103"


def test_bonifica_users_client_fetch_consorziati_uses_configured_role_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.config.settings.wc_sync_user_detail_concurrency", 1)
    monkeypatch.setattr("app.core.config.settings.wc_sync_detail_delay_ms", 0)
    monkeypatch.setattr("app.core.config.settings.wc_sync_consorziati_role_id", "3")

    class DummySessionManager:
        def get_http_client(self):  # pragma: no cover - unused in this test
            raise AssertionError("HTTP client should not be used directly in this test")

    class InstrumentedUsersClient:
        def __init__(self) -> None:
            from app.modules.elaborazioni.bonifica_oristanese.apps.users.client import BonificaUsersClient

            self.client = BonificaUsersClient(DummySessionManager())  # type: ignore[arg-type]
            self.role_calls: list[str] = []

        async def fetch_all_datatable_rows(self, *args, **kwargs):
            filter_role = kwargs["extra_params"]["filter_role"]
            self.role_calls.append(filter_role)
            return (
                [["", "Consorziato", "", "", '<a href="/users/201">Scheda</a>']],
                1,
            )

        async def fetch_detail_html(self, path: str) -> str:
            wc_id = path.rstrip("/").split("/")[-1]
            return f"""
            <form>
              <input name="username" value="consorziato-{wc_id}">
              <input name="email" value="consorziato-{wc_id}@example.local">
              <input name="business_name" value="Consorziato {wc_id} srl">
              <input name="tax" value="01234567890">
              <input name="enabled" value="1">
              <input name="role" value="Consorziato">
            </form>
            """

    instrumented = InstrumentedUsersClient()
    monkeypatch.setattr(instrumented.client, "fetch_all_datatable_rows", instrumented.fetch_all_datatable_rows)
    monkeypatch.setattr(instrumented.client, "fetch_detail_html", instrumented.fetch_detail_html)

    rows, total = asyncio.run(instrumented.client.fetch_consorziati())

    assert instrumented.role_calls == ["3"]
    assert total == 1
    assert len(rows) == 1
    assert rows[0].wc_id == 201
    assert rows[0].role == "Consorziato"


def test_bonifica_sync_run_creates_jobs_and_imports_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_report_types(self):
        return ([BonificaReportTypeRow(wc_id=38, name="Rottura condotta/Piantone (A-C)", areas_csv="Distretto A")], 1)

    async def fake_fetch_reports(self, *, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
        return (
            [
                BonificaReportRow(
                    external_code="60067",
                    report_type_name="Rottura condotta/Piantone (A-C)",
                    urgent=False,
                    description="Apertura carico 1 vasca",
                    reporter_name="Stefano Biancu",
                    area_code="Distr_34_2 Distretto Terralba Lotto Sud",
                    created_at_text="08/04/2026 18:18",
                    latitude_text="39.748869",
                    longitude_text="8.679270",
                    archived=False,
                    status_text="Completato",
                    assigned_responsibles="Serafino Meloni, Franco Piras",
                )
            ],
            1,
        )

    async def fake_fetch_vehicles(self):
        return ([], 0)

    async def fake_fetch_refuels(self, *, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
        return ([], 0)

    async def fake_fetch_taken_charge(self, *, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
        return ([], 0)

    async def fake_fetch_users(self):
        return ([], 0)

    async def fake_fetch_areas(self):
        return ([], 0)

    async def fake_fetch_warehouse_requests(self, *, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
        return ([], 0)

    async def fake_fetch_org_charts(self):
        return ([], 0)

    async def fake_fetch_consorziati(self):
        return ([], 0)

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.report_types.client.BonificaReportTypesClient.fetch_report_types",
        fake_fetch_report_types,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.reports.client.BonificaReportsClient.fetch_reports",
        fake_fetch_reports,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.vehicles.client.BonificaVehiclesClient.fetch_vehicles",
        fake_fetch_vehicles,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client.BonificaRefuelsClient.fetch_refuels",
        fake_fetch_refuels,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.taken_charge.client.BonificaTakenChargeClient.fetch_taken_charge",
        fake_fetch_taken_charge,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.users.client.BonificaUsersClient.fetch_users",
        fake_fetch_users,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.areas.client.BonificaAreasClient.fetch_areas",
        fake_fetch_areas,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.warehouse_requests.client.BonificaWarehouseRequestsClient.fetch_warehouse_requests",
        fake_fetch_warehouse_requests,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.org_charts.client.BonificaOrgChartsClient.fetch_org_charts",
        fake_fetch_org_charts,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.users.client.BonificaUsersClient.fetch_consorziati",
        fake_fetch_consorziati,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": "all"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"]["report_types"]["status"] == "queued"
    assert payload["jobs"]["reports"]["status"] == "queued"
    assert payload["jobs"]["vehicles"]["status"] == "queued"
    assert payload["jobs"]["refuels"]["status"] == "queued"
    assert payload["jobs"]["taken_charge"]["status"] == "queued"
    assert payload["jobs"]["users"]["status"] == "queued"
    assert payload["jobs"]["areas"]["status"] == "queued"
    assert payload["jobs"]["warehouse_requests"]["status"] == "queued"
    assert payload["jobs"]["org_charts"]["status"] == "queued"
    assert payload["jobs"]["consorziati"]["status"] == "queued"

    db = TestingSessionLocal()
    try:
        jobs = db.query(WCSyncJob).all()
        assert len(jobs) == 10

        category = db.scalar(select(FieldReportCategory).where(FieldReportCategory.wc_id == 38))
        assert category is not None
        assert category.name == "Rottura condotta/Piantone (A-C)"

        report = db.scalar(select(FieldReport).where(FieldReport.external_code == "60067"))
        assert report is not None
        assert report.report_number == "REP-WHITE-60067"
        assert report.status == "resolved"
        assert report.source_system == "white"
    finally:
        db.close()

    status_response = client.get("/elaborazioni/bonifica/sync/status", headers=auth_headers())
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["entities"]["reports"]["status"] == "completed"
    assert status_payload["entities"]["reports"]["records_synced"] == 1
    assert status_payload["entities"]["reports"]["params_json"]["source_total"] == 1
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["entity"] == "reports"
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["outcome"] == "completed"
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["records_synced"] == 1
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["records_skipped"] == 0
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["records_errors"] == 0
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["source_total"] == 1
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["range_used"]["date_from"] is not None
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["range_used"]["date_to"] is not None
    assert status_payload["entities"]["reports"]["params_json"]["report_summary"]["duration_seconds"] >= 0
    assert status_payload["entities"]["report_types"]["records_synced"] == 1
    assert status_payload["entities"]["report_types"]["params_json"]["source_total"] == 1
    assert status_payload["entities"]["vehicles"]["records_synced"] == 0
    assert status_payload["entities"]["refuels"]["records_synced"] == 0
    assert status_payload["entities"]["taken_charge"]["records_synced"] == 0
    assert status_payload["entities"]["users"]["records_synced"] == 0
    assert status_payload["entities"]["areas"]["records_synced"] == 0
    assert status_payload["entities"]["warehouse_requests"]["records_synced"] == 0
    assert status_payload["entities"]["org_charts"]["records_synced"] == 0
    assert status_payload["entities"]["consorziati"]["records_synced"] == 0


def test_bonifica_sync_rerun_reuses_previous_date_window_for_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync reports",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    observed_windows: list[tuple[str, str]] = []

    async def fake_fetch_reports(self, *, date_from, date_to):
        observed_windows.append((date_from.isoformat(), date_to.isoformat()))
        return ([], 0)

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.reports.client.BonificaReportsClient.fetch_reports",
        fake_fetch_reports,
    )

    first_run = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={
            "entities": ["reports"],
            "date_from": "2025-01-01",
            "date_to": "2025-04-13",
        },
    )

    assert first_run.status_code == 200
    assert observed_windows == [("2025-01-01", "2025-04-13")]

    second_run = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["reports"]},
    )

    assert second_run.status_code == 200
    assert observed_windows == [
        ("2025-01-01", "2025-04-13"),
        ("2025-01-01", "2025-04-13"),
    ]

    db = TestingSessionLocal()
    try:
        jobs = db.scalars(select(WCSyncJob).where(WCSyncJob.entity == "reports").order_by(WCSyncJob.started_at.asc())).all()
        assert len(jobs) == 2
        assert jobs[0].params_json["date_from"] == "2025-01-01"
        assert jobs[0].params_json["date_to"] == "2025-04-13"
        assert jobs[1].params_json["date_from"] == "2025-01-01"
        assert jobs[1].params_json["date_to"] == "2025-04-13"
    finally:
        db.close()


def test_bonifica_sync_failed_job_persists_final_report_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync reports failed",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_reports(self, *, date_from, date_to):
        raise RuntimeError("White provider timeout on reports export")

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.reports.client.BonificaReportsClient.fetch_reports",
        fake_fetch_reports,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={
            "entities": ["reports"],
            "date_from": "2025-01-01",
            "date_to": "2025-04-13",
        },
    )

    assert response.status_code == 200

    status_response = client.get("/elaborazioni/bonifica/sync/status", headers=auth_headers())
    assert status_response.status_code == 200
    report_summary = status_response.json()["entities"]["reports"]["params_json"]["report_summary"]
    assert status_response.json()["entities"]["reports"]["status"] == "failed"
    assert report_summary["entity"] == "reports"
    assert report_summary["outcome"] == "failed"
    assert report_summary["records_synced"] == 0
    assert report_summary["records_errors"] == 1
    assert report_summary["range_used"]["date_from"] == "2025-01-01"
    assert report_summary["range_used"]["date_to"] == "2025-04-13"
    assert "White provider timeout on reports export" in report_summary["error_preview"][0]


def test_bonifica_sync_run_imports_org_charts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync organigrammi",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_org_charts(self):
        return (
            [
                BonificaOrgChartRow(
                    wc_id=9001,
                    chart_type="area",
                    name="Area Campidano",
                    entries=[
                        BonificaOrgChartEntryRow(
                            wc_id=301,
                            label="Mario Rossi",
                            role="referents",
                            operator_wc_id=301,
                            area_wc_id=None,
                            source_field="referents[]",
                            sort_order=0,
                        ),
                        BonificaOrgChartEntryRow(
                            wc_id=44,
                            label="Distretto A",
                            role="areas",
                            operator_wc_id=None,
                            area_wc_id=44,
                            source_field="areas[]",
                            sort_order=1,
                        ),
                    ],
                )
            ],
            1,
        )

    db = TestingSessionLocal()
    db.add(
        WCOperator(
            wc_id=301,
            username="mrossi",
            email="mario.rossi@example.local",
            first_name="Mario",
            last_name="Rossi",
            tax="RSSMRA80A01H501Z",
            role="Acquaiolo",
            enabled=True,
        )
    )
    db.add(
        WCArea(
            wc_id=44,
            name="Distretto A",
            color="#00AA00",
            is_district=True,
        )
    )
    db.commit()
    db.close()

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.org_charts.client.BonificaOrgChartsClient.fetch_org_charts",
        fake_fetch_org_charts,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["org_charts"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"]["org_charts"]["status"] == "queued"

    db = TestingSessionLocal()
    try:
        chart = db.scalar(
            select(WCOrgChart).where(
                WCOrgChart.chart_type == "area",
                WCOrgChart.wc_id == 9001,
            )
        )
        assert chart is not None
        assert chart.name == "Area Campidano"

        entries = db.scalars(
            select(WCOrgChartEntry)
            .where(WCOrgChartEntry.org_chart_id == chart.id)
            .order_by(WCOrgChartEntry.sort_order.asc())
        ).all()
        assert len(entries) == 2
        assert entries[0].label == "Mario Rossi"
        assert entries[0].wc_operator_id is not None
        assert entries[1].label == "Distretto A"
        assert entries[1].wc_area_id is not None
    finally:
        db.close()


def test_bonifica_sync_run_imports_consorziati_and_approve_creates_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync consorziati",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_consorziati(self):
        return (
            [
                BonificaUserRow(
                    wc_id=8801,
                    username="consorziato.azienda",
                    email="azienda@example.local",
                    user_type="company",
                    business_name="Azienda Agricola Demo",
                    first_name=None,
                    last_name=None,
                    tax="12345678901",
                    contact_phone="0783-123456",
                    contact_mobile="3331234567",
                    enabled=True,
                    role="Consorziato",
                )
            ],
            1,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.users.client.BonificaUsersClient.fetch_consorziati",
        fake_fetch_consorziati,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["consorziati"]},
    )
    assert response.status_code == 200
    assert response.json()["jobs"]["consorziati"]["status"] == "queued"

    list_response = client.get("/utenze/bonifica-staging", headers=auth_headers())
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["review_status"] == "new"

    staging_id = items[0]["id"]
    approve_response = client.post(
        f"/utenze/bonifica-staging/{staging_id}/approve",
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["review_status"] == "matched"
    assert approve_response.json()["matched_subject_id"] is not None

    db = TestingSessionLocal()
    try:
        staging = db.get(BonificaUserStaging, uuid.UUID(approve_response.json()["id"]))
        assert staging is not None
        assert staging.matched_subject_id is not None

        subject = db.get(AnagraficaSubject, staging.matched_subject_id)
        assert subject is not None
        assert subject.subject_type == "company"
        assert subject.source_system == "whitecompany"
        assert subject.source_external_id == "8801"
        assert subject.imported_at is not None

        company = db.get(AnagraficaCompany, subject.id)
        assert company is not None
        assert company.ragione_sociale == "Azienda Agricola Demo"
        assert company.partita_iva == "12345678901"
    finally:
        db.close()


def test_bonifica_sync_run_imports_consorziati_even_when_role_is_not_human_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync consorziati raw role",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_consorziati(self):
        return (
            [
                BonificaUserRow(
                    wc_id=8802,
                    username="consorziato.raw-role",
                    email="raw-role@example.local",
                    user_type="company",
                    business_name="Consorziato Raw Role Srl",
                    first_name=None,
                    last_name=None,
                    tax="98765432109",
                    contact_phone="0783-000000",
                    contact_mobile="3330000000",
                    enabled=True,
                    role="3",
                )
            ],
            1,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.users.client.BonificaUsersClient.fetch_consorziati",
        fake_fetch_consorziati,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["consorziati"]},
    )
    assert response.status_code == 200
    assert response.json()["jobs"]["consorziati"]["status"] == "queued"

    list_response = client.get("/utenze/bonifica-staging", headers=auth_headers())
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["wc_id"] == 8802
    assert items[0]["review_status"] == "new"

    status_response = client.get("/elaborazioni/bonifica/sync/status", headers=auth_headers())
    assert status_response.status_code == 200
    consorziati_status = status_response.json()["entities"]["consorziati"]
    assert consorziati_status["records_synced"] == 1
    assert consorziati_status["records_skipped"] == 0

    db = TestingSessionLocal()
    try:
        staging = db.scalar(select(BonificaUserStaging).where(BonificaUserStaging.wc_id == 8802))
        assert staging is not None
        assert staging.review_status == "new"
    finally:
        db.close()


def test_bonifica_staging_reject_is_preserved_on_resync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync consorziati reject",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_consorziati(self):
        return (
            [
                BonificaUserRow(
                    wc_id=8802,
                    username="consorziato.privato",
                    email="privato@example.local",
                    user_type="private",
                    business_name=None,
                    first_name="Luigi",
                    last_name="Verdi",
                    tax="VRDLGU80A01H501Z",
                    contact_phone=None,
                    contact_mobile="3337654321",
                    enabled=True,
                    role="Consorziato",
                )
            ],
            1,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.users.client.BonificaUsersClient.fetch_consorziati",
        fake_fetch_consorziati,
    )

    first_sync = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["consorziati"]},
    )
    assert first_sync.status_code == 200

    list_response = client.get("/utenze/bonifica-staging", headers=auth_headers())
    staging_id = list_response.json()["items"][0]["id"]

    reject_response = client.post(
        f"/utenze/bonifica-staging/{staging_id}/reject",
        headers=auth_headers(),
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["review_status"] == "rejected"

    second_sync = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["consorziati"]},
    )
    assert second_sync.status_code == 200

    detail_response = client.get(
        f"/utenze/bonifica-staging/{staging_id}",
        headers=auth_headers(),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["review_status"] == "rejected"
    assert detail_response.json()["email"] == "privato@example.local"


def test_bonifica_sync_run_imports_vehicles_and_taken_charge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync mezzi",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_vehicles(self):
        return (
            [
                BonificaVehicleRow(
                    wc_id=101,
                    vehicle_code="ZA123AA",
                    vehicle_name="Daily 35C",
                    vehicle_type_label="automezzo",
                    km_start=12000,
                    km_limit=200000,
                    override_km_global=False,
                    override_ask_km_overflow=False,
                )
            ],
            1,
        )

    async def fake_fetch_taken_charge(self, *, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
        return (
            [
                BonificaTakenChargeRow(
                    wc_id=501,
                    vehicle_code="ZA123AA",
                    operator_name="Mario Rossi",
                    started_at_text="09/04/2026 07:30",
                    km_start=12100,
                    ended_at_text="09/04/2026 12:45",
                    km_end=12186,
                )
            ],
            1,
        )

    async def fake_fetch_refuels_for_vehicle_codes(self, *, vehicle_codes, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
        assert vehicle_codes is not None
        return (
            [
                BonificaRefuelRow(
                    wc_id=701,
                    vehicle_code="ZA123AA",
                    operator_name="Mario Rossi",
                    fueled_at_text="09/04/2026 10:15",
                    odometer_km=12150,
                    liters=None,
                    total_cost=None,
                    station_name=None,
                ),
                BonificaRefuelRow(
                    wc_id=702,
                    vehicle_code="ZA123AA",
                    operator_name="Mario Rossi",
                    fueled_at_text="09/04/2026 13:00",
                    odometer_km=12190,
                    liters=__import__("decimal").Decimal("32.500"),
                    total_cost=__import__("decimal").Decimal("58.40"),
                    station_name="Q8 Oristano",
                ),
            ],
            2,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.vehicles.client.BonificaVehiclesClient.fetch_vehicles",
        fake_fetch_vehicles,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client.BonificaRefuelsClient.fetch_refuels_for_vehicle_codes",
        fake_fetch_refuels_for_vehicle_codes,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.taken_charge.client.BonificaTakenChargeClient.fetch_taken_charge",
        fake_fetch_taken_charge,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["vehicles", "refuels", "taken_charge"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"]["vehicles"]["status"] == "queued"
    assert payload["jobs"]["refuels"]["status"] == "queued"
    assert payload["jobs"]["taken_charge"]["status"] == "queued"

    db = TestingSessionLocal()
    try:
        vehicle = db.scalar(select(Vehicle).where(Vehicle.wc_id == 101))
        assert vehicle is not None
        assert vehicle.code == "WC-101"
        assert vehicle.wc_vehicle_id == "ZA123AA"
        assert vehicle.name == "Daily 35C"

        usage_session = db.scalar(select(VehicleUsageSession).where(VehicleUsageSession.wc_id == 501))
        assert usage_session is not None
        assert usage_session.vehicle_id == vehicle.id
        assert usage_session.operator_name == "Mario Rossi"
        assert usage_session.km_start == 12100
        assert usage_session.km_end == 12186
        assert usage_session.status == "closed"

        fuel_log = db.scalar(select(VehicleFuelLog).where(VehicleFuelLog.wc_id == 702))
        assert fuel_log is not None
        assert fuel_log.vehicle_id == vehicle.id
        assert str(fuel_log.liters) == "32.500"
        assert fuel_log.station_name == "Q8 Oristano"

        skipped_fuel_log = db.scalar(select(VehicleFuelLog).where(VehicleFuelLog.wc_id == 701))
        assert skipped_fuel_log is None
        wc_refuel_event = db.scalar(select(WCRefuelEvent).where(WCRefuelEvent.wc_id == 701))
        assert wc_refuel_event is not None
        assert wc_refuel_event.vehicle_id == vehicle.id
        assert wc_refuel_event.operator_name == "Mario Rossi"
        assert wc_refuel_event.matched_fuel_log_id is None
    finally:
        db.close()


def test_bonifica_sync_run_requires_vehicle_base_for_vehicle_dependent_entities() -> None:
    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["refuels", "taken_charge"]},
    )

    assert response.status_code == 400
    assert "base mezzi locale" in response.json()["detail"]
    assert "Automezzi e attrezzature" in response.json()["detail"]


def test_sync_white_vehicles_matches_existing_vehicle_by_plate_number() -> None:
    db = TestingSessionLocal()
    try:
        current_user = db.scalar(select(ApplicationUser).where(ApplicationUser.username == "elaborazioni-admin"))
        assert current_user is not None

        existing_vehicle = Vehicle(
            code="LEGACY-VEHICLE-1",
            wc_id=None,
            plate_number="MOTOPOMPA_A1106054",
            wc_vehicle_id=None,
            name="Motopompa legacy",
            vehicle_type="attrezzatura",
            vehicle_type_wc="attrezzatura",
            current_status="available",
            is_active=True,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(existing_vehicle)
        db.commit()

        result = sync_white_vehicles(
            db=db,
            current_user=current_user,
            rows=[
                BonificaVehicleRow(
                    wc_id=207,
                    vehicle_code="MOTOPOMPA_A1106054",
                    vehicle_name="MOTOPOMPA MAGAZZINO",
                    vehicle_type_label="attrezzatura",
                    km_start=None,
                    km_limit=None,
                    override_km_global=False,
                    override_ask_km_overflow=False,
                )
            ],
        )

        refreshed_vehicle = db.scalar(select(Vehicle).where(Vehicle.id == existing_vehicle.id))
        assert refreshed_vehicle is not None
        assert result.vehicles_synced == 0
        assert result.vehicles_skipped == 1
        assert result.errors == []
        assert refreshed_vehicle.wc_id == 207
        assert refreshed_vehicle.wc_vehicle_id == "MOTOPOMPA_A1106054"
        assert refreshed_vehicle.plate_number == "MOTOPOMPA_A1106054"
        assert refreshed_vehicle.name == "MOTOPOMPA MAGAZZINO"
        assert db.query(Vehicle).count() == 1
    finally:
        db.close()


def test_bonifica_sync_refuels_skips_orphaned_white_detail_and_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync refuels",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_vehicles(self):
        return (
            [
                BonificaVehicleRow(
                    wc_id=101,
                    vehicle_code="ZA123AA",
                    vehicle_name="Daily 35C",
                    vehicle_type_label="automezzo",
                    km_start=12000,
                    km_limit=200000,
                    override_km_global=False,
                    override_ask_km_overflow=False,
                )
            ],
            1,
        )

    async def fake_fetch_refuels_for_vehicle_codes(self, *, vehicle_codes, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
        assert vehicle_codes is not None
        return (
            [
                BonificaRefuelRow(
                    wc_id=2472,
                    vehicle_code="MOTOPOMPA_A1106052",
                    operator_name="Mario Rossi",
                    fueled_at_text="09/04/2026 08:00",
                    odometer_km=0,
                    liters=None,
                    total_cost=None,
                    station_name=None,
                    source_issue="Dettaglio White non disponibile: il mezzo sorgente potrebbe essere stato cancellato.",
                ),
                BonificaRefuelRow(
                    wc_id=702,
                    vehicle_code="ZA123AA",
                    operator_name="Mario Rossi",
                    fueled_at_text="09/04/2026 13:00",
                    odometer_km=12190,
                    liters=__import__("decimal").Decimal("32.500"),
                    total_cost=__import__("decimal").Decimal("58.40"),
                    station_name="Q8 Oristano",
                ),
            ],
            2,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.vehicles.client.BonificaVehiclesClient.fetch_vehicles",
        fake_fetch_vehicles,
    )
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client.BonificaRefuelsClient.fetch_refuels_for_vehicle_codes",
        fake_fetch_refuels_for_vehicle_codes,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={
            "entities": ["vehicles", "refuels"],
            "date_from": "2025-01-01",
            "date_to": "2025-04-13",
        },
    )

    assert response.status_code == 200

    status_response = client.get("/elaborazioni/bonifica/sync/status", headers=auth_headers())
    assert status_response.status_code == 200
    refuels_status = status_response.json()["entities"]["refuels"]
    assert refuels_status["status"] == "completed"
    assert refuels_status["records_synced"] == 2
    assert refuels_status["records_skipped"] == 0
    assert refuels_status["records_errors"] == 0

    db = TestingSessionLocal()
    try:
        fuel_log = db.scalar(select(VehicleFuelLog).where(VehicleFuelLog.wc_id == 702))
        assert fuel_log is not None
        assert db.scalar(select(VehicleFuelLog).where(VehicleFuelLog.wc_id == 2472)) is None
        staged_event = db.scalar(select(WCRefuelEvent).where(WCRefuelEvent.wc_id == 2472))
        assert staged_event is not None
        assert staged_event.source_issue is not None
    finally:
        db.close()


def test_bonifica_sync_run_imports_operational_users_and_exposes_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync operatori",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_users(self):
        return (
            [
                BonificaUserRow(
                    wc_id=901,
                    username="mrossi",
                    email="elaborazioni@example.local",
                    user_type="private",
                    business_name=None,
                    first_name="Mario",
                    last_name="Rossi",
                    tax="RSSMRA80A01H501U",
                    contact_phone=None,
                    contact_mobile=None,
                    enabled=True,
                    role="Admin",
                ),
                BonificaUserRow(
                    wc_id=902,
                    username="consorziato.demo",
                    email="consorziato@example.local",
                    user_type="company",
                    business_name="Azienda Demo",
                    first_name=None,
                    last_name=None,
                    tax="12345678901",
                    contact_phone=None,
                    contact_mobile=None,
                    enabled=True,
                    role="Consorziato",
                ),
            ],
            2,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.users.client.BonificaUsersClient.fetch_users",
        fake_fetch_users,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["users"]},
    )
    assert response.status_code == 200
    assert response.json()["jobs"]["users"]["status"] == "queued"

    db = TestingSessionLocal()
    try:
        operator = db.scalar(select(WCOperator).where(WCOperator.wc_id == 901))
        assert operator is not None
        assert operator.email == "elaborazioni@example.local"
        assert operator.gaia_user_id == 1

        consorziato = db.scalar(select(WCOperator).where(WCOperator.wc_id == 902))
        assert consorziato is None

        admin_user = db.scalar(select(ApplicationUser).where(ApplicationUser.id == 1))
        assert admin_user is not None
        admin_user.module_operazioni = True
        db.commit()
    finally:
        db.close()

    list_response = client.get("/operazioni/operators", headers=auth_headers())
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1

    operator_id = payload["items"][0]["id"]
    detail_response = client.get(f"/operazioni/operators/{operator_id}", headers=auth_headers())
    assert detail_response.status_code == 200


def test_bonifica_sync_run_imports_company_operator_non_consorziato(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync operatori company",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_users(self):
        return (
            [
                BonificaUserRow(
                    wc_id=903,
                    username="azienda.operativa",
                    email="azienda.operativa@example.local",
                    user_type="company",
                    business_name="WhiteCompany Service Srl",
                    first_name=None,
                    last_name=None,
                    tax="01234567890",
                    contact_phone=None,
                    contact_mobile=None,
                    enabled=True,
                    role="Operatore",
                ),
            ],
            1,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.users.client.BonificaUsersClient.fetch_users",
        fake_fetch_users,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["users"]},
    )
    assert response.status_code == 200
    assert response.json()["jobs"]["users"]["status"] == "queued"

    db = TestingSessionLocal()
    try:
        operator = db.scalar(select(WCOperator).where(WCOperator.wc_id == 903))
        assert operator is not None
        assert operator.email == "azienda.operativa@example.local"
        assert operator.first_name is None
        assert operator.last_name is None
        assert operator.role == "Operatore"

        admin_user = db.scalar(select(ApplicationUser).where(ApplicationUser.id == 1))
        assert admin_user is not None
        admin_user.module_operazioni = True
        db.commit()
    finally:
        db.close()

    list_response = client.get("/operazioni/operators", headers=auth_headers())
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["wc_id"] == 903

    operator_id = payload["items"][0]["id"]
    detail_response = client.get(f"/operazioni/operators/{operator_id}", headers=auth_headers())
    assert detail_response.status_code == 200
    assert detail_response.json()["wc_id"] == 903


def test_bonifica_sync_run_imports_areas_and_exposes_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync aree",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_areas(self):
        return (
            [
                BonificaAreaRow(
                    wc_id=301,
                    name="Distretto Terralba Lotto Sud",
                    color="#00AA55",
                    is_district=True,
                    description="Area irrigua test",
                    lat=__import__("decimal").Decimal("39.7488690"),
                    lng=__import__("decimal").Decimal("8.6792700"),
                    polygon="POLYGON((0 0,1 1,1 0,0 0))",
                )
            ],
            1,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.areas.client.BonificaAreasClient.fetch_areas",
        fake_fetch_areas,
    )

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["areas"]},
    )
    assert response.status_code == 200
    assert response.json()["jobs"]["areas"]["status"] == "queued"

    db = TestingSessionLocal()
    try:
        area = db.scalar(select(WCArea).where(WCArea.wc_id == 301))
        assert area is not None
        assert area.name == "Distretto Terralba Lotto Sud"
        assert area.is_district is True

        admin_user = db.scalar(select(ApplicationUser).where(ApplicationUser.id == 1))
        assert admin_user is not None
        admin_user.module_operazioni = True
        db.commit()
    finally:
        db.close()

    list_response = client.get("/operazioni/areas", headers=auth_headers())
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1

    area_id = payload["items"][0]["id"]
    detail_response = client.get(f"/operazioni/areas/{area_id}", headers=auth_headers())
    assert detail_response.status_code == 200


def test_bonifica_sync_run_imports_warehouse_requests_and_exposes_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/elaborazioni/bonifica/credentials",
        headers=auth_headers(),
        json={
            "label": "Account sync magazzino",
            "login_identifier": "utente@example.local",
            "password": "bonifica-secret",
            "remember_me": True,
        },
    )
    assert create_response.status_code == 201

    async def fake_login(self):
        from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSession

        self._session = BonificaOristaneseSession(
            authenticated_url="https://login.bonificaoristanese.it/dashboard",
            cookie_names=["XSRF-TOKEN", "laravel_session"],
        )
        return self._session

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_warehouse_requests(self, *, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
        return (
            [
                BonificaWarehouseRequestRow(
                    wc_id=1101,
                    wc_report_id=60067,
                    report_type="Rottura condotta/Piantone (A-C)",
                    reported_by="Stefano Biancu",
                    requested_by="Mario Rossi",
                    report_date=__import__("datetime").datetime(2026, 4, 8, 18, 18),
                    request_date=__import__("datetime").datetime(2026, 4, 9, 9, 30),
                    archived=False,
                    status_active=True,
                )
            ],
            1,
        )

    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.bonifica_oristanese.session.BonificaOristaneseSessionManager.close", fake_close)
    monkeypatch.setattr(
        "app.modules.elaborazioni.bonifica_oristanese.apps.warehouse_requests.client.BonificaWarehouseRequestsClient.fetch_warehouse_requests",
        fake_fetch_warehouse_requests,
    )

    db = TestingSessionLocal()
    try:
        admin_user = db.scalar(select(ApplicationUser).where(ApplicationUser.id == 1))
        assert admin_user is not None
        admin_user.module_inventario = True
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": ["warehouse_requests"]},
    )
    assert response.status_code == 200
    assert response.json()["jobs"]["warehouse_requests"]["status"] == "queued"

    db = TestingSessionLocal()
    try:
        item = db.scalar(select(WarehouseRequest).where(WarehouseRequest.wc_id == 1101))
        assert item is not None
        assert item.wc_report_id == 60067
        assert item.report_type == "Rottura condotta/Piantone (A-C)"
    finally:
        db.close()

    list_response = client.get("/api/inventory/warehouse-requests", headers=auth_headers())
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1

    item_id = payload["items"][0]["id"]
    detail_response = client.get(f"/api/inventory/warehouse-requests/{item_id}", headers=auth_headers())
    assert detail_response.status_code == 200
