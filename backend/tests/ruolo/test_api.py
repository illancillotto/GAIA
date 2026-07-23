from collections.abc import Generator
from datetime import datetime, timezone
import sys
from types import ModuleType, SimpleNamespace
from uuid import UUID, uuid4

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
from app.models.catasto import CatastoParcel
from app.models.catasto_phase1 import CatImportBatch, CatUtenzaIrrigua
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.utenze.models import AnagraficaPaymentNotice, AnagraficaPerson, AnagraficaSubject


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
        filename="storico_ruolo_2025",
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
    assert detail_payload["filename"] == "storico_ruolo_2025"


def test_import_job_detail_returns_404_for_unknown_job() -> None:
    response = client.get(f"/ruolo/import/jobs/{uuid4()}", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "Job non trovato"


def test_ruolo_file_upload_endpoints_are_unregistered() -> None:
    files = {"file": ("ruolo-2025.txt", b"fake ruolo payload", "text/plain")}

    upload_response = client.post("/ruolo/import/upload", files=files, headers=auth_headers())
    assert upload_response.status_code == 404

    detect_response = client.post("/ruolo/import/detect-year", files=files, headers=auth_headers())
    assert detect_response.status_code == 404


def test_list_avvisi_supports_unified_search_query() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="storico_ruolo_2025",
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


def test_avvisi_detail_export_and_subject_endpoints() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(anno_tributario=2025, filename="ruolo_detail_2025", status="completed")
    linked_subject = AnagraficaSubject(source_name_raw="Dettaglio Rossi")
    db.add_all([job, linked_subject])
    db.flush()
    db.add(
        AnagraficaPerson(
            subject_id=linked_subject.id,
            cognome="ROSSI",
            nome="DETTAGLIO",
            codice_fiscale="RSSDTL80A01H501Z",
        )
    )

    avviso = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-DETAIL-001",
        anno_tributario=2025,
        codice_fiscale_raw="RSSDTL80A01H501Z",
        nominativo_raw="ROSSI DETTAGLIO",
        codice_utenza="UT-DETAIL",
        importo_totale_0648=10.0,
        importo_totale_0985=5.0,
        importo_totale_0668=2.0,
        importo_totale_euro=17.0,
        subject_id=linked_subject.id,
    )
    db.add(avviso)
    db.flush()
    partita = RuoloPartita(
        avviso_id=avviso.id,
        codice_partita="P-DETAIL",
        comune_nome="ORISTANO",
        comune_codice="G113",
        contribuente_cf="RSSDTL80A01H501Z",
        importo_0648=10.0,
        importo_0985=5.0,
        importo_0668=2.0,
    )
    db.add(partita)
    db.flush()
    db.add(
        RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            foglio="1",
            particella="10",
            subalterno=None,
            sup_catastale_are=100.0,
            sup_catastale_ha=1.0,
            sup_irrigata_ha=0.75,
        )
    )
    db.commit()
    avviso_id = avviso.id
    subject_id = linked_subject.id
    db.close()

    detail_response = client.get(f"/ruolo/avvisi/{avviso_id}", headers=auth_headers())
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["codice_cnc"] == "CNC-DETAIL-001"
    assert detail_payload["partite"][0]["codice_partita"] == "P-DETAIL"
    assert detail_payload["partite"][0]["particelle"][0]["particella"] == "10"
    assert detail_payload["display_name"] == "ROSSI DETTAGLIO"

    subject_response = client.get(f"/ruolo/soggetti/{subject_id}/avvisi", headers=auth_headers())
    assert subject_response.status_code == 200
    assert subject_response.json()[0]["codice_cnc"] == "CNC-DETAIL-001"

    subject_filter_response = client.get(f"/ruolo/avvisi?subject_id={subject_id}", headers=auth_headers())
    assert subject_filter_response.status_code == 200
    assert subject_filter_response.json()["items"][0]["codice_cnc"] == "CNC-DETAIL-001"

    export_response = client.get("/ruolo/avvisi/export?anno=2025", headers=auth_headers())
    assert export_response.status_code == 200
    assert "avvisi_ruolo.csv" in export_response.headers["content-disposition"]
    assert "CNC-DETAIL-001" in export_response.text
    assert "Si" in export_response.text

    missing_response = client.get(f"/ruolo/avvisi/{uuid4()}", headers=auth_headers())
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Avviso non trovato"


def test_list_avvisi_supports_individual_filters_and_invalid_subject_id() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(anno_tributario=2025, filename="ruolo_filters_2025", status="completed")
    db.add(job)
    db.flush()
    avviso = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-FILTER-001",
        anno_tributario=2025,
        codice_fiscale_raw="FLTMRR80A01H501Z",
        nominativo_raw="FILTRO MARIO",
        codice_utenza="UT-FILTER",
        importo_totale_euro=12.0,
    )
    db.add(avviso)
    db.flush()
    db.add(RuoloPartita(avviso_id=avviso.id, codice_partita="P-FILTER", comune_nome="Nurachi"))
    db.commit()
    db.close()

    response = client.get(
        "/ruolo/avvisi?subject_id=not-a-uuid&codice_fiscale=FLTMRR&comune=Nurachi&codice_utenza=UT-FILTER",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["codice_cnc"] == "CNC-FILTER-001"


def test_stats_comuni_counts_distinct_avvisi_partite_and_particelle() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="ruolo_stats_2025",
        status="completed",
    )
    db.add(job)
    db.flush()

    avviso_1 = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-STATS-001",
        anno_tributario=2025,
        nominativo_raw="Rossi Mario",
        importo_totale_0648=100.00,
        importo_totale_0985=50.00,
        importo_totale_0668=10.00,
        importo_totale_euro=160.00,
    )
    avviso_2 = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-STATS-002",
        anno_tributario=2025,
        nominativo_raw="Pinna Maria",
        importo_totale_0648=80.00,
        importo_totale_0985=0.00,
        importo_totale_0668=20.00,
        importo_totale_euro=100.00,
    )
    db.add_all([avviso_1, avviso_2])
    db.flush()

    partita_oristano_1 = RuoloPartita(
        avviso_id=avviso_1.id,
        codice_partita="P-OR-1",
        comune_nome="Oristano",
        importo_0648=70.00,
        importo_0985=20.00,
        importo_0668=5.00,
    )
    partita_oristano_2 = RuoloPartita(
        avviso_id=avviso_1.id,
        codice_partita="P-OR-2",
        comune_nome="Oristano",
        importo_0648=30.00,
        importo_0985=30.00,
        importo_0668=5.00,
    )
    partita_cabras = RuoloPartita(
        avviso_id=avviso_2.id,
        codice_partita="P-CA-1",
        comune_nome="Cabras",
        importo_0648=80.00,
        importo_0985=0.00,
        importo_0668=20.00,
    )
    db.add_all([partita_oristano_1, partita_oristano_2, partita_cabras])
    db.flush()

    db.add_all([
        RuoloParticella(
            partita_id=partita_oristano_1.id,
            anno_tributario=2025,
            foglio="1",
            particella="10",
            importo_manut=20.00,
            cat_particella_id=None,
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="no_cat_particella_match",
        ),
        RuoloParticella(
            partita_id=partita_oristano_1.id,
            anno_tributario=2025,
            foglio="1",
            particella="11",
            importo_manut=15.00,
            cat_particella_id=uuid4(),
            cat_particella_match_status="matched",
        ),
        RuoloParticella(
            partita_id=partita_oristano_2.id,
            anno_tributario=2025,
            foglio="2",
            particella="20",
            importo_manut=25.00,
            cat_particella_id=uuid4(),
            cat_particella_match_status="matched",
        ),
        RuoloParticella(
            partita_id=partita_cabras.id,
            anno_tributario=2025,
            foglio="3",
            particella="30",
            importo_manut=40.00,
            cat_particella_id=None,
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="catasto_skipped",
        ),
    ])
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/comuni?anno=2025", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()

    assert payload["anno_tributario"] == 2025
    items = {item["comune_nome"]: item for item in payload["items"]}

    assert items["Oristano"]["num_avvisi"] == 1
    assert items["Oristano"]["num_partite"] == 2
    assert items["Oristano"]["num_particelle"] == 3
    assert items["Oristano"]["non_collegate_catasto"] == 1
    assert items["Oristano"]["totale_euro"] == 160.0

    assert items["Cabras"]["num_avvisi"] == 1
    assert items["Cabras"]["num_partite"] == 1
    assert items["Cabras"]["num_particelle"] == 1
    assert items["Cabras"]["non_collegate_catasto"] == 1
    assert items["Cabras"]["totale_euro"] == 100.0


def test_stats_and_particelle_summary_endpoints() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(anno_tributario=2025, filename="ruolo_stats_base_2025", status="completed")
    subject = AnagraficaSubject(source_name_raw="Stats Rossi")
    db.add_all([job, subject])
    db.flush()
    linked = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-STATS-LINKED",
        anno_tributario=2025,
        nominativo_raw="ROSSI STATS",
        subject_id=subject.id,
        importo_totale_0648=10.0,
        importo_totale_0985=5.0,
        importo_totale_0668=2.0,
        importo_totale_euro=17.0,
    )
    unlinked = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-STATS-UNLINKED",
        anno_tributario=2025,
        nominativo_raw="PINNA STATS",
        importo_totale_0648=20.0,
        importo_totale_0985=10.0,
        importo_totale_0668=4.0,
        importo_totale_euro=34.0,
    )
    db.add_all([linked, unlinked])
    db.flush()
    partita = RuoloPartita(avviso_id=linked.id, codice_partita="P-STATS", comune_nome="ORISTANO")
    db.add(partita)
    db.flush()
    db.add_all(
        [
            RuoloParticella(
                partita_id=partita.id,
                anno_tributario=2025,
                foglio="1",
                particella="1",
                cat_particella_match_status="matched",
                cat_particella_match_confidence="exact_no_sub",
            ),
            RuoloParticella(
                partita_id=partita.id,
                anno_tributario=2025,
                foglio="1",
                particella="2",
                cat_particella_match_status="unmatched",
                cat_particella_match_reason="no_cat_particella_match",
            ),
        ]
    )
    db.commit()
    db.close()

    stats_response = client.get("/ruolo/stats?anno=2025", headers=auth_headers())
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()["items"][0]
    assert stats_payload["total_avvisi"] == 2
    assert stats_payload["avvisi_collegati"] == 1
    assert stats_payload["avvisi_non_collegati"] == 1
    assert stats_payload["totale_euro"] == 51.0

    particelle_response = client.get("/ruolo/stats/particelle?anno=2025", headers=auth_headers())
    assert particelle_response.status_code == 200
    summary = particelle_response.json()
    assert summary["total_particelle"] == 2
    assert summary["collegate_catasto"] == 0
    assert summary["non_collegate_catasto"] == 2


def test_capacitas_detail_returns_404_when_missing() -> None:
    response = client.get(
        "/ruolo/stats/capacitas-check/detail?anno=2025&tax_code=RSSMRA80A01H501Z",
        headers=auth_headers(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dettaglio calcolo Capacitas non trovato"


def test_empty_analytics_and_calculation_endpoints_without_active_batch() -> None:
    analytics_response = client.get("/ruolo/stats/analytics?anno=2030", headers=auth_headers())
    assert analytics_response.status_code == 200
    analytics_payload = analytics_response.json()
    assert analytics_payload["anno_tributario"] == 2030
    assert analytics_payload["tributi_breakdown"] == []
    assert analytics_payload["comuni"] == []

    gaia_response = client.get("/ruolo/stats/calcolo-gaia?anno=2030", headers=auth_headers())
    assert gaia_response.status_code == 200
    gaia_payload = gaia_response.json()
    assert gaia_payload["summary"]["active_batch_id"] is None
    assert gaia_payload["items"] == []


def test_capacitas_detail_returns_404_when_active_batch_has_no_matching_tax_code() -> None:
    db = TestingSessionLocal()
    active_batch = CatImportBatch(
        filename="capacitas-empty-2025.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=2025,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(active_batch)
    db.flush()
    db.add(
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="OTHER80A01H501Z",
            denominazione="ALTRO",
            nome_comune="ORISTANO",
            imponibile_sf=100,
            aliquota_0648=0.1,
            aliquota_0985=0.05,
            importo_0648=10,
            importo_0985=5,
        )
    )
    db.commit()
    db.close()

    response = client.get(
        "/ruolo/stats/capacitas-check/detail?anno=2025&tax_code=RSSMRA80A01H501Z",
        headers=auth_headers(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dettaglio calcolo Capacitas non trovato"


def test_gaia_calculation_covers_status_edges_and_anomalous_filter() -> None:
    db = TestingSessionLocal()
    active_batch = CatImportBatch(
        filename="capacitas-gaia-edges-2025.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=2025,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(active_batch)
    db.flush()
    db.add_all(
        [
            AnagraficaPaymentNotice(
                source_system="incass",
                source_notice_id="EDGE-B",
                anno="2025",
                codice_fiscale="EDGEBB80A01H501Z",
                display_name="RUOLO EDGE B",
                raw_detail_json={
                    "partitario": {
                        "partite": [
                            {
                                "importo_0648_euro": "10.00",
                                "importo_0985_euro": "0.00",
                                "importo_0668_euro": "0.00",
                                "comune_nome": "ORISTANO",
                            }
                        ]
                    }
                },
            ),
        ]
    )
    db.add_all(
        [
            CatUtenzaIrrigua(
                import_batch_id=active_batch.id,
                anno_campagna=2025,
                codice_fiscale=None,
                denominazione="MISSING TAX",
                nome_comune="ORISTANO",
                imponibile_sf=100,
                aliquota_0648=0.1,
                aliquota_0985=0,
                importo_0648=10,
                importo_0985=0,
            ),
            CatUtenzaIrrigua(
                import_batch_id=active_batch.id,
                anno_campagna=2025,
                codice_fiscale="EDGEAA80A01H501Z",
                denominazione=None,
                nome_comune="ORISTANO",
                imponibile_sf=100,
                aliquota_0648=0.1,
                aliquota_0985=0,
                importo_0648=10,
                importo_0985=0,
            ),
            CatUtenzaIrrigua(
                import_batch_id=active_batch.id,
                anno_campagna=2025,
                codice_fiscale="EDGEAA80A01H501Z",
                denominazione="EDGE A",
                nome_comune="ORISTANO",
                imponibile_sf=100,
                aliquota_0648=0.1,
                aliquota_0985=0,
                importo_0648=10,
                importo_0985=0,
            ),
            CatUtenzaIrrigua(
                import_batch_id=active_batch.id,
                anno_campagna=2025,
                codice_fiscale="EDGEBB80A01H501Z",
                denominazione="EDGE B",
                nome_comune="CABRAS",
                imponibile_sf=100,
                aliquota_0648=0.1,
                aliquota_0985=0,
                importo_0648=20,
                importo_0985=0,
            ),
        ]
    )
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/calcolo-gaia?anno=2025", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    by_tax = {item["tax_code"]: item for item in payload["items"]}
    assert payload["summary"]["positions_missing_tax_code"] == 1
    assert by_tax["EDGEAA80A01H501Z"]["status"] == "only_in_capacitas"
    assert by_tax["EDGEAA80A01H501Z"]["display_name"] == "EDGE A"
    assert by_tax["EDGEBB80A01H501Z"]["status"] == "matched"
    assert by_tax["EDGEBB80A01H501Z"]["gap_excel_gaia_total"] == 10.0

    anomalous_response = client.get(
        "/ruolo/stats/calcolo-gaia?anno=2025&anomalous_only=true",
        headers=auth_headers(),
    )
    assert anomalous_response.status_code == 200
    assert anomalous_response.json()["items"] == []


def test_catasto_parcels_endpoints_list_history_and_404() -> None:
    db = TestingSessionLocal()
    older = CatastoParcel(
        comune_codice="A357",
        comune_nome="ARBOREA",
        foglio="5",
        particella="120",
        subalterno=None,
        sup_catastale_are=90.0,
        sup_catastale_ha=0.9,
        valid_from=2024,
        valid_to=2024,
        source="ruolo_import",
    )
    current = CatastoParcel(
        comune_codice="A357",
        comune_nome="ARBOREA",
        foglio="5",
        particella="120",
        subalterno=None,
        sup_catastale_are=95.0,
        sup_catastale_ha=0.95,
        valid_from=2025,
        valid_to=None,
        source="ruolo_import",
    )
    db.add_all([older, current])
    db.commit()
    current_id = current.id
    db.close()

    list_response = client.get(
        "/catasto/parcels?comune_codice=A357&foglio=5&particella=120&active_only=true",
        headers=auth_headers(),
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload) == 1
    assert list_payload[0]["id"] == str(current_id)

    history_response = client.get(f"/catasto/parcels/{current_id}/history", headers=auth_headers())
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert [item["valid_from"] for item in history_payload] == [2024, 2025]

    missing_response = client.get(f"/catasto/parcels/{uuid4()}/history", headers=auth_headers())
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Parcella non trovata"


def test_capacitas_check_compares_ruolo_and_capacitas_amounts_by_tax_code() -> None:
    db = TestingSessionLocal()
    active_batch = CatImportBatch(
        filename="capacitas-2025.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=2025,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(active_batch)
    db.flush()
    active_batch_id = str(active_batch.id)
    db.add_all([
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="020250000000001",
            anno="2025",
            codice_fiscale="RSSMRA80A01H501Z",
            display_name="ROSSI MARIO",
            raw_detail_json={
                "partitario": {
                    "partite": [
                        {
                            "importo_0648_euro": "100.00",
                            "importo_0985_euro": "50.00",
                            "importo_0668_euro": "10.00",
                            "comune_nome": "Marrubiu",
                        }
                    ]
                }
            },
        ),
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="020250000000002",
            anno="2025",
            codice_fiscale="PLLGNN80A01H501X",
            display_name="PILLA GIOVANNI",
            raw_detail_json={
                "partitario": {
                    "partite": [
                        {
                            "importo_0648_euro": "80.00",
                            "importo_0985_euro": "10.00",
                            "importo_0668_euro": "0.00",
                            "comune_nome": "Arborea",
                        }
                    ]
                }
            },
        ),
    ])
    db.add_all([
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione="ROSSI MARIO",
            nome_comune="Marrubiu",
            imponibile_sf=1000,
            aliquota_0648=0.09,
            aliquota_0985=0.05,
            importo_0648=90.00,
            importo_0985=50.00,
            anomalia_imponibile=True,
            anomalia_importi=True,
        ),
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="BNCLCU80A01H501Y",
            denominazione="BIANCHI LUCA",
            imponibile_sf=500,
            aliquota_0648=0.08,
            aliquota_0985=0.01,
            importo_0648=40.00,
            importo_0985=5.00,
        ),
    ])
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/capacitas-check?anno=2025", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["anno_tributario"] == 2025
    assert payload["summary"]["ruolo_positions"] == 2
    assert payload["summary"]["capacitas_positions"] == 2
    assert payload["summary"]["capacitas_active_batch_id"] == active_batch_id
    assert payload["summary"]["matched_positions"] == 1
    assert payload["summary"]["only_in_ruolo"] == 1
    assert payload["summary"]["only_in_capacitas"] == 1
    assert payload["summary"]["delta_totale_0648"] == 50.0
    assert payload["summary"]["delta_totale_0985"] == 5.0
    assert payload["summary"]["gaia_totale_0648"] == 130.0
    assert payload["summary"]["gaia_totale_0985"] == 55.0
    assert payload["summary"]["excel_totale_0648"] == 130.0
    assert payload["summary"]["excel_totale_0985"] == 55.0
    assert payload["summary"]["delta_gaia_excel_totale_0648"] == 0.0
    assert payload["summary"]["delta_gaia_excel_totale_0985"] == 0.0
    assert payload["summary"]["delta_gaia_excel_totale_confrontabile"] == 0.0
    assert payload["summary"]["ruolo_totale_0668"] == 10.0
    assert payload["summary"]["mismatch_positions"] == 3
    assert payload["summary"]["diagnosis_ruolo_count"] == 2
    assert payload["summary"]["diagnosis_gaia_count"] == 0
    assert payload["summary"]["diagnosis_excel_count"] == 1

    items_by_tax = {item["tax_code"]: item for item in payload["items"]}
    assert items_by_tax["RSSMRA80A01H501Z"]["status"] == "amount_mismatch"
    assert items_by_tax["RSSMRA80A01H501Z"]["diagnosis"] == "problema_ruolo"
    assert items_by_tax["RSSMRA80A01H501Z"]["delta_0648"] == 10.0
    assert items_by_tax["RSSMRA80A01H501Z"]["gaia_0648"] == 90.0
    assert items_by_tax["RSSMRA80A01H501Z"]["excel_0648"] == 90.0
    assert items_by_tax["RSSMRA80A01H501Z"]["delta_gaia_excel_totale_confrontabile"] == 0.0
    assert items_by_tax["RSSMRA80A01H501Z"]["anomalous_rows_count"] == 1
    assert items_by_tax["RSSMRA80A01H501Z"]["clean_rows_count"] == 0
    assert items_by_tax["RSSMRA80A01H501Z"]["anomaly_gap_share"] == 0.0
    assert items_by_tax["RSSMRA80A01H501Z"]["anomaly_driven_case"] is False
    assert items_by_tax["PLLGNN80A01H501X"]["status"] == "only_in_ruolo"
    assert items_by_tax["PLLGNN80A01H501X"]["diagnosis"] == "problema_snapshot_excel"
    assert items_by_tax["BNCLCU80A01H501Y"]["status"] == "only_in_capacitas"
    assert items_by_tax["BNCLCU80A01H501Y"]["diagnosis"] == "problema_ruolo"
    assert items_by_tax["BNCLCU80A01H501Y"]["gaia_totale_confrontabile"] == 45.0
    assert items_by_tax["BNCLCU80A01H501Y"]["excel_totale_confrontabile"] == 45.0
    assert items_by_tax["BNCLCU80A01H501Y"]["delta_gaia_excel_totale_confrontabile"] == 0.0

    comuni_response = client.get("/ruolo/stats/capacitas-check/comuni?anno=2025", headers=auth_headers())
    assert comuni_response.status_code == 200
    comuni_payload = comuni_response.json()
    comuni_by_name = {item["comune_nome"]: item for item in comuni_payload["items"]}
    assert comuni_payload["anno_tributario"] == 2025
    assert comuni_by_name["MARRUBIU"]["capacitas_active_batch_id"] == active_batch_id
    assert comuni_by_name["MARRUBIU"]["source_comuni_ruolo"] == ["Marrubiu"]
    assert comuni_by_name["MARRUBIU"]["source_comuni_capacitas"] == ["Marrubiu"]
    assert "N/D" in comuni_by_name

    export_response = client.get("/ruolo/stats/capacitas-check/export?anno=2025", headers=auth_headers())
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "CF/PIVA" in export_response.text
    assert "GAIA 0648" in export_response.text
    assert "Excel 0648" in export_response.text
    assert "RSSMRA80A01H501Z" in export_response.text


def test_capacitas_check_comuni_normalizes_fractions_and_aliases() -> None:
    db = TestingSessionLocal()
    active_batch = CatImportBatch(
        filename="capacitas-comuni-2025.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=2025,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(active_batch)
    db.flush()
    active_batch_id = str(active_batch.id)

    db.add_all([
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="020250000000010",
            anno="2025",
            codice_fiscale="RSSMRA80A01H501Z",
            display_name="ROSSI MARIO",
            raw_detail_json={
                "partitario": {
                    "partite": [
                        {
                            "importo_0648_euro": "100.00",
                            "importo_0985_euro": "50.00",
                            "comune_nome": "ORISTANO",
                        },
                        {
                            "importo_0648_euro": "20.00",
                            "importo_0985_euro": "10.00",
                            "comune_nome": "SILI",
                        },
                    ]
                }
            },
        ),
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="020250000000011",
            anno="2025",
            codice_fiscale="VRDGNN80A01H501X",
            display_name="VERDI GIOVANNI",
            raw_detail_json={
                "partitario": {
                    "partite": [
                        {
                            "importo_0648_euro": "7.00",
                            "importo_0985_euro": "3.00",
                            "comune_nome": "SAN NICOLO D'ARCIDANO",
                        }
                    ]
                }
            },
        ),
    ])
    db.add_all([
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione="ROSSI MARIO",
            nome_comune="ORISTANO*ORISTANO",
            imponibile_sf=1000,
            aliquota_0648=0.10,
            aliquota_0985=0.05,
            importo_0648=100.00,
            importo_0985=50.00,
        ),
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione="ROSSI MARIO",
            nome_comune="SILI'*ORISTANO",
            imponibile_sf=200,
            aliquota_0648=0.10,
            aliquota_0985=0.05,
            importo_0648=20.00,
            importo_0985=10.00,
        ),
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="VRDGNN80A01H501X",
            denominazione="VERDI GIOVANNI",
            nome_comune="SAN NICOLO ARCIDANO",
            imponibile_sf=100,
            aliquota_0648=0.07,
            aliquota_0985=0.03,
            importo_0648=7.00,
            importo_0985=3.00,
        ),
    ])
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/capacitas-check/comuni?anno=2025&limit=20", headers=auth_headers())
    assert response.status_code == 200

    payload = response.json()
    comuni_by_name = {item["comune_nome"]: item for item in payload["items"]}
    assert set(comuni_by_name) == {"ORISTANO", "SAN NICOLO ARCIDANO"}
    assert comuni_by_name["ORISTANO"]["capacitas_active_batch_id"] == active_batch_id
    assert comuni_by_name["ORISTANO"]["ruolo_totale_confrontabile"] == 180.0
    assert comuni_by_name["ORISTANO"]["gaia_totale_confrontabile"] == 180.0
    assert comuni_by_name["ORISTANO"]["excel_totale_confrontabile"] == 180.0
    assert comuni_by_name["ORISTANO"]["source_comuni_ruolo"] == ["ORISTANO", "SILI"]
    assert comuni_by_name["ORISTANO"]["source_comuni_capacitas"] == ["ORISTANO*ORISTANO", "SILI'*ORISTANO"]
    assert comuni_by_name["SAN NICOLO ARCIDANO"]["delta_totale_confrontabile"] == 0.0
    assert comuni_by_name["SAN NICOLO ARCIDANO"]["source_comuni_ruolo"] == ["SAN NICOLO D'ARCIDANO"]
    assert comuni_by_name["SAN NICOLO ARCIDANO"]["source_comuni_capacitas"] == ["SAN NICOLO ARCIDANO"]


def test_capacitas_check_detail_returns_calculation_breakdown_for_tax_code() -> None:
    db = TestingSessionLocal()
    active_batch = CatImportBatch(
        filename="capacitas-detail-2025.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=2025,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(active_batch)
    db.flush()
    active_batch_id = str(active_batch.id)

    db.add_all([
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione="ROSSI MARIO",
            cco="CCO-1",
            cod_provincia=95,
            cod_comune_capacitas=42,
            cod_frazione=7,
            num_distretto=3,
            nome_distretto_loc="Distretto Nord",
            nome_comune="Marrubiu",
            sezione_catastale="A",
            foglio="10",
            particella="100",
            sup_catastale_mq=1200,
            sup_irrigabile_mq=1000,
            ind_spese_fisse=0.72,
            imponibile_sf=720,
            aliquota_0648=0.03,
            aliquota_0985=0.015,
            importo_0648=21.60,
            importo_0985=10.80,
            codice_fiscale_raw=" rssmra80a01h501z ",
            anomalia_imponibile=False,
            anomalia_importi=False,
        ),
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione="ROSSI MARIO",
            cco="CCO-2",
            nome_comune="Arborea",
            foglio="11",
            particella="200",
            subalterno="1",
            sup_irrigabile_mq=500,
            ind_spese_fisse=1.24,
            imponibile_sf=620,
            aliquota_0648=0.03,
            aliquota_0985=0.015,
            importo_0648=25.00,
            importo_0985=13.00,
            anomalia_superficie=True,
            anomalia_imponibile=True,
            anomalia_importi=True,
        ),
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="BNCLCU80A01H501Y",
            denominazione="BIANCHI LUCA",
            nome_comune="Marrubiu",
            foglio="12",
            particella="300",
            sup_irrigabile_mq=400,
            ind_spese_fisse=0.72,
            imponibile_sf=288,
            aliquota_0648=0.03,
            aliquota_0985=0.015,
            importo_0648=8.64,
            importo_0985=4.32,
            anomalia_imponibile=False,
            anomalia_importi=False,
        ),
    ])
    ruolo_job = RuoloImportJob(
        anno_tributario=2025,
        filename="ruolo-detail-2025.txt",
        status="completed",
    )
    db.add(ruolo_job)
    db.flush()
    avviso = RuoloAvviso(
        import_job_id=ruolo_job.id,
        codice_cnc="CNC-CALC-001",
        anno_tributario=2025,
        codice_fiscale_raw="RSSMRA80A01H501Z",
        nominativo_raw="ROSSI MARIO",
    )
    db.add(avviso)
    db.flush()
    db.add(
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="020250001234560",
            codice_fiscale="RSSMRA80A01H501Z",
            display_name="ROSSI MARIO",
            anno="2025",
            detail_url="https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=020250001234560",
        )
    )
    partita_marrubiu = RuoloPartita(
        avviso_id=avviso.id,
        codice_partita="CCO-1/Q0001",
        comune_nome="Marrubiu",
        contribuente_cf="RSSMRA80A01H501Z",
    )
    partita_arborea = RuoloPartita(
        avviso_id=avviso.id,
        codice_partita="CCO-2/Q0001",
        comune_nome="Arborea",
        contribuente_cf="RSSMRA80A01H501Z",
    )
    db.add_all([partita_marrubiu, partita_arborea])
    db.flush()
    db.add_all([
        RuoloParticella(
            partita_id=partita_marrubiu.id,
            anno_tributario=2025,
            foglio="010",
            particella="100",
            subalterno="PB",
            importo_manut=20.0,
            importo_ist=10.0,
        ),
        RuoloParticella(
            partita_id=partita_arborea.id,
            anno_tributario=2025,
            foglio="11",
            particella="200",
            subalterno="1",
            importo_manut=12.5,
            importo_ist=6.5,
        ),
    ])
    avviso_id = str(avviso.id)
    db.commit()
    db.close()

    response = client.get(
        "/ruolo/stats/capacitas-check/detail?anno=2025&tax_code=RSSMRA80A01H501Z",
        headers=auth_headers(),
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["summary"]["anno_tributario"] == 2025
    assert payload["summary"]["tax_code"] == "RSSMRA80A01H501Z"
    assert payload["summary"]["display_name"] == "ROSSI MARIO"
    assert payload["summary"]["active_batch_id"] == active_batch_id
    assert payload["summary"]["source_filename"] == "capacitas-detail-2025.xlsx"
    assert payload["summary"]["ruolo_avviso_id"] == avviso_id
    assert payload["summary"]["codice_cnc"] == "CNC-CALC-001"
    assert payload["summary"]["capacitas_url"] == "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=020250001234560"
    assert payload["summary"]["capacitas_avviso_code"] == "020250001234560"
    assert payload["summary"]["capacitas_link_source"] == "incass_live"
    assert payload["summary"]["rows_count"] == 2
    assert payload["summary"]["anomalous_rows_count"] == 1
    assert payload["summary"]["clean_rows_count"] == 1
    assert payload["summary"]["total_sup_irrigabile_mq"] == 1500.0
    assert payload["summary"]["total_imponibile_sf"] == 1340.0
    assert payload["summary"]["gaia_total"] == 60.3
    assert payload["summary"]["excel_total"] == 70.4
    assert payload["summary"]["gap_excel_gaia_total"] == 10.1
    assert payload["summary"]["gaia_total_anomalous_rows"] == 27.9
    assert payload["summary"]["excel_total_anomalous_rows"] == 38.0
    assert payload["summary"]["gaia_total_clean_rows"] == 32.4
    assert payload["summary"]["excel_total_clean_rows"] == 32.4
    assert payload["summary"]["distinct_ind_spese_fisse"] == [0.72, 1.24]
    assert payload["summary"]["distinct_imponibile_per_mq"] == [0.72, 1.24]

    comuni_by_name = {item["comune_nome"]: item for item in payload["comuni"]}
    assert comuni_by_name["Arborea"]["rows_count"] == 1
    assert comuni_by_name["Arborea"]["anomalous_rows_count"] == 1
    assert comuni_by_name["Arborea"]["gap_excel_gaia_total"] == 10.1
    assert comuni_by_name["Arborea"]["ruolo_0648"] == 12.5
    assert comuni_by_name["Arborea"]["ruolo_0985"] == 6.5
    assert comuni_by_name["Arborea"]["ruolo_total"] == 19.0
    assert comuni_by_name["Arborea"]["ruolo_matched_rows_count"] == 1
    assert comuni_by_name["Arborea"]["gaia_0648"] == 18.6
    assert comuni_by_name["Arborea"]["gaia_0985"] == 9.3
    assert comuni_by_name["Arborea"]["excel_0648"] == 25.0
    assert comuni_by_name["Arborea"]["excel_0985"] == 13.0
    assert comuni_by_name["Arborea"]["delta_ruolo_gaia_total"] == -8.9
    assert comuni_by_name["Arborea"]["delta_ruolo_excel_total"] == -19.0
    assert comuni_by_name["Marrubiu"]["rows_count"] == 1
    assert comuni_by_name["Marrubiu"]["anomalous_rows_count"] == 0
    assert comuni_by_name["Marrubiu"]["gap_excel_gaia_total"] == 0.0
    assert comuni_by_name["Marrubiu"]["ruolo_total"] == 30.0
    assert comuni_by_name["Marrubiu"]["delta_ruolo_gaia_total"] == -2.4

    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["comune_nome"] == "Arborea"
    assert payload["rows"][0]["particella"] == "200"
    assert payload["rows"][0]["subalterno"] == "1"
    assert payload["rows"][0]["source_filename"] == "capacitas-detail-2025.xlsx"
    assert payload["rows"][0]["gap_excel_gaia_total"] == 10.1
    assert payload["rows"][0]["ruolo_match_found"] is True
    assert payload["rows"][0]["ruolo_match_level"] == "exact"
    assert payload["rows"][0]["ruolo_partite_count"] == 1
    assert payload["rows"][0]["ruolo_comuni"] == ["Arborea"]
    assert payload["rows"][0]["ruolo_0648"] == 12.5
    assert payload["rows"][0]["ruolo_0985"] == 6.5
    assert payload["rows"][0]["ruolo_total"] == 19.0
    assert payload["rows"][0]["delta_ruolo_gaia_total"] == -8.9
    assert payload["rows"][0]["delta_ruolo_excel_total"] == -19.0
    assert payload["rows"][0]["anomalia_superficie"] is True
    assert payload["rows"][0]["anomalia_imponibile"] is True
    assert payload["rows"][0]["anomalia_importi"] is True
    assert payload["rows"][1]["comune_nome"] == "Marrubiu"
    assert payload["rows"][1]["cco"] == "CCO-1"
    assert payload["rows"][1]["cod_provincia"] == 95
    assert payload["rows"][1]["cod_comune_capacitas"] == 42
    assert payload["rows"][1]["cod_frazione"] == 7
    assert payload["rows"][1]["num_distretto"] == 3
    assert payload["rows"][1]["nome_distretto_loc"] == "Distretto Nord"
    assert payload["rows"][1]["sezione_catastale"] == "A"
    assert payload["rows"][1]["sup_catastale_mq"] == 1200.0
    assert payload["rows"][1]["codice_fiscale_raw"] == " rssmra80a01h501z "
    assert payload["rows"][1]["gap_excel_gaia_total"] == 0.0
    assert payload["rows"][1]["ruolo_match_found"] is True
    assert payload["rows"][1]["ruolo_match_level"] == "without_sub"
    assert payload["rows"][1]["ruolo_total"] == 30.0


def test_gaia_role_calculation_returns_expected_subject_aggregates() -> None:
    db = TestingSessionLocal()
    active_batch = CatImportBatch(
        filename="gaia-calcolo-2025.xlsx",
        tipo="capacitas_ruolo",
        anno_campagna=2025,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(active_batch)
    db.flush()
    active_batch_id = str(active_batch.id)

    db.add_all([
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="notice-rossi-2025",
            anno="2025",
            codice_fiscale="RSSMRA80A01H501Z",
            partita_iva=None,
            display_name="ROSSI MARIO",
            raw_detail_json={
                "partitario": {
                    "partite": [
                        {
                            "importo_0648_euro": "46.60",
                            "importo_0985_euro": "23.80",
                            "importo_0668_euro": "0.00",
                        }
                    ]
                }
            },
        ),
        AnagraficaPaymentNotice(
            source_system="incass",
            source_notice_id="notice-bianchi-2025",
            anno="2025",
            codice_fiscale="BNCLCU80A01H501Y",
            partita_iva=None,
            display_name="BIANCHI LUCA",
            raw_detail_json={
                "partitario": {
                    "partite": [
                        {
                            "importo_0648_euro": "8.64",
                            "importo_0985_euro": "4.32",
                            "importo_0668_euro": "0.00",
                        }
                    ]
                }
            },
        ),
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione="ROSSI MARIO",
            nome_comune="Marrubiu",
            sup_irrigabile_mq=1000,
            imponibile_sf=720,
            aliquota_0648=0.03,
            aliquota_0985=0.015,
            importo_0648=21.60,
            importo_0985=10.80,
            anomalia_imponibile=False,
            anomalia_importi=False,
        ),
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="RSSMRA80A01H501Z",
            denominazione="ROSSI MARIO",
            nome_comune="Arborea",
            sup_irrigabile_mq=500,
            imponibile_sf=620,
            aliquota_0648=0.03,
            aliquota_0985=0.015,
            importo_0648=25.00,
            importo_0985=13.00,
            anomalia_imponibile=True,
            anomalia_importi=True,
        ),
        CatUtenzaIrrigua(
            import_batch_id=active_batch.id,
            anno_campagna=2025,
            codice_fiscale="BNCLCU80A01H501Y",
            denominazione="BIANCHI LUCA",
            nome_comune="Marrubiu",
            sup_irrigabile_mq=400,
            imponibile_sf=288,
            aliquota_0648=0.03,
            aliquota_0985=0.015,
            importo_0648=8.64,
            importo_0985=4.32,
            anomalia_imponibile=False,
            anomalia_importi=False,
        ),
    ])
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/calcolo-gaia?anno=2025", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()

    assert payload["summary"]["anno_tributario"] == 2025
    assert payload["summary"]["active_batch_id"] == active_batch_id
    assert payload["summary"]["positions"] == 2
    assert payload["summary"]["ruolo_positions"] == 2
    assert payload["summary"]["positions_missing_tax_code"] == 0
    assert payload["summary"]["ruolo_positions_missing_tax_code"] == 0
    assert payload["summary"]["anomalous_positions"] == 1
    assert payload["summary"]["anomaly_driven_positions"] == 1
    assert payload["summary"]["total_rows"] == 3
    assert payload["summary"]["anomalous_rows"] == 1
    assert payload["summary"]["clean_rows"] == 2
    assert payload["summary"]["total_sup_irrigabile_mq"] == 1900.0
    assert payload["summary"]["total_imponibile_sf"] == 1628.0
    assert payload["summary"]["ruolo_totale_0648"] == 55.24
    assert payload["summary"]["gaia_totale_0648"] == 48.84
    assert payload["summary"]["ruolo_totale_0985"] == 28.12
    assert payload["summary"]["gaia_totale_0985"] == 24.42
    assert payload["summary"]["ruolo_totale_0668"] == 0.0
    assert payload["summary"]["ruolo_totale_confrontabile"] == 83.36
    assert payload["summary"]["gaia_totale_confrontabile"] == 73.26
    assert payload["summary"]["excel_totale_0648"] == 55.24
    assert payload["summary"]["excel_totale_0985"] == 28.12
    assert payload["summary"]["excel_totale_confrontabile"] == 83.36
    assert payload["summary"]["delta_ruolo_gaia_totale"] == 10.1
    assert payload["summary"]["gap_excel_gaia_totale"] == 10.1
    assert payload["summary"]["mismatch_positions"] == 1
    assert payload["summary"]["diagnosis_ruolo_count"] == 0
    assert payload["summary"]["diagnosis_gaia_count"] == 1
    assert payload["summary"]["diagnosis_excel_count"] == 0

    items_by_tax = {item["tax_code"]: item for item in payload["items"]}
    assert items_by_tax["RSSMRA80A01H501Z"]["display_name"] == "ROSSI MARIO"
    assert items_by_tax["RSSMRA80A01H501Z"]["ruolo_display_name"] == "ROSSI MARIO"
    assert items_by_tax["RSSMRA80A01H501Z"]["status"] == "amount_mismatch"
    assert items_by_tax["RSSMRA80A01H501Z"]["diagnosis"] == "problema_ricalcolo_gaia"
    assert items_by_tax["RSSMRA80A01H501Z"]["comuni_count"] == 2
    assert items_by_tax["RSSMRA80A01H501Z"]["rows_count"] == 2
    assert items_by_tax["RSSMRA80A01H501Z"]["anomalous_rows_count"] == 1
    assert items_by_tax["RSSMRA80A01H501Z"]["clean_rows_count"] == 1
    assert items_by_tax["RSSMRA80A01H501Z"]["ruolo_0648"] == 46.6
    assert items_by_tax["RSSMRA80A01H501Z"]["ruolo_0985"] == 23.8
    assert items_by_tax["RSSMRA80A01H501Z"]["ruolo_totale_confrontabile"] == 70.4
    assert items_by_tax["RSSMRA80A01H501Z"]["gaia_total"] == 60.3
    assert items_by_tax["RSSMRA80A01H501Z"]["excel_total"] == 70.4
    assert items_by_tax["RSSMRA80A01H501Z"]["delta_ruolo_gaia_totale"] == 10.1
    assert items_by_tax["RSSMRA80A01H501Z"]["gap_excel_gaia_total"] == 10.1
    assert items_by_tax["RSSMRA80A01H501Z"]["anomaly_gap_share"] == 100.0
    assert items_by_tax["RSSMRA80A01H501Z"]["anomaly_driven_case"] is True

    assert items_by_tax["BNCLCU80A01H501Y"]["status"] == "matched"
    assert items_by_tax["BNCLCU80A01H501Y"]["diagnosis"] == "allineato"
    assert items_by_tax["BNCLCU80A01H501Y"]["delta_ruolo_gaia_totale"] == 0.0

    filtered = client.get(
        "/ruolo/stats/calcolo-gaia?anno=2025&tax_code=RSSMRA80A01H501Z&anomalous_only=true",
        headers=auth_headers(),
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["summary"]["positions"] == 1
    assert len(filtered_payload["items"]) == 1
    assert filtered_payload["items"][0]["tax_code"] == "RSSMRA80A01H501Z"

    export_response = client.get(
        "/ruolo/stats/calcolo-gaia/export?anno=2025&anomalous_only=true&tax_code=RSSMRA80A01H501Z",
        headers=auth_headers(),
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "CF/PIVA" in export_response.text
    assert "Gap ruolo/GAIA" in export_response.text
    assert "RSSMRA80A01H501Z" in export_response.text


def test_stats_analytics_returns_breakdowns_for_selected_anno() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="ruolo_analytics_2025",
        status="completed",
    )
    linked_subject = AnagraficaSubject(source_name_raw="Impresa Agricola Test")
    db.add_all([job, linked_subject])
    db.flush()

    avviso = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-AN-001",
        anno_tributario=2025,
        subject_id=linked_subject.id,
        nominativo_raw="Impresa Agricola Test",
        importo_totale_0648=120.00,
        importo_totale_0985=30.00,
        importo_totale_0668=50.00,
        importo_totale_euro=200.00,
    )
    db.add(avviso)
    db.flush()

    partita = RuoloPartita(
        avviso_id=avviso.id,
        codice_partita="PART-01",
        comune_nome="Marrubiu",
        importo_0648=120.00,
        importo_0985=30.00,
        importo_0668=50.00,
    )
    db.add(partita)
    db.flush()

    db.add_all([
        RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            domanda_irrigua="23",
            distretto="10",
            foglio="1",
            particella="100",
            coltura="MAIS",
            cat_particella_id=uuid4(),
            cat_particella_match_status="matched",
            importo_manut=60.00,
        ),
        RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            domanda_irrigua="23",
            distretto="10",
            foglio="1",
            particella="101",
            coltura="MAIS",
            cat_particella_id=None,
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="no_cat_particella_match",
            ade_scan_classification="suppressed",
            importo_manut=60.00,
        ),
    ])
    db.commit()
    db.close()

    response = client.get("/ruolo/stats/analytics?anno=2025", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()

    assert payload["anno_tributario"] == 2025
    assert payload["particelle_summary"]["total_particelle"] == 2
    assert payload["particelle_summary"]["collegate_catasto"] == 1
    assert payload["particelle_summary"]["non_collegate_catasto"] == 1
    assert payload["particelle_summary"]["soppresse_ade"] == 1

    tributi = {item["key"]: item["amount"] for item in payload["tributi_breakdown"]}
    assert tributi == {"0648": 120.0, "0985": 30.0, "0668": 50.0}

    match_status = {item["key"]: item["count"] for item in payload["match_status_breakdown"]}
    assert match_status["matched"] == 1
    assert match_status["unmatched"] == 1

    match_reasons = {item["key"]: item["count"] for item in payload["match_reason_breakdown"]}
    assert match_reasons["no_cat_particella_match"] == 1

    distretti = {item["key"]: item["count"] for item in payload["distretto_breakdown"]}
    assert distretti["10"] == 2

    colture = {item["key"]: item["count"] for item in payload["coltura_breakdown"]}
    assert colture["MAIS"] == 2

    comuni = {item["comune_nome"]: item for item in payload["comuni"]}
    assert comuni["Marrubiu"]["num_avvisi"] == 1
    assert comuni["Marrubiu"]["num_partite"] == 1
    assert comuni["Marrubiu"]["num_particelle"] == 2
    assert comuni["Marrubiu"]["non_collegate_catasto"] == 1


def test_search_particelle_supports_match_status_and_match_reason_filters() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="ruolo_particelle_filter_2025",
        status="completed",
    )
    db.add(job)
    db.flush()

    avviso = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc="CNC-PART-001",
        anno_tributario=2025,
        nominativo_raw="Test Particelle",
        importo_totale_euro=150.00,
    )
    db.add(avviso)
    db.flush()

    partita = RuoloPartita(
        avviso_id=avviso.id,
        codice_partita="PT-01",
        comune_nome="Oristano",
    )
    db.add(partita)
    db.flush()

    db.add_all([
        RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            foglio="1",
            particella="100",
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="no_cat_particella_match",
        ),
        RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            foglio="1",
            particella="101",
            cat_particella_id=uuid4(),
            cat_particella_match_status="matched",
            cat_particella_match_reason="ruolo_sub_not_present_in_cat_particelle",
        ),
        RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            foglio="1",
            particella="102",
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="catasto_skipped",
        ),
    ])
    db.commit()
    db.close()

    response = client.get(
        "/ruolo/particelle?anno=2025&match_status=unmatched",
        headers=auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["particella"] for item in payload] == ["100", "102"]

    response = client.get(
        "/ruolo/particelle?anno=2025&match_reason=no_cat_particella_match",
        headers=auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["particella"] == "100"

    response = client.get(
        "/ruolo/particelle?anno=2025&match_status=unmatched&match_reason=catasto_skipped",
        headers=auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["particella"] == "102"


def test_search_particelle_filters_by_location_and_unmatched_only() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(anno_tributario=2025, filename="ruolo_particelle_location_2025", status="completed")
    db.add(job)
    db.flush()
    avviso = RuoloAvviso(import_job_id=job.id, codice_cnc="CNC-PART-LOCATION", anno_tributario=2025)
    db.add(avviso)
    db.flush()
    partita = RuoloPartita(avviso_id=avviso.id, codice_partita="P-LOCATION", comune_nome="ORISTANO")
    db.add(partita)
    db.flush()
    db.add_all(
        [
            RuoloParticella(
                partita_id=partita.id,
                anno_tributario=2025,
                foglio="9",
                particella="900",
                cat_particella_id=None,
            ),
            RuoloParticella(
                partita_id=partita.id,
                anno_tributario=2025,
                foglio="9",
                particella="901",
                cat_particella_id=uuid4(),
            ),
        ]
    )
    db.commit()
    db.close()

    response = client.get(
        "/ruolo/particelle?anno=2025&foglio=9&particella=900&comune=ORISTANO&unmatched_only=true",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["particella"] == "900"
