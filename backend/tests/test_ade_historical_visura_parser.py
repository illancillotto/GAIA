from pathlib import Path

import pytest

from app.modules.catasto.services.ade_historical_visura_parser import (
    parse_historical_visura_pdf,
    parse_historical_visura_text,
)


def test_parse_historical_visura_extracts_suppression_and_originated_parcels() -> None:
    text = """
    Comune di ARBOREA (Codice:A357C)
    Sezione TERRALBA (Provincia di ORISTANO)
    Catasto Terreni Foglio: 25 Particella: 215

    Numero di mappa soppresso dal 11/07/2019
    FRAZIONAMENTO del 11/07/2019 Pratica n. OR0032243 in atti dal
    11/07/2019 presentato il 11/07/2019 (n. 32243.1/2019)

    La soppressione ha originato e/o variato i seguenti immobili
    Foglio 25 Particella 243 ; Foglio 25 Particella 244 ;

    Situazione dell'unità immobiliare dal 04/04/2007
    FRAZIONAMENTO del 04/04/2007 Pratica n. OR0105138 in atti dal 04/04/2007 (n. 105138.1/2007)
    Nella variazione sono stati soppressi i seguenti immobili:
    Foglio:25 Particella:24 ; Foglio:25 Particella:182 ;
    Sono stati inoltre variati i seguenti immobili:
    Foglio:25 Particella:212 ; Foglio:25 Particella:213 ; Foglio:25 Particella:214 ;
    """

    payload = parse_historical_visura_text(text)

    assert payload["classification"] == "suppressed"
    assert payload["requested"]["comune"] == "ARBOREA"
    assert payload["requested"]["codice"] == "A357C"
    assert payload["requested"]["sezione"] == "TERRALBA"
    assert payload["requested"]["foglio"] == "25"
    assert payload["requested"]["particella"] == "215"
    assert payload["suppression"]["suppressed_from"] == "11/07/2019"
    assert payload["suppression"]["act_type"] == "FRAZIONAMENTO"
    assert payload["originated_or_varied_parcels"] == [
        {"foglio": "25", "particella": "243", "subalterno": None},
        {"foglio": "25", "particella": "244", "subalterno": None},
    ]
    assert {"foglio": "25", "particella": "182", "subalterno": None} in payload["first_variation"]["suppressed_parcels"]
    assert {"foglio": "25", "particella": "214", "subalterno": None} in payload["first_variation"]["varied_parcels"]


def test_parse_historical_visura_real_arborea_pdf_fixture() -> None:
    fixture_path = next(
        (
            parent / "data-example" / "DOC_1998356604.pdf"
            for parent in Path(__file__).resolve().parents
            if (parent / "data-example" / "DOC_1998356604.pdf").exists()
        ),
        None,
    )
    if fixture_path is None:
        pytest.skip("real AdE PDF fixture not available")

    payload = parse_historical_visura_pdf(fixture_path)

    assert payload["classification"] == "suppressed"
    assert payload["requested"] == {
        "comune": "ARBOREA",
        "codice": "A357C",
        "sezione": "TERRALBA",
        "foglio": "25",
        "particella": "215",
        "subalterno": None,
    }
    assert payload["suppression"] == {
        "is_suppressed": True,
        "suppressed_from": "11/07/2019",
        "act_type": "FRAZIONAMENTO",
        "act_reference": "32243.1/2019",
    }
    assert payload["originated_or_varied_parcels"] == [
        {"foglio": "25", "particella": "243", "subalterno": None},
        {"foglio": "25", "particella": "244", "subalterno": None},
    ]
    assert payload["first_variation"]["suppressed_parcels"] == [
        {"foglio": "25", "particella": "24", "subalterno": None},
        {"foglio": "25", "particella": "182", "subalterno": None},
    ]
    assert payload["first_variation"]["varied_parcels"] == [
        {"foglio": "25", "particella": "212", "subalterno": None},
        {"foglio": "25", "particella": "213", "subalterno": None},
        {"foglio": "25", "particella": "214", "subalterno": None},
    ]
    assert len(payload["events"]) >= 5


def test_parse_historical_visura_real_san_vero_milis_pdf_fixture() -> None:
    fixture_path = Path(__file__).resolve().parents[2] / "data-example" / "DOC_1998476900.pdf"

    payload = parse_historical_visura_pdf(fixture_path)

    assert payload["classification"] == "suppressed"
    assert payload["requested"] == {
        "comune": "SAN VERO MILIS",
        "codice": "I384",
        "sezione": None,
        "foglio": "18",
        "particella": "1174",
        "subalterno": None,
    }
    assert payload["suppression"] == {
        "is_suppressed": True,
        "suppressed_from": "25/05/2023",
        "act_type": "TIPO MAPPALE",
        "act_reference": "20842.1/2023",
    }
    assert payload["originated_or_varied_parcels"] == [
        {"foglio": "18", "particella": "4180", "subalterno": None},
        {"foglio": "18", "particella": "4181", "subalterno": None},
        {"foglio": "18", "particella": "4182", "subalterno": None},
    ]
    assert payload["first_variation"]["suppressed_parcels"] == []
    assert {"foglio": "18", "particella": "1175", "subalterno": None} in payload["first_variation"]["varied_parcels"]
    assert {"foglio": "18", "particella": "1649", "subalterno": None} in payload["first_variation"]["varied_parcels"]
    assert len(payload["events"]) >= 3
