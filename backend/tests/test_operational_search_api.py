from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto import CatastoDocument
from app.models.catasto_phase1 import CatImportBatch, CatParticella, CatUtenzaIntestatario, CatUtenzaIrrigua
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob
from app.modules.search.service import search_operational
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPaymentNotice, AnagraficaPerson, AnagraficaSubject


engine = create_engine(
    "sqlite://",
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


def setup_function() -> None:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _create_user(
    username: str,
    *,
    role: str = ApplicationUserRole.ADMIN.value,
    module_utenze: bool = True,
    module_ruolo: bool = True,
    module_catasto: bool = True,
) -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash=hash_password("secret123"),
        role=role,
        is_active=True,
        module_utenze=module_utenze,
        module_ruolo=module_ruolo,
        module_catasto=module_catasto,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _auth_headers(username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_search_rows(user_id: int) -> None:
    db = TestingSessionLocal()
    subject_id = uuid4()
    piras_subject_id = uuid4()
    subject = AnagraficaSubject(id=subject_id, source_name_raw="Rossi Mario")
    piras_subject = AnagraficaSubject(id=piras_subject_id, source_name_raw="Piras Aldo")
    person = AnagraficaPerson(subject_id=subject_id, cognome="Rossi", nome="Mario", codice_fiscale="RSSMRA80A01H501U")
    piras_person = AnagraficaPerson(subject_id=piras_subject_id, cognome="Piras", nome="Aldo", codice_fiscale="PRSALD59L01F272U")
    company = AnagraficaCompany(subject_id=uuid4(), ragione_sociale="Rossi Agricola", partita_iva="01234567890")
    notice = AnagraficaPaymentNotice(
        subject_id=subject_id,
        source_system="incass",
        source_notice_id="ROSSI-NOTICE-1",
        display_name="Rossi Mario",
        codice_fiscale="RSSMRA80A01H501U",
        anno="2026",
        stato_label="Da pagare",
    )
    job = RuoloImportJob(anno_tributario=2026, filename="ruolo-rossi.txt", status="completed")
    particella = CatParticella(
        id=uuid4(),
        cod_comune_capacitas=95,
        nome_comune="Oristano",
        foglio="12",
        particella="345",
        cfm="ROSSI-CFM",
    )
    piras_particella = CatParticella(
        id=uuid4(),
        cod_comune_capacitas=95,
        nome_comune="Oristano",
        foglio="14",
        particella="789",
        cfm="PIRAS-CFM",
    )
    intestatario_only_particella = CatParticella(
        id=uuid4(),
        cod_comune_capacitas=95,
        nome_comune="Oristano",
        foglio="15",
        particella="900",
        cfm="INTESTATARIO-CFM",
    )
    catasto_batch = CatImportBatch(filename="capacitas-piras.xlsx", tipo="capacitas", anno_campagna=2026, status="completed")
    document = CatastoDocument(
        id=uuid4(),
        user_id=user_id,
        tipo_visura="storica",
        filename="visura-rossi.pdf",
        filepath="/tmp/visura-rossi.pdf",
        intestazione="Rossi Mario",
        codice_fiscale="RSSMRA80A01H501U",
        comune="Oristano",
        foglio="12",
        particella="345",
    )
    db.add_all([
        subject,
        piras_subject,
        person,
        piras_person,
        company,
        notice,
        job,
        particella,
        piras_particella,
        intestatario_only_particella,
        catasto_batch,
        document,
    ])
    db.flush()
    piras_utenza = CatUtenzaIrrigua(
        import_batch_id=catasto_batch.id,
        anno_campagna=2026,
        cod_comune_capacitas=95,
        nome_comune="Oristano",
        foglio="14",
        particella="789",
        particella_id=piras_particella.id,
        denominazione="Piras Aldo",
        codice_fiscale="PRSALD59L01F272U",
    )
    db.add(piras_utenza)
    db.flush()
    db.add(
        CatUtenzaIntestatario(
            utenza_id=piras_utenza.id,
            subject_id=piras_subject_id,
            anno_riferimento=2026,
            codice_fiscale="PRSALD59L01F272U",
            denominazione="Piras Aldo",
            comune_residenza="Oristano",
            collected_at=datetime.now(UTC),
        )
    )
    intestatario_only_utenza = CatUtenzaIrrigua(
        import_batch_id=catasto_batch.id,
        anno_campagna=2026,
        cod_comune_capacitas=95,
        nome_comune="Oristano",
        foglio="15",
        particella="900",
        particella_id=intestatario_only_particella.id,
        denominazione="Occupante generico",
        codice_fiscale="GENERIC000000000",
    )
    db.add(intestatario_only_utenza)
    db.flush()
    db.add(
        CatUtenzaIntestatario(
            utenza_id=intestatario_only_utenza.id,
            anno_riferimento=2026,
            codice_fiscale="VRDLGU59L01F272U",
            denominazione="Verdi Luigi",
            comune_residenza="Oristano",
            collected_at=datetime.now(UTC),
        )
    )
    db.add(
        RuoloAvviso(
            import_job_id=job.id,
            codice_cnc="ROSSI-CNC-1",
            anno_tributario=2026,
            subject_id=subject_id,
            codice_fiscale_raw="RSSMRA80A01H501U",
            nominativo_raw="Rossi Mario",
            codice_utenza="ROSSI-UT-1",
        )
    )
    db.add(
        RuoloAvviso(
            import_job_id=job.id,
            codice_cnc="PIRAS-CNC-1",
            anno_tributario=2026,
            subject_id=piras_subject_id,
            codice_fiscale_raw="PRSALD59L01F272U",
            nominativo_raw="Piras Aldo",
            codice_utenza="PIRAS-UT-1",
        )
    )
    db.commit()
    db.close()


def test_operational_search_returns_grouped_domain_hits() -> None:
    user = _create_user("search-admin")
    _seed_search_rows(user.id)

    response = client.get("/search?q=rossi&limit=20", headers=_auth_headers("search-admin"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "rossi"
    assert payload["modules"] == ["utenze", "ruolo", "catasto"]
    result_types = {(item["module"], item["type"]) for item in payload["items"]}
    assert ("utenze", "subject_person") in result_types
    assert ("utenze", "subject_company") in result_types
    assert ("utenze", "payment_notice") in result_types
    assert ("ruolo", "avviso") in result_types
    assert ("catasto", "particella") in result_types
    assert ("catasto", "document") in result_types
    assert payload["items"][0]["score"] >= payload["items"][-1]["score"]


def test_operational_search_is_available_under_api_prefix() -> None:
    user = _create_user("search-api-prefix")
    _seed_search_rows(user.id)

    response = client.get("/api/search?q=rossi&limit=3", headers=_auth_headers("search-api-prefix"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "rossi"
    assert payload["items"]


def test_operational_search_matches_multitoken_names_across_enabled_domains() -> None:
    user = _create_user("search-multitoken")
    _seed_search_rows(user.id)

    response = client.get("/api/search?q=piras%20al&limit=20", headers=_auth_headers("search-multitoken"))

    assert response.status_code == 200
    payload = response.json()
    result_types = {(item["module"], item["type"]) for item in payload["items"]}
    assert ("utenze", "subject_person") in result_types
    assert ("ruolo", "avviso") in result_types
    assert ("catasto", "particella") in result_types


def test_operational_search_finds_catasto_from_intestatari_and_deduplicates_particelle() -> None:
    user = _create_user("search-catasto-intestatari")
    _seed_search_rows(user.id)

    intestatari_response = client.get("/api/search?q=verdi%20lu&limit=20", headers=_auth_headers("search-catasto-intestatari"))
    assert intestatari_response.status_code == 200
    intestatari_payload = intestatari_response.json()
    assert ("catasto", "particella") in {(item["module"], item["type"]) for item in intestatari_payload["items"]}

    duplicate_response = client.get("/api/search?q=14&limit=20", headers=_auth_headers("search-catasto-intestatari"))
    assert duplicate_response.status_code == 200
    catasto_particelle = [
        item for item in duplicate_response.json()["items"]
        if item["module"] == "catasto" and item["type"] == "particella" and item["metadata"]["particella"] == "789"
    ]
    assert len(catasto_particelle) == 1


def test_operational_search_respects_enabled_modules() -> None:
    user = _create_user("utenze-only", module_ruolo=False, module_catasto=False)
    _seed_search_rows(user.id)

    response = client.get("/search?q=rossi", headers=_auth_headers("utenze-only"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["modules"] == ["utenze"]
    assert {item["module"] for item in payload["items"]} == {"utenze"}


def test_operational_search_handles_super_admin_and_empty_query() -> None:
    user = _create_user("root-search", role=ApplicationUserRole.SUPER_ADMIN.value, module_utenze=False, module_ruolo=False, module_catasto=False)
    db = TestingSessionLocal()
    try:
        empty = search_operational(db, user, "   ")
        assert empty.model_dump() == {"query": "", "items": [], "total": 0, "modules": []}
        visible_modules = search_operational(db, user, "missing").modules
        assert visible_modules == ["utenze", "ruolo", "catasto"]
    finally:
        db.close()
