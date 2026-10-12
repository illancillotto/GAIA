from __future__ import annotations

import re

_FISCAL_IDENTIFIER = re.compile(r"(?:[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]|\d{11})\Z")
_POSTAL_ADDRESS = re.compile(r"\b\d{5}\b")


def recipient_address_columns(cells: list[str]) -> tuple[str, str, str | None]:
    address = cells[3]
    fiscal_identifier = address.strip().upper()
    if not _FISCAL_IDENTIFIER.fullmatch(fiscal_identifier):
        return address, cells[4] if len(cells) > 4 else "", None
    if len(cells) < 5 or not _POSTAL_ADDRESS.search(cells[4]):
        raise ValueError(
            "Dettaglio Poste: codice fiscale al posto dell'indirizzo, layout incompleto"
        )
    return cells[4], " ".join(cells[5:]), fiscal_identifier
