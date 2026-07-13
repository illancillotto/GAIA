from collections.abc import Generator
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import require_active_user
from app.core.database import get_db
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto_phase1 import CatDistretto, CatParticella, CatParticellaHistory
from app.modules.catasto.services.indici_overview import build_ruolo_excluded_particelle, build_ruolo_reconciliation
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
client = TestClient(app)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def active_user() -> ApplicationUser:
    return ApplicationUser(
        username="catasto-test",
        email="catasto-test@example.local",
        password_hash="unused",
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_catasto=True,
    )


def setup_function() -> None:
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_active_user] = active_user
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def seed_excluded_role_particles() -> None:
    db = TestingSessionLocal()
    try:
        db.add(CatDistretto(num_distretto="01", nome_distretto="Distretto Uno", attivo=True))
        ruolo_job = RuoloImportJob(anno_tributario=2033, status="completed")
        db.add(ruolo_job)
        db.flush()
        avviso = RuoloAvviso(
            import_job_id=ruolo_job.id,
            codice_cnc="CNC-ESCLUSI",
            anno_tributario=2033,
            nominativo_raw="Azienda esclusa",
        )
        db.add(avviso)
        db.flush()
        partita = RuoloPartita(
            avviso_id=avviso.id,
            codice_partita="PARTITA-ESCLUSA",
            comune_nome="Arborea",
        )
        db.add(partita)
        db.flush()
        no_distretto = CatParticella(
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="Arborea",
            foglio="70",
            particella="200",
            num_distretto=None,
            nome_distretto=None,
            superficie_mq=Decimal("10000"),
            is_current=True,
        )
        included = CatParticella(
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="Arborea",
            foglio="70",
            particella="300",
            num_distretto="01",
            nome_distretto="Distretto",
            superficie_mq=Decimal("10000"),
            is_current=True,
        )
        swapped_no_distretto = CatParticella(
            cod_comune_capacitas=280,
            codice_catastale="L122",
            nome_comune="Terralba",
            foglio="70",
            particella="400",
            num_distretto=None,
            nome_distretto=None,
            superficie_mq=Decimal("10000"),
            is_current=True,
        )
        db.add_all([no_distretto, included, swapped_no_distretto])
        db.flush()
        db.add_all(
            [
                RuoloParticella(
                    partita_id=partita.id,
                    cat_particella_id=None,
                    anno_tributario=2033,
                    foglio="70",
                    particella="150",
                    sup_irrigata_ha=Decimal("0.2"),
                    importo_manut=Decimal("11"),
                    importo_irrig=Decimal("22"),
                    importo_ist=Decimal("33"),
                ),
                RuoloParticella(
                    partita_id=partita.id,
                    cat_particella_id=no_distretto.id,
                    anno_tributario=2033,
                    foglio="70",
                    particella="200",
                    sup_irrigata_ha=Decimal("0.3"),
                    importo_manut=Decimal("7"),
                    importo_irrig=Decimal("8"),
                    importo_ist=Decimal("9"),
                ),
                RuoloParticella(
                    partita_id=partita.id,
                    cat_particella_id=included.id,
                    anno_tributario=2033,
                    foglio="70",
                    particella="300",
                    sup_irrigata_ha=Decimal("0.4"),
                    importo_manut=Decimal("1"),
                    importo_irrig=Decimal("2"),
                    importo_ist=Decimal("3"),
                ),
                RuoloParticella(
                    partita_id=partita.id,
                    cat_particella_id=swapped_no_distretto.id,
                    cat_particella_match_reason="swapped_arborea_terralba",
                    anno_tributario=2033,
                    foglio="70",
                    particella="400",
                    sup_irrigata_ha=Decimal("0.1"),
                    importo_manut=Decimal("4"),
                    importo_irrig=Decimal("5"),
                    importo_ist=Decimal("6"),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


def test_build_ruolo_excluded_particelle_groups_only_excluded_rows() -> None:
    seed_excluded_role_particles()
    db = TestingSessionLocal()
    try:
        payload = build_ruolo_excluded_particelle(db, 2033)
    finally:
        db.close()

    assert payload.anno_riferimento == 2033
    assert payload.total == 3
    assert [item.reason_key for item in payload.items] == [
        "non_collegata",
        "senza_distretto",
        "swapped_arborea_terralba",
    ]
    assert payload.items[0].avvisi == ["CNC-ESCLUSI"]
    assert payload.items[0].nominativi == ["Azienda esclusa"]
    assert payload.items[0].partite == ["PARTITA-ESCLUSA"]
    assert payload.items[0].importo_ruolo == Decimal("66")
    assert payload.items[1].catasto_is_current is True
    assert payload.items[1].catasto_num_distretto is None
    assert payload.items[1].importo_ruolo == Decimal("24")
    assert payload.items[2].reason_label == "Particella Arborea/Terralba risolta sul comune storico alternativo"
    assert payload.items[2].importo_ruolo == Decimal("15")


def test_build_ruolo_reconciliation_reports_swapped_arborea_terralba_separately() -> None:
    seed_excluded_role_particles()
    db = TestingSessionLocal()
    try:
        payload = build_ruolo_reconciliation(db, 2033)
    finally:
        db.close()

    reasons = {item.key: item for item in payload.reasons}
    assert reasons["swapped_arborea_terralba"].righe_ruolo_count == 1
    assert reasons["swapped_arborea_terralba"].importo_ruolo == Decimal("15")
    assert reasons["senza_distretto"].righe_ruolo_count == 1


def test_build_ruolo_excluded_particelle_handles_missing_year_and_blank_labels() -> None:
    db = TestingSessionLocal()
    try:
        assert build_ruolo_excluded_particelle(db, None).items == []

        ruolo_job = RuoloImportJob(anno_tributario=2034, status="completed")
        db.add(ruolo_job)
        db.flush()
        avviso = RuoloAvviso(
            import_job_id=ruolo_job.id,
            codice_cnc=" ",
            anno_tributario=2034,
            nominativo_raw=None,
        )
        db.add(avviso)
        db.flush()
        partita = RuoloPartita(
            avviso_id=avviso.id,
            codice_partita="",
            comune_nome="Arborea",
        )
        db.add(partita)
        db.flush()
        db.add_all(
            [
                RuoloParticella(
                    partita_id=partita.id,
                    cat_particella_id=None,
                    anno_tributario=2034,
                    foglio="80",
                    particella="900",
                    sup_irrigata_ha=Decimal("0.1"),
                    importo_manut=Decimal("1"),
                    importo_irrig=Decimal("2"),
                    importo_ist=Decimal("3"),
                ),
                RuoloParticella(
                    partita_id=partita.id,
                    cat_particella_id=None,
                    anno_tributario=2034,
                    foglio="80",
                    particella="900",
                    sup_irrigata_ha=Decimal("0.2"),
                    importo_manut=Decimal("4"),
                    importo_irrig=Decimal("5"),
                    importo_ist=Decimal("6"),
                ),
            ]
        )
        db.commit()

        payload = build_ruolo_excluded_particelle(db, 2034)
    finally:
        db.close()

    assert payload.total == 1
    assert payload.items[0].righe_ruolo_count == 2
    assert payload.items[0].avvisi == []
    assert payload.items[0].nominativi == []
    assert payload.items[0].partite == []
    assert payload.items[0].importo_ruolo == Decimal("21")


def test_get_indici_ruolo_esclusi_endpoint() -> None:
    seed_excluded_role_particles()

    response = client.get("/catasto/indici/ruolo-esclusi?anno=2033")

    assert response.status_code == 200
    body = response.json()
    assert body["anno_riferimento"] == 2033
    assert body["total"] == 3
    assert body["items"][0]["reason_key"] == "non_collegata"
    assert body["items"][0]["importo_ruolo"] == "66.00"


def test_assign_distretto_to_ruolo_excluded_particella_updates_current_catasto_and_history() -> None:
    seed_excluded_role_particles()
    db = TestingSessionLocal()
    try:
        particella = db.query(CatParticella).filter(CatParticella.particella == "200").one()
        distretto = db.query(CatDistretto).filter(CatDistretto.num_distretto == "01").one()
        particella_id = str(particella.id)
        distretto_id = str(distretto.id)
    finally:
        db.close()

    response = client.post(
        "/catasto/indici/ruolo-esclusi/assegna-distretto",
        json={
            "cat_particella_id": particella_id,
            "distretto_id": distretto_id,
            "note": "Verifica operatore distretto 01",
        },
    )

    assert response.status_code == 200
    assert response.json()["updated"] is True
    assert response.json()["num_distretto"] == "01"
    db = TestingSessionLocal()
    try:
        cat_particella_uuid = UUID(particella_id)
        updated = db.get(CatParticella, cat_particella_uuid)
        assert updated is not None
        assert updated.num_distretto == "01"
        assert updated.nome_distretto == "Distretto Uno"
        history = db.query(CatParticellaHistory).filter(CatParticellaHistory.particella_id == cat_particella_uuid).one()
        assert history.num_distretto is None
        assert history.change_reason == "Verifica operatore distretto 01"
    finally:
        db.close()
