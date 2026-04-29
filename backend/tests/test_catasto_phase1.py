from collections.abc import Generator
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

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
    CatCapacitasCertificato,
    CatCapacitasIntestatario,
    CatCapacitasTerrenoDetail,
    CatCapacitasTerrenoRow,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatConsorzioUnitSegment,
    CatDistretto,
    CatImportBatch,
    CatParticella,
    CatParticellaHistory,
    CatSchemaContributo,
    CatUtenzaIntestatario,
    CatUtenzaIrrigua,
)
from app.modules.utenze.models import AnagraficaSubject
from app.modules.utenze.models import AnagraficaPerson, AnagraficaPersonSnapshot
from app.modules.catasto.routes import import_routes as import_routes_module
from app.modules.catasto.services.import_capacitas import CapacitasImportDuplicateError, import_capacitas_excel
from app.modules.catasto.services.comuni_reference import load_comuni_reference
from app.modules.elaborazioni.capacitas.models import CapacitasAnagraficaDetail, CapacitasIntestatario, CapacitasTerrenoCertificato
from app.modules.catasto.services.validation import (
    validate_codice_fiscale,
    validate_comune,
    validate_superficie,
)
from tests.catasto_fixtures import (
    build_capacitas_dataframe,
    build_capacitas_workbook_bytes,
    build_oristanese_dirty_capacitas_dataframe,
    build_oristanese_dirty_capacitas_workbook_bytes,
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
    db.add(
        ApplicationUser(
            username="catasto-reviewer",
            email="catasto-reviewer@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.REVIEWER.value,
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
    return auth_headers_for("catasto-admin")


def auth_headers_for(username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_phase1_lookup_data(db: Session) -> None:
    comune_arborea = CatComune(
        nome_comune="Arborea",
        codice_catastale="A357",
        cod_comune_capacitas=165,
        codice_comune_formato_numerico=115006,
        codice_comune_numerico_2017_2025=95006,
        nome_comune_legacy="Arborea",
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    comune_cabras = CatComune(
        nome_comune="Cabras",
        codice_catastale="B314",
        cod_comune_capacitas=212,
        codice_comune_formato_numerico=115019,
        codice_comune_numerico_2017_2025=95018,
        nome_comune_legacy="Cabras",
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
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
        comune=comune_arborea,
        cod_comune_capacitas=165,
        codice_catastale="A357",
        nome_comune="Arborea",
        foglio="5",
        particella="120",
        subalterno="1",
        num_distretto="10",
        nome_distretto="Distretto 10",
        is_current=True,
        superficie_mq=1000,
        superficie_grafica_mq=975,
    )
    db.add_all(
        [
            batch,
            comune_arborea,
            comune_cabras,
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
            comune=comune_arborea,
            cod_comune_capacitas=165,
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
    subject = AnagraficaSubject(
        subject_type="person",
        status="active",
        source_system="capacitas",
        source_external_id="seed-dnifse64c01l122y",
        source_name_raw="Fenu Denise",
        requires_review=False,
    )
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome="Fenu",
            nome="Denise",
            codice_fiscale="DNIFSE64C01L122Y",
            comune_nascita="Terralba",
            comune_residenza="Arborea",
        )
    )
    db.add(
        CatParticellaHistory(
            particella_id=particella.id,
            comune_id=comune_arborea.id,
            cod_comune_capacitas=165,
            codice_catastale="A357",
            foglio="5",
            particella="120",
            subalterno="1",
            superficie_mq=950,
            superficie_grafica_mq=940,
            num_distretto="10",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            change_reason="seed-history",
        )
    )
    consorzio_unit = CatConsorzioUnit(
        particella_id=particella.id,
        comune_id=comune_arborea.id,
        cod_comune_capacitas=165,
        source_comune_id=comune_cabras.id,
        source_cod_comune_capacitas=212,
        source_codice_catastale="B314",
        source_comune_label="Cabras",
        comune_resolution_mode="swapped_arborea_terralba",
        foglio="5",
        particella="120",
        subalterno="1",
        descrizione="Unità consortile seed",
        source_first_seen=date(2025, 1, 1),
        source_last_seen=date(2025, 12, 31),
        is_active=True,
    )
    db.add(consorzio_unit)
    db.flush()
    db.add(
        CatConsorzioOccupancy(
            unit_id=consorzio_unit.id,
            utenza_id=db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.cco == "UT-SEED-001").one().id,
            cco="UT-SEED-001",
            fra="38",
            ccs="00000",
            pvc="097",
            com="212",
            source_type="capacitas_terreni",
            relationship_type="utilizzatore_reale",
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            is_current=True,
            confidence=Decimal("0.90"),
            notes="Occupazione seed da Capacitas Terreni",
        )
    )
    db.commit()


def seed_additional_distretto_kpi_data(db: Session) -> None:
    batch_id = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one().id
    comune_arborea = db.query(CatComune).filter(CatComune.cod_comune_capacitas == 165).one()
    comune_cabras = db.query(CatComune).filter(CatComune.cod_comune_capacitas == 212).one()
    distretto_20 = CatDistretto(num_distretto="20", nome_distretto="Distretto 20")
    particella_20 = CatParticella(
        comune=comune_cabras,
        cod_comune_capacitas=212,
        codice_catastale="B314",
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
                comune=comune_arborea,
                cod_comune_capacitas=165,
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
                comune=comune_cabras,
                cod_comune_capacitas=212,
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
                comune=comune_cabras,
                cod_comune_capacitas=212,
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
            cod_comune_capacitas=212,
            codice_catastale="B314",
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
        cod_comune_capacitas=165,
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
        cod_comune_capacitas=212,
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
    assert validate_comune(232) == {"is_valid": True, "nome_ufficiale": "Riola Sardo"}
    assert validate_comune(286) == {"is_valid": True, "nome_ufficiale": "San Nicolo d'Arcidano"}
    assert validate_superficie(16834, 16834)["ok"] is True
    assert validate_superficie(17100, 16834)["ok"] is False


def test_comuni_reference_dataset_covers_capacitas_legacy_codes() -> None:
    comuni = load_comuni_reference()
    assert sorted(comuni["cod_istat"].tolist()) == [
        50,
        59,
        165,
        170,
        173,
        176,
        179,
        186,
        189,
        200,
        206,
        212,
        222,
        226,
        229,
        232,
        239,
        242,
        249,
        252,
        266,
        280,
        283,
        286,
        289,
        743,
    ]
    by_catastale = {row["codice_catastale"]: row["cod_istat"] for _, row in comuni.iterrows()}
    assert by_catastale["A357"] == 165
    assert by_catastale["H301"] == 232
    assert by_catastale["G286"] == 229
    assert by_catastale["I791"] == 252
    assert by_catastale["A368"] == 286


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


def test_anomalie_endpoint_patch_requires_admin_role() -> None:
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
        headers=auth_headers_for("catasto-reviewer"),
        json={"status": "chiusa"},
    )

    assert response.status_code == 403


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
        subject = AnagraficaSubject(
            subject_type="person",
            status="active",
            source_system="capacitas",
            source_external_id="IDX-ANA-1",
            source_name_raw="Rossi_Mario_RSSMRA80A01H501Z",
            requires_review=False,
        )
        db.add(subject)
        db.flush()
        subject_id = subject.id
        db.add(
            AnagraficaPerson(
                subject_id=subject.id,
                cognome="Rossi",
                nome="Mario",
                codice_fiscale="RSSMRA80A01H501Z",
                comune_residenza="Oristano",
                indirizzo="Via Roma 1",
            )
        )
        db.flush()
        db.add(
            AnagraficaPersonSnapshot(
                subject_id=subject.id,
                source_system="capacitas",
                source_ref="IDX-ANA-1",
                cognome="Rossi",
                nome="Mario",
                codice_fiscale="RSSMRA80A01H501Z",
                comune_residenza="Uras",
                indirizzo="Via Vecchia 3",
                collected_at=datetime.now(timezone.utc),
            )
        )
        particella_id = particella.id
        certificato = CatCapacitasCertificato(
            cco="UT-SEED-001",
            fra="38",
            ccs="00000",
            pvc="097",
            com="289",
            partita_code="UT-SEED-001/38/00000",
            collected_at=datetime.now(timezone.utc),
        )
        db.add(certificato)
        db.flush()
        now = datetime.now(timezone.utc)
        db.add(
            CatCapacitasIntestatario(
                certificato_id=certificato.id,
                subject_id=subject.id,
                idxana="IDX-ANA-1",
                idxesa="IDX-ESA-1",
                codice_fiscale="RSSMRA80A01H501Z",
                denominazione="Rossi Mario",
                comune_residenza="ORISTANO",
                titoli="Proprieta` 1/1",
                deceduto=False,
                collected_at=now,
            )
        )
        db.add(
            CatUtenzaIntestatario(
                utenza_id=utenza.id,
                subject_id=subject.id,
                idxana="IDX-ANA-1",
                idxesa="IDX-ESA-1",
                history_id="HIST-1",
                anno_riferimento=2025,
                data_agg=now,
                codice_fiscale="RSSMRA80A01H501Z",
                denominazione="Rossi Mario",
                comune_residenza="ORISTANO",
                residenza="09070 ORISTANO - Via Roma 1",
                titoli="Proprieta` 1/1",
                deceduto=False,
                collected_at=now,
            )
        )
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
    consorzio_response = client.get(f"/catasto/particelle/{particella_id}/consorzio", headers=auth_headers())

    assert detail_response.status_code == 200
    assert detail_response.json()["foglio"] == "5"
    assert detail_response.json()["superficie_mq"] == "1000.00"
    assert detail_response.json()["superficie_grafica_mq"] == "975.00"
    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
    assert history_response.json()[0]["superficie_grafica_mq"] == "940.00"
    assert utenze_response.status_code == 200
    assert len(utenze_response.json()) == 1
    assert utenze_response.json()[0]["codice_fiscale"] == "DNIFSE64C01L122Y"
    assert anomalie_response.status_code == 200
    assert len(anomalie_response.json()) == 1
    assert anomalie_response.json()[0]["tipo"] == "VAL-06-imponibile"
    assert consorzio_response.status_code == 200
    consorzio_payload = consorzio_response.json()
    assert consorzio_payload["particella_id"] == str(particella_id)
    assert len(consorzio_payload["units"]) == 1
    assert consorzio_payload["units"][0]["comune_resolution_mode"] == "swapped_arborea_terralba"
    assert consorzio_payload["units"][0]["source_comune_label"] == "Cabras"
    assert consorzio_payload["units"][0]["occupancies"][0]["cco"] == "UT-SEED-001"
    assert consorzio_payload["units"][0]["intestatari_proprietari"][0]["codice_fiscale"] == "RSSMRA80A01H501Z"
    assert consorzio_payload["units"][0]["intestatari_proprietari"][0]["subject_id"] == str(subject_id)
    assert consorzio_payload["units"][0]["intestatari_proprietari"][0]["person"]["comune_residenza"] == "Oristano"
    assert consorzio_payload["units"][0]["intestatari_proprietari"][0]["person_snapshots"][0]["comune_residenza"] == "Uras"


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
    assert payload[0]["cod_comune_capacitas"] == 165
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


def test_bulk_search_anagrafica_returns_mixed_row_outcomes() -> None:
    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={
            "rows": [
                {"row_index": 2, "comune": "165", "foglio": "5", "particella": "120"},
                {"row_index": 3, "comune": "999", "foglio": "5", "particella": "120"},
                {"row_index": 4, "comune": None, "foglio": None, "particella": "120"},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"]
    assert payload[0]["esito"] == "FOUND"
    assert payload[0]["match"]["cod_comune_capacitas"] == 165
    assert payload[0]["match"]["intestatari"][0]["codice_fiscale"] == "DNIFSE64C01L122Y"
    assert payload[0]["match"]["intestatari"][0]["cognome"] == "Fenu"
    assert payload[0]["match"]["intestatari"][0]["nome"] == "Denise"
    assert payload[0]["match"]["intestatari"][0]["source"] == "capacitas"
    assert payload[1]["esito"] == "NOT_FOUND"
    assert payload[2]["esito"] == "INVALID_ROW"


def test_bulk_search_anagrafica_uses_all_particella_intestatari() -> None:
    db = TestingSessionLocal()
    try:
        utenza = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.cco == "UT-SEED-001").one()
        now = datetime.now(timezone.utc)
        db.add_all(
            [
                CatUtenzaIntestatario(
                    utenza_id=utenza.id,
                    subject_id=None,
                    idxana="IDX-ANA-OWNER-1",
                    idxesa="IDX-ESA-OWNER-1",
                    history_id="HIST-OWNER-1",
                    anno_riferimento=2025,
                    data_agg=now,
                    codice_fiscale="RSSMRA80A01H501U",
                    denominazione="Rossi Mario",
                    titoli="Proprieta` 1/3",
                    deceduto=False,
                    collected_at=now,
                ),
                CatUtenzaIntestatario(
                    utenza_id=utenza.id,
                    subject_id=None,
                    idxana="IDX-ANA-OWNER-2",
                    idxesa="IDX-ESA-OWNER-2",
                    history_id="HIST-OWNER-2",
                    anno_riferimento=2025,
                    data_agg=now,
                    codice_fiscale="VRDLGI80A01H501V",
                    denominazione="Verdi Luigi",
                    titoli="Proprieta` 1/3",
                    deceduto=False,
                    collected_at=now,
                ),
                CatUtenzaIntestatario(
                    utenza_id=utenza.id,
                    subject_id=None,
                    idxana="IDX-ANA-OWNER-3",
                    idxesa="IDX-ESA-OWNER-3",
                    history_id="HIST-OWNER-3",
                    anno_riferimento=2025,
                    data_agg=now,
                    codice_fiscale="BNCLRA80A01H501W",
                    denominazione="Bianchi Laura",
                    titoli="Proprieta` 1/3",
                    deceduto=False,
                    collected_at=now,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={"rows": [{"row_index": 2, "comune": "165", "foglio": "5", "particella": "120", "sub": "1"}]},
    )

    assert response.status_code == 200
    intestatari = response.json()["results"][0]["match"]["intestatari"]
    assert {item["codice_fiscale"] for item in intestatari} == {
        "RSSMRA80A01H501U",
        "VRDLGI80A01H501V",
        "BNCLRA80A01H501W",
    }


def test_bulk_search_anagrafica_multiple_matches_does_not_pick_first_particella() -> None:
    db = TestingSessionLocal()
    try:
        comune = db.query(CatComune).filter(CatComune.cod_comune_capacitas == 165).one()
        db.add(
            CatParticella(
                comune=comune,
                cod_comune_capacitas=165,
                codice_catastale="A357",
                nome_comune="Arborea",
                foglio="5",
                particella="120",
                subalterno="2",
                num_distretto="10",
                nome_distretto="Distretto 10",
                is_current=True,
                superficie_mq=1100,
                superficie_grafica_mq=1090,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={"rows": [{"row_index": 2, "comune": "165", "foglio": "5", "particella": "120"}]},
    )

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["esito"] == "MULTIPLE_MATCHES"
    assert row["matches_count"] == 2
    assert row["particella_id"] is None
    assert row["match"] is None
    assert len(row["matches"]) == 2
    assert sorted(match["subalterno"] for match in row["matches"]) == ["1", "2"]


def test_bulk_search_anagrafica_falls_back_to_live_capacitas_for_missing_intestatario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    try:
        seed_anomalie_workflow_data(db)
        particella = db.query(CatParticella).filter(CatParticella.foglio == "5", CatParticella.particella == "120").one()
        utenza = (
            db.query(CatUtenzaIrrigua)
            .filter(CatUtenzaIrrigua.cco == "UT-ANOM-10-2025")
            .one()
        )
        utenza.anno_campagna = 2026
        unit = CatConsorzioUnit(
            particella_id=particella.id,
            cod_comune_capacitas=165,
            foglio="5",
            particella="120",
            subalterno="1",
            descrizione="Unit test live lookup",
        )
        db.add(unit)
        db.flush()
        db.add(
            CatConsorzioOccupancy(
                unit_id=unit.id,
                utenza_id=utenza.id,
                cco="UT-ANOM-10-2025",
                fra="38",
                ccs="00000",
                pvc="097",
                com="289",
                source_type="capacitas_terreni",
                relationship_type="utilizzatore_reale",
                valid_from=date(2025, 1, 1),
            )
        )
        db.commit()
    finally:
        db.close()

    async def fake_login(self) -> None:
        return None

    async def fake_activate_app(self, app_name: str) -> None:
        assert app_name == "involture"

    async def fake_close(self) -> None:
        return None

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        assert kwargs["cco"] == "UT-ANOM-10-2025"
        return CapacitasTerrenoCertificato(
            cco=kwargs["cco"],
            com=kwargs["com"],
            pvc=kwargs["pvc"],
            fra=kwargs["fra"],
            ccs=kwargs["ccs"],
            intestatari=[
                CapacitasIntestatario(
                    idxana="IDX-LIVE-001",
                    idxesa="IDX-ESA-LIVE-001",
                    codice_fiscale="RSSMRA80A01H501U",
                    denominazione="Rossi Mario",
                    comune_residenza="Oristano",
                    cap="09170",
                    residenza="09170 Oristano (OR) - Via Roma 1",
                )
            ],
        )

    async def fake_fetch_current_anagrafica_detail(self, *, idxana: str, idxesa: str) -> CapacitasAnagraficaDetail:
        assert idxana == "IDX-LIVE-001"
        assert idxesa == "IDX-ESA-LIVE-001"
        return CapacitasAnagraficaDetail(
            idxana=idxana,
            idxesa=idxesa,
            cognome="Rossi",
            nome="Mario",
            denominazione="Rossi Mario",
            codice_fiscale="RSSMRA80A01H501U",
            luogo_nascita="Oristano",
            data_nascita=date(1980, 1, 1),
            residenza_belfiore="Oristano",
            residenza_localita="Oristano",
            residenza_toponimo="Via",
            residenza_indirizzo="Roma",
            residenza_civico="1",
            residenza_cap="09170",
            telefono="0783000000",
            email="mario.rossi@example.local",
        )

    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.pick_credential", lambda db, credential_id: (SimpleNamespace(id=1, username="live-user"), "secret"))
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_used", lambda db, credential_id: None)
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_error", lambda db, credential_id, error: None)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.apps.involture.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)
    monkeypatch.setattr(
        "app.modules.elaborazioni.capacitas.apps.involture.client.InVoltureClient.fetch_current_anagrafica_detail",
        fake_fetch_current_anagrafica_detail,
    )

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={
            "include_capacitas_live": True,
            "rows": [{"row_index": 1, "comune": "165", "foglio": "5", "particella": "120", "sub": "1"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["esito"] == "FOUND"
    assert payload["match"]["intestatari"][0]["codice_fiscale"] == "RSSMRA80A01H501U"
    assert payload["match"]["intestatari"][0]["cognome"] == "Rossi"
    assert payload["match"]["intestatari"][0]["nome"] == "Mario"
    assert payload["match"]["intestatari"][0]["source"] == "capacitas"

    db = TestingSessionLocal()
    try:
        subject = (
            db.query(AnagraficaSubject)
            .filter(
                AnagraficaSubject.source_system == "capacitas",
                AnagraficaSubject.source_external_id == "IDX-LIVE-001",
            )
            .one()
        )
        person = db.query(AnagraficaPerson).filter(AnagraficaPerson.subject_id == subject.id).one()
        assert person.codice_fiscale == "RSSMRA80A01H501U"
        assert person.cognome == "Rossi"
        assert person.nome == "Mario"
        assert person.indirizzo == "Via Roma 1"
        assert person.comune_residenza == "Oristano"
    finally:
        db.close()


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


def test_import_history_endpoint_supports_status_and_limit_filters() -> None:
    db = TestingSessionLocal()
    try:
        completed_batch = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one()
        db.add(
            CatImportBatch(
                filename="failed-import.xlsx",
                tipo="capacitas_ruolo",
                anno_campagna=2025,
                hash_file="failed-hash",
                status="failed",
                righe_totali=10,
                righe_importate=0,
                righe_anomalie=0,
                created_by=1,
                errore="Workbook non valido",
            )
        )
        db.add(
            CatImportBatch(
                filename="shapefile-import",
                tipo="shapefile",
                anno_campagna=None,
                hash_file="shape-hash",
                status="completed",
                righe_totali=2,
                righe_importate=2,
                righe_anomalie=0,
                created_by=1,
            )
        )
        db.commit()
        completed_batch_id = str(completed_batch.id)
    finally:
        db.close()

    failed_only = client.get("/catasto/import/history?status=failed&limit=1", headers=auth_headers())
    completed_capacitas = client.get(
        "/catasto/import/history?status=completed&tipo=capacitas_ruolo&limit=5",
        headers=auth_headers(),
    )

    assert failed_only.status_code == 200
    failed_payload = failed_only.json()
    assert len(failed_payload) == 1
    assert failed_payload[0]["status"] == "failed"

    assert completed_capacitas.status_code == 200
    completed_payload = completed_capacitas.json()
    assert len(completed_payload) == 1
    assert completed_payload[0]["id"] == completed_batch_id
    assert completed_payload[0]["tipo"] == "capacitas_ruolo"


def test_import_summary_endpoint_returns_status_counters() -> None:
    db = TestingSessionLocal()
    try:
        completed_batch = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one()
        completed_batch.completed_at = datetime.now(timezone.utc)
        db.add_all(
            [
                CatImportBatch(
                    filename="processing-import.xlsx",
                    tipo="capacitas_ruolo",
                    anno_campagna=2025,
                    hash_file="processing-hash",
                    status="processing",
                    righe_totali=10,
                    righe_importate=0,
                    righe_anomalie=0,
                    created_by=1,
                ),
                CatImportBatch(
                    filename="failed-import.xlsx",
                    tipo="capacitas_ruolo",
                    anno_campagna=2025,
                    hash_file="failed-summary-hash",
                    status="failed",
                    righe_totali=10,
                    righe_importate=0,
                    righe_anomalie=0,
                    created_by=1,
                    errore="Workbook non valido",
                ),
                CatImportBatch(
                    filename="replaced-import.xlsx",
                    tipo="capacitas_ruolo",
                    anno_campagna=2024,
                    hash_file="replaced-summary-hash",
                    status="replaced",
                    righe_totali=8,
                    righe_importate=8,
                    righe_anomalie=1,
                    created_by=1,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/catasto/import/summary?tipo=capacitas_ruolo", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["tipo"] == "capacitas_ruolo"
    assert payload["totale_batch"] >= 4
    assert payload["processing_batch"] == 1
    assert payload["completed_batch"] >= 1
    assert payload["failed_batch"] == 1
    assert payload["replaced_batch"] == 1
    assert payload["ultimo_completed_at"] is not None


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
        assert {u.cod_comune_capacitas for u in utenze if u.cod_comune_capacitas is not None}.issuperset({165, 200, 212})
    finally:
        db.close()


def test_import_capacitas_excel_accepts_dirty_oristanese_workbook_fixture() -> None:
    df = build_oristanese_dirty_capacitas_dataframe()
    db = TestingSessionLocal()
    try:
        batch = import_capacitas_excel(
            db=db,
            file_bytes=build_oristanese_dirty_capacitas_workbook_bytes(df),
            filename="ruoli-oristanese-dirty-fixture.xlsx",
            created_by=1,
        )
        utenze = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.import_batch_id == batch.id).all()
        anomalie = db.query(CatAnomalia).filter(CatAnomalia.utenza_id.isnot(None)).all()

        assert batch.status == "completed"
        assert batch.righe_importate == len(df)
        assert len(utenze) == len(df)
        assert batch.righe_anomalie >= 3
        assert {u.cod_comune_capacitas for u in utenze if u.cod_comune_capacitas is not None}.issuperset({165, 212, 222, 239, 280, 283})
        assert any(u.codice_fiscale == "DNIFSE64C01L122Y" for u in utenze)
        assert any(u.anomalia_cf_mancante for u in utenze)
        assert any(u.anomalia_cf_invalido for u in utenze)
        assert any(u.anomalia_comune_invalido for u in utenze)
        assert any(a.tipo == "VAL-04-comune_invalido" for a in anomalie)
        assert any(a.tipo == "VAL-03-cf_mancante" for a in anomalie)
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


def test_catasto_consorzio_tables_are_registered_in_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())

    assert "cat_consorzio_units" in table_names
    assert "cat_consorzio_unit_segments" in table_names
    assert "cat_consorzio_occupancies" in table_names
    assert "cat_capacitas_terreni_rows" in table_names
    assert "cat_capacitas_certificati" in table_names
    assert "cat_capacitas_intestatari" in table_names
    assert "cat_capacitas_terreno_details" in table_names


def test_catasto_consorzio_unit_segment_and_occupancy_can_be_persisted() -> None:
    db = TestingSessionLocal()
    try:
        particella = db.query(CatParticella).filter(CatParticella.foglio == "5", CatParticella.particella == "120").one()
        utenza = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.cco == "UT-SEED-001").one()
        comune = db.query(CatComune).filter(CatComune.cod_comune_capacitas == 165).one()

        unit = CatConsorzioUnit(
            particella_id=particella.id,
            comune_id=comune.id,
            cod_comune_capacitas=165,
            sezione_catastale="A",
            foglio="5",
            particella="120",
            subalterno="1",
            descrizione="Unità consortile Arborea 5/120/1",
            source_first_seen=date(2025, 1, 1),
            source_last_seen=date(2025, 12, 31),
        )
        db.add(unit)
        db.flush()

        segment = CatConsorzioUnitSegment(
            unit_id=unit.id,
            label="Porzione A",
            segment_type="porzione_irrigua",
            surface_declared_mq=Decimal("600.00"),
            surface_irrigable_mq=Decimal("540.00"),
            riordino_code="R.F. 23/8099",
            riordino_maglia="178",
            riordino_lotto="1",
            current_status="attiva",
            valid_from=date(2025, 1, 1),
        )
        db.add(segment)
        db.flush()

        occupancy = CatConsorzioOccupancy(
            unit_id=unit.id,
            segment_id=segment.id,
            utenza_id=utenza.id,
            cco="UT-SEED-001",
            fra="38",
            ccs="00000",
            pvc="097",
            com="289",
            source_type="capacitas_terreni",
            relationship_type="utilizzatore_reale",
            valid_from=date(2025, 1, 1),
            confidence=Decimal("0.95"),
            notes="Occupazione derivata da certificato Capacitas",
        )
        db.add(occupancy)
        db.commit()
        db.expire_all()

        saved_unit = db.query(CatConsorzioUnit).filter(CatConsorzioUnit.id == unit.id).one()
        saved_segment = db.query(CatConsorzioUnitSegment).filter(CatConsorzioUnitSegment.id == segment.id).one()
        saved_occupancy = db.query(CatConsorzioOccupancy).filter(CatConsorzioOccupancy.id == occupancy.id).one()

        assert saved_unit.particella_record is not None
        assert saved_unit.particella_record.id == particella.id
        assert saved_unit.occupancies[0].id == saved_occupancy.id
        assert saved_segment.unit.id == saved_unit.id
        assert saved_occupancy.segment is not None
        assert saved_occupancy.segment.id == saved_segment.id
        assert saved_occupancy.utenza_record is not None
        assert saved_occupancy.utenza_record.id == utenza.id
    finally:
        db.close()


def test_catasto_capacitas_snapshots_can_be_persisted() -> None:
    db = TestingSessionLocal()
    try:
        particella = db.query(CatParticella).filter(CatParticella.foglio == "5", CatParticella.particella == "120").one()
        comune = db.query(CatComune).filter(CatComune.cod_comune_capacitas == 165).one()

        unit = CatConsorzioUnit(
            particella_id=particella.id,
            comune_id=comune.id,
            cod_comune_capacitas=165,
            foglio="5",
            particella="120",
            subalterno="1",
            descrizione="Snapshot test",
        )
        db.add(unit)
        db.flush()

        terreno_row = CatCapacitasTerrenoRow(
            unit_id=unit.id,
            search_key="165|5|120|1",
            external_row_id="row-001",
            cco="0A1103877",
            fra="38",
            ccs="00000",
            pvc="097",
            com="289",
            belfiore="A357",
            foglio="5",
            particella="120",
            sub="1",
            anno=2025,
            voltura="N",
            opcode="R",
            data_reg="2025-04-26",
            superficie_mq=Decimal("1000.00"),
            bac_descr="Distretto Arborea",
            row_visual_state="current_black",
            raw_payload_json={"contribuente": "0A1103877", "anno": 2025},
            collected_at=datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc),
        )
        db.add(terreno_row)

        certificato = CatCapacitasCertificato(
            cco="0A1103877",
            fra="38",
            ccs="00000",
            pvc="097",
            com="289",
            partita_code="P-001",
            utenza_code="U-001",
            utenza_status="attiva",
            ruolo_status="corrente",
            raw_html="<html>certificato</html>",
            parsed_json={"riordino": "R.F. 23/8099"},
            collected_at=datetime(2026, 4, 23, 10, 5, tzinfo=timezone.utc),
        )
        db.add(certificato)
        db.flush()

        dettaglio = CatCapacitasTerrenoDetail(
            terreno_row_id=terreno_row.id,
            external_row_id="row-001",
            foglio="5",
            particella="120",
            sub="1",
            riordino_code="R.F. 23/8099",
            riordino_maglia="178",
            riordino_lotto="1",
            irridist="10",
            raw_html="<html>dettaglio</html>",
            parsed_json={"porzione": "A"},
            collected_at=datetime(2026, 4, 23, 10, 10, tzinfo=timezone.utc),
        )
        db.add(dettaglio)
        db.commit()
        db.expire_all()

        saved_row = db.query(CatCapacitasTerrenoRow).filter(CatCapacitasTerrenoRow.external_row_id == "row-001").one()
        saved_certificato = (
            db.query(CatCapacitasCertificato).filter(CatCapacitasCertificato.cco == "0A1103877").one()
        )
        saved_detail = (
            db.query(CatCapacitasTerrenoDetail).filter(CatCapacitasTerrenoDetail.external_row_id == "row-001").one()
        )

        assert saved_row.unit is not None
        assert saved_row.unit.id == unit.id
        assert saved_row.detail_snapshots[0].id == saved_detail.id
        assert saved_certificato.parsed_json == {"riordino": "R.F. 23/8099"}
        assert saved_detail.terreno_row is not None
        assert saved_detail.terreno_row.id == saved_row.id
    finally:
        db.close()


def test_finalize_shapefile_route_returns_service_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_finalize_shapefile_import(
        db: Session,
        *,
        created_by: int,
        cleanup_staging: bool,
        **_: object,
    ) -> dict[str, object]:
        captured["created_by"] = created_by
        captured["cleanup_staging"] = cleanup_staging
        return {"status": "completed", "inserted_current": 3, "updated_history": 1}

    monkeypatch.setattr(import_routes_module, "finalize_shapefile_import", fake_finalize_shapefile_import)

    response = client.post("/catasto/import/shapefile/finalize", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured["created_by"] > 0
    assert captured["cleanup_staging"] is True
