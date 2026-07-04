from __future__ import annotations

from collections import Counter
from collections.abc import Generator
from datetime import date
from decimal import Decimal
from pathlib import Path
import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
import app.db.base  # noqa: F401 - ensure all FK targets are registered in Base.metadata
from app.models.catasto_phase1 import (
    CatCapacitasGridRow,
    CatCapacitasGridSnapshot,
    CatComune,
    CatConsorzioOccupancy,
    CatConsorzioUnit,
    CatParticella,
)
from app.services.capacitas_consorzio_grid_import import (
    CapacitasGridImportOptions,
    GRID_REQUIRED_COLUMNS,
    GRID_SOURCE_TYPE,
    GridRow,
    ImportRuntime,
    UnitResolution,
    _clean_text,
    _find_official_particella,
    _find_source_comune,
    _find_subject_by_tax_identifier,
    _json_safe_value,
    _normalize_cco,
    _normalize_fixed_width,
    _normalize_numeric_text,
    _normalize_sub,
    _occupancy_key,
    _row_report,
    _to_decimal,
    _to_int,
    _update_unit,
    _uuid_or_none,
    build_runtime,
    find_or_create_occupancy,
    process_grid_row,
    parse_capacitas_grid_xlsx,
    resolve_unit_target,
    run_capacitas_consorzio_grid_import,
)


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    arborea = CatComune(
        nome_comune="Arborea",
        codice_catastale="A357",
        cod_comune_capacitas=165,
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    terralba = CatComune(
        nome_comune="Terralba",
        codice_catastale="L122",
        cod_comune_capacitas=280,
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    db.add_all([arborea, terralba])
    db.flush()
    db.add(
        CatParticella(
            comune_id=terralba.id,
            cod_comune_capacitas=280,
            codice_catastale="L122",
            nome_comune="Terralba",
            foglio="10",
            particella="20",
            subalterno=None,
            is_current=True,
            superficie_mq=1000,
            source_type="ade_wfs",
        )
    )
    db.add(
        CatParticella(
            comune_id=arborea.id,
            cod_comune_capacitas=165,
            codice_catastale="A357",
            nome_comune="Arborea",
            foglio="11",
            particella="21",
            subalterno="1",
            is_current=True,
            superficie_mq=2000,
            source_type="ade_wfs",
        )
    )
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _write_grid(path: Path, rows: list[dict[str, object]]) -> Path:
    defaults = {
        "CODICE": "A357",
        "COMUNE": "ARBOREA",
        "PVC": "097",
        "COM": "165",
        "CCO": "6",
        "FRA": "31",
        "CCS": "00000",
        "NUM. DISTR.": 24,
        "DISTRETTO": "Lotto Sud Arborea",
        "SEZIONE": None,
        "FOGLIO": "11",
        "PARTIC": "21",
        "SUB": "1",
        "SUP. CATASTALE": 2000,
        "SUP. IRRIGATA": 0,
        "COLTURA": None,
        "INTESTATARIO": "Mario Rossi",
        "CODICE FISCALE": "RSSMRA80A01A357U",
        "MANUTENZIONE": 1,
        "DOMANDA": 0,
        "NUMDOMANDA": 0,
        "STATO": None,
        "NOTE": None,
        "AUTORINNOVO": 0,
    }
    payload = [{**defaults, **row} for row in rows]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(payload).to_excel(writer, sheet_name="Esportazione", index=False)
    return path


def _run(db: Session, xlsx_path: Path, output_dir: Path, *, apply: bool) -> dict:
    return run_capacitas_consorzio_grid_import(
        db,
        CapacitasGridImportOptions(
            xlsx_path=xlsx_path,
            snapshot_year=2026,
            source_file=xlsx_path.name,
            output_dir=output_dir,
            apply=apply,
        ),
    )


def test_parse_grid_maps_codice_to_source_codice_catastale(tmp_path: Path) -> None:
    xlsx_path = _write_grid(tmp_path / "grid.xlsx", [{"CODICE": "A357", "CCO": "6"}])

    rows = parse_capacitas_grid_xlsx(xlsx_path)

    assert rows[0].source_codice_catastale == "A357"
    assert rows[0].source_cod_comune_capacitas == 165
    assert rows[0].cco == "000000006"
    assert rows[0].pvc == "097"
    assert rows[0].ccs == "00000"


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    xlsx_path = _write_grid(tmp_path / "grid.xlsx", [{"FOGLIO": "11", "PARTIC": "21", "SUB": "1"}])
    db = TestingSessionLocal()
    before_particelle = len(db.scalars(select(CatParticella)).all())

    summary = _run(db, xlsx_path, tmp_path / "out", apply=False)

    assert summary["mode"] == "dry-run"
    assert summary["cat_particelle_unchanged"] is True
    assert len(db.scalars(select(CatConsorzioUnit)).all()) == 0
    assert len(db.scalars(select(CatConsorzioOccupancy)).all()) == 0
    assert len(db.scalars(select(CatCapacitasGridSnapshot)).all()) == 0
    assert len(db.scalars(select(CatParticella)).all()) == before_particelle
    db.close()


def test_apply_is_idempotent_and_never_writes_cat_particelle(tmp_path: Path) -> None:
    xlsx_path = _write_grid(tmp_path / "grid.xlsx", [{"FOGLIO": "11", "PARTIC": "21", "SUB": "1"}])
    db = TestingSessionLocal()
    before_particelle = len(db.scalars(select(CatParticella)).all())

    first = _run(db, xlsx_path, tmp_path / "out", apply=True)
    second = _run(db, xlsx_path, tmp_path / "out2", apply=True)

    assert first["cat_particelle_unchanged"] is True
    assert second["cat_particelle_unchanged"] is True
    assert len(db.scalars(select(CatParticella)).all()) == before_particelle
    assert len(db.scalars(select(CatConsorzioUnit)).all()) == 1
    assert len(db.scalars(select(CatConsorzioOccupancy)).all()) == 1
    assert len(db.scalars(select(CatCapacitasGridSnapshot)).all()) == 1
    assert len(db.scalars(select(CatCapacitasGridRow)).all()) == 1
    unit = db.scalars(select(CatConsorzioUnit)).one()
    assert unit.source_codice_catastale == "A357"
    assert unit.source_cod_comune_capacitas == 165
    db.close()


def test_apply_marks_arborea_terralba_swap(tmp_path: Path) -> None:
    xlsx_path = _write_grid(
        tmp_path / "grid.xlsx",
        [
            {
                "CODICE": "A357",
                "COMUNE": "ARBOREA",
                "COM": "165",
                "FRA": "31",
                "FOGLIO": "10",
                "PARTIC": "20",
                "SUB": None,
            }
        ],
    )
    db = TestingSessionLocal()

    summary = _run(db, xlsx_path, tmp_path / "out", apply=True)

    assert summary["counters"]["unit_resolution_unit_swapped_arborea_terralba"] == 1
    unit = db.scalars(select(CatConsorzioUnit)).one()
    assert unit.source_codice_catastale == "A357"
    assert unit.source_cod_comune_capacitas == 165
    assert unit.cod_comune_capacitas == 280
    assert unit.comune_resolution_mode == "swapped_arborea_terralba"
    assert unit.particella_id is not None
    db.close()


def test_apply_reuses_existing_occupancy_across_duplicate_units(tmp_path: Path) -> None:
    xlsx_path = _write_grid(
        tmp_path / "grid_duplicate_units.xlsx",
        [
            {
                "CODICE": "F272",
                "COMUNE": "Mogoro",
                "COM": "50",
                "FRA": "33",
                "CCO": "0A0865320",
                "FOGLIO": "3",
                "PARTIC": "439",
                "SUB": None,
                "CODICE FISCALE": "MTTGRG75T27H856Q",
            }
        ],
    )
    db = TestingSessionLocal()
    mogoro = CatComune(
        nome_comune="Mogoro",
        codice_catastale="F272",
        cod_comune_capacitas=50,
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    db.add(mogoro)
    db.flush()
    first_unit = CatConsorzioUnit(
        id=uuid.uuid4(),
        comune_id=mogoro.id,
        cod_comune_capacitas=50,
        source_comune_id=mogoro.id,
        source_cod_comune_capacitas=50,
        source_codice_catastale="F272",
        source_comune_label="Mogoro",
        comune_resolution_mode="source_match",
        foglio="3",
        particella="439",
        subalterno=None,
        descrizione="Legacy duplicate A",
        source_first_seen=date(2026, 4, 29),
        source_last_seen=date(2026, 4, 29),
        is_active=True,
    )
    second_unit = CatConsorzioUnit(
        id=uuid.uuid4(),
        comune_id=mogoro.id,
        cod_comune_capacitas=50,
        source_comune_id=mogoro.id,
        source_cod_comune_capacitas=50,
        source_codice_catastale="F272",
        source_comune_label="Mogoro",
        comune_resolution_mode="source_match",
        foglio="3",
        particella="439",
        subalterno=None,
        descrizione="Legacy duplicate B",
        source_first_seen=date(2026, 4, 29),
        source_last_seen=date(2026, 4, 29),
        is_active=True,
    )
    db.add_all([first_unit, second_unit])
    db.commit()

    first = _run(db, xlsx_path, tmp_path / "out", apply=True)
    second = _run(db, xlsx_path, tmp_path / "out2", apply=True)

    occupancies = db.scalars(
        select(CatConsorzioOccupancy).where(CatConsorzioOccupancy.cco == "0A0865320")
    ).all()
    assert first["counters"]["occupancy_created"] == 1
    assert second["counters"].get("occupancy_created", 0) == 0
    assert second["counters"]["occupancy_existing_current"] == 1
    assert len(occupancies) == 1
    assert occupancies[0].unit_id in {first_unit.id, second_unit.id}
    db.close()


def test_parse_grid_rejects_missing_required_columns(tmp_path: Path) -> None:
    payload = {column: ["x"] for column in sorted(GRID_REQUIRED_COLUMNS - {"DOMANDA"})}
    xlsx_path = tmp_path / "grid_missing_column.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame(payload).to_excel(writer, sheet_name="Esportazione", index=False)

    with pytest.raises(ValueError, match="Colonne Excel mancanti: DOMANDA"):
        parse_capacitas_grid_xlsx(xlsx_path)


def test_service_helper_branches_and_runtime_aliases() -> None:
    db = TestingSessionLocal()

    legacy_a = CatConsorzioUnit(foglio="77", particella="88", subalterno=None, source_codice_catastale=None)
    legacy_b = CatConsorzioUnit(foglio="77", particella="88", subalterno=None, source_codice_catastale=None)
    db.add_all([legacy_a, legacy_b])
    db.flush()
    db.add(
        CatConsorzioOccupancy(
            unit_id=legacy_a.id,
            cco="123",
            fra="1",
            ccs="00000",
            pvc="097",
            com="165",
            source_type=GRID_SOURCE_TYPE,
            valid_from=None,
            valid_to=None,
            is_current=True,
        )
    )
    db.commit()

    runtime = build_runtime(db)
    assert runtime.units_by_legacy_key[(None, "77", "88", None)].id in {legacy_a.id, legacy_b.id}
    assert set(runtime.unit_alias_ids_by_unit_id[legacy_a.id]) == {legacy_a.id, legacy_b.id}
    assert runtime.occupancies_by_key == {}

    invalid_row = GridRow(
        row_number=2,
        source_codice_catastale="",
        source_cod_comune_capacitas=None,
        source_comune_label=None,
        pvc=None,
        com=None,
        cco=None,
        fra=None,
        ccs=None,
        num_distretto=None,
        distretto=None,
        sezione_catastale=None,
        foglio=None,
        particella=None,
        subalterno=None,
        sup_catastale_mq=None,
        sup_irrigata_mq=None,
        coltura=None,
        intestatario=None,
        codice_fiscale=None,
        manutenzione=None,
        domanda=None,
        numdomanda=None,
        stato=None,
        note=None,
        autorinnovo=None,
        raw_payload={},
    )
    counters = Counter()
    report = process_grid_row(
        db,
        invalid_row,
        options=CapacitasGridImportOptions(
            xlsx_path=Path("unused.xlsx"),
            snapshot_year=2026,
            source_file="unused.xlsx",
            output_dir=Path("/tmp"),
            apply=False,
        ),
        counters=counters,  # type: ignore[arg-type]
        runtime=runtime,
    )
    assert counters["row_invalid_key"] == 1
    assert report["unit_classification"] == "row_invalid_key"
    db.close()


def test_resolution_and_helper_functions_cover_edge_cases() -> None:
    arborea = CatComune(
        nome_comune="Arborea",
        codice_catastale="A357",
        cod_comune_capacitas=165,
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    terralba = CatComune(
        nome_comune="Terralba",
        codice_catastale="L122",
        cod_comune_capacitas=280,
        cod_provincia=115,
        sigla_provincia="OR",
        regione="Sardegna",
    )
    particella = CatParticella(
        comune=arborea,
        cod_comune_capacitas=165,
        codice_catastale="A357",
        nome_comune="Arborea",
        foglio="11",
        particella="21",
        subalterno="1",
        is_current=True,
        superficie_mq=100,
        source_type="ade_wfs",
    )
    runtime = ImportRuntime(
        comuni_by_codice={"A357": arborea, "L122": terralba},
        comuni_by_capacitas_code={165: arborea, 280: terralba},
        particelle_exact={(165, "11", "21", "1"): [particella]},
        particelle_base={(165, "11", "21"): [particella]},
        units_by_source_key={},
        units_by_legacy_key={},
        unit_alias_ids_by_unit_id={},
        occupancies_by_key={},
        subjects_by_tax_id={},
    )
    row = GridRow(
        row_number=2,
        source_codice_catastale="A357",
        source_cod_comune_capacitas=165,
        source_comune_label="Arborea",
        pvc="097",
        com="165",
        cco="123",
        fra="31",
        ccs="00000",
        num_distretto=None,
        distretto=None,
        sezione_catastale=None,
        foglio="11",
        particella="21",
        subalterno=None,
        sup_catastale_mq=None,
        sup_irrigata_mq=None,
        coltura=None,
        intestatario="Mario Rossi",
        codice_fiscale="RSSMRA80A01A357U",
        manutenzione=1,
        domanda=0,
        numdomanda=None,
        stato=None,
        note=None,
        autorinnovo=None,
        raw_payload={},
    )
    resolution = resolve_unit_target(row, runtime)
    assert resolution.classification == "unit_sub_mismatch"
    assert _find_source_comune(row, runtime) == arborea
    assert _find_source_comune(
        GridRow(**{**row.__dict__, "source_codice_catastale": "", "source_cod_comune_capacitas": 165}),
        runtime,
    ) == arborea
    assert _find_source_comune(
        GridRow(**{**row.__dict__, "source_codice_catastale": "", "source_cod_comune_capacitas": 999}),
        runtime,
    ) is None
    assert _find_source_comune(
        GridRow(**{**row.__dict__, "source_codice_catastale": "", "source_cod_comune_capacitas": None}),
        runtime,
    ) is None
    assert _find_official_particella(row, None, runtime) == (None, "unmatched")
    ambiguous_runtime = ImportRuntime(
        comuni_by_codice=runtime.comuni_by_codice,
        comuni_by_capacitas_code=runtime.comuni_by_capacitas_code,
        particelle_exact={(165, "11", "21", "1"): [particella, particella]},
        particelle_base={},
        units_by_source_key={},
        units_by_legacy_key={},
        unit_alias_ids_by_unit_id={},
        occupancies_by_key={},
        subjects_by_tax_id={},
    )
    assert resolve_unit_target(GridRow(**{**row.__dict__, "subalterno": "1"}), ambiguous_runtime).classification == "unit_ambiguous"
    swapped_ambiguous_runtime = ImportRuntime(
        comuni_by_codice=runtime.comuni_by_codice,
        comuni_by_capacitas_code=runtime.comuni_by_capacitas_code,
        particelle_exact={(280, "11", "21", ""): [CatParticella(cod_comune_capacitas=280, foglio="11", particella="21", subalterno=None, is_current=True, source_type="ade_wfs"), CatParticella(cod_comune_capacitas=280, foglio="11", particella="21", subalterno=None, is_current=True, source_type="ade_wfs")]},
        particelle_base={},
        units_by_source_key={},
        units_by_legacy_key={},
        unit_alias_ids_by_unit_id={},
        occupancies_by_key={},
        subjects_by_tax_id={},
    )
    assert resolve_unit_target(row, swapped_ambiguous_runtime).classification == "unit_ambiguous"
    assert _find_official_particella(row, arborea, runtime) == (None, "sub_mismatch")


def test_occupancy_subject_and_normalization_helpers() -> None:
    unit = CatConsorzioUnit(id=uuid.uuid4(), foglio="11", particella="21", source_codice_catastale="A357")
    row = GridRow(
        row_number=2,
        source_codice_catastale="A357",
        source_cod_comune_capacitas=165,
        source_comune_label="Arborea",
        pvc="097",
        com="165",
        cco="123",
        fra="31",
        ccs="00000",
        num_distretto=None,
        distretto=None,
        sezione_catastale=None,
        foglio="11",
        particella="21",
        subalterno="1",
        sup_catastale_mq=Decimal("12.5"),
        sup_irrigata_mq=None,
        coltura=None,
        intestatario="Mario Rossi",
        codice_fiscale="RSSMRA80A01A357U",
        manutenzione=1,
        domanda=0,
        numdomanda=None,
        stato=None,
        note=None,
        autorinnovo=None,
        raw_payload={"x": 1},
    )
    runtime = ImportRuntime({}, {}, {}, {}, {}, {}, {}, {}, {})
    db = Mock()
    occupancy, classification = find_or_create_occupancy(
        db,
        row,
        unit,
        snapshot_year=2026,
        apply=False,
        runtime=runtime,
    )
    assert occupancy is None
    assert classification == "occupancy_created"
    assert find_or_create_occupancy(db, GridRow(**{**row.__dict__, "cco": None}), unit, snapshot_year=2026, apply=False, runtime=runtime) == (None, None)

    resolution = UnitResolution(source_comune=None, canonical_comune=None, particella=None, resolution_mode="source_only", classification="unit_unmatched_official")
    _update_unit(unit, row, resolution)
    assert unit.source_last_seen == date.today()
    assert unit.is_active is True

    unit_missing = CatConsorzioUnit(id=uuid.uuid4(), foglio="11", particella="21")
    comune = CatComune(nome_comune="Arborea", codice_catastale="A357", cod_comune_capacitas=165, cod_provincia=115, sigla_provincia="OR", regione="Sardegna")
    particella = CatParticella(id=uuid.uuid4(), comune=comune, cod_comune_capacitas=165, foglio="11", particella="21", subalterno="1", is_current=True, source_type="ade_wfs")
    full_resolution = UnitResolution(source_comune=comune, canonical_comune=comune, particella=particella, resolution_mode="source_match", classification="unit_existing_exact")
    _update_unit(unit_missing, row, full_resolution)
    assert unit_missing.particella_id == particella.id
    assert unit_missing.comune_id == comune.id
    assert unit_missing.cod_comune_capacitas == 165
    assert unit_missing.source_comune_id == comune.id

    report = _row_report(row, unit=unit_missing, occupancy=None, unit_classification="unit_existing_exact")
    assert report["unit_id"] == str(unit_missing.id)
    assert _occupancy_key(unit.id, "123", "31", "00000", "097", "165", date(2026, 1, 1), date(2026, 12, 31))[1] == "123"
    assert _uuid_or_none(None) is None
    generated = uuid.uuid4()
    assert _uuid_or_none(generated) == generated
    assert _uuid_or_none(str(generated)) == generated
    assert _normalize_cco("6") == "000000006"
    assert _normalize_cco("0A0865320") == "0A0865320"
    assert _normalize_fixed_width("7", 3) == "007"
    assert _normalize_sub("001") == "1"
    assert _normalize_numeric_text("007.0") == "007.0"
    assert _normalize_numeric_text(r"007\.0").startswith("007\\")
    assert _normalize_numeric_text("0A0865320") == "0A0865320"
    assert _clean_text(" nan ") == ""
    assert _to_int(None) is None
    assert _to_int("abc") is None
    assert _to_decimal(None) is None
    assert _to_decimal("bad") is None
    assert _to_decimal("1,25") == Decimal("1.25")

    class ItemValue:
        def item(self) -> int:
            return 7

    assert _json_safe_value(None) is None
    assert _json_safe_value(Decimal("1.2")) == "1.2"
    assert _json_safe_value(ItemValue()) == 7
    assert _json_safe_value(SimpleNamespace(a=1)).startswith("namespace(")

    cached_runtime = ImportRuntime({}, {}, {}, {}, {}, {}, {}, {}, {"RSSMRA80A01A357U": None})
    assert _find_subject_by_tax_identifier(Mock(), None, cached_runtime) is None
    assert _find_subject_by_tax_identifier(Mock(), "RSSMRA80A01A357U", cached_runtime) is None

    vat_runtime = ImportRuntime({}, {}, {}, {}, {}, {}, {}, {}, {})
    vat_db = Mock()
    company = SimpleNamespace(subject_id=generated)
    subject = SimpleNamespace(id=generated)
    vat_db.scalar.return_value = company
    vat_db.get.return_value = subject
    assert _find_subject_by_tax_identifier(vat_db, "12345678901", vat_runtime) == subject

    person_runtime = ImportRuntime({}, {}, {}, {}, {}, {}, {}, {}, {})
    person_db = Mock()
    person = SimpleNamespace(subject_id=generated)
    person_db.scalar.return_value = person
    person_db.get.return_value = subject
    assert _find_subject_by_tax_identifier(person_db, "RSSMRA80A01A357U", person_runtime) == subject
