from collections.abc import Generator
from datetime import date

from fastapi.testclient import TestClient
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto_phase1 import (
    CatAnomalia,
    CatDistretto,
    CatImportBatch,
    CatParticella,
    CatParticellaHistory,
    CatSchemaContributo,
    CatUtenzaIrrigua,
)
from app.modules.catasto.routes import import_routes as import_routes_module
from app.modules.catasto.services.import_capacitas import CapacitasImportDuplicateError, import_capacitas_excel
from app.modules.catasto.services.validation import (
    validate_codice_fiscale,
    validate_comune,
    validate_superficie,
)
from tests.catasto_fixtures import (
    build_capacitas_dataframe,
    build_capacitas_workbook_bytes,
    build_oristanese_territorial_capacitas_dataframe,
    build_oristanese_territorial_capacitas_workbook_bytes,
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
    seed_phase1_lookup_data(db)
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "catasto-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_phase1_lookup_data(db: Session) -> None:
    batch = CatImportBatch(
        filename="seed.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=2025,
        hash_file="seed-hash",
        status="completed",
        righe_totali=2,
        righe_importate=2,
        righe_anomalie=1,
        created_by=1,
    )
    particella = CatParticella(
        cod_comune_istat=165,
        nome_comune="Arborea",
        foglio="5",
        particella="120",
        subalterno="1",
        num_distretto="10",
        nome_distretto="Distretto 10",
        is_current=True,
        superficie_mq=1000,
    )
    db.add_all(
        [
            batch,
            CatSchemaContributo(codice="0648", descrizione="Schema 0648", tipo_calcolo="fisso", attivo=True),
            CatSchemaContributo(codice="0985", descrizione="Schema 0985", tipo_calcolo="contatori", attivo=True),
            particella,
        ]
    )
    db.flush()
    db.add(
        CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2025,
            cco="UT-SEED-001",
            cod_comune_istat=165,
            num_distretto=10,
            nome_comune="Arborea",
            foglio="5",
            particella="120",
            subalterno="1",
            particella_id=particella.id,
            sup_catastale_mq=1000,
            sup_irrigabile_mq=900,
            imponibile_sf=1350,
            ind_spese_fisse=1.5,
            aliquota_0648=0.1,
            importo_0648=135,
            aliquota_0985=0.2,
            importo_0985=270,
            codice_fiscale="DNIFSE64C01L122Y",
            codice_fiscale_raw="Dnifse64c01l122y",
        )
    )
    db.add(
        CatParticellaHistory(
            particella_id=particella.id,
            cod_comune_istat=165,
            foglio="5",
            particella="120",
            subalterno="1",
            superficie_mq=950,
            num_distretto="10",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            change_reason="seed-history",
        )
    )
    db.commit()


def seed_additional_distretto_kpi_data(db: Session) -> None:
    batch_id = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one().id
    distretto_20 = CatDistretto(num_distretto="20", nome_distretto="Distretto 20")
    particella_20 = CatParticella(
        cod_comune_istat=212,
        nome_comune="Cabras",
        foglio="8",
        particella="321",
        subalterno=None,
        num_distretto="20",
        nome_distretto="Distretto 20",
        is_current=True,
        superficie_mq=2500,
    )
    db.add_all([distretto_20, particella_20])
    db.flush()

    particella_10 = db.query(CatParticella).filter(CatParticella.foglio == "5").one()

    db.add_all(
        [
            CatUtenzaIrrigua(
                import_batch_id=batch_id,
                anno_campagna=2024,
                cco="UT-SEED-010-2024",
                cod_comune_istat=165,
                num_distretto=10,
                nome_comune="Arborea",
                foglio="5",
                particella="120",
                subalterno="1",
                particella_id=particella_10.id,
                sup_catastale_mq=1000,
                sup_irrigabile_mq=700,
                imponibile_sf=980,
                ind_spese_fisse=1.4,
                aliquota_0648=0.1,
                importo_0648=98,
                aliquota_0985=0.15,
                importo_0985=147,
                codice_fiscale="FNDGPP63E11B354D",
                codice_fiscale_raw="FNDGPP63E11B354D",
            ),
            CatUtenzaIrrigua(
                import_batch_id=batch_id,
                anno_campagna=2025,
                cco="UT-SEED-020-2025-A",
                cod_comune_istat=212,
                num_distretto=20,
                nome_comune="Cabras",
                foglio="8",
                particella="321",
                subalterno=None,
                particella_id=particella_20.id,
                sup_catastale_mq=2500,
                sup_irrigabile_mq=1200,
                imponibile_sf=1800,
                ind_spese_fisse=1.5,
                aliquota_0648=0.1,
                importo_0648=180,
                aliquota_0985=0.2,
                importo_0985=360,
                codice_fiscale="00588230953",
                codice_fiscale_raw="00588230953",
            ),
            CatUtenzaIrrigua(
                import_batch_id=batch_id,
                anno_campagna=2025,
                cco="UT-SEED-020-2025-B",
                cod_comune_istat=212,
                num_distretto=20,
                nome_comune="Cabras",
                foglio="8",
                particella="321",
                subalterno=None,
                particella_id=particella_20.id,
                sup_catastale_mq=2500,
                sup_irrigabile_mq=800,
                imponibile_sf=1200,
                ind_spese_fisse=1.5,
                aliquota_0648=0.1,
                importo_0648=120,
                aliquota_0985=0.2,
                importo_0985=240,
                codice_fiscale="RSSMRA80A01H501U",
                codice_fiscale_raw="RSSMRA80A01H501U",
            ),
        ]
    )
    db.flush()

    utenze_20 = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.num_distretto == 20).all()
    db.add_all(
        [
            CatAnomalia(
                utenza_id=utenze_20[0].id,
                particella_id=particella_20.id,
                anno_campagna=2025,
                tipo="VAL-01-sup_eccede",
                severita="warning",
                status="aperta",
                descrizione="Superficie incoerente",
            ),
            CatAnomalia(
                utenza_id=utenze_20[1].id,
                particella_id=particella_20.id,
                anno_campagna=2025,
                tipo="VAL-02-cf_invalido",
                severita="error",
                status="aperta",
                descrizione="CF incoerente",
            ),
        ]
    )
    db.commit()


def seed_anomalie_workflow_data(db: Session) -> None:
    batch_id = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one().id
    particella_10 = db.query(CatParticella).filter(CatParticella.foglio == "5").one()

    distretto_20 = db.query(CatDistretto).filter(CatDistretto.num_distretto == "20").one_or_none()
    particella_20 = db.query(CatParticella).filter(CatParticella.num_distretto == "20").one_or_none()
    if distretto_20 is None:
        distretto_20 = CatDistretto(num_distretto="20", nome_distretto="Distretto 20")
        db.add(distretto_20)
    if particella_20 is None:
        particella_20 = CatParticella(
            cod_comune_istat=212,
            nome_comune="Cabras",
            foglio="9",
            particella="401",
            subalterno=None,
            num_distretto="20",
            nome_distretto="Distretto 20",
            is_current=True,
            superficie_mq=1800,
        )
        db.add(particella_20)
    db.flush()

    utenza_10 = CatUtenzaIrrigua(
        import_batch_id=batch_id,
        anno_campagna=2025,
        cco="UT-ANOM-10-2025",
        cod_comune_istat=165,
        num_distretto=10,
        nome_comune="Arborea",
        foglio="5",
        particella="120",
        subalterno="1",
        particella_id=particella_10.id,
        sup_catastale_mq=1000,
        sup_irrigabile_mq=950,
        imponibile_sf=1425,
        ind_spese_fisse=1.5,
        aliquota_0648=0.1,
        importo_0648=142.5,
        aliquota_0985=0.2,
        importo_0985=285,
        codice_fiscale="RSSMRA80A01H501U",
        codice_fiscale_raw="rssmra80a01h501u",
    )
    utenza_20 = CatUtenzaIrrigua(
        import_batch_id=batch_id,
        anno_campagna=2024,
        cco="UT-ANOM-20-2024",
        cod_comune_istat=212,
        num_distretto=20,
        nome_comune="Cabras",
        foglio=particella_20.foglio,
        particella=particella_20.particella,
        subalterno=particella_20.subalterno,
        particella_id=particella_20.id,
        sup_catastale_mq=1800,
        sup_irrigabile_mq=1400,
        imponibile_sf=2100,
        ind_spese_fisse=1.5,
        aliquota_0648=0.1,
        importo_0648=210,
        aliquota_0985=0.2,
        importo_0985=420,
        codice_fiscale="00588230953",
        codice_fiscale_raw="00588230953",
    )
    db.add_all([utenza_10, utenza_20])
    db.flush()

    db.add_all(
        [
            CatAnomalia(
                utenza_id=utenza_10.id,
                particella_id=particella_10.id,
                anno_campagna=2025,
                tipo="VAL-06-imponibile",
                severita="warning",
                status="aperta",
                descrizione="Imponibile da verificare",
            ),
            CatAnomalia(
                utenza_id=utenza_10.id,
                particella_id=particella_10.id,
                anno_campagna=2025,
                tipo="VAL-07-importi",
                severita="warning",
                status="chiusa",
                descrizione="Importi storicamente incoerenti",
            ),
            CatAnomalia(
                utenza_id=utenza_20.id,
                particella_id=particella_20.id,
                anno_campagna=2024,
                tipo="VAL-02-cf_invalido",
                severita="error",
                status="assegnata",
                descrizione="CF da correggere",
                assigned_to=1,
            ),
        ]
    )
    db.commit()


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
    assert validate_comune(212) == {"is_valid": True, "nome_ufficiale": "Cabras"}
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


def test_anomalie_endpoint_supports_combined_filters_and_pagination() -> None:
    db = TestingSessionLocal()
    try:
        seed_anomalie_workflow_data(db)
    finally:
        db.close()

    filtered = client.get(
        "/catasto/anomalie/?status=aperta&severita=warning&anno=2025&distretto=10&page=1&page_size=1",
        headers=auth_headers(),
    )
    second_page = client.get(
        "/catasto/anomalie/?status=aperta&severita=warning&anno=2025&distretto=10&page=2&page_size=1",
        headers=auth_headers(),
    )

    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["tipo"] == "VAL-06-imponibile"

    assert second_page.status_code == 200
    assert second_page.json()["items"] == []


def test_anomalie_endpoint_patch_updates_workflow_fields() -> None:
    db = TestingSessionLocal()
    try:
        seed_anomalie_workflow_data(db)
        anomalia_id = (
            db.query(CatAnomalia)
            .filter(CatAnomalia.tipo == "VAL-06-imponibile", CatAnomalia.status == "aperta")
            .one()
            .id
        )
    finally:
        db.close()

    response = client.patch(
        f"/catasto/anomalie/{anomalia_id}",
        headers=auth_headers(),
        json={"status": "chiusa", "note_operatore": "Verifica completata", "assigned_to": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "chiusa"
    assert payload["note_operatore"] == "Verifica completata"
    assert payload["assigned_to"] == 1


def test_import_capacitas_requires_authentication() -> None:
    response = client.post(
        "/catasto/import/capacitas",
        files={"file": ("capacitas.xlsx", b"fake-content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 401


def test_distretto_kpi_endpoint_returns_aggregates_for_year() -> None:
    response = client.get("/catasto/distretti/", headers=auth_headers())
    distretto_id = response.json()[0]["id"]

    kpi_response = client.get(f"/catasto/distretti/{distretto_id}/kpi?anno=2025", headers=auth_headers())

    assert kpi_response.status_code == 200
    payload = kpi_response.json()
    assert payload["num_distretto"] == "10"
    assert payload["totale_particelle"] == 1
    assert payload["totale_utenze"] == 1
    assert payload["importo_totale_0648"] == "135.00"
    assert payload["importo_totale_0985"] == "270.00"
    assert payload["superficie_irrigabile_mq"] == "900.00"


def test_distretto_kpi_endpoint_filters_multi_year_data() -> None:
    db = TestingSessionLocal()
    try:
        seed_additional_distretto_kpi_data(db)
    finally:
        db.close()

    response = client.get("/catasto/distretti/", headers=auth_headers())
    distretti = {item["num_distretto"]: item["id"] for item in response.json()}

    yearly_2025 = client.get(f"/catasto/distretti/{distretti['10']}/kpi?anno=2025", headers=auth_headers())
    yearly_2024 = client.get(f"/catasto/distretti/{distretti['10']}/kpi?anno=2024", headers=auth_headers())
    all_years = client.get(f"/catasto/distretti/{distretti['10']}/kpi", headers=auth_headers())

    assert yearly_2025.status_code == 200
    assert yearly_2025.json()["totale_utenze"] == 1
    assert yearly_2025.json()["importo_totale_0648"] == "135.00"
    assert yearly_2025.json()["importo_totale_0985"] == "270.00"
    assert yearly_2025.json()["superficie_irrigabile_mq"] == "900.00"

    assert yearly_2024.status_code == 200
    assert yearly_2024.json()["totale_utenze"] == 1
    assert yearly_2024.json()["importo_totale_0648"] == "98.00"
    assert yearly_2024.json()["importo_totale_0985"] == "147.00"
    assert yearly_2024.json()["superficie_irrigabile_mq"] == "700.00"

    assert all_years.status_code == 200
    assert all_years.json()["totale_utenze"] == 2
    assert all_years.json()["importo_totale_0648"] == "233.00"
    assert all_years.json()["importo_totale_0985"] == "417.00"
    assert all_years.json()["superficie_irrigabile_mq"] == "1600.00"


def test_distretto_kpi_endpoint_keeps_aggregates_isolated_per_distretto() -> None:
    db = TestingSessionLocal()
    try:
        seed_additional_distretto_kpi_data(db)
    finally:
        db.close()

    response = client.get("/catasto/distretti/", headers=auth_headers())
    payload = response.json()
    assert len(payload) == 2
    distretti = {item["num_distretto"]: item["id"] for item in payload}

    kpi_response = client.get(f"/catasto/distretti/{distretti['20']}/kpi?anno=2025", headers=auth_headers())

    assert kpi_response.status_code == 200
    kpi = kpi_response.json()
    assert kpi["num_distretto"] == "20"
    assert kpi["totale_particelle"] == 1
    assert kpi["totale_utenze"] == 2
    assert kpi["totale_anomalie"] == 2
    assert kpi["anomalie_error"] == 1
    assert kpi["importo_totale_0648"] == "300.00"
    assert kpi["importo_totale_0985"] == "600.00"
    assert kpi["superficie_irrigabile_mq"] == "2000.00"


def test_particella_detail_history_utenze_and_anomalie_endpoints() -> None:
    db = TestingSessionLocal()
    try:
        particella = db.query(CatParticella).filter(CatParticella.foglio == "5").one()
        utenza = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.cco == "UT-SEED-001").one()
        particella_id = particella.id
        db.add(
            CatAnomalia(
                utenza_id=utenza.id,
                particella_id=particella.id,
                anno_campagna=2025,
                tipo="VAL-06-imponibile",
                severita="warning",
                status="aperta",
                descrizione="Imponibile incoerente",
            )
        )
        db.commit()
    finally:
        db.close()

    detail_response = client.get(f"/catasto/particelle/{particella_id}", headers=auth_headers())
    history_response = client.get(f"/catasto/particelle/{particella_id}/history", headers=auth_headers())
    utenze_response = client.get(f"/catasto/particelle/{particella_id}/utenze?anno=2025", headers=auth_headers())
    anomalie_response = client.get(f"/catasto/particelle/{particella_id}/anomalie?anno=2025", headers=auth_headers())

    assert detail_response.status_code == 200
    assert detail_response.json()["foglio"] == "5"
    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
    assert utenze_response.status_code == 200
    assert len(utenze_response.json()) == 1
    assert utenze_response.json()[0]["codice_fiscale"] == "DNIFSE64C01L122Y"
    assert anomalie_response.status_code == 200
    assert len(anomalie_response.json()) == 1
    assert anomalie_response.json()[0]["tipo"] == "VAL-06-imponibile"


def test_particelle_endpoint_supports_combined_lookup_filters() -> None:
    db = TestingSessionLocal()
    try:
        seed_anomalie_workflow_data(db)
    finally:
        db.close()

    response = client.get(
        "/catasto/particelle/?comune=165&foglio=5&particella=120&distretto=10&anno=2025&cf=RSSMRA80A01H501U&ha_anomalie=true",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["cod_comune_istat"] == 165
    assert payload[0]["foglio"] == "5"
    assert payload[0]["particella"] == "120"
    assert payload[0]["num_distretto"] == "10"


def test_particelle_endpoint_returns_empty_when_combined_filters_conflict() -> None:
    db = TestingSessionLocal()
    try:
        seed_anomalie_workflow_data(db)
    finally:
        db.close()

    response = client.get(
        "/catasto/particelle/?comune=165&foglio=5&particella=120&distretto=10&anno=2025&cf=RSSMRA80A01H501U&ha_anomalie=false",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_import_history_and_report_endpoints_return_batch_data() -> None:
    db = TestingSessionLocal()
    try:
        batch = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one()
        utenza = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.import_batch_id == batch.id).one()
        db.add(
            CatAnomalia(
                utenza_id=utenza.id,
                anno_campagna=2025,
                tipo="VAL-07-importi",
                severita="warning",
                status="aperta",
                descrizione="Importi incoerenti",
            )
        )
        db.commit()
    finally:
        db.close()

    history_response = client.get("/catasto/import/history", headers=auth_headers())
    assert history_response.status_code == 200
    batch_id = history_response.json()[0]["id"]

    status_response = client.get(f"/catasto/import/{batch_id}/status", headers=auth_headers())
    report_response = client.get(f"/catasto/import/{batch_id}/report?tipo=VAL-07-importi", headers=auth_headers())

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert report_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["total"] == 1
    assert report_payload["items"][0]["tipo"] == "VAL-07-importi"


def test_import_capacitas_excel_creates_batch_and_normalizes_cf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.catasto.services.import_capacitas.pd.read_excel",
        lambda *args, **kwargs: {"Ruoli 2025": build_capacitas_dataframe()},
    )

    db = TestingSessionLocal()
    try:
        batch = import_capacitas_excel(
            db=db,
            file_bytes=b"fake-xlsx-content",
            filename="ruoli-2025.xlsx",
            created_by=1,
        )

        utenze = (
            db.query(CatUtenzaIrrigua)
            .filter(CatUtenzaIrrigua.import_batch_id == batch.id)
            .order_by(CatUtenzaIrrigua.cco)
            .all()
        )
        anomalie = db.query(CatAnomalia).all()

        assert batch.status == "completed"
        assert batch.righe_importate == 2
        assert batch.righe_anomalie == 1
        assert len(utenze) == 2
        assert utenze[0].codice_fiscale == "DNIFSE64C01L122Y"
        assert utenze[0].codice_fiscale_raw == "Dnifse64c01l122y"
        assert utenze[1].anomalia_cf_invalido is True
        assert utenze[1].anomalia_comune_invalido is True
        assert len(anomalie) >= 4
    finally:
        db.close()


def test_import_capacitas_excel_duplicate_and_force(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.catasto.services.import_capacitas.pd.read_excel",
        lambda *args, **kwargs: {"Ruoli 2025": build_capacitas_dataframe().head(1)},
    )

    db = TestingSessionLocal()
    try:
        first_batch = import_capacitas_excel(
            db=db,
            file_bytes=b"same-content",
            filename="ruoli-2025.xlsx",
            created_by=1,
        )

        with pytest.raises(CapacitasImportDuplicateError):
            import_capacitas_excel(
                db=db,
                file_bytes=b"same-content",
                filename="ruoli-2025.xlsx",
                created_by=1,
            )

        second_batch = import_capacitas_excel(
            db=db,
            file_bytes=b"same-content",
            filename="ruoli-2025.xlsx",
            created_by=1,
            force=True,
        )

        db.refresh(first_batch)
        assert first_batch.status == "replaced"
        assert second_batch.status == "completed"
        assert second_batch.id != first_batch.id
    finally:
        db.close()


def test_import_capacitas_excel_reads_real_workbook_bytes() -> None:
    db = TestingSessionLocal()
    try:
        batch = import_capacitas_excel(
            db=db,
            file_bytes=build_capacitas_workbook_bytes(build_capacitas_dataframe().head(1)),
            filename="ruoli-real-workbook.xlsx",
            created_by=1,
        )
        utenze = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.import_batch_id == batch.id).all()

        assert batch.status == "completed"
        assert batch.righe_importate == 1
        assert len(utenze) == 1
        assert utenze[0].codice_fiscale == "DNIFSE64C01L122Y"
    finally:
        db.close()


def test_import_capacitas_excel_accepts_realistic_oristanese_fixture() -> None:
    df = build_oristanese_territorial_capacitas_dataframe()
    db = TestingSessionLocal()
    try:
        batch = import_capacitas_excel(
            db=db,
            file_bytes=build_oristanese_territorial_capacitas_workbook_bytes(df),
            filename="ruoli-oristanese-fixture.xlsx",
            created_by=1,
        )
        utenze = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.import_batch_id == batch.id).all()

        assert batch.status == "completed"
        assert batch.righe_importate == len(df)
        assert len(utenze) == len(df)
        assert {u.cod_comune_istat for u in utenze if u.cod_comune_istat is not None}.issuperset({165, 200, 212})
    finally:
        db.close()


def test_import_capacitas_excel_accepts_legacy_alias_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    alias_df = pd.DataFrame(
        [
            {
                "ANNO": "2025",
                "PVC": "95",
                "COM": "165",
                "CCO": "UT-ALIAS-001",
                "DISTRETTO": "10",
                "COMUNE": "Arborea",
                "FOGLIO": "5",
                "PARTIC": "120",
                "SUB": "1",
                "SUP.CATA.": "1000",
                "SUP.IRRIGABILE": "1000",
                "Ind. Spese Fisse": "1.5",
                "Imponibile s.f.": "1500",
                "ALIQUOTA 0648": "0.1",
                "IMPORTO 0648": "150",
                "ALIQUOTA 0985": "0.2",
                "IMPORTO 0985": "300",
                "DENOMINAZ": "Mario Rossi Alias",
                "CODFISC": "Dnifse64c01l122y",
            }
        ]
    )
    monkeypatch.setattr(
        "app.modules.catasto.services.import_capacitas.pd.read_excel",
        lambda *args, **kwargs: {"Ruoli 2025": alias_df},
    )

    db = TestingSessionLocal()
    try:
        batch = import_capacitas_excel(
            db=db,
            file_bytes=b"alias-xlsx-content",
            filename="ruoli-alias-2025.xlsx",
            created_by=1,
        )
        utenza = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.import_batch_id == batch.id).one()

        assert utenza.denominazione == "Mario Rossi Alias"
        assert utenza.codice_fiscale == "DNIFSE64C01L122Y"
        assert utenza.codice_fiscale_raw == "Dnifse64c01l122y"
    finally:
        db.close()


def test_finalize_shapefile_route_returns_service_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, int] = {}

    def fake_finalize_shapefile_import(db: Session, *, created_by: int, **_: object) -> dict[str, object]:
        captured["created_by"] = created_by
        return {"status": "completed", "inserted_current": 3, "updated_history": 1}

    monkeypatch.setattr(import_routes_module, "finalize_shapefile_import", fake_finalize_shapefile_import)

    response = client.post("/catasto/import/shapefile/finalize", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured["created_by"] > 0
