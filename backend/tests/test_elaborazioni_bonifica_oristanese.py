from __future__ import annotations

from collections.abc import Generator

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
)
from app.modules.elaborazioni.bonifica_oristanese.apps.report_types.client import BonificaReportTypeRow
from app.modules.elaborazioni.bonifica_oristanese.apps.areas.client import BonificaAreaRow
from app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client import BonificaRefuelRow
from app.modules.elaborazioni.bonifica_oristanese.apps.reports.client import BonificaReportRow
from app.modules.elaborazioni.bonifica_oristanese.apps.taken_charge.client import BonificaTakenChargeRow
from app.modules.elaborazioni.bonifica_oristanese.apps.users.client import BonificaUserRow
from app.modules.elaborazioni.bonifica_oristanese.apps.vehicles.client import BonificaVehicleRow
from app.modules.elaborazioni.bonifica_oristanese.apps.warehouse_requests.client import (
    BonificaWarehouseRequestRow,
)
from app.modules.inventory.models import WarehouseRequest
from app.modules.elaborazioni.bonifica_oristanese.models import BonificaOristaneseCredentialTestResult
from app.modules.operazioni.models.reports import FieldReport, FieldReportCategory
from app.modules.operazioni.models.wc_area import WCArea
from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.models.wc_operator import WCOperator
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

    response = client.post(
        "/elaborazioni/bonifica/sync/run",
        headers=auth_headers(),
        json={"entities": "all"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"]["report_types"]["status"] == "completed"
    assert payload["jobs"]["reports"]["status"] == "completed"
    assert payload["jobs"]["vehicles"]["status"] == "completed"
    assert payload["jobs"]["refuels"]["status"] == "completed"
    assert payload["jobs"]["taken_charge"]["status"] == "completed"
    assert payload["jobs"]["users"]["status"] == "completed"
    assert payload["jobs"]["areas"]["status"] == "completed"
    assert payload["jobs"]["warehouse_requests"]["status"] == "completed"
    assert payload["jobs"]["org_charts"]["status"] == "completed"

    db = TestingSessionLocal()
    try:
        jobs = db.query(WCSyncJob).all()
        assert len(jobs) == 9

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
    assert status_payload["entities"]["report_types"]["records_synced"] == 1
    assert status_payload["entities"]["vehicles"]["records_synced"] == 0
    assert status_payload["entities"]["refuels"]["records_synced"] == 0
    assert status_payload["entities"]["taken_charge"]["records_synced"] == 0
    assert status_payload["entities"]["users"]["records_synced"] == 0
    assert status_payload["entities"]["areas"]["records_synced"] == 0
    assert status_payload["entities"]["warehouse_requests"]["records_synced"] == 0
    assert status_payload["entities"]["org_charts"]["records_synced"] == 0


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
    assert payload["jobs"]["org_charts"]["status"] == "completed"

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

    async def fake_fetch_refuels(self, *, date_from, date_to):
        assert date_from is not None
        assert date_to is not None
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
        "app.modules.elaborazioni.bonifica_oristanese.apps.refuels.client.BonificaRefuelsClient.fetch_refuels",
        fake_fetch_refuels,
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
    assert payload["jobs"]["vehicles"]["status"] == "completed"
    assert payload["jobs"]["refuels"]["status"] == "completed"
    assert payload["jobs"]["taken_charge"]["status"] == "completed"

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
    assert response.json()["jobs"]["users"]["status"] == "completed"

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
    assert response.json()["jobs"]["areas"]["status"] == "completed"

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
    assert response.json()["jobs"]["warehouse_requests"]["status"] == "completed"

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
