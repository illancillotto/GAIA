from __future__ import annotations

from collections.abc import Generator
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto_phase1 import CatComune, CatParticella
from app.modules.catasto.services.irrigation_tariffs import (
    build_irrigation_tariff_preview,
    resolve_crop_rule,
    resolve_territorial_index,
)
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita


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


def setup_function() -> None:
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
    db.commit()
    db.close()


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "catasto-admin", "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_irrigation_tariff_preview_resolves_crop_and_territorial_matrix() -> None:
    crop_rule = resolve_crop_rule("Mais da foraggio")
    assert crop_rule is not None
    assert crop_rule.euro_ha_base_ib_1_00 == Decimal("80.00")

    assert resolve_territorial_index(nome_distretto="Lotto Sud Arborea", num_distretto="24", nome_comune="Arborea") == Decimal("1.24")
    assert resolve_territorial_index(nome_distretto="3 Distretto Terralba - Zona Morimenta", num_distretto="292", nome_comune="Mogoro") == Decimal("1.00")
    assert resolve_territorial_index(nome_distretto="Santa Lucia", num_distretto="12", nome_comune="Oristano") == Decimal("0.72")

    preview = build_irrigation_tariff_preview(
        coltura="Mais da foraggio",
        sup_irrigata_ha=Decimal("0.50"),
        nome_distretto="Lotto Sud Arborea",
        num_distretto="24",
        nome_comune="Arborea",
    )

    assert preview.crop_group_label == "Erbai, Medica, Mais, Sorgo"
    assert preview.indice_territoriale == Decimal("1.24")
    assert preview.euro_ha_base == Decimal("80.00")
    assert preview.euro_ha_finale == Decimal("99.2000")
    assert preview.euro_mc_finale == Decimal("0.0186")
    assert preview.importo_stimato == Decimal("49.600000")

    fallback_preview = build_irrigation_tariff_preview(
        coltura=None,
        sup_irrigata_ha=None,
        nome_distretto="Distretto sconosciuto",
        num_distretto="25",
        nome_comune="Arborea",
    )
    assert fallback_preview.crop_group_label is None
    assert fallback_preview.indice_territoriale == Decimal("1.24")
    assert fallback_preview.euro_ha_base is None
    assert fallback_preview.euro_ha_finale is None

    assert resolve_crop_rule("Coltura non censita") is None
    assert resolve_territorial_index(nome_distretto="Distretto sconosciuto", num_distretto="99", nome_comune="Comune ignoto") is None


def test_particella_detail_exposes_irrigation_tariff_preview_from_latest_ruolo() -> None:
    db = TestingSessionLocal()
    try:
        comune = CatComune(
            nome_comune="Arborea",
            codice_catastale="A357",
            cod_comune_capacitas=165,
            codice_comune_formato_numerico=115006,
            codice_comune_numerico_2017_2025=95006,
        )
        db.add(comune)
        db.flush()
        particella = CatParticella(
            comune_id=comune.id,
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="Arborea",
            foglio="7",
            particella="91",
            superficie_mq=Decimal("5000.00"),
            superficie_grafica_mq=Decimal("4900.00"),
            num_distretto="24",
            nome_distretto="Lotto Sud Arborea",
            source_type="ade_wfs",
            valid_from=date(2025, 1, 1),
            is_current=True,
        )
        db.add(particella)
        db.flush()
        ruolo_job = RuoloImportJob(anno_tributario=2025, status="completed")
        db.add(ruolo_job)
        db.flush()
        avviso = RuoloAvviso(import_job_id=ruolo_job.id, codice_cnc="CNC-IRR-001", anno_tributario=2025)
        db.add(avviso)
        db.flush()
        partita = RuoloPartita(avviso_id=avviso.id, codice_partita="P-IRR-001", comune_nome="Arborea")
        db.add(partita)
        db.flush()
        db.add(
            RuoloParticella(
                partita_id=partita.id,
                anno_tributario=2025,
                domanda_irrigua="D-2025",
                distretto="24",
                foglio="7",
                particella="91",
                sup_catastale_ha=Decimal("0.5000"),
                sup_irrigata_ha=Decimal("0.5000"),
                coltura="Mais",
                importo_manut=Decimal("12.00"),
                importo_irrig=Decimal("30.00"),
                importo_ist=Decimal("4.00"),
                cat_particella_id=particella.id,
            )
        )
        db.commit()
        particella_id = str(particella.id)
    finally:
        db.close()

    response = client.get(f"/catasto/particelle/{particella_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["indice_irriguo_coltura"] == "Mais"
    assert payload["indice_irriguo_gruppo_coltura"] == "Erbai, Medica, Mais, Sorgo"
    assert payload["indice_irriguo_sup_irrigata_ha"] == "0.5000"
    assert payload["indice_irriguo_base"] == "80.00"
    assert payload["indice_irriguo_moltiplicatore"] == "1.24"
    assert payload["indice_irriguo_finale"] == "99.2000"
    assert payload["indice_irriguo_euro_mc"] == "0.0186"
    assert payload["indice_irriguo_importo_stimato"] == "49.60000000"
    assert payload["indice_irriguo_anno_riferimento"] == 2025
    assert payload["indice_irriguo_comune_arborea"] is True


def test_particella_detail_defaults_irrigation_preview_when_ruolo_missing() -> None:
    db = TestingSessionLocal()
    try:
        comune = CatComune(
            nome_comune="Mogoro",
            codice_catastale="F272",
            cod_comune_capacitas=50,
            codice_comune_formato_numerico=111111,
            codice_comune_numerico_2017_2025=222222,
        )
        db.add(comune)
        db.flush()
        particella = CatParticella(
            comune_id=comune.id,
            cod_comune_capacitas=50,
            codice_catastale="F272",
            nome_comune="Mogoro",
            foglio="1",
            particella="3971",
            superficie_grafica_mq=Decimal("100.00"),
            num_distretto="293",
            nome_distretto="3 Distretto Terralba - Zona Uras",
            source_type="ade_wfs",
            valid_from=date(2025, 1, 1),
            is_current=True,
        )
        db.add(particella)
        db.commit()
        particella_id = str(particella.id)
    finally:
        db.close()

    response = client.get(f"/catasto/particelle/{particella_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["indice_irriguo_base"] is None
    assert payload["indice_irriguo_finale"] is None
    assert payload["indice_irriguo_coltura"] is None
    assert payload["indice_irriguo_anno_riferimento"] is None
    assert payload["indice_irriguo_moltiplicatore"] == "1.00"
    assert payload["indice_irriguo_euro_mc"] == "0.0150"
    assert payload["indice_irriguo_comune_arborea"] is False
