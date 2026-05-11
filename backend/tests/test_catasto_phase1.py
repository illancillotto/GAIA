from collections.abc import Generator
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

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
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaPersonSnapshot, AnagraficaSubject
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.catasto.routes import import_routes as import_routes_module
from app.modules.catasto.services.import_capacitas import CapacitasImportDuplicateError, import_capacitas_excel
from app.modules.catasto.services.comuni_reference import load_comuni_reference
from app.modules.catasto.services.import_distretti_excel import import_distretti_excel
from app.modules.catasto.services import import_distretti_excel as import_distretti_excel_module
from app.modules.elaborazioni.capacitas.models import CapacitasAnagraficaDetail, CapacitasIntestatario, CapacitasTerrenoCertificato
from app.modules.elaborazioni.capacitas.models import CapacitasLookupOption, CapacitasTerreniSearchResult
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


def build_distretti_excel_bytes(rows: list[dict[str, object]]) -> bytes:
    buffer = BytesIO()
    dataframe = pd.DataFrame(rows)
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return buffer.getvalue()


def test_import_distretti_excel_updates_current_particelle_ignoring_sub() -> None:
    db = TestingSessionLocal()
    payload = build_distretti_excel_bytes(
        [
            {
                "ANNO": "2025",
                "N_DISTRETTO": "26",
                "DISTRETTO": "Sassu",
                "COMUNE": "ARBOREA",
                "SEZIONE": None,
                "FOGLIO": "5",
                "PARTIC": "120",
                "SUB": "77",
            }
        ]
    )

    batch = import_distretti_excel(
        db=db,
        file_bytes=payload,
        filename="distretti.xlsx",
        created_by=1,
    )

    particella = (
        db.query(CatParticella)
        .filter(CatParticella.cod_comune_capacitas == 165, CatParticella.foglio == "5", CatParticella.particella == "120")
        .one()
    )
    assert particella.subalterno == "1"
    assert particella.num_distretto == "26"
    assert particella.nome_distretto == "Sassu"
    assert batch.status == "completed"
    assert batch.report_json["particelle_aggiornate"] == 1
    assert batch.report_json["righe_senza_match_particella"] == 0

    history_rows = (
        db.query(CatParticellaHistory)
        .filter(CatParticellaHistory.change_reason == "import_distretti_excel")
        .all()
    )
    assert len(history_rows) == 1
    assert history_rows[0].num_distretto == "10"
    db.close()


def test_import_distretti_excel_collapses_rows_that_differ_only_by_sub() -> None:
    db = TestingSessionLocal()
    payload = build_distretti_excel_bytes(
        [
            {
                "ANNO": "2025",
                "N_DISTRETTO": "26",
                "DISTRETTO": "Sassu",
                "COMUNE": "ARBOREA",
                "SEZIONE": None,
                "FOGLIO": "5",
                "PARTIC": "120",
                "SUB": "1",
            },
            {
                "ANNO": "2025",
                "N_DISTRETTO": "26",
                "DISTRETTO": "Sassu",
                "COMUNE": "ARBOREA",
                "SEZIONE": None,
                "FOGLIO": "5",
                "PARTIC": "120",
                "SUB": "9",
            },
        ]
    )

    batch = import_distretti_excel(
        db=db,
        file_bytes=payload,
        filename="distretti.xlsx",
        created_by=1,
    )

    particella = (
        db.query(CatParticella)
        .filter(CatParticella.cod_comune_capacitas == 165, CatParticella.foglio == "5", CatParticella.particella == "120")
        .one()
    )
    history_rows = (
        db.query(CatParticellaHistory)
        .filter(CatParticellaHistory.change_reason == "import_distretti_excel")
        .all()
    )
    assert particella.num_distretto == "26"
    assert batch.report_json["righe_totali"] == 2
    assert batch.report_json["righe_univoche"] == 1
    assert batch.report_json["righe_duplicate_collassate"] == 1
    assert batch.report_json["particelle_aggiornate"] == 1
    assert len(history_rows) == 1
    db.close()


def test_upload_distretti_excel_endpoint_starts_and_completes_batch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(import_routes_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(import_distretti_excel_module, "IMPORT_STORAGE_DIR", tmp_path / "imports")
    db = TestingSessionLocal()
    db.add(
        CatParticella(
            comune=db.query(CatComune).filter(CatComune.cod_comune_capacitas == 165).one(),
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="Arborea",
            foglio="7",
            particella="321",
            subalterno=None,
            num_distretto="10",
            nome_distretto="Distretto 10",
            is_current=True,
        )
    )
    db.commit()
    db.close()

    payload = build_distretti_excel_bytes(
        [
            {
                "ANNO": "2025",
                "N_DISTRETTO": "30",
                "DISTRETTO": "Nuovo Distretto",
                "COMUNE": "A357",
                "SEZIONE": None,
                "FOGLIO": "7",
                "PARTIC": "321",
                "SUB": "5",
            }
        ]
    )

    response = client.post(
        "/catasto/import/distretti/excel",
        headers=auth_headers(),
        files={
            "file": (
                "distretti.xlsx",
                payload,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 202
    batch_id = response.json()["batch_id"]

    status_response = client.get(f"/catasto/import/{batch_id}/status", headers=auth_headers())
    assert status_response.status_code == 200
    payload_status = status_response.json()
    assert payload_status["tipo"] == "distretti_excel"
    assert payload_status["status"] == "completed"
    assert payload_status["report_json"]["particelle_aggiornate"] == 1
    assert payload_status["report_json"]["distretti_creati"] == 1


def test_import_distretti_excel_resolves_local_comune_aliases_and_sections() -> None:
    db = TestingSessionLocal()
    comune_oristano = CatComune(
        nome_comune="Oristano",
        codice_catastale="G113",
        cod_comune_capacitas=500,
    )
    comune_simaxis = CatComune(
        nome_comune="Simaxis",
        codice_catastale="I743",
        cod_comune_capacitas=501,
    )
    comune_arcidano = CatComune(
        nome_comune="San Nicolo d'Arcidano",
        codice_catastale="A368",
        cod_comune_capacitas=286,
    )
    db.add_all([comune_oristano, comune_simaxis, comune_arcidano])
    db.flush()
    db.add_all(
        [
            CatParticella(
                comune_id=comune_oristano.id,
                cod_comune_capacitas=500,
                codice_catastale="G113",
                nome_comune="Oristano",
                sezione_catastale="B",
                foglio="11",
                particella="20",
                subalterno=None,
                num_distretto="10",
                nome_distretto="Distretto 10",
                is_current=True,
            ),
            CatParticella(
                comune_id=comune_simaxis.id,
                cod_comune_capacitas=501,
                codice_catastale="I743",
                nome_comune="Simaxis",
                sezione_catastale="B",
                foglio="7",
                particella="33",
                subalterno=None,
                num_distretto="10",
                nome_distretto="Distretto 10",
                is_current=True,
            ),
            CatParticella(
                comune_id=comune_arcidano.id,
                cod_comune_capacitas=286,
                codice_catastale="A368",
                nome_comune="San Nicolo d'Arcidano",
                sezione_catastale=None,
                foglio="3",
                particella="101",
                subalterno=None,
                num_distretto="10",
                nome_distretto="Distretto 10",
                is_current=True,
            ),
        ]
    )
    db.commit()

    payload = build_distretti_excel_bytes(
        [
            {
                "ANNO": "2025",
                "N_DISTRETTO": "40",
                "DISTRETTO": "Oristano B",
                "COMUNE": "DONIGALA FENUGHEDU*ORISTANO",
                "SEZIONE": None,
                "FOGLIO": "11",
                "PARTIC": "20",
                "SUB": None,
            },
            {
                "ANNO": "2025",
                "N_DISTRETTO": "41",
                "DISTRETTO": "Simaxis B",
                "COMUNE": "SAN VERO CONGIUS*SIMAXIS",
                "SEZIONE": None,
                "FOGLIO": "7",
                "PARTIC": "33",
                "SUB": None,
            },
            {
                "ANNO": "2025",
                "N_DISTRETTO": "42",
                "DISTRETTO": "Arcidano",
                "COMUNE": "SAN NICOLO ARCIDANO",
                "SEZIONE": None,
                "FOGLIO": "3",
                "PARTIC": "101",
                "SUB": None,
            },
        ]
    )

    batch = import_distretti_excel(
        db=db,
        file_bytes=payload,
        filename="distretti-alias.xlsx",
        created_by=1,
    )

    updated_oristano = (
        db.query(CatParticella)
        .filter(CatParticella.comune_id == comune_oristano.id, CatParticella.foglio == "11", CatParticella.particella == "20")
        .one()
    )
    updated_simaxis = (
        db.query(CatParticella)
        .filter(CatParticella.comune_id == comune_simaxis.id, CatParticella.foglio == "7", CatParticella.particella == "33")
        .one()
    )
    updated_arcidano = (
        db.query(CatParticella)
        .filter(CatParticella.comune_id == comune_arcidano.id, CatParticella.foglio == "3", CatParticella.particella == "101")
        .one()
    )

    assert batch.report_json["righe_scartate_comune_non_risolto"] == 0
    assert batch.report_json["righe_senza_match_particella"] == 0
    assert batch.report_json["particelle_aggiornate"] == 3
    assert updated_oristano.num_distretto == "40"
    assert updated_simaxis.num_distretto == "41"
    assert updated_arcidano.num_distretto == "42"
    db.close()


def test_distretti_excel_analysis_endpoint_returns_not_found_rows(tmp_path: Path) -> None:
    payload = build_distretti_excel_bytes(
        [
            {
                "ANNO": "2025",
                "N_DISTRETTO": "26",
                "DISTRETTO": "Sassu",
                "COMUNE": "ARBOREA",
                "SEZIONE": None,
                "FOGLIO": "999",
                "PARTIC": "888",
                "SUB": None,
            }
        ]
    )
    source_path = tmp_path / "distretti-analysis.xlsx"
    source_path.write_bytes(payload)

    db = TestingSessionLocal()
    batch = CatImportBatch(
        filename="distretti-analysis.xlsx",
        tipo="distretti_excel",
        status="completed",
        righe_totali=1,
        righe_importate=0,
        righe_anomalie=1,
        created_by=1,
        report_json={"source_file_path": str(source_path)},
    )
    db.add(batch)
    db.commit()
    batch_id = batch.id
    db.close()

    response = client.get(
        f"/catasto/import/{batch_id}/distretti-excel/analysis?tipo=NOT_FOUND&page=1&page_size=50",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload_json = response.json()
    assert payload_json["total"] == 1
    assert payload_json["items"][0]["esito"] == "NOT_FOUND"
    assert payload_json["items"][0]["foglio_input"] == "999"
    assert payload_json["items"][0]["particella_input"] == "888"
    assert payload_json["counters"]["NOT_FOUND"] == 1


def test_distretti_excel_analysis_endpoint_returns_duplicate_conflicts(tmp_path: Path) -> None:
    payload = build_distretti_excel_bytes(
        [
            {
                "ANNO": "2025",
                "N_DISTRETTO": "26",
                "DISTRETTO": "Sassu",
                "COMUNE": "ARBOREA",
                "SEZIONE": None,
                "FOGLIO": "5",
                "PARTIC": "120",
                "SUB": "1",
            },
            {
                "ANNO": "2025",
                "N_DISTRETTO": "30",
                "DISTRETTO": "Nuovo Distretto",
                "COMUNE": "ARBOREA",
                "SEZIONE": None,
                "FOGLIO": "5",
                "PARTIC": "120",
                "SUB": "9",
            },
        ]
    )
    source_path = tmp_path / "distretti-conflict.xlsx"
    source_path.write_bytes(payload)

    db = TestingSessionLocal()
    batch = CatImportBatch(
        filename="distretti-conflict.xlsx",
        tipo="distretti_excel",
        status="completed",
        righe_totali=2,
        righe_importate=1,
        righe_anomalie=1,
        created_by=1,
        report_json={"source_file_path": str(source_path)},
    )
    db.add(batch)
    db.commit()
    batch_id = batch.id
    db.close()

    response = client.get(
        f"/catasto/import/{batch_id}/distretti-excel/analysis?tipo=DUPLICATE_CONFLICT&page=1&page_size=50",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload_json = response.json()
    assert payload_json["total"] == 1
    assert payload_json["items"][0]["esito"] == "DUPLICATE_CONFLICT"
    assert payload_json["items"][0]["current_num_distretti"] == ["26"]
    assert payload_json["counters"]["DUPLICATE_CONFLICT"] == 1


def test_distretti_excel_analysis_endpoint_returns_409_when_source_file_is_missing() -> None:
    db = TestingSessionLocal()
    batch = CatImportBatch(
        filename="missing-source.xlsx",
        tipo="distretti_excel",
        status="completed",
        righe_totali=1,
        righe_importate=0,
        righe_anomalie=1,
        created_by=1,
        report_json={"source_file_path": "/tmp/does-not-exist-anymore.xlsx"},
    )
    db.add(batch)
    db.commit()
    batch_id = batch.id
    db.close()

    response = client.get(
        f"/catasto/import/{batch_id}/distretti-excel/analysis?page=1&page_size=50",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert "Reimporta il file" in response.json()["detail"]


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


def test_distretto_geojson_endpoint_returns_feature() -> None:
    raw_conn = engine.raw_connection()
    try:
        raw_conn.create_function(
            "AsGeoJSON",
            1,
            lambda value: '{"type":"MultiPolygon","coordinates":[]}' if value else None,
        )
    finally:
        raw_conn.close()

    db = TestingSessionLocal()
    try:
        distretto = db.query(CatDistretto).filter(CatDistretto.num_distretto == "10").one()
        distretto.geometry = "SRID=4326;MULTIPOLYGON(((8.58 39.78,8.581 39.78,8.581 39.781,8.58 39.781,8.58 39.78)))"
        db.add(distretto)
        db.commit()
        distretto_id = str(distretto.id)
    finally:
        db.close()

    response = client.get(f"/catasto/distretti/{distretto_id}/geojson", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "Feature"
    assert payload["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert payload["properties"]["num_distretto"] == "10"


def test_distretto_geojson_endpoint_returns_404_without_geometry() -> None:
    db = TestingSessionLocal()
    try:
        distretto = db.query(CatDistretto).filter(CatDistretto.num_distretto == "10").one()
        distretto.geometry = None
        db.add(distretto)
        db.commit()
        distretto_id = str(distretto.id)
    finally:
        db.close()

    response = client.get(f"/catasto/distretti/{distretto_id}/geojson", headers=auth_headers())

    assert response.status_code == 404
    assert "geometria" in response.json()["detail"].lower()


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
    assert utenze_response.json()[0]["subject_id"] is not None
    assert utenze_response.json()[0]["subject_display_name"] == "Fenu Denise"
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


def test_particella_utenze_response_keeps_subject_unresolved_when_identifier_is_ambiguous() -> None:
    db = TestingSessionLocal()
    particella_id: UUID
    try:
        particella = db.query(CatParticella).filter(CatParticella.foglio == "5", CatParticella.particella == "120").one()
        particella_id = particella.id
        comune = db.query(CatComune).filter(CatComune.cod_comune_capacitas == 165).one()
        batch = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one()
        ambiguous_cf = "AMBGCF80A01H501U"

        utenza = CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2025,
            cco="UT-AMB-001",
            comune_id=comune.id,
            cod_comune_capacitas=165,
            nome_comune="Arborea",
            foglio="5",
            particella="120",
            particella_id=particella.id,
            codice_fiscale=ambiguous_cf,
            denominazione="Identificatore ambiguo",
        )
        person_subject = AnagraficaSubject(
            subject_type="person",
            status="active",
            source_system="manual",
            source_external_id="amb-person",
            source_name_raw="Ambiguo Persona",
            requires_review=False,
        )
        company_subject = AnagraficaSubject(
            subject_type="company",
            status="active",
            source_system="manual",
            source_external_id="amb-company",
            source_name_raw="Ambigua SRL",
            requires_review=False,
        )
        db.add_all([utenza, person_subject, company_subject])
        db.flush()
        db.add(
            AnagraficaPerson(
                subject_id=person_subject.id,
                cognome="Ambiguo",
                nome="Persona",
                codice_fiscale=ambiguous_cf,
            )
        )
        db.add(
            AnagraficaCompany(
                subject_id=company_subject.id,
                ragione_sociale="Ambigua SRL",
                partita_iva="12345678901",
                codice_fiscale=ambiguous_cf,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(f"/catasto/particelle/{particella_id}/utenze?anno=2025", headers=auth_headers())

    assert response.status_code == 200
    ambiguous_row = next(item for item in response.json() if item["cco"] == "UT-AMB-001")
    assert ambiguous_row["subject_id"] is None
    assert ambiguous_row["subject_display_name"] is None


def test_particella_consorzio_filters_out_zero_share_owner_titles() -> None:
    db = TestingSessionLocal()
    particella_id: UUID
    try:
        particella = db.query(CatParticella).filter(CatParticella.foglio == "5", CatParticella.particella == "120").one()
        particella_id = particella.id
        comune = db.query(CatComune).filter(CatComune.cod_comune_capacitas == 165).one()
        batch = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one()
        utenza = CatUtenzaIrrigua(
            import_batch_id=batch.id,
            anno_campagna=2025,
            cco="UT-FILTER-001",
            comune_id=comune.id,
            cod_comune_capacitas=165,
            nome_comune="Arborea",
            foglio="5",
            particella="120",
            subalterno="1",
            particella_id=particella.id,
            codice_fiscale="FILTER01A01H501Z",
            denominazione="Utenza filtro titoli",
        )
        db.add(utenza)
        db.flush()

        unit = CatConsorzioUnit(
            particella_id=particella.id,
            comune_id=comune.id,
            cod_comune_capacitas=165,
            foglio="5",
            particella="120",
            subalterno="1",
            descrizione="Filtro titoli",
        )
        db.add(unit)
        db.flush()

        db.add(
            CatConsorzioOccupancy(
                unit_id=unit.id,
                utenza_id=utenza.id,
                cco="UT-FILTER-001",
                fra="38",
                ccs="00000",
                pvc="097",
                com="165",
                source_type="capacitas_terreni",
                relationship_type="utilizzatore_reale",
                is_current=True,
            )
        )

        now = datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc)
        db.add_all(
            [
                CatUtenzaIntestatario(
                    utenza_id=utenza.id,
                    idxana="IDX-ZERO",
                    anno_riferimento=2025,
                    codice_fiscale="ZERO01A01H501Z",
                    denominazione="Residuo Zero",
                    titoli="Proprieta` 0/0",
                    collected_at=now,
                ),
                CatUtenzaIntestatario(
                    utenza_id=utenza.id,
                    idxana="IDX-VALID",
                    anno_riferimento=2025,
                    codice_fiscale="VALID01A01H501Z",
                    denominazione="Proprietario Valido",
                    titoli="Proprieta` 1/1",
                    collected_at=now,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(f"/catasto/particelle/{particella_id}/consorzio", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    filtered_unit = next(
        unit for unit in payload["units"] if any(occ["cco"] == "UT-FILTER-001" for occ in unit["occupancies"])
    )
    owner_rows = filtered_unit["intestatari_proprietari"]
    assert len(owner_rows) == 1
    assert owner_rows[0]["denominazione"] == "Proprietario Valido"
    assert owner_rows[0]["titoli"] == "Proprieta` 1/1"


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


def test_particelle_endpoint_supports_numeric_cf_search() -> None:
    db = TestingSessionLocal()
    try:
        seed_anomalie_workflow_data(db)
    finally:
        db.close()

    response = client.get(
        "/catasto/particelle/?cf=00588230953",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["cod_comune_capacitas"] == 212
    assert payload[0]["foglio"] == "9"
    assert payload[0]["particella"] == "401"


def test_particelle_endpoint_supports_partial_cf_search() -> None:
    db = TestingSessionLocal()
    try:
        seed_anomalie_workflow_data(db)
    finally:
        db.close()

    response = client.get(
        "/catasto/particelle/?search=RSS",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["cod_comune_capacitas"] == 165
    assert payload[0]["foglio"] == "5"
    assert payload[0]["particella"] == "120"


def test_particelle_endpoint_supports_intestatario_search_on_annual_owners() -> None:
    db = TestingSessionLocal()
    try:
        seed_anomalie_workflow_data(db)
        utenza = db.query(CatUtenzaIrrigua).filter(CatUtenzaIrrigua.cco == "UT-ANOM-10-2025").one()
        now = datetime.now(timezone.utc)
        db.add(
            CatUtenzaIntestatario(
                utenza_id=utenza.id,
                idxana="IDX-ANA-PART-SEARCH",
                idxesa="IDX-ESA-PART-SEARCH",
                history_id="HIST-PART-SEARCH",
                anno_riferimento=2025,
                data_agg=now,
                codice_fiscale="VRDLGI80A01H501V",
                denominazione="Verdi Luigi",
                titoli="Proprieta` 1/1",
                deceduto=False,
                collected_at=now,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/catasto/particelle/?intestatario=Verdi%20Luigi",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["cod_comune_capacitas"] == 165
    assert payload[0]["foglio"] == "5"
    assert payload[0]["particella"] == "120"


def test_particelle_endpoint_supports_solo_a_ruolo_filter() -> None:
    db = TestingSessionLocal()
    try:
        particella = db.query(CatParticella).filter(CatParticella.cod_comune_capacitas == 165).one()
        ruolo_job = RuoloImportJob(anno_tributario=2025, status="completed")
        db.add(ruolo_job)
        db.flush()
        avviso = RuoloAvviso(
            import_job_id=ruolo_job.id,
            codice_cnc="CNC-SEED-001",
            anno_tributario=2025,
        )
        db.add(avviso)
        db.flush()
        partita = RuoloPartita(
            avviso_id=avviso.id,
            codice_partita="P-SEED-001",
            comune_nome="Arborea",
        )
        db.add(partita)
        db.flush()
        db.add(
            RuoloParticella(
                partita_id=partita.id,
                anno_tributario=2025,
                foglio=particella.foglio,
                particella=particella.particella,
                subalterno=particella.subalterno,
                catasto_parcel_id=particella.id,
            )
        )
        db.commit()
    finally:
        db.close()

    filtered_response = client.get(
        "/catasto/particelle/?solo_a_ruolo=true",
        headers=auth_headers(),
    )
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert len(filtered_payload) == 1
    assert filtered_payload[0]["cod_comune_capacitas"] == 165
    assert filtered_payload[0]["foglio"] == "5"
    assert filtered_payload[0]["particella"] == "120"

    non_matching_response = client.get(
        "/catasto/particelle/?solo_a_ruolo=true&comune=212",
        headers=auth_headers(),
    )
    assert non_matching_response.status_code == 200
    assert non_matching_response.json() == []


def test_particelle_endpoint_supports_solo_con_anagrafica_filter() -> None:
    db = TestingSessionLocal()
    try:
        particella_con_anagrafica = db.query(CatParticella).filter(CatParticella.cod_comune_capacitas == 165).one()
        db.add(
            CatParticella(
                comune_id=particella_con_anagrafica.comune_id,
                cod_comune_capacitas=165,
                codice_catastale="A357",
                nome_comune="Arborea",
                foglio="6",
                particella="601",
                is_current=True,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/catasto/particelle/?solo_con_anagrafica=true",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["foglio"] == "5"
    assert payload[0]["particella"] == "120"
    assert payload[0]["ha_anagrafica"] is True


def test_particelle_endpoint_direct_lookup_keeps_particella_without_anagrafica_visible() -> None:
    db = TestingSessionLocal()
    try:
        particella_con_anagrafica = db.query(CatParticella).filter(CatParticella.cod_comune_capacitas == 165).one()
        db.add(
            CatParticella(
                comune_id=particella_con_anagrafica.comune_id,
                cod_comune_capacitas=165,
                codice_catastale="A357",
                nome_comune="Arborea",
                foglio="6",
                particella="602",
                is_current=True,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/catasto/particelle/?solo_con_anagrafica=true&comune=165&foglio=6&particella=602",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["foglio"] == "6"
    assert payload[0]["particella"] == "602"
    assert payload[0]["ha_anagrafica"] is False
    assert payload[0]["utenza_cf"] is None
    assert payload[0]["utenza_denominazione"] is None


def test_particelle_endpoint_solo_a_ruolo_falls_back_to_previous_year_when_filtered_current_year_is_missing() -> None:
    db = TestingSessionLocal()
    try:
        particella = db.query(CatParticella).filter(CatParticella.cod_comune_capacitas == 165).one()
        altra_particella = CatParticella(
            comune_id=particella.comune_id,
            cod_comune_capacitas=212,
            codice_catastale="B314",
            nome_comune="Cabras",
            foglio="9",
            particella="900",
            is_current=True,
        )
        db.add(altra_particella)
        db.flush()

        ruolo_job_2024 = RuoloImportJob(anno_tributario=2024, status="completed")
        ruolo_job_2025 = RuoloImportJob(anno_tributario=2025, status="completed")
        db.add_all([ruolo_job_2024, ruolo_job_2025])
        db.flush()

        avviso_2024 = RuoloAvviso(import_job_id=ruolo_job_2024.id, codice_cnc="CNC-SEED-2024", anno_tributario=2024)
        avviso_2025 = RuoloAvviso(import_job_id=ruolo_job_2025.id, codice_cnc="CNC-SEED-2025", anno_tributario=2025)
        db.add_all([avviso_2024, avviso_2025])
        db.flush()

        partita_2024 = RuoloPartita(avviso_id=avviso_2024.id, codice_partita="P-SEED-2024", comune_nome="Arborea")
        partita_2025 = RuoloPartita(avviso_id=avviso_2025.id, codice_partita="P-SEED-2025", comune_nome="Cabras")
        db.add_all([partita_2024, partita_2025])
        db.flush()

        db.add_all(
            [
                RuoloParticella(
                    partita_id=partita_2024.id,
                    anno_tributario=2024,
                    foglio=particella.foglio,
                    particella=particella.particella,
                    subalterno=particella.subalterno,
                    catasto_parcel_id=particella.id,
                ),
                RuoloParticella(
                    partita_id=partita_2025.id,
                    anno_tributario=2025,
                    foglio=altra_particella.foglio,
                    particella=altra_particella.particella,
                    catasto_parcel_id=altra_particella.id,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/catasto/particelle/?solo_a_ruolo=true&comune=165",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["cod_comune_capacitas"] == 165
    assert payload[0]["foglio"] == "5"
    assert payload[0]["particella"] == "120"


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


def test_bulk_search_anagrafica_supports_codice_catastale_in_comune_column() -> None:
    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={
            "rows": [
                {"row_index": 2, "comune": "A357", "foglio": "5", "particella": "120"},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"]
    assert len(payload) == 1
    assert payload[0]["esito"] == "FOUND"
    assert payload[0]["match"]["codice_catastale"] == "A357"
    assert payload[0]["match"]["cod_comune_capacitas"] == 165
    assert payload[0]["match"]["foglio"] == "5"
    assert payload[0]["match"]["particella"] == "120"


def test_bulk_search_presente_consorzio_true_when_utenza_without_consorzio_unit() -> None:
    """Senza CatConsorzioUnit ma con utenza di campagna il flag export non deve dire 'non presente'."""
    db = TestingSessionLocal()
    try:
        batch = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one()
        comune = db.query(CatComune).filter(CatComune.cod_comune_capacitas == 165).one()
        particella = CatParticella(
            comune=comune,
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="Arborea",
            foglio="99",
            particella="777",
            subalterno=None,
            num_distretto="10",
            nome_distretto="Distretto 10",
            is_current=True,
            superficie_mq=500,
        )
        db.add(particella)
        db.flush()
        db.add(
            CatUtenzaIrrigua(
                import_batch_id=batch.id,
                anno_campagna=2025,
                cco="UT-NO-UNIT-001",
                comune=comune,
                cod_comune_capacitas=165,
                num_distretto=10,
                nome_comune="Arborea",
                foglio="99",
                particella="777",
                particella_id=particella.id,
                sup_catastale_mq=500,
                sup_irrigabile_mq=400,
                imponibile_sf=600,
                ind_spese_fisse=1.5,
                aliquota_0648=0.1,
                importo_0648=60,
                aliquota_0985=0.2,
                importo_0985=120,
                codice_fiscale="BNCCCC80A01H501Z",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={"rows": [{"row_index": 0, "comune": "165", "foglio": "99", "particella": "777"}]},
    )
    assert response.status_code == 200
    match = response.json()["results"][0]["match"]
    assert match["presente_in_catasto_consorzio"] is True


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


def test_bulk_search_anagrafica_uses_exact_cert_context_for_reused_cco() -> None:
    db = TestingSessionLocal()
    try:
        batch = CatImportBatch(filename="test.xlsx", tipo="test", status="completed")
        db.add(batch)
        db.flush()
        comune_uras = CatComune(
            nome_comune="Uras",
            codice_catastale="L496",
            cod_comune_capacitas=289,
            codice_comune_formato_numerico=115081,
            codice_comune_numerico_2017_2025=95078,
            nome_comune_legacy="Uras",
            cod_provincia=115,
            sigla_provincia="OR",
            regione="Sardegna",
        )
        db.add(comune_uras)
        db.flush()
        particella = CatParticella(
            comune_id=comune_uras.id,
            cod_comune_capacitas=289,
            codice_catastale="L496",
            nome_comune="Uras",
            foglio="17",
            particella="244",
            subalterno=None,
            is_current=True,
        )
        db.add(particella)
        db.flush()
        unit = CatConsorzioUnit(
            particella_id=particella.id,
            comune_id=comune_uras.id,
            cod_comune_capacitas=289,
            source_comune_label="Uras",
            foglio="17",
            particella="244",
            subalterno=None,
            is_active=True,
        )
        db.add(unit)
        db.flush()
        db.add(
            CatUtenzaIrrigua(
                import_batch_id=batch.id,
                anno_campagna=2025,
                cco="000000074",
                comune_id=comune_uras.id,
                cod_comune_capacitas=289,
                nome_comune="Uras",
                foglio="17",
                particella="244",
                particella_id=particella.id,
                denominazione="Comune Di Uras",
                codice_fiscale="80000590952",
            )
        )
        db.add(
            CatConsorzioOccupancy(
                unit_id=unit.id,
                cco="000000074",
                com="289",
                pvc="097",
                fra="38",
                ccs="00000",
                source_type="capacitas_terreni",
                relationship_type="utilizzatore_reale",
                is_current=True,
            )
        )
        wrong_cert = CatCapacitasCertificato(
            cco="000000074",
            com="165",
            pvc="097",
            fra="31",
            ccs="00000",
            collected_at=datetime(2026, 5, 5, 6, 0, tzinfo=timezone.utc),
        )
        right_cert = CatCapacitasCertificato(
            cco="000000074",
            com="289",
            pvc="097",
            fra="38",
            ccs="00000",
            collected_at=datetime(2026, 4, 30, 13, 37, tzinfo=timezone.utc),
        )
        db.add_all([wrong_cert, right_cert])
        db.flush()
        db.add(
            CatCapacitasIntestatario(
                certificato_id=wrong_cert.id,
                denominazione="Fiandri Giuseppe",
                codice_fiscale="FNDGPP80A01H501U",
                collected_at=wrong_cert.collected_at,
            )
        )
        db.add(
            CatCapacitasIntestatario(
                certificato_id=right_cert.id,
                denominazione="Comune Di Uras",
                codice_fiscale="80000590952",
                collected_at=right_cert.collected_at,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={"rows": [{"row_index": 1, "comune": "Uras", "foglio": "17", "particella": "244"}]},
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]["match"]
    assert payload["cert_com"] == "289"
    assert payload["cert_fra"] == "38"


def test_bulk_search_anagrafica_uses_latest_utenza_context_when_cco_exists_on_multiple_comuni() -> None:
    db = TestingSessionLocal()
    try:
        batch = CatImportBatch(filename="test.xlsx", tipo="test", status="completed")
        db.add(batch)
        db.flush()
        comune_uras = CatComune(
            nome_comune="Uras",
            codice_catastale="L496",
            cod_comune_capacitas=289,
            codice_comune_formato_numerico=115081,
            codice_comune_numerico_2017_2025=95078,
            nome_comune_legacy="Uras",
            cod_provincia=115,
            sigla_provincia="OR",
            regione="Sardegna",
        )
        db.add(comune_uras)
        db.flush()
        particella = CatParticella(
            comune_id=comune_uras.id,
            cod_comune_capacitas=289,
            codice_catastale="L496",
            nome_comune="Uras",
            foglio="17",
            particella="245",
            subalterno=None,
            is_current=True,
        )
        db.add(particella)
        db.flush()
        db.add(
            CatUtenzaIrrigua(
                import_batch_id=batch.id,
                anno_campagna=2025,
                cco="000000252",
                comune_id=comune_uras.id,
                cod_comune_capacitas=289,
                cod_frazione=38,
                nome_comune="Uras",
                foglio="17",
                particella="245",
                particella_id=particella.id,
                denominazione="Utente Uras Corretto",
                codice_fiscale="RSSMRA80A01H501U",
            )
        )
        wrong_cert = CatCapacitasCertificato(
            cco="000000252",
            com="165",
            pvc="097",
            fra="31",
            ccs="00000",
            collected_at=datetime(2026, 5, 7, 9, 0, tzinfo=timezone.utc),
        )
        right_cert = CatCapacitasCertificato(
            cco="000000252",
            com="289",
            pvc="097",
            fra="38",
            ccs="00000",
            collected_at=datetime(2026, 5, 6, 9, 0, tzinfo=timezone.utc),
        )
        db.add_all([wrong_cert, right_cert])
        db.flush()
        db.add(
            CatCapacitasIntestatario(
                certificato_id=wrong_cert.id,
                denominazione="Utente Arborea Errato",
                codice_fiscale="RWRRRA80A01H501U",
                collected_at=wrong_cert.collected_at,
            )
        )
        db.add(
            CatCapacitasIntestatario(
                certificato_id=right_cert.id,
                denominazione="Utente Uras Corretto",
                codice_fiscale="RSSMRA80A01H501U",
                collected_at=right_cert.collected_at,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={"rows": [{"row_index": 1, "comune": "Uras", "foglio": "17", "particella": "245"}]},
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]["match"]
    assert payload["cert_com"] == "289"
    assert payload["cert_fra"] == "38"


def test_bulk_search_anagrafica_sub_matches_preserve_case_variants() -> None:
    db = TestingSessionLocal()
    try:
        comune = CatComune(
            nome_comune="Santa Giusta",
            codice_catastale="I205",
            cod_comune_capacitas=239,
            codice_comune_formato_numerico=115048,
            codice_comune_numerico_2017_2025=95048,
            nome_comune_legacy="Santa Giusta",
            cod_provincia=115,
            sigla_provincia="OR",
            regione="Sardegna",
        )
        db.add(comune)
        db.flush()
        particella = CatParticella(
            comune_id=comune.id,
            cod_comune_capacitas=239,
            codice_catastale="I205",
            nome_comune="Santa Giusta",
            foglio="20",
            particella="265",
            subalterno=None,
            is_current=True,
        )
        db.add(particella)
        db.flush()
        unit_upper = CatConsorzioUnit(
            particella_id=None,
            comune_id=comune.id,
            cod_comune_capacitas=239,
            source_comune_label="Santa Giusta",
            foglio="20",
            particella="265",
            subalterno="A",
            is_active=True,
        )
        unit_lower = CatConsorzioUnit(
            particella_id=None,
            comune_id=comune.id,
            cod_comune_capacitas=239,
            source_comune_label="Santa Giusta",
            foglio="20",
            particella="265",
            subalterno="a",
            is_active=True,
        )
        db.add_all([unit_upper, unit_lower])
        db.flush()
        db.add(
            CatConsorzioOccupancy(
                unit_id=unit_upper.id,
                cco="014000929",
                com="239",
                pvc="097",
                fra="14",
                ccs="00000",
                source_type="capacitas_terreni",
                relationship_type="utilizzatore_reale",
                is_current=False,
                valid_from=date(2007, 1, 1),
            )
        )
        db.add(
            CatConsorzioOccupancy(
                unit_id=unit_lower.id,
                cco="0A0621305",
                com="239",
                pvc="097",
                fra="14",
                ccs="00000",
                source_type="capacitas_terreni",
                relationship_type="utilizzatore_reale",
                is_current=True,
                valid_from=date(2011, 1, 1),
            )
        )
        cert = CatCapacitasCertificato(
            cco="0A0621305",
            com="239",
            pvc="097",
            fra="14",
            ccs="00000",
            collected_at=datetime.now(timezone.utc),
        )
        db.add(cert)
        db.flush()
        db.add(
            CatCapacitasIntestatario(
                certificato_id=cert.id,
                denominazione="Figus Maddalena",
                codice_fiscale="FGSMDL70A41H501U",
                collected_at=cert.collected_at,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={"rows": [{"row_index": 1, "comune": "Santa Giusta", "foglio": "20", "particella": "265"}]},
    )

    assert response.status_code == 200
    matches = response.json()["results"][0]["matches"]
    assert len(matches) == 2
    assert sorted((match["subalterno"], match["utenza_latest"]["cco"]) for match in matches) == [
        ("A", "014000929"),
        ("a", "0A0621305"),
    ]


def test_bulk_search_anagrafica_sub_historical_falls_back_to_current_base_owner() -> None:
    db = TestingSessionLocal()
    try:
        comune = CatComune(
            nome_comune="Santa Giusta",
            codice_catastale="I205",
            cod_comune_capacitas=239,
            codice_comune_formato_numerico=115048,
            codice_comune_numerico_2017_2025=95048,
            nome_comune_legacy="Santa Giusta",
            cod_provincia=115,
            sigla_provincia="OR",
            regione="Sardegna",
        )
        db.add(comune)
        db.flush()
        particella = CatParticella(
            comune_id=comune.id,
            cod_comune_capacitas=239,
            codice_catastale="I205",
            nome_comune="Santa Giusta",
            foglio="20",
            particella="184",
            subalterno=None,
            is_current=True,
        )
        db.add(particella)
        db.flush()
        db.add(
            CatUtenzaIrrigua(
                anno_campagna=2025,
                cco="0A1260895",
                comune_id=comune.id,
                cod_comune_capacitas=239,
                nome_comune="Santa Giusta",
                foglio="20",
                particella="184",
                particella_id=particella.id,
                denominazione="D'ettorre Carmine",
                codice_fiscale="DTTCMN54M12H398A",
            )
        )
        base_cert = CatCapacitasCertificato(
            cco="0A1260895",
            com="239",
            pvc="097",
            fra="14",
            ccs="00000",
            collected_at=datetime.now(timezone.utc),
        )
        db.add(base_cert)
        db.flush()
        db.add(
            CatCapacitasIntestatario(
                certificato_id=base_cert.id,
                denominazione="D'ettorre Carmine",
                codice_fiscale="DTTCMN54M12H398A",
                collected_at=base_cert.collected_at,
            )
        )
        unit_a = CatConsorzioUnit(
            comune_id=comune.id,
            cod_comune_capacitas=239,
            source_comune_label="Santa Giusta",
            foglio="20",
            particella="184",
            subalterno="A",
            is_active=True,
        )
        db.add(unit_a)
        db.flush()
        db.add(
            CatConsorzioOccupancy(
                unit_id=unit_a.id,
                cco="014000896",
                com="239",
                pvc="097",
                fra="14",
                ccs="00000",
                source_type="capacitas_terreni",
                relationship_type="utilizzatore_reale",
                is_current=False,
                valid_from=date(2021, 1, 1),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={"rows": [{"row_index": 1, "comune": "Santa Giusta", "foglio": "20", "particella": "184"}]},
    )

    assert response.status_code == 200
    matches = response.json()["results"][0]["matches"]
    assert len(matches) == 1
    assert matches[0]["subalterno"] == "A"
    assert matches[0]["utenza_latest"]["cco"] == "0A1260895"
    assert matches[0]["intestatari"][0]["denominazione"] == "D'ettorre Carmine"
    assert matches[0]["note"] == "Presenti dati non aggiornati/storici del sub: intestatario corrente derivato dalla particella base"


def test_bulk_search_anagrafica_live_enriches_sub_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    try:
        comune = CatComune(
            nome_comune="Santa Giusta",
            codice_catastale="I205",
            cod_comune_capacitas=239,
            codice_comune_formato_numerico=115048,
            codice_comune_numerico_2017_2025=95048,
            nome_comune_legacy="Santa Giusta",
            cod_provincia=115,
            sigla_provincia="OR",
            regione="Sardegna",
        )
        db.add(comune)
        db.flush()
        particella = CatParticella(
            comune_id=comune.id,
            cod_comune_capacitas=239,
            codice_catastale="I205",
            nome_comune="Santa Giusta",
            foglio="20",
            particella="265",
            subalterno=None,
            is_current=True,
        )
        db.add(particella)
        db.flush()
        unit = CatConsorzioUnit(
            comune_id=comune.id,
            cod_comune_capacitas=239,
            source_comune_label="Santa Giusta",
            foglio="20",
            particella="265",
            subalterno="c",
            is_active=True,
        )
        db.add(unit)
        db.flush()
        db.add(
            CatConsorzioOccupancy(
                unit_id=unit.id,
                cco="014000215",
                com="239",
                pvc="097",
                fra="14",
                ccs="00000",
                source_type="capacitas_terreni",
                relationship_type="utilizzatore_reale",
                is_current=True,
                valid_from=date(2007, 1, 1),
            )
        )
        stale_cert = CatCapacitasCertificato(
            cco="014000215",
            com="239",
            pvc="097",
            fra="14",
            ccs="00000",
            collected_at=datetime.now(timezone.utc),
        )
        db.add(stale_cert)
        db.flush()
        db.add(
            CatCapacitasIntestatario(
                certificato_id=stale_cert.id,
                denominazione="Consorzio Industriale Provinciale Oristanese",
                codice_fiscale="80003430958",
                collected_at=stale_cert.collected_at,
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
        assert kwargs == {"cco": "014000215", "com": "239", "pvc": "097", "fra": "14", "ccs": "00000"}
        return CapacitasTerrenoCertificato(
            cco="014000215",
            com="239",
            pvc="097",
            fra="14",
            ccs="00000",
            intestatari=[
                CapacitasIntestatario(
                    idxana="IDX-FIGUS",
                    idxesa="IDX-ESA-FIGUS",
                    codice_fiscale="FGSMDL70A41H501U",
                    denominazione="Figus Maddalena",
                    luogo_nascita="Oristano",
                )
            ],
        )

    async def fake_fetch_current_anagrafica_detail(self, *, idxana: str, idxesa: str) -> CapacitasAnagraficaDetail:
        assert idxana == "IDX-FIGUS"
        assert idxesa == "IDX-ESA-FIGUS"
        return CapacitasAnagraficaDetail(
            idxana=idxana,
            idxesa=idxesa,
            cognome="Figus",
            nome="Maddalena",
            denominazione="Figus Maddalena",
            codice_fiscale="FGSMDL70A41H501U",
            luogo_nascita="Oristano",
            data_nascita=date(1970, 1, 1),
            residenza_localita="Santa Giusta",
            residenza_indirizzo="Via Roma",
            residenza_civico="1",
            residenza_cap="09096",
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
            "rows": [{"row_index": 1, "comune": "Santa Giusta", "foglio": "20", "particella": "265"}],
        },
    )

    assert response.status_code == 200
    matches = response.json()["results"][0]["matches"]
    assert len(matches) == 1
    assert matches[0]["subalterno"] == "c"
    assert matches[0]["intestatari"][0]["denominazione"] == "Figus Maddalena"


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


def test_bulk_search_anagrafica_syncs_live_terreni_and_persists_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    try:
        comune_oristano = CatComune(
            nome_comune="Oristano",
            codice_catastale="G113",
            cod_comune_capacitas=200,
            codice_comune_formato_numerico=115057,
            codice_comune_numerico_2017_2025=95038,
            nome_comune_legacy="Oristano",
            cod_provincia=115,
            sigla_provincia="OR",
            regione="Sardegna",
        )
        db.add(comune_oristano)
        db.flush()
        db.add(
            CatParticella(
                comune_id=comune_oristano.id,
                cod_comune_capacitas=200,
                codice_catastale="G113",
                nome_comune="Oristano",
                sezione_catastale="A",
                foglio="24",
                particella="191",
                subalterno=None,
                num_distretto="20",
                nome_distretto="Distretto 20",
                is_current=True,
                superficie_mq=430,
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

    async def fake_search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        assert query == "Oristano"
        return [
            CapacitasLookupOption(id="04", display="04 DONIGALA FENUGHEDU*ORISTANO"),
            CapacitasLookupOption(id="11", display="11 ORISTANO*ORISTANO"),
        ]

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        assert request.foglio == "24"
        assert request.particella == "191"
        if request.frazione_id != "11":
            raise RuntimeError("Particella non trovata")
        if request.sezione == "A":
            return CapacitasTerreniSearchResult(total=0, rows=[])
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "or-live-row-191",
                    "PVC": "097",
                    "COM": "200",
                    "CCO": "011000009",
                    "FRA": "11",
                    "CCS": "00000",
                    "Foglio": "24",
                    "Partic": "191",
                    "Sub": "",
                    "Sez": "A",
                    "Anno": "2017",
                    "Belfiore": "G113",
                    "Ta_ext": " 7",
                }
            ],
        )

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        assert kwargs["cco"] == "011000009"
        return CapacitasTerrenoCertificato(
            cco="011000009",
            com="200",
            pvc="097",
            fra="11",
            ccs="00000",
            intestatari=[
                CapacitasIntestatario(
                    idxana="IDX-OR-191",
                    idxesa="IDX-ESA-OR-191",
                    codice_fiscale="VRDLGI80A01G113Z",
                    denominazione="Verdi Luigi",
                    comune_residenza="Oristano",
                    cap="09170",
                    residenza="09170 Oristano (OR) - Via Cagliari 12",
                )
            ],
        )

    async def fake_fetch_current_anagrafica_detail(self, *, idxana: str, idxesa: str) -> CapacitasAnagraficaDetail:
        assert idxana == "IDX-OR-191"
        assert idxesa == "IDX-ESA-OR-191"
        return CapacitasAnagraficaDetail(
            idxana=idxana,
            idxesa=idxesa,
            cognome="Verdi",
            nome="Luigi",
            denominazione="Verdi Luigi",
            codice_fiscale="VRDLGI80A01G113Z",
            luogo_nascita="Oristano",
            data_nascita=date(1980, 1, 1),
            residenza_belfiore="Oristano",
            residenza_localita="Oristano",
            residenza_toponimo="Via",
            residenza_indirizzo="Cagliari",
            residenza_civico="12",
            residenza_cap="09170",
        )

    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.pick_credential", lambda db, credential_id: (SimpleNamespace(id=1, username="live-user"), "secret"))
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_used", lambda db, credential_id: None)
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_error", lambda db, credential_id, error: None)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
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
            "rows": [{"row_index": 1, "comune": "Oristano", "sezione": "A", "foglio": "24", "particella": "191"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["esito"] == "FOUND"
    assert payload["match"]["utenza_latest"]["cco"] == "011000009"
    assert payload["match"]["presente_in_catasto_consorzio"] is True
    assert payload["match"]["intestatari"][0]["codice_fiscale"] == "VRDLGI80A01G113Z"

    db = TestingSessionLocal()
    try:
        particella = db.query(CatParticella).filter(
            CatParticella.nome_comune == "Oristano",
            CatParticella.sezione_catastale == "A",
            CatParticella.foglio == "24",
            CatParticella.particella == "191",
        ).one()
        unit = db.query(CatConsorzioUnit).filter(CatConsorzioUnit.particella_id == particella.id).one()
        occupancy = db.query(CatConsorzioOccupancy).filter(CatConsorzioOccupancy.unit_id == unit.id).one()
        terreno_row = db.query(CatCapacitasTerrenoRow).filter(CatCapacitasTerrenoRow.unit_id == unit.id).one()
        certificato = db.query(CatCapacitasCertificato).filter(CatCapacitasCertificato.cco == "011000009").one()
        assert occupancy.cco == "011000009"
        assert occupancy.com == "200"
        assert occupancy.fra == "11"
        assert terreno_row.particella == "191"
        assert certificato.com == "200"
    finally:
        db.close()


def test_bulk_search_anagrafica_backfills_certificato_for_existing_cco_without_link_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    try:
        batch = db.query(CatImportBatch).filter(CatImportBatch.hash_file == "seed-hash").one()
        comune_oristano = CatComune(
            nome_comune="Oristano",
            codice_catastale="G113",
            cod_comune_capacitas=200,
            codice_comune_formato_numerico=115057,
            codice_comune_numerico_2017_2025=95038,
            nome_comune_legacy="Oristano",
            cod_provincia=115,
            sigla_provincia="OR",
            regione="Sardegna",
        )
        db.add(comune_oristano)
        db.flush()
        particella = CatParticella(
            comune_id=comune_oristano.id,
            cod_comune_capacitas=200,
            codice_catastale="G113",
            nome_comune="Oristano",
            sezione_catastale="A",
            foglio="24",
            particella="10",
            subalterno=None,
            num_distretto="20",
            nome_distretto="Distretto 20",
            is_current=True,
            superficie_mq=1200,
        )
        db.add(particella)
        db.flush()
        db.add(
            CatUtenzaIrrigua(
                import_batch_id=batch.id,
                anno_campagna=2025,
                cco="0A0980205",
                comune_id=comune_oristano.id,
                cod_comune_capacitas=200,
                nome_comune="Oristano",
                num_distretto=20,
                foglio="24",
                particella="10",
                particella_id=particella.id,
                sup_catastale_mq=1200,
                sup_irrigabile_mq=1200,
                imponibile_sf=100,
                ind_spese_fisse=1,
                aliquota_0648=0.1,
                importo_0648=10,
                aliquota_0985=0.2,
                importo_0985=20,
                codice_fiscale="RSSMRA80A01H501U",
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

    async def fake_search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        assert query == "Oristano"
        return [CapacitasLookupOption(id="11", display="11 ORISTANO*ORISTANO")]

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        assert request.foglio == "24"
        assert request.particella == "10"
        if request.sezione == "A":
            return CapacitasTerreniSearchResult(total=0, rows=[])
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "or-live-row-10",
                    "PVC": "097",
                    "COM": "200",
                    "CCO": "0A0980205",
                    "FRA": "11",
                    "CCS": "00000",
                    "Foglio": "24",
                    "Partic": "10",
                    "Sub": "",
                    "Sez": "A",
                    "Anno": "2017",
                    "Belfiore": "G113",
                    "Ta_ext": " 9",
                }
            ],
        )

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        assert kwargs["cco"] == "0A0980205"
        return CapacitasTerrenoCertificato(
            cco="0A0980205",
            com="200",
            pvc="097",
            fra="11",
            ccs="00000",
            intestatari=[
                CapacitasIntestatario(
                    idxana="IDX-OR-10",
                    idxesa="IDX-ESA-OR-10",
                    codice_fiscale="RSSMRA80A01H501U",
                    denominazione="Rossi Mario",
                    comune_residenza="Oristano",
                    cap="09170",
                    residenza="09170 Oristano (OR) - Via Roma 1",
                )
            ],
        )

    async def fake_fetch_current_anagrafica_detail(self, *, idxana: str, idxesa: str) -> CapacitasAnagraficaDetail:
        assert idxana == "IDX-OR-10"
        assert idxesa == "IDX-ESA-OR-10"
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
        )

    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.pick_credential", lambda db, credential_id: (SimpleNamespace(id=1, username="live-user"), "secret"))
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_used", lambda db, credential_id: None)
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_error", lambda db, credential_id, error: None)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
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
            "rows": [{"row_index": 1, "comune": "Oristano", "sezione": "A", "foglio": "24", "particella": "10"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["esito"] == "FOUND"
    assert payload["match"]["utenza_latest"]["cco"] == "0A0980205"
    assert payload["match"]["intestatari"][0]["codice_fiscale"] == "RSSMRA80A01H501U"

    link_response = client.get(
        "/elaborazioni/capacitas/involture/link/rpt-certificato",
        headers=auth_headers(),
        params={"cco": "0A0980205"},
    )
    assert link_response.status_code == 200
    assert "CCO=0A0980205" in link_response.json()["url"]
    assert "COM=200" in link_response.json()["url"]
    assert "PVC=097" in link_response.json()["url"]
    assert "FRA=11" in link_response.json()["url"]

    db = TestingSessionLocal()
    try:
        certificato = db.query(CatCapacitasCertificato).filter(CatCapacitasCertificato.cco == "0A0980205").one()
        intestatari = db.query(CatCapacitasIntestatario).filter(CatCapacitasIntestatario.certificato_id == certificato.id).all()
        terreno_row = db.query(CatCapacitasTerrenoRow).filter(CatCapacitasTerrenoRow.cco == "0A0980205").one()
        occupancy = db.query(CatConsorzioOccupancy).filter(CatConsorzioOccupancy.cco == "0A0980205").one()
        assert certificato.com == "200"
        assert certificato.pvc == "097"
        assert certificato.fra == "11"
        assert len(intestatari) == 1
        assert terreno_row.particella == "10"
        assert occupancy.com == "200"
    finally:
        db.close()


def test_bulk_search_anagrafica_swapped_terralba_b_looks_up_arborea(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    try:
        comune_arborea = db.query(CatComune).filter(CatComune.codice_catastale == "A357").one()
        comune_terralba = CatComune(
            nome_comune="Terralba",
            codice_catastale="L122",
            cod_comune_capacitas=280,
            codice_comune_formato_numerico=115032,
            codice_comune_numerico_2017_2025=95067,
            nome_comune_legacy="Terralba",
            cod_provincia=115,
            sigla_provincia="OR",
            regione="Sardegna",
        )
        db.add(comune_terralba)
        db.flush()
        db.add(
            CatParticella(
                comune_id=comune_terralba.id,
                cod_comune_capacitas=280,
                codice_catastale="L122",
                nome_comune="Terralba",
                sezione_catastale="B",
                foglio="27",
                particella="2",
                subalterno=None,
                is_current=True,
                superficie_mq=35436,
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

    async def fake_search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        assert query == "Arborea"
        return [
            CapacitasLookupOption(id="31", display="31 ARBOREA"),
        ]

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        assert request.foglio == "27"
        assert request.particella == "2"
        if request.sezione == "B":
            return CapacitasTerreniSearchResult(total=0, rows=[])
        return CapacitasTerreniSearchResult(
            total=1,
            rows=[
                {
                    "ID": "swap-live-row-27-2",
                    "PVC": "097",
                    "COM": "165",
                    "CCO": "0A1022843",
                    "FRA": "31",
                    "CCS": "00000",
                    "Foglio": "27",
                    "Partic": "2",
                    "Sub": "",
                    "Sez": "",
                    "Anno": "2017",
                    "Belfiore": "A357",
                    "Ta_ext": " 9",
                }
            ],
        )

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        assert kwargs["cco"] == "0A1022843"
        return CapacitasTerrenoCertificato(
            cco="0A1022843",
            com="165",
            pvc="097",
            fra="31",
            ccs="00000",
            intestatari=[],
        )

    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.pick_credential", lambda db, credential_id: (SimpleNamespace(id=1, username="live-user"), "secret"))
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_used", lambda db, credential_id: None)
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_error", lambda db, credential_id, error: None)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.apps.involture.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={
            "include_capacitas_live": True,
            "rows": [{"row_index": 1, "comune": "Terralba", "foglio": "27 sez.B", "particella": "2"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["esito"] == "FOUND"
    assert payload["match"]["utenza_latest"]["cco"] == "0A1022843"
    assert payload["match"]["presente_in_catasto_consorzio"] is True

    db = TestingSessionLocal()
    try:
        particella = db.query(CatParticella).filter(
            CatParticella.codice_catastale == "L122",
            CatParticella.sezione_catastale == "B",
            CatParticella.foglio == "27",
            CatParticella.particella == "2",
        ).one()
        unit = db.query(CatConsorzioUnit).filter(CatConsorzioUnit.particella_id == particella.id).one()
        occupancy = db.query(CatConsorzioOccupancy).filter(CatConsorzioOccupancy.unit_id == unit.id).one()
        assert occupancy.cco == "0A1022843"
        assert occupancy.com == "165"
        assert occupancy.fra == "31"
        assert unit.source_comune_label == "Arborea"
    finally:
        db.close()


def test_bulk_search_anagrafica_live_fallback_uses_alternate_comune_without_sezione(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(self) -> None:
        return None

    async def fake_activate_app(self, app_name: str) -> None:
        assert app_name == "involture"

    async def fake_close(self) -> None:
        return None

    async def fake_search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        if query == "Terralba":
            return [CapacitasLookupOption(id="37", display="37 TERRALBA")]
        if query == "Arborea":
            return [CapacitasLookupOption(id="31", display="31 ARBOREA")]
        return []

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        assert request.sezione == ""
        if request.frazione_id == "37":
            return CapacitasTerreniSearchResult(total=0, rows=[])
        if request.frazione_id == "31":
            return CapacitasTerreniSearchResult(
                total=1,
                rows=[
                    {
                        "ID": "live-only-swap-row-27-2",
                        "PVC": "097",
                        "COM": "165",
                        "CCO": "0A1022843",
                        "FRA": "31",
                        "CCS": "00000",
                        "Foglio": "27",
                        "Partic": "2",
                        "Sub": "",
                        "Sez": "",
                        "Anno": "2024",
                        "Belfiore": "A357",
                        "Ta_ext": " 9",
                    }
                ],
            )
        return CapacitasTerreniSearchResult(total=0, rows=[])

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        return CapacitasTerrenoCertificato(
            cco="0A1022843",
            com="165",
            pvc="097",
            fra="31",
            ccs="00000",
            ruolo_status="Iscrivibile a ruolo",
            utenza_status="non iscritta a ruolo",
            intestatari=[],
        )

    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.pick_credential", lambda db, credential_id: (SimpleNamespace(id=1, username="live-user"), "secret"))
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_used", lambda db, credential_id: None)
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_error", lambda db, credential_id, error: None)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.apps.involture.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={
            "include_capacitas_live": True,
            "rows": [{"row_index": 1, "comune": "Terralba", "foglio": "27 sez.B", "particella": "2"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["esito"] == "FOUND"
    assert payload["match"]["foglio"] == "27"
    assert payload["match"]["particella"] == "2"
    assert payload["match"]["utenza_latest"]["cco"] == "0A1022843"
    assert "comune alternativo" in (payload["match"]["note"] or "")


def test_bulk_search_anagrafica_live_fallback_uses_same_comune_without_sezione(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(self) -> None:
        return None

    async def fake_activate_app(self, app_name: str) -> None:
        assert app_name == "involture"

    async def fake_close(self) -> None:
        return None

    async def fake_search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        assert query == "Arborea"
        return [CapacitasLookupOption(id="31", display="31 ARBOREA")]

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        assert request.sezione == ""
        if request.frazione_id == "31":
            return CapacitasTerreniSearchResult(
                total=1,
                rows=[
                    {
                        "ID": "live-only-arborea-row-23-423",
                        "PVC": "097",
                        "COM": "165",
                        "CCO": "0A0172980",
                        "FRA": "31",
                        "CCS": "00000",
                        "Foglio": "23",
                        "Partic": "423",
                        "Sub": "",
                        "Sez": "",
                        "Anno": "2024",
                        "Belfiore": "A357",
                        "Ta_ext": " 9",
                    }
                ],
            )
        return CapacitasTerreniSearchResult(total=0, rows=[])

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        return CapacitasTerrenoCertificato(
            cco="0A0172980",
            com="165",
            pvc="097",
            fra="31",
            ccs="00000",
            ruolo_status="Iscrivibile a ruolo",
            utenza_status="non iscritta a ruolo",
            intestatari=[],
        )

    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.pick_credential", lambda db, credential_id: (SimpleNamespace(id=1, username="live-user"), "secret"))
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_used", lambda db, credential_id: None)
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_error", lambda db, credential_id, error: None)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.apps.involture.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={
            "include_capacitas_live": True,
            "rows": [{"row_index": 1, "comune": "Arborea", "foglio": "23 sez.C", "particella": "423"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["esito"] == "FOUND"
    assert payload["match"]["foglio"] == "23"
    assert payload["match"]["particella"] == "423"
    assert payload["match"]["utenza_latest"]["cco"] == "0A0172980"
    assert payload["match"]["note"] == "Dati recuperati da Capacitas live: particella non risolta nel catasto locale"


def test_bulk_search_anagrafica_live_fallback_returns_multiple_matches_for_ambiguous_live_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(self) -> None:
        return None

    async def fake_activate_app(self, app_name: str) -> None:
        assert app_name == "involture"

    async def fake_close(self) -> None:
        return None

    async def fake_search_frazioni(self, query: str) -> list[CapacitasLookupOption]:
        if query == "Arborea":
            return [CapacitasLookupOption(id="31", display="31 ARBOREA")]
        if query == "Terralba":
            return [CapacitasLookupOption(id="37", display="37 TERRALBA")]
        return []

    async def fake_search_terreni(self, request) -> CapacitasTerreniSearchResult:
        assert request.sezione == ""
        if request.frazione_id == "31":
            return CapacitasTerreniSearchResult(
                total=1,
                rows=[
                        {
                            "ID": "live-arborea-16-30",
                            "PVC": "097",
                            "COM": "165",
                            "CCO": "000000511",
                            "FRA": "31",
                            "CCS": "00000",
                            "Foglio": "16",
                            "Partic": "3000",
                            "Sub": "",
                            "Sez": "",
                            "Anno": "2024",
                            "Belfiore": "A357",
                            "Ta_ext": " 7",
                        }
                    ],
                )
        if request.frazione_id == "37":
            return CapacitasTerreniSearchResult(
                total=1,
                rows=[
                    {
                        "ID": "live-terralba-16-30",
                        "PVC": "097",
                        "COM": "280",
                        "CCO": "0A1022843",
                        "FRA": "37",
                        "CCS": "00000",
                        "Foglio": "16",
                        "Partic": "3000",
                        "Sub": "",
                        "Sez": "",
                        "Anno": "2024",
                        "Belfiore": "L122",
                        "Ta_ext": " 9",
                    }
                ],
            )
        return CapacitasTerreniSearchResult(total=0, rows=[])

    async def fake_fetch_certificato(self, **kwargs) -> CapacitasTerrenoCertificato:
        return CapacitasTerrenoCertificato(
            cco=kwargs["cco"],
            com=kwargs["com"],
            pvc=kwargs["pvc"],
            fra=kwargs["fra"],
            ccs=kwargs["ccs"],
            intestatari=[],
        )

    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.pick_credential", lambda db, credential_id: (SimpleNamespace(id=1, username="live-user"), "secret"))
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_used", lambda db, credential_id: None)
    monkeypatch.setattr("app.modules.catasto.routes.anagrafica.mark_credential_error", lambda db, credential_id, error: None)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.login", fake_login)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.activate_app", fake_activate_app)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.session.CapacitasSessionManager.close", fake_close)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_frazioni", fake_search_frazioni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.client.InVoltureClient.search_terreni", fake_search_terreni)
    monkeypatch.setattr("app.modules.elaborazioni.capacitas.apps.involture.client.InVoltureClient.fetch_certificato", fake_fetch_certificato)

    response = client.post(
        "/catasto/elaborazioni-massive/particelle",
        headers=auth_headers(),
        json={
            "include_capacitas_live": True,
            "rows": [{"row_index": 1, "comune": "Arborea", "foglio": "16 sez.C", "particella": "3000"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()["results"][0]
    assert payload["esito"] == "MULTIPLE_MATCHES"
    assert payload["matches_count"] == 2
    ccos = sorted(match["utenza_latest"]["cco"] for match in payload["matches"])
    assert ccos == ["000000511", "0A1022843"]


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


def test_import_history_and_summary_support_shapefile_distretti_batches() -> None:
    db = TestingSessionLocal()
    try:
        completed_at = datetime.now(timezone.utc)
        db.add_all(
            [
                CatImportBatch(
                    filename="distretti-ok.zip",
                    tipo="shapefile_distretti",
                    anno_campagna=None,
                    hash_file="distretti-ok",
                    status="completed",
                    righe_totali=4,
                    righe_importate=3,
                    righe_anomalie=1,
                    created_by=1,
                    completed_at=completed_at,
                    report_json={"distretti_aggiornati": 2},
                ),
                CatImportBatch(
                    filename="distretti-failed.zip",
                    tipo="shapefile_distretti",
                    anno_campagna=None,
                    hash_file="distretti-failed",
                    status="failed",
                    righe_totali=4,
                    righe_importate=0,
                    righe_anomalie=0,
                    created_by=1,
                    errore="Shape non valido",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    history_response = client.get("/catasto/import/history?tipo=shapefile_distretti&limit=10", headers=auth_headers())
    summary_response = client.get("/catasto/import/summary?tipo=shapefile_distretti", headers=auth_headers())

    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert len(history_payload) == 2
    assert {item["status"] for item in history_payload} == {"completed", "failed"}
    assert all(item["tipo"] == "shapefile_distretti" for item in history_payload)

    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["tipo"] == "shapefile_distretti"
    assert summary_payload["totale_batch"] == 2
    assert summary_payload["completed_batch"] == 1
    assert summary_payload["failed_batch"] == 1
    assert summary_payload["ultimo_completed_at"] is not None


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


def test_upload_distretti_shapefile_creates_processing_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_distretti_import(
        batch_id,
        zip_bytes: bytes,
        shp_filename: str,
        created_by: int,
        source_srid: int,
    ) -> None:
        captured["batch_id"] = str(batch_id)
        captured["zip_size"] = len(zip_bytes)
        captured["filename"] = shp_filename
        captured["created_by"] = created_by
        captured["source_srid"] = source_srid

    monkeypatch.setattr(import_routes_module, "_run_distretti_shapefile_import", fake_run_distretti_import)

    response = client.post(
        "/catasto/import/distretti/upload?source_srid=3003",
        headers=auth_headers(),
        files={"file": ("distretti.zip", b"PK\x03\x04fakezip", "application/zip")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "processing"
    assert captured["filename"] == "distretti.zip"
    assert captured["zip_size"] > 0
    assert captured["source_srid"] == 3003

    db = TestingSessionLocal()
    try:
        batch = db.get(CatImportBatch, UUID(payload["batch_id"]))
        assert batch is not None
        assert batch.tipo == "shapefile_distretti"
        assert batch.status == "processing"
        assert batch.filename == "distretti.zip"
    finally:
        db.close()


def test_upload_distretti_shapefile_rejects_non_zip() -> None:
    response = client.post(
        "/catasto/import/distretti/upload",
        headers=auth_headers(),
        files={"file": ("distretti.txt", b"not-a-zip", "text/plain")},
    )

    assert response.status_code == 400
    assert "ZIP" in response.json()["detail"]


def test_finalize_distretti_shapefile_route_returns_service_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_finalize_distretti_shapefile_import(
        db: Session,
        *,
        created_by: int,
        cleanup_staging: bool,
        **_: object,
    ) -> dict[str, object]:
        captured["created_by"] = created_by
        captured["cleanup_staging"] = cleanup_staging
        return {"status": "completed", "distretti_aggiornati": 2}

    monkeypatch.setattr(import_routes_module, "finalize_distretti_shapefile_import", fake_finalize_distretti_shapefile_import)

    response = client.post("/catasto/import/distretti/finalize", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured["created_by"] > 0
    assert captured["cleanup_staging"] is True
