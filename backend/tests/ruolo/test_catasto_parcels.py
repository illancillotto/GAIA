from collections.abc import Generator
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.catasto import CatastoComune, CatastoParcel
from app.models.catasto_phase1 import CatParticella
from app.modules.ruolo.services.catasto_linking import (
    _normalize_comune_codice,
    _resolve_comune_codice_for_ruolo,
    _upsert_catasto_parcel,
    resolve_cat_particella_match,
)
from app.modules.ruolo.services import catasto_linking as catasto_linking_service


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


def test_normalize_comune_codice_handles_composite_sister_value() -> None:
    assert _normalize_comune_codice("F272#MOGORO#0#0") == "F272"


def test_normalize_comune_codice_keeps_short_plain_code() -> None:
    assert _normalize_comune_codice("A357") == "A357"


def test_normalize_comune_codice_handles_empty_and_embedded_codes() -> None:
    assert _normalize_comune_codice(None) is None
    assert _normalize_comune_codice("   ") is None
    assert _normalize_comune_codice("Comune catastale A357 Arborea") == "A357"
    assert _normalize_comune_codice("codice-sconosciuto-molto-lungo") == "CODICE-SCO"


def test_resolve_comune_codice_for_ruolo_falls_back_to_cat_particella_or_none() -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            CatParticella(
                cod_comune_capacitas=999,
                codice_catastale="Z999",
                nome_comune="COMUNE SOLO PARTICELLE",
                foglio="1",
                particella="1",
                is_current=True,
            )
        )
        db.commit()

        assert _resolve_comune_codice_for_ruolo(db, "Comune solo particelle") == "Z999"
        assert _resolve_comune_codice_for_ruolo(db, "Comune inesistente") is None
    finally:
        db.close()


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


def test_upsert_catasto_parcel_returns_none_without_required_keys_or_comune() -> None:
    db = TestingSessionLocal()
    try:
        assert (
            _upsert_catasto_parcel(
                db,
                comune_nome="ARBOREA",
                foglio="",
                particella="120",
                subalterno=None,
                sup_catastale_are=Decimal("95"),
                anno=2025,
            )
            is None
        )
        assert (
            _upsert_catasto_parcel(
                db,
                comune_nome="COMUNE INESISTENTE",
                foglio="5",
                particella="120",
                subalterno=None,
                sup_catastale_are=Decimal("95"),
                anno=2025,
            )
            is None
        )
    finally:
        db.close()


def test_upsert_catasto_parcel_reuses_current_when_surfaces_are_both_missing() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="12",
            particella="600",
            subalterno=None,
            sup_catastale_are=None,
            anno=2024,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="12",
            particella="600",
            subalterno=None,
            sup_catastale_are=None,
            anno=2025,
        )
        db.commit()

        assert second_id == first_id
        saved = db.get(CatastoParcel, first_id)
        assert saved is not None
        assert saved.valid_to is None
    finally:
        db.close()


def test_upsert_catasto_parcel_reuses_same_from_after_closing_previous_current() -> None:
    db = TestingSessionLocal()
    try:
        current = CatastoParcel(
            comune_codice="A357",
            comune_nome="ARBOREA",
            foglio="13",
            particella="601",
            subalterno=None,
            sup_catastale_are=100.0,
            sup_catastale_ha=1.0,
            valid_from=2024,
            valid_to=None,
            source="ruolo_import",
        )
        same_from = CatastoParcel(
            comune_codice="A357",
            comune_nome="ARBOREA",
            foglio="13",
            particella="601",
            subalterno=None,
            sup_catastale_are=None,
            sup_catastale_ha=None,
            valid_from=2025,
            valid_to=2025,
            source="ruolo_import",
        )
        db.add_all([current, same_from])
        db.commit()

        parcel_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="13",
            particella="601",
            subalterno=None,
            sup_catastale_are=Decimal("120"),
            anno=2025,
        )
        db.commit()

        assert parcel_id == same_from.id
        assert current.valid_to == 2024
        assert same_from.sup_catastale_are == 120.0
        assert float(same_from.sup_catastale_ha) == 1.2
    finally:
        db.close()


def test_upsert_catasto_parcel_updates_same_from_when_no_current_exists() -> None:
    db = TestingSessionLocal()
    try:
        same_from = CatastoParcel(
            comune_codice="A357",
            comune_nome="ARBOREA",
            foglio="14",
            particella="602",
            subalterno=None,
            sup_catastale_are=None,
            sup_catastale_ha=None,
            valid_from=2025,
            valid_to=2025,
            source="ruolo_import",
        )
        db.add(same_from)
        db.commit()

        parcel_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="14",
            particella="602",
            subalterno=None,
            sup_catastale_are=Decimal("130"),
            anno=2025,
        )
        db.commit()

        assert parcel_id == same_from.id
        assert same_from.sup_catastale_are == 130.0
        assert float(same_from.sup_catastale_ha) == 1.3
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


def test_resolve_cat_particella_match_exact_subalterno() -> None:
    db = TestingSessionLocal()
    try:
        particella = CatParticella(
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="ARBOREA",
            foglio="7",
            particella="99",
            subalterno="A",
            is_current=True,
        )
        db.add(particella)
        db.commit()

        particella_id, status, confidence, reason = resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="7",
            particella="99",
            subalterno="a",
        )

        assert particella_id == particella.id
        assert status == "matched"
        assert confidence == "exact_sub"
        assert reason is None
    finally:
        db.close()


def test_resolve_cat_particella_match_rejects_missing_key_and_sub_without_base() -> None:
    db = TestingSessionLocal()
    try:
        assert resolve_cat_particella_match(
            db,
            comune_codice=None,
            foglio="7",
            particella="99",
            subalterno=None,
        ) == (None, "unmatched", None, "missing_match_key")
        assert resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="7",
            particella="404",
            subalterno="A",
        ) == (None, "unmatched", None, "no_cat_particella_for_sub_or_base")
    finally:
        db.close()


def test_resolve_cat_particella_match_ambiguous_exact_subalterno() -> None:
    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                CatParticella(
                    cod_comune_capacitas=165,
                    codice_catastale="A357",
                    nome_comune="ARBOREA",
                    foglio="8",
                    particella="100",
                    subalterno="A",
                    is_current=True,
                ),
                CatParticella(
                    cod_comune_capacitas=165,
                    codice_catastale="A357",
                    nome_comune="ARBOREA",
                    foglio="8",
                    particella="100",
                    subalterno="A",
                    is_current=True,
                ),
            ]
        )
        db.commit()

        assert resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="8",
            particella="100",
            subalterno="A",
        ) == (None, "ambiguous", None, "multiple_exact_sub_matches")
    finally:
        db.close()


def test_resolve_cat_particella_match_ambiguous_base_without_sub() -> None:
    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                CatParticella(
                    cod_comune_capacitas=165,
                    codice_catastale="A357",
                    nome_comune="ARBOREA",
                    foglio="8",
                    particella="101",
                    subalterno=None,
                    is_current=True,
                ),
                CatParticella(
                    cod_comune_capacitas=165,
                    codice_catastale="A357",
                    nome_comune="ARBOREA",
                    foglio="8",
                    particella="101",
                    subalterno=None,
                    is_current=True,
                ),
            ]
        )
        db.commit()

        assert resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="8",
            particella="101",
            subalterno=None,
        ) == (None, "ambiguous", None, "multiple_base_matches")
    finally:
        db.close()


def test_resolve_cat_particella_match_detects_only_subalterno_variants() -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            CatParticella(
                cod_comune_capacitas=165,
                codice_catastale="A357",
                nome_comune="ARBOREA",
                foglio="8",
                particella="102",
                subalterno="A",
                is_current=True,
            )
        )
        db.commit()

        assert resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="8",
            particella="102",
            subalterno=None,
        ) == (None, "unmatched", None, "only_subalterno_variants_found")
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


def test_resolve_cat_particella_match_swaps_exact_sub_and_exact_no_sub() -> None:
    db = TestingSessionLocal()
    try:
        exact_sub = CatParticella(
            cod_comune_capacitas=280,
            codice_catastale="L122",
            nome_comune="TERRALBA",
            foglio="25",
            particella="11",
            subalterno="A",
            is_current=True,
        )
        exact_no_sub = CatParticella(
            cod_comune_capacitas=280,
            codice_catastale="L122",
            nome_comune="TERRALBA",
            foglio="25",
            particella="12",
            subalterno=None,
            is_current=True,
        )
        db.add_all([exact_sub, exact_no_sub])
        db.commit()

        assert resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="25",
            particella="11",
            subalterno="A",
        ) == (exact_sub.id, "matched", "swapped_exact_sub", "swapped_arborea_terralba")
        assert resolve_cat_particella_match(
            db,
            comune_codice="A357",
            foglio="25",
            particella="12",
            subalterno=None,
        ) == (exact_no_sub.id, "matched", "swapped_exact_no_sub", "swapped_arborea_terralba")
    finally:
        db.close()


def test_resolve_cat_particella_match_preserves_unknown_swapped_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    swapped_id = uuid4()
    calls: list[str | None] = []

    def fake_resolver(_db, *, comune_codice, **_kwargs):
        calls.append(comune_codice)
        if comune_codice == "A357":
            return None, "unmatched", None, "no_cat_particella_match"
        return swapped_id, "matched", "future_confidence", None

    monkeypatch.setattr(catasto_linking_service, "_resolve_cat_particella_match_for_code", fake_resolver)

    assert resolve_cat_particella_match(
        object(),
        comune_codice="A357",
        foglio="25",
        particella="13",
        subalterno=None,
    ) == (swapped_id, "matched", "future_confidence", "swapped_arborea_terralba")
    assert calls == ["A357", "L122"]


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
