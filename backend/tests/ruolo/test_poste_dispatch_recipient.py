import pytest

from app.modules.ruolo.services import poste_dispatch_address as address
from app.modules.ruolo.services import poste_dispatch_recipient as recipient

from .poste_dispatch_fixtures import payload

ORISTANO = {
    "street": "VIA CAGLIARI",
    "number": "170",
    "city": "ORISTANO",
    "province": "OR",
    "zipcode": "09170",
}


def _recipient(**overrides):
    return {
        "name": "ROSSI MARIO",
        "name_extra": "",
        "address": "VIA CAGLIARI 170",
        "cap": "09170",
        "city": "ORISTANO",
        "province": "OR",
    } | overrides


def test_shipment_name_uses_notice_number_within_poste_limit():
    assert recipient.shipment_name(" 020217801062586 ") == "GAIA 020217801062586"
    for invalid in ("", "9" * 40):
        with pytest.raises(ValueError, match="nome spedizione"):
            recipient.shipment_name(invalid)


def test_long_names_move_to_the_second_poste_line():
    assert recipient.split_name("ROSSI MARIO") == ("ROSSI MARIO", "")
    name = "SOCIETA AGRICOLA SEMPLICE FRATELLI ROSSI E FIGLI DI ORISTANO"
    first, second = recipient.split_name(name)
    assert len(first) <= recipient.NAME_LIMIT and f"{first} {second}" == name
    assert recipient.split_name("X" * 50) == ("X" * 44, "X" * 6)


def test_recipient_is_the_one_printed_on_the_letter():
    assert recipient.recipient_from_payload(payload()) == _recipient()
    assert recipient.recipient_from_payload({"avvisi": []})["name"] == ""


def test_normalized_fields_are_uppercase_and_trimmed():
    assert recipient.normalize_recipient({"name": "  rossi   mario ", "cap": None}) == {
        "name": "ROSSI MARIO",
        "name_extra": "",
        "address": "",
        "cap": "",
        "city": "",
        "province": "",
    }


def test_problems_list_missing_and_overlong_fields():
    assert recipient.recipient_problems(_recipient()) == []
    assert recipient.recipient_problems(_recipient(cap="", province="")) == []
    problems = recipient.recipient_problems(
        _recipient(name="", address="V" * 89, city="", cap="091", province="ORI")
    )
    assert problems == [
        "address: oltre 88 caratteri",
        "name: mancante",
        "city: mancante",
        "cap: servono 5 cifre",
        "province: servono 2 lettere",
    ]


def test_manual_address_requires_cap_and_province():
    problems = recipient.recipient_problems(_recipient(cap="", province=""), manual=True)
    assert problems == ["cap: servono 5 cifre", "province: servono 2 lettere"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("VIA CAGLIARI 170", ("VIA CAGLIARI", "170")),
        ("V. Cagliari, n. 170", ("VIA CAGLIARI", "170")),
        ("P.ZZA ROMA 3/A", ("PIAZZA ROMA", "3A")),
        ("C.SO UMBERTO 12 B", ("CORSO UMBERTO", "12B")),
        ("LOC. SA RODIA SNC", ("LOCALITA SA RODIA", "SNC")),
        ("VIA ROMA", ("VIA ROMA", "")),
    ],
)
def test_street_and_number_are_compared_in_canonical_form(raw, expected):
    assert address.split_street_number(raw) == expected


def test_only_an_exact_directory_match_is_accepted():
    suggestions = address.normalize_suggestions(
        [
            {
                "street": "VIA ORISTANO",
                "number": "170",
                "city": "CAGLIARI",
                "province": "CA",
                "zipcode": "09127",
            },
            ORISTANO,
            "not-a-suggestion",
        ]
    )
    match = address.match_address(_recipient(), suggestions)
    assert match.suggestion == ORISTANO
    assert address.suggestion_label(ORISTANO) == "VIA CAGLIARI 170, ORISTANO (OR), 09170"
    assert address.search_term(_recipient()) == "VIA CAGLIARI 170 ORISTANO"


def test_directory_fills_a_missing_cap_but_never_overrides_a_different_one():
    suggestions = address.normalize_suggestions([ORISTANO])
    assert (
        address.match_address(_recipient(cap="", province=""), suggestions).suggestion == ORISTANO
    )
    assert address.match_address(_recipient(cap="09100"), suggestions).suggestion is None


def test_ambiguous_or_missing_directory_entries_go_to_review():
    twice = address.normalize_suggestions([ORISTANO, dict(ORISTANO)])
    assert "Più indirizzi" in address.match_address(_recipient(), twice).reason
    none = address.match_address(_recipient(address="VIA ROMA 1"), twice)
    assert none.suggestion is None and "Nessun indirizzo" in none.reason
    no_number = address.normalize_suggestions([ORISTANO | {"number": None}])
    assert address.suggestion_label(no_number[0]) == "VIA CAGLIARI, ORISTANO (OR), 09170"
