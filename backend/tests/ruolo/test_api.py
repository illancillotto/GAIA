from collections.abc import Generator
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
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.utenze.models import AnagraficaSubject


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
        filename="RUOLO_BONIFICA_2025.dmp",
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
    assert detail_payload["filename"] == "RUOLO_BONIFICA_2025.dmp"


def test_list_avvisi_supports_unified_search_query() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="RUOLO_BONIFICA_2025.dmp",
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


def test_stats_comuni_counts_distinct_avvisi_partite_and_particelle() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="RUOLO_STATS_2025.dmp",
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


def test_stats_analytics_returns_breakdowns_for_selected_anno() -> None:
    db = TestingSessionLocal()
    job = RuoloImportJob(
        anno_tributario=2025,
        filename="RUOLO_ANALYTICS_2025.dmp",
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
        filename="RUOLO_PARTICELLE_FILTER_2025.dmp",
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
