from app.modules.ruolo.services import tributi_reminder_service as reminder_service
from app.modules.ruolo.services.partitario_by_avviso import GENERATE_ONLY_KEY, partitario_by_avviso

HEADER = "ELENCO DELLE PARTITE SOGGETTE A CONTRIBUTO"
STORED = f"{HEADER}\nPartita 000000347/00000 beni in comune di ARBOREA"


def _partita(code: str) -> dict:
    return {
        "codice_partita": code,
        "comune_nome": "URAS",
        "importo_0648": "10,00",
        "particelle": [],
    }


def _lines(payload: dict) -> list[str]:
    return reminder_service._batch_partitario_lines(payload)


def test_avviso_without_incass_partitario_gets_gaia_partite_next_to_stored_ones() -> None:
    lines = _lines(
        {
            "display_name": "ROSSI MARIO",
            "avvisi": [
                {"anno_tributario": 2021, "partitario": {"info_text": STORED}, "partite": []},
                {
                    "anno_tributario": 2021,
                    "partitario": {"info_text": "Chiudi Scarica"},
                    "partite": [_partita("P-ORD")],
                },
                {"anno_tributario": 2021, "partitario": None, "partite": []},
            ],
        }
    )
    assert lines[:2] == [HEADER, "Partita 000000347/00000 beni in comune di ARBOREA"]
    assert lines[2] == ""
    assert "Partita P-ORD beni in comune di URAS" in lines
    assert GENERATE_ONLY_KEY not in " ".join(lines)


def test_stored_partitari_are_printed_once_and_unchanged_without_gaps() -> None:
    avviso = {
        "anno_tributario": 2021,
        "partitario": {"info_text": STORED},
        "partite": [_partita("P")],
    }
    assert _lines({"avvisi": [avviso, dict(avviso), "bad"]}) == [
        HEADER,
        "Partita 000000347/00000 beni in comune di ARBOREA",
    ]
    # Without any stored partitario GAIA builds the whole attachment, as before.
    generated = _lines({"avvisi": [{"anno_tributario": 2021, "partite": [_partita("P")]}]})
    assert "Partita P beni in comune di URAS" in generated
    # A notice-level partitario keeps the original behaviour.
    assert _lines({"partitario_text": "RAW A", "avvisi": [{"partitario_text": "RAW B"}]}) == [
        "RAW A",
        "",
        "RAW B",
    ]


def test_generate_only_payloads_skip_the_stored_lookup() -> None:
    def fail(_payload: dict) -> list[str]:
        raise AssertionError("not called")

    assert partitario_by_avviso({GENERATE_ONLY_KEY: True}, fail, fail) == []


def test_partita_already_in_an_incass_partitario_is_not_repeated() -> None:
    ord_avviso = {"anno_tributario": 2021, "partitario": {"info_text": STORED}, "partite": []}
    list_b = {
        "anno_tributario": 2021,
        "partitario": {"info_text": "Chiudi Scarica"},
        "partite": [_partita("000000347/00000"), _partita("P-NUOVA")],
    }
    lines = _lines({"avvisi": [ord_avviso, list_b]})
    assert sum(line.startswith("Partita 000000347/00000 ") for line in lines) == 1
    assert "Partita P-NUOVA beni in comune di URAS" in lines
    only_printed = {**list_b, "partite": [_partita("000000347/00000")]}
    assert _lines({"avvisi": [ord_avviso, only_printed]}) == [
        HEADER,
        "Partita 000000347/00000 beni in comune di ARBOREA",
    ]


def test_generated_partitario_lines_fit_the_page_width() -> None:
    partita = {
        **_partita("P"),
        "particelle": [{"foglio": "2", "particella": "100", "coltura": "RISO"}],
    }
    lines = _lines({"avvisi": [{"anno_tributario": 2021, "partite": [partita]}]})
    assert max(len(line) for line in lines) <= reminder_service.PARTITARIO_LINE_WIDTH
