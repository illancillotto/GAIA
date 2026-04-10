from collections.abc import Generator
from datetime import datetime
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
    InternalCaseEvent,
)
from app.modules.operazioni.services.parsing import (
    parse_completion_time,
    parse_italian_datetime,
)


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


def _seed_operazioni_user() -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni-white",
        email="operazioni-white@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _auth_headers() -> dict[str, str]:
    _seed_operazioni_user()
    response = client.post(
        "/auth/login",
        json={"username": "operazioni-white", "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _build_white_workbook() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(
        [
            "Codice",
            "Titolo",
            "Incarico",
            "Note",
            "Segnalatore",
            "Area",
            "Data",
            "Pos. sel. lat",
            "Pos. sel. lng",
            "Pos. disp. lat",
            "Pos. disp. lng",
            "Incarichi",
            "Incarichi completati",
            "Esito pos.",
            "Esito neg.",
            "Archiviata",
            "Data di archiv.",
            "Stato",
            "Responsabili",
            "Data di complet.",
            "Tempo di complet.",
        ]
    )
    worksheet.append(
        [
            60067,
            "Rottura condotta/Piantone (A-C)",
            "No",
            "Apertura carico 1° vasca",
            "Stefano Biancu",
            "Distr_34_2° Distretto Terralba Lotto Sud",
            "08/04/2026 18:18",
            39.748869,
            8.679270,
            None,
            None,
            2,
            1,
            1,
            0,
            "No",
            None,
            "Completato",
            "Serafino Meloni, Franco Piras",
            "09/04/2026 07:04",
            "12 ore 46 minuti e 37 secondi",
        ]
    )
    worksheet.append(
        [
            60067,
            "Rottura condotta/Piantone (A-C) - Richiesta di intervento",
            "Si",
            None,
            "Stefano Biancu",
            "Distr_34_2° Distretto Terralba Lotto Sud",
            "08/04/2026 18:20",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "No",
            None,
            None,
            None,
            None,
            None,
        ]
    )
    worksheet.append(
        [
            60067,
            "Rottura condotta/Piantone (A-C) - Richiesta materiale Magazzino",
            "Si",
            "Tubo DN160",
            "Stefano Biancu",
            "Distr_34_2° Distretto Terralba Lotto Sud",
            "08/04/2026 19:00",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "No",
            None,
            None,
            None,
            None,
            None,
        ]
    )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _seed_dashboard_records() -> None:
    db = TestingSessionLocal()
    user = db.scalar(select(ApplicationUser).where(ApplicationUser.username == "operazioni-white"))
    severity = FieldReportSeverity(
        code="normal",
        name="Normale",
        rank_order=20,
        is_active=True,
    )
    category = FieldReportCategory(
        code="rottura_condotta_piantone_ac",
        name="Rottura condotta/Piantone (A-C)",
        is_active=True,
    )
    db.add_all([severity, category])
    db.flush()

    report_open = FieldReport(
        report_number="REP-WHITE-70001",
        external_code="70001",
        reporter_user_id=user.id,
        category_id=category.id,
        severity_id=severity.id,
        title="Rottura condotta/Piantone (A-C)",
        description="Perdita lato canale",
        reporter_name="Andrea Madeddu",
        area_code="Distr_24_Arborea lotto Sud",
        status="open",
        source_system="white",
        created_at=datetime.fromisoformat("2026-04-08T09:00:00"),
    )
    report_resolved = FieldReport(
        report_number="REP-WHITE-70002",
        external_code="70002",
        reporter_user_id=user.id,
        category_id=category.id,
        severity_id=severity.id,
        title="Rottura condotta/Piantone (A-C)",
        description="Riparazione completata",
        reporter_name="Pietro Spiga",
        area_code="Distr_25_Arborea lotto Nord",
        status="resolved",
        source_system="white",
        completion_time_text="2 ore 15 minuti",
        completion_time_minutes=135,
        created_at=datetime.fromisoformat("2026-04-09T10:00:00"),
    )
    db.add_all([report_open, report_resolved])
    db.flush()

    case_open = InternalCase(
        case_number="CAS-WHITE-70001",
        source_report_id=report_open.id,
        title=report_open.title,
        status="open",
        created_at=report_open.created_at,
    )
    case_resolved = InternalCase(
        case_number="CAS-WHITE-70002",
        source_report_id=report_resolved.id,
        title=report_resolved.title,
        status="resolved",
        resolved_at=datetime.fromisoformat("2026-04-09T12:15:00"),
        created_at=report_resolved.created_at,
    )
    db.add_all([case_open, case_resolved])
    db.flush()
    report_open.internal_case_id = case_open.id
    report_resolved.internal_case_id = case_resolved.id

    db.add_all(
        [
            InternalCaseEvent(
                internal_case_id=case_open.id,
                event_type="imported",
                event_at=report_open.created_at,
                actor_user_id=user.id,
            ),
            InternalCaseEvent(
                internal_case_id=case_open.id,
                event_type="richiesta_intervento",
                event_at=datetime.fromisoformat("2026-04-08T09:05:00"),
                note="Verifica perdita",
            ),
            InternalCaseEvent(
                internal_case_id=case_resolved.id,
                event_type="riparazione_eseguita",
                event_at=datetime.fromisoformat("2026-04-09T11:20:00"),
                note="Ripristino completato",
            ),
        ]
    )
    db.commit()
    db.close()


def setup_function() -> None:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_parse_completion_time() -> None:
    assert parse_completion_time("12 ore 46 minuti e 37 secondi") == 767
    assert parse_completion_time("37 secondi") == 1
    assert parse_completion_time("") is None


def test_parse_italian_datetime() -> None:
    parsed = parse_italian_datetime("08/04/2026 18:18")
    assert parsed == datetime(2026, 4, 8, 18, 18)
    assert parse_italian_datetime("2026-04-08T18:18:00") is None


def test_import_white_reports_endpoint_is_idempotent() -> None:
    headers = _auth_headers()
    workbook_bytes = _build_white_workbook()

    response = client.post(
        "/operazioni/reports/import-white",
        headers=headers,
        files={
            "file": (
                "white.xlsx",
                workbook_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] == 1
    assert payload["skipped"] == 0
    assert payload["total_events_created"] == 3
    assert payload["categories_created"] == ["rottura_condotta_piantone_ac"]

    db = TestingSessionLocal()
    report = db.scalar(select(FieldReport).where(FieldReport.external_code == "60067"))
    assert report is not None
    assert report.report_number == "REP-WHITE-60067"
    assert report.reporter_name == "Stefano Biancu"
    assert report.area_code == "Distr_34_2° Distretto Terralba Lotto Sud"
    assert report.status == "resolved"
    assert report.completion_time_minutes == 767
    assert report.source_system == "white"

    case = db.scalar(select(InternalCase).where(InternalCase.id == report.internal_case_id))
    assert case is not None
    assert case.case_number == "CAS-WHITE-60067"
    assert case.status == "resolved"

    events = db.scalars(
        select(InternalCaseEvent)
        .where(InternalCaseEvent.internal_case_id == case.id)
        .order_by(InternalCaseEvent.event_at)
    ).all()
    assert [event.event_type for event in events] == [
        "imported",
        "richiesta_intervento",
        "richiesta_materiale",
    ]
    db.close()

    repeat_response = client.post(
        "/operazioni/reports/import-white",
        headers=headers,
        files={
            "file": (
                "white.xlsx",
                workbook_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    repeat_payload = repeat_response.json()
    assert repeat_response.status_code == 200
    assert repeat_payload["imported"] == 0
    assert repeat_payload["skipped"] == 1
    assert repeat_payload["total_events_created"] == 0


def test_reports_dashboard_filters_and_aggregates() -> None:
    headers = _auth_headers()
    _seed_dashboard_records()

    response = client.get(
        "/operazioni/reports/dashboard",
        headers=headers,
        params={
            "status_filter": "open",
            "reporter_name": "Andrea",
            "search": "70001",
            "date_from": "2026-04-08",
            "date_to": "2026-04-08",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["external_code"] == "70001"
    assert payload["items"][0]["events_count"] == 1
    assert payload["items"][0]["events"][0]["event_type"] == "richiesta_intervento"
    assert payload["aggregates"]["by_status"]["open"] == 1
    assert payload["aggregates"]["total_with_events"] == 1
    assert payload["aggregates"]["total_without_events"] == 0
    assert payload["aggregates"]["by_area"][0]["area"] == "Distr_24_Arborea lotto Sud"
