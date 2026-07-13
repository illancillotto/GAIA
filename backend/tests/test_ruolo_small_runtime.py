from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.ruolo.bootstrap import RUOLO_SECTIONS
from app.modules.ruolo.enums import CatastoParcelSource, CodiceTributo, RuoloImportStatus
from app.modules.ruolo.schemas import RuoloImportJobResponse
from app.modules.ruolo.services.parsing_common import (
    looks_like_number,
    normalize_partita_comune_nome,
    parse_italian_decimal,
    parse_particella_line,
    resolve_section_hint_for_ruolo_comune,
)


def test_ruolo_enums_expose_stable_values() -> None:
    assert RuoloImportStatus.PENDING == "pending"
    assert RuoloImportStatus.RUNNING == "running"
    assert RuoloImportStatus.COMPLETED == "completed"
    assert RuoloImportStatus.FAILED == "failed"
    assert CodiceTributo.MANUTENZIONE == "0648"
    assert CodiceTributo.ISTITUZIONALE == "0985"
    assert CodiceTributo.IRRIGAZIONE == "0668"
    assert CatastoParcelSource.RUOLO_IMPORT == "ruolo_import"
    assert CatastoParcelSource.SISTER == "sister"
    assert CatastoParcelSource.CAPACITAS == "capacitas"


def test_ruolo_bootstrap_sections_are_complete() -> None:
    section_keys = {section["key"] for section in RUOLO_SECTIONS}

    assert section_keys == {
        "ruolo.dashboard",
        "ruolo.avvisi",
        "ruolo.import",
        "ruolo.stats",
    }
    assert all(section["module"] == "ruolo" for section in RUOLO_SECTIONS)


def test_ruolo_import_job_duration_seconds() -> None:
    started_at = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)
    job = RuoloImportJobResponse(
        id=uuid4(),
        anno_tributario=2026,
        filename="ruolo.html",
        status="completed",
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=12.34),
        created_at=started_at,
    )
    pending = job.model_copy(update={"finished_at": None})

    assert job.duration_seconds == 12.3
    assert pending.duration_seconds is None


def test_ruolo_parsing_common_normalizers_and_numeric_helpers() -> None:
    assert parse_italian_decimal("") is None
    assert parse_italian_decimal("1.234,56") == Decimal("1234.56")
    assert parse_italian_decimal("non-numero") is None
    assert looks_like_number("1.234,56") is True
    assert looks_like_number("abc") is False
    assert normalize_partita_comune_nome(" SAN NICOLO ARCIDANO (OR) ") == "SAN NICOLO D'ARCIDANO"
    assert normalize_partita_comune_nome("Sili'*Oristano") == "SILI"
    assert resolve_section_hint_for_ruolo_comune(None) is None
    assert resolve_section_hint_for_ruolo_comune("Massama") == "C"
    assert resolve_section_hint_for_ruolo_comune("Cabras") is None


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (
            ["DOM1", "D1", "10", "20", "1", "100,00", "0,75", "VIGNETO", "1,10", "2,20", "3,30"],
            {
                "domanda_irrigua": "DOM1",
                "distretto": "D1",
                "foglio": "10",
                "particella": "20",
                "subalterno": "1",
                "sup_catastale_are": Decimal("100.00"),
                "sup_catastale_ha": Decimal("1.00"),
                "sup_irrigata_ha": Decimal("0.75"),
                "coltura": "VIGNETO",
                "importo_manut": Decimal("1.10"),
                "importo_irrig": Decimal("2.20"),
                "importo_ist": Decimal("3.30"),
            },
        ),
        (
            ["DOM1B", "D1B", "10", "21", "2", "100,00", "0,75", "1,10", "2,20", "3,30", "ignored"],
            {
                "domanda_irrigua": "DOM1B",
                "distretto": "D1B",
                "foglio": "10",
                "particella": "21",
                "subalterno": "2",
                "sup_catastale_are": Decimal("100.00"),
                "sup_catastale_ha": Decimal("1.00"),
                "sup_irrigata_ha": Decimal("0.75"),
                "coltura": None,
                "importo_manut": Decimal("1.10"),
                "importo_irrig": Decimal("2.20"),
                "importo_ist": Decimal("3.30"),
            },
        ),
        (
            ["DOM2", "D2", "11", "21", "120", "0,80", "4,40", "5,50", "6,60", "extra"],
            {
                "domanda_irrigua": "DOM2",
                "distretto": "D2",
                "foglio": "11",
                "particella": "21",
                "subalterno": None,
                "sup_catastale_are": Decimal("120"),
                "sup_catastale_ha": Decimal("1.2"),
                "sup_irrigata_ha": Decimal("0.80"),
                "coltura": None,
                "importo_manut": Decimal("4.40"),
                "importo_irrig": Decimal("5.50"),
                "importo_ist": Decimal("6.60"),
            },
        ),
        (
            ["DOM2B", "D2B", "11", "22", "120", "0,80", "SEMINATIVO", "4,40", "5,50", "6,60"],
            {
                "domanda_irrigua": "DOM2B",
                "distretto": "D2B",
                "foglio": "11",
                "particella": "22",
                "subalterno": None,
                "sup_catastale_are": Decimal("120"),
                "sup_catastale_ha": Decimal("1.2"),
                "sup_irrigata_ha": Decimal("0.80"),
                "coltura": "SEMINATIVO",
                "importo_manut": Decimal("4.40"),
                "importo_irrig": Decimal("5.50"),
                "importo_ist": Decimal("6.60"),
            },
        ),
        (
            ["D3", "12", "22", "A", "90", "0,50", "7,70", "8,80", "9,90"],
            {
                "domanda_irrigua": None,
                "distretto": "D3",
                "foglio": "12",
                "particella": "22",
                "subalterno": "A",
                "sup_catastale_are": Decimal("90"),
                "sup_catastale_ha": Decimal("0.9"),
                "sup_irrigata_ha": Decimal("0.50"),
                "coltura": None,
                "importo_manut": Decimal("7.70"),
                "importo_irrig": Decimal("8.80"),
                "importo_ist": Decimal("9.90"),
            },
        ),
        (
            ["D4", "13", "23", "80", "0,40", "unused", "10,10", "11,11", "12,12"],
            {
                "domanda_irrigua": None,
                "distretto": "D4",
                "foglio": "13",
                "particella": "23",
                "subalterno": None,
                "sup_catastale_are": Decimal("80"),
                "sup_catastale_ha": Decimal("0.8"),
                "sup_irrigata_ha": Decimal("0.40"),
                "coltura": None,
                "importo_manut": Decimal("10.10"),
                "importo_irrig": Decimal("11.11"),
                "importo_ist": Decimal("12.12"),
            },
        ),
        (
            ["D5", "14", "24", "70", "0,30", "13,13", "14,14", "15,15"],
            {
                "domanda_irrigua": None,
                "distretto": "D5",
                "foglio": "14",
                "particella": "24",
                "subalterno": None,
                "sup_catastale_are": Decimal("70"),
                "sup_catastale_ha": Decimal("0.7"),
                "sup_irrigata_ha": Decimal("0.30"),
                "coltura": None,
                "importo_manut": Decimal("13.13"),
                "importo_irrig": Decimal("14.14"),
                "importo_ist": Decimal("15.15"),
            },
        ),
        (
            ["D6", "15", "25", "B", "60", "0,20", "16,16"],
            {
                "domanda_irrigua": None,
                "distretto": "D6",
                "foglio": "15",
                "particella": "25",
                "subalterno": "B",
                "sup_catastale_are": Decimal("60"),
                "sup_catastale_ha": Decimal("0.6"),
                "sup_irrigata_ha": Decimal("0.20"),
                "coltura": None,
                "importo_manut": Decimal("16.16"),
                "importo_irrig": None,
                "importo_ist": None,
            },
        ),
        (
            ["D7", "16", "26", "50", "0,10", "17,17", "18,18"],
            {
                "domanda_irrigua": None,
                "distretto": "D7",
                "foglio": "16",
                "particella": "26",
                "subalterno": None,
                "sup_catastale_are": Decimal("50"),
                "sup_catastale_ha": Decimal("0.5"),
                "sup_irrigata_ha": Decimal("0.10"),
                "coltura": None,
                "importo_manut": Decimal("17.17"),
                "importo_irrig": None,
                "importo_ist": Decimal("18.18"),
            },
        ),
        (
            ["D8", "17", "27", "40", "0,05", "19,19"],
            {
                "domanda_irrigua": None,
                "distretto": "D8",
                "foglio": "17",
                "particella": "27",
                "subalterno": None,
                "sup_catastale_are": Decimal("40"),
                "sup_catastale_ha": Decimal("0.4"),
                "sup_irrigata_ha": Decimal("0.05"),
                "coltura": None,
                "importo_manut": Decimal("19.19"),
                "importo_irrig": None,
                "importo_ist": None,
            },
        ),
        (
            ["18", "28", "30", "0,03", "20,20"],
            {
                "domanda_irrigua": None,
                "distretto": None,
                "foglio": "18",
                "particella": "28",
                "subalterno": None,
                "sup_catastale_are": Decimal("30"),
                "sup_catastale_ha": Decimal("0.3"),
                "sup_irrigata_ha": Decimal("0.03"),
                "coltura": None,
                "importo_manut": Decimal("20.20"),
                "importo_irrig": None,
                "importo_ist": None,
            },
        ),
        (
            ["19", "29", "20", "21,21"],
            {
                "domanda_irrigua": None,
                "distretto": None,
                "foglio": "19",
                "particella": "29",
                "subalterno": None,
                "sup_catastale_are": Decimal("20"),
                "sup_catastale_ha": Decimal("0.2"),
                "sup_irrigata_ha": None,
                "coltura": None,
                "importo_manut": Decimal("21.21"),
                "importo_irrig": None,
                "importo_ist": None,
            },
        ),
    ],
)
def test_ruolo_parse_particella_line_variants(values: list[str], expected: dict[str, object]) -> None:
    parsed = parse_particella_line(values)

    assert parsed is not None
    assert parsed.__dict__ == expected


def test_ruolo_parse_particella_line_rejects_invalid_rows() -> None:
    assert parse_particella_line([]) is None
    assert parse_particella_line(["1", "2", "3"]) is None
    assert parse_particella_line(["foglio=1", "2", "3", "4"]) is None
    assert parse_particella_line(["foglio", "29", "20", "21,21"]) is None
    assert parse_particella_line(["1", "particella", "20", "21,21"]) is None
