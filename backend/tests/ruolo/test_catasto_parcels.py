from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.catasto import CatastoComune, CatastoParcel
from app.models.catasto_phase1 import CatParticella
from app.modules.ruolo.services.import_service import _upsert_catasto_parcel, resolve_cat_particella_match


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(CatastoComune(nome="MOGORO", codice_sister="F272#MOGORO#0#0", ufficio="ORISTANO Territorio"))
    db.add(CatastoComune(nome="Arborea", codice_sister="A357#ARBOREA#3#0", ufficio="ORISTANO Territorio"))
    db.add(CatastoComune(nome="Palmas Arborea", codice_sister="G286#PALMAS ARBOREA#0#0", ufficio="ORISTANO Territorio"))
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


def test_upsert_catasto_parcel_creates_new_current_record() -> None:
    db = TestingSessionLocal()
    try:
        parcel_id = _upsert_catasto_parcel(
            db,
            comune_nome="MOGORO",
            foglio="35",
            particella="41",
            subalterno="A",
            sup_catastale_are=Decimal("100"),
            anno=2025,
        )
        db.commit()

        saved = db.get(CatastoParcel, parcel_id)
        assert saved is not None
        assert saved.comune_codice == "F272"
        assert saved.valid_from == 2025
        assert saved.valid_to is None
        assert float(saved.sup_catastale_are) == 100.0
        assert float(saved.sup_catastale_ha) == 1.0
    finally:
        db.close()


def test_upsert_catasto_parcel_same_year_reuses_existing_record() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="5",
            particella="120",
            subalterno=None,
            sup_catastale_are=Decimal("95"),
            anno=2025,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="5",
            particella="120",
            subalterno=None,
            sup_catastale_are=Decimal("97"),
            anno=2025,
        )
        db.commit()

        rows = db.scalars(select(CatastoParcel)).all()
        assert second_id == first_id
        assert len(rows) == 1
        assert rows[0].valid_from == 2025
        assert rows[0].valid_to is None
    finally:
        db.close()


def test_upsert_catasto_parcel_prefers_exact_comune_over_partial_name() -> None:
    db = TestingSessionLocal()
    try:
        parcel_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="13",
            particella="29",
            subalterno="A",
            sup_catastale_are=Decimal("100"),
            anno=2025,
        )
        db.commit()

        saved = db.get(CatastoParcel, parcel_id)
        assert saved is not None
        assert saved.comune_codice == "A357"
        assert saved.comune_nome == "ARBOREA"
    finally:
        db.close()


def test_upsert_catasto_parcel_next_year_same_surface_keeps_current_record() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="7",
            particella="98",
            subalterno=None,
            sup_catastale_are=Decimal("250"),
            anno=2024,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="7",
            particella="98",
            subalterno=None,
            sup_catastale_are=Decimal("250"),
            anno=2025,
        )
        db.commit()

        rows = db.scalars(select(CatastoParcel)).all()
        assert second_id == first_id
        assert len(rows) == 1
        assert rows[0].valid_from == 2024
        assert rows[0].valid_to is None
    finally:
        db.close()


def test_upsert_catasto_parcel_next_year_different_surface_versions_record() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="MOGORO",
            foglio="28",
            particella="18",
            subalterno="A",
            sup_catastale_are=Decimal("2025"),
            anno=2024,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="MOGORO",
            foglio="28",
            particella="18",
            subalterno="A",
            sup_catastale_are=Decimal("2030"),
            anno=2025,
        )
        db.commit()

        rows = db.scalars(
            select(CatastoParcel).order_by(CatastoParcel.valid_from.asc())
        ).all()
        assert second_id != first_id
        assert len(rows) == 2
        assert rows[0].valid_from == 2024
        assert rows[0].valid_to == 2024
        assert float(rows[0].sup_catastale_are) == 2025.0
        assert rows[1].valid_from == 2025
        assert rows[1].valid_to is None
        assert float(rows[1].sup_catastale_are) == 2030.0
    finally:
        db.close()


def test_upsert_catasto_parcel_same_year_updates_missing_surface() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="11",
            particella="525",
            subalterno=None,
            sup_catastale_are=None,
            anno=2025,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="11",
            particella="525",
            subalterno=None,
            sup_catastale_are=Decimal("7300"),
            anno=2025,
        )
        db.commit()

        saved = db.get(CatastoParcel, first_id)
        assert second_id == first_id
        assert saved is not None
        assert float(saved.sup_catastale_are) == 7300.0
        assert float(saved.sup_catastale_ha) == 73.0
    finally:
        db.close()


def test_resolve_cat_particella_match_exact_base_without_sub() -> None:
    db = TestingSessionLocal()
    try:
        particella = CatParticella(
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="ARBOREA",
            foglio="11",
            particella="525",
            subalterno=None,
            is_current=True,
        )
        db.add(particella)
        db.commit()

        particella_id, status, confidence, reason = resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="11",
            particella="525",
            subalterno=None,
        )

        assert particella_id == particella.id
        assert status == "matched"
        assert confidence == "exact_no_sub"
        assert reason is None
    finally:
        db.close()


def test_resolve_cat_particella_match_role_sub_falls_back_to_base_parcel() -> None:
    db = TestingSessionLocal()
    try:
        particella = CatParticella(
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="ARBOREA",
            foglio="7",
            particella="98",
            subalterno=None,
            is_current=True,
        )
        db.add(particella)
        db.commit()

        particella_id, status, confidence, reason = resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="7",
            particella="98",
            subalterno="A",
        )

        assert particella_id == particella.id
        assert status == "matched"
        assert confidence == "base_without_sub"
        assert reason == "ruolo_sub_not_present_in_cat_particelle"
    finally:
        db.close()


def test_resolve_cat_particella_match_swaps_arborea_terralba_when_source_missing() -> None:
    db = TestingSessionLocal()
    try:
        particella = CatParticella(
            cod_comune_capacitas=280,
            codice_catastale="L122",
            nome_comune="TERRALBA",
            foglio="25",
            particella="10",
            subalterno=None,
            is_current=True,
        )
        db.add(particella)
        db.commit()

        particella_id, status, confidence, reason = resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="25",
            particella="10",
            subalterno="E",
        )

        assert particella_id == particella.id
        assert status == "matched"
        assert confidence == "swapped_base_without_sub"
        assert reason == "swapped_arborea_terralba"
    finally:
        db.close()


def test_resolve_cat_particella_match_respects_oristano_frazione_section_hint() -> None:
    db = TestingSessionLocal()
    try:
        wrong_section = CatParticella(
            cod_comune_capacitas=200,
            codice_catastale="G113",
            nome_comune="ORISTANO",
            sezione_catastale="D",
            foglio="2",
            particella="272",
            subalterno=None,
            is_current=True,
        )
        sili_section = CatParticella(
            cod_comune_capacitas=200,
            codice_catastale="G113",
            nome_comune="ORISTANO",
            sezione_catastale="E",
            foglio="2",
            particella="272",
            subalterno=None,
            is_current=True,
        )
        db.add_all([wrong_section, sili_section])
        db.commit()

        particella_id, status, confidence, reason = resolve_cat_particella_match(
            db,
            comune_codice="G113",
            foglio="2",
            particella="272",
            subalterno=None,
            sezione_catastale="E",
        )

        assert particella_id == sili_section.id
        assert particella_id != wrong_section.id
        assert status == "matched"
        assert confidence == "exact_no_sub"
        assert reason is None
    finally:
        db.close()


def test_resolve_cat_particella_match_section_hint_prevents_wrong_frazione_link() -> None:
    db = TestingSessionLocal()
    try:
        wrong_section = CatParticella(
            cod_comune_capacitas=200,
            codice_catastale="G113",
            nome_comune="ORISTANO",
            sezione_catastale="D",
            foglio="2",
            particella="272",
            subalterno=None,
            is_current=True,
        )
        db.add(wrong_section)
        db.commit()

        particella_id, status, confidence, reason = resolve_cat_particella_match(
            db,
            comune_codice="G113",
            foglio="2",
            particella="272",
            subalterno=None,
            sezione_catastale="E",
        )

        assert particella_id is None
        assert status == "unmatched"
        assert confidence is None
        assert reason == "no_cat_particella_match"
    finally:
        db.close()


def test_resolve_cat_particella_match_keeps_ambiguous_base_unlinked() -> None:
    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                CatParticella(
                    cod_comune_capacitas=165,
                    codice_catastale="A357",
                    nome_comune="ARBOREA",
                    foglio="9",
                    particella="877",
                    subalterno=None,
                    is_current=True,
                ),
                CatParticella(
                    cod_comune_capacitas=165,
                    codice_catastale="A357",
                    nome_comune="ARBOREA",
                    foglio="9",
                    particella="877",
                    subalterno=None,
                    is_current=True,
                ),
            ]
        )
        db.commit()

        particella_id, status, confidence, reason = resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="9",
            particella="877",
            subalterno="I",
        )

        assert particella_id is None
        assert status == "ambiguous"
        assert confidence is None
        assert reason == "multiple_base_matches_for_ruolo_sub"
    finally:
        db.close()
