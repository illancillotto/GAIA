"""Pick the Poste street-directory suggestion that is exactly the GAIA address.

The directory is fuzzy: "VIA CAGLIARI 170 ORISTANO" also returns
"VIA ORISTANO 170, CAGLIARI". Street, number, city, CAP and province must all
agree, otherwise the operator reviews the address.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

_PHRASES = (
    (r"\bP ZZA\b|\bPZZA\b|\bPZA\b", "PIAZZA"),
    (r"\bC SO\b|\bCSO\b", "CORSO"),
    (r"\bV LE\b|\bVLE\b", "VIALE"),
    (r"\bV LO\b|\bVLO\b", "VICOLO"),
    (r"\bLOC\b", "LOCALITA"),
    (r"\bFRAZ\b", "FRAZIONE"),
    (r"^V\b", "VIA"),
)
_NUMBER_RE = re.compile(r"^(?:\d+(?: ?[A-Z])?(?: ?\d+)?|SNC)$")
_NUMBER_PREFIXES = {"N", "NR", "NUM", "CIV"}
_SUGGESTION_KEYS = ("street", "number", "city", "province", "zipcode")


@dataclass(frozen=True)
class AddressMatch:
    suggestion: dict[str, str] | None
    reason: str


def comparable(value: Any) -> str:
    """Uppercase ASCII words, without punctuation."""
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", text.upper()).split())


def _street(value: str) -> str:
    text = comparable(value)
    for pattern, replacement in _PHRASES:
        text = re.sub(pattern, replacement, text)
    return text


def split_street_number(address: str) -> tuple[str, str]:
    words = _street(address).split()
    for size in (2, 1):
        number = " ".join(words[-size:])
        if len(words) > size and _NUMBER_RE.match(number):
            street = words[:-size]
            if street and street[-1] in _NUMBER_PREFIXES:
                street = street[:-1]
            return " ".join(street), number.replace(" ", "")
    return " ".join(words), ""


def search_term(recipient: dict[str, str]) -> str:
    return f"{recipient['address']} {recipient['city']}".strip()


def suggestion_label(suggestion: dict[str, str]) -> str:
    """The text Poste shows in its autocomplete list for this suggestion."""
    street = " ".join(part for part in (suggestion["street"], suggestion["number"]) if part)
    return f"{street}, {suggestion['city']} ({suggestion['province']}), {suggestion['zipcode']}"


def _agrees(recipient: dict[str, str], suggestion: dict[str, str]) -> bool:
    street, number = split_street_number(recipient["address"])
    return (
        _street(suggestion.get("street", "")) == street
        and comparable(suggestion.get("number", "")).replace(" ", "") == number
        and comparable(suggestion.get("city", "")) == comparable(recipient["city"])
        and recipient["cap"] in ("", suggestion.get("zipcode", ""))
        and recipient["province"] in ("", comparable(suggestion.get("province", "")))
    )


def normalize_suggestions(suggestions: list[Any]) -> list[dict[str, str]]:
    return [
        {key: str(item.get(key) or "").strip() for key in _SUGGESTION_KEYS}
        for item in suggestions
        if isinstance(item, dict)
    ]


def match_address(recipient: dict[str, str], suggestions: list[dict[str, str]]) -> AddressMatch:
    """Expects normalized suggestions; exactly one must agree on every field."""
    exact = [item for item in suggestions if _agrees(recipient, item)]
    if len(exact) == 1:
        return AddressMatch(exact[0], "Indirizzo trovato nello stradario Poste")
    if exact:
        return AddressMatch(None, "Più indirizzi dello stradario coincidono: scegliere a mano")
    return AddressMatch(
        None, "Nessun indirizzo dello stradario Poste coincide con via, civico, comune e CAP"
    )
