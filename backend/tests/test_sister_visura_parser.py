from datetime import date

import pytest

from app.services import sister_visura_parser as runtime
from app.services.sister_visura_parser import parse_sister_visura_text


def test_parse_current_sister_snapshot_with_multiple_owners() -> None:
    payload = parse_sister_visura_text(
        """
        Visura storica per immobile
        Situazione degli atti informatizzati al 23/09/2026
        Dati della richiesta Comune di TRAMATZA (Codice:L321)
        Catasto Terreni Foglio: 4 Particella: 94
        INTESTATI
        1 TROGU Costantino nato a SOLARUSSA (OR) il 16/05/1950 TRGCTN50E16I791R* (1) Proprieta' 1/3
        2 MANCA Antonino nato a TRAMATZA (OR) il 09/07/1953 MNCNNN53L09L321N* (1) Proprieta' 2/3
        Situazione degli intestati dal 01/05/2015
        1 OLD Owner nato a ORISTANO (OR) il 01/01/1940 OLDOWN40A01G113X* (1) Proprieta' 1/1
        """
    )
    assert payload["status"] == "completed"
    assert payload["comune_codice"] == "L321"
    assert payload["parcel"] == {"foglio": "4", "particella": "94", "subalterno": None}
    assert payload["observed_at"] == date(2026, 9, 23)
    assert len(payload["owners"]) == 2
    assert payload["owners"][0]["codice_fiscale"] == "TRGCTN50E16I791R"
    assert payload["owners"][1]["quota"] == "2/3"


def test_parse_review_required_when_cadastral_reference_is_missing() -> None:
    payload = parse_sister_visura_text(
        """
        Visura per soggetto
        Comune di TRAMATZA (Codice:L321)
        INTESTATO
        1 MANCA Grazia nata a TRAMATZA (OR) il 12/07/1930
        """
    )
    assert payload["status"] == "review_required"
    assert payload["owners"][0]["denominazione"] == "MANCA Grazia"


def test_parse_sister_historical_layout_and_ownership_event() -> None:
    payload = parse_sister_visura_text(
        """
        Visura storica per immobile
        Situazione degli atti informatizzati dall'impianto meccanografico al 23/08/2026
        Dati identificativi: Comune di MARRUBIU (E972) (OR)
        Foglio 6 Particella 832
        Intestati catastali
        1. REGIONE AUTONOMA DELLA SARDEGNA (CF 80002870923)
        Diritto di: Proprieta' per 1/1
        Sono stati inoltre variati/soppressi i seguenti immobili:
        Comune: MARRUBIU (E972)
        Foglio 6 Particella 834
        Storia degli intestati dell'immobile
        Dati identificativi: Immobile attuale - Comune di MARRUBIU (E972) (OR) Foglio 6 Particella 832
        dal 03/11/2025
        1. REGIONE AUTONOMA DELLA SARDEGNA                    1. Atto amministrativo DECRETO
        (CF 80002870923)
        Diritto di: Proprieta' per 1/1
        """
    )
    assert payload["status"] == "completed"
    assert payload["parcel"]["particella"] == "832"
    assert payload["owners"][0]["codice_fiscale"] == "80002870923"
    assert payload["owners"][0]["quota"] == "1/1"
    assert payload["related_parcels"] == [{"foglio": "6", "particella": "834"}]
    assert payload["history_events"][0]["from_date"] == date(2025, 11, 3)
    assert payload["history_events"][0]["owner"]["codice_fiscale"] == "80002870923"


@pytest.mark.parametrize("value,expected", [(None, None), ("invalid", None), ("31/02/2020", None)])
def test_invalid_dates(value, expected):
    assert runtime._parse_date(value) == expected


@pytest.mark.parametrize(
    "name,expected", [("Solo", ("Solo", None, None)), ("", (None, None, None))]
)
def test_single_or_empty_owner_name(name, expected):
    assert runtime._owner_name_parts(name) == expected


@pytest.mark.parametrize(
    "line", ["1. Atto amministrativo", "1. Compravendita casa", "1. Dichiarazione successione"]
)
def test_act_header_is_not_an_owner(line):
    assert runtime._parse_owner_header(line) is None


def test_current_owner_split_fiscal_and_right_details():
    lines = [
        "ignored",
        "1. Rossi Mario",
        "(CF rssmra80a01h501u*)",
        "Diritto di: Usufrutto",
        "Dati identificativi",
    ]
    owners = runtime._parse_current_owners(lines, 0)
    assert owners == [
        {
            "denominazione": "Rossi Mario",
            "cognome": "Rossi",
            "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501U",
            "diritto": "Usufrutto",
            "quota": None,
        }
    ]


def test_history_pending_owners_invalid_date_and_act_precedence():
    lines = [
        "ignored",
        "1. Primo Owner",
        "(CF abcdefghijk)",
        "ignored",
        "dal 31/02/2020",
        "2. Secondo Owner",
        "dal 01/01/2021",
        "(CF lmnopqrstuv)",
        "Diritto di: Proprieta per 1/2",
        "Atto amministrativo 31/02/2020",
        "Compravendita 02/02/2022",
        "dal 03/03/2023",
        "3. Terzo Owner",
    ]
    events, related = runtime._parse_history_events(lines, 0)
    assert related == []
    assert events[0]["from_date"] is None
    assert events[0]["owner"]["denominazione"] == "Primo Owner"
    assert events[0]["owner"]["codice_fiscale"] == "ABCDEFGHIJK"
    assert events[1]["owner"]["denominazione"] == "Secondo Owner"
    assert events[1]["owner"]["codice_fiscale"] == "LMNOPQRSTUV"
    assert events[1]["owner"]["quota"] == "1/2"
    assert events[1]["act"] == "Compravendita 02/02/2022"
    assert events[1]["act_date"] is None
    assert events[2]["owner"]["denominazione"] == "Terzo Owner"


def test_history_related_duplicates_invalid_references_and_reset():
    lines = [
        "Sono stati inoltre variati/soppressi",
        "ignored",
        "Foglio 1 Particella /",
        "Foglio 1 Particella *",
        "Foglio 1 Particella 2",
        "Foglio 1 Particella 2",
        "Dati identificativi: Immobile attuale",
        "Foglio 1 Particella 3",
    ]
    events, related = runtime._parse_history_events(lines, 0)
    assert events == []
    assert related == [{"foglio": "1", "particella": "2"}] * 2


def test_legacy_owner_continuations_and_structured_fallback():
    payload = parse_sister_visura_text("""
        Visura attuale
        Comune di Comune (A001)
        Foglio 1 Particella 2 Subalterno: 3
        INTESTATI
        ignored
        1 Rossi Mario nato a Roma (RM) il 01/01/1980
        rssmra80a01h501u*
        (1) Usufrutto 1/2
        ignored
        2 Bianchi Anna nata a Roma (RM) il 02/02/1982
    """)
    assert payload["document_type"] == "attuale"
    assert payload["parcel"]["subalterno"] == "3"
    assert len(payload["owners"]) == 2
    assert payload["owners"][0]["codice_fiscale"] == "RSSMRA80A01H501U"
    assert payload["owners"][0]["quota"] == "1/2"
    assert "codice_fiscale" not in payload["owners"][1]


def test_pdf_pages_and_parse_adapter(monkeypatch):
    from types import SimpleNamespace

    import pypdf

    paths = []

    def read_pages(path):
        paths.append(path)
        return SimpleNamespace(
            pages=[
                SimpleNamespace(extract_text=lambda: "Visura attuale"),
                SimpleNamespace(extract_text=lambda: None),
            ]
        )

    monkeypatch.setattr(pypdf, "PdfReader", read_pages)
    assert runtime.extract_sister_pdf_text("visura.pdf") == "Visura attuale\n"
    assert runtime.parse_sister_visura_pdf("visura.pdf")["document_type"] == "attuale"
    assert paths == ["visura.pdf", "visura.pdf"]


@pytest.mark.parametrize("content", [b"", b"small", b"a" * (1024 * 1024 + 1)])
def test_pdf_sha256_reads_all_chunks(tmp_path, content):
    import hashlib

    path = tmp_path / "visura.pdf"
    path.write_bytes(content)
    assert runtime.sister_pdf_sha256(path) == hashlib.sha256(content).hexdigest()
