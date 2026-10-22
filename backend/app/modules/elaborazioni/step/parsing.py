"""Value parsing for STEP records.

STEP grids mix Italian formatted strings (``1.405,12``, ``16/11/2024``) with
raw numbers (``258.27``) and serialized dates (``2024-11-16``). Parsing is
strict: an unparseable value becomes ``None`` and the original stays in the
row ``raw_json``. Missing values are never coerced to zero.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal

# A dot is a thousands separator only when a decimal comma follows ("1.405,12");
# otherwise it is a decimal point with at most two digits ("258.27"). "1.405"
# is ambiguous and rejected.
_ITALIAN_AMOUNT = re.compile(r"^-?\d{1,3}(\.\d{3})+,\d{1,2}$|^-?\d+,\d{1,2}$")
_PLAIN_AMOUNT = re.compile(r"^-?\d+(\.\d{1,2})?$")
_CNC = re.compile(r"(?<!\d)([01]\d{14})(?!\d)")
_REFERENCE = re.compile(r"(?:Avv|Bollettazione)\.?\s*n\.?\s*(\S+)", re.IGNORECASE)
_YEAR = re.compile(r"^(19|20)\d{2}$")


def fingerprint(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def text(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def amount(value: object) -> Decimal | None:
    raw = text(value)
    if raw is None:
        return None
    if _PLAIN_AMOUNT.match(raw):
        candidate = raw
    elif _ITALIAN_AMOUNT.match(raw):
        candidate = raw.replace(".", "").replace(",", ".")
    else:
        return None
    return Decimal(candidate).quantize(Decimal("0.01"))


def parse_date(value: object) -> date | None:
    raw = text(value)
    if raw is None:
        return None
    for layout in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, layout).date()
        except ValueError:
            continue
    return None


def integer(value: object) -> int | None:
    raw = text(value)
    if raw is None or not raw.lstrip("-").isdigit():
        return None
    return int(raw)


def year(value: object) -> int | None:
    raw = text(value)
    if raw is None or not _YEAR.match(raw):
        return None
    return int(raw)


def avviso_reference(value: object) -> tuple[str | None, str | None]:
    """Return ``(raw_reference, codice_cnc)`` from a STEP description.

    STEP prints the notice code after ``Avv. N.`` or, for the 2022/2023
    billings, ``Bollettazione n.``. Only a 15 digit code starting with 0 or 1
    is a recognized ``codice_cnc``.
    Shorter codes (leading zero dropped by STEP) or ``PG...`` protocol
    numbers are kept as raw references and never padded or guessed.
    """

    raw = text(value)
    if raw is None:
        return None, None
    match = _REFERENCE.search(raw)
    reference = match.group(1) if match else raw
    cnc = _CNC.fullmatch(reference)
    return reference[:300], cnc.group(1) if cnc else None
