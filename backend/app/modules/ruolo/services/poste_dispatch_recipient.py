"""Recipient and shipment name of a Posta Online draft, read from the letter payload.

The draft must carry the same name and address printed on the letter, so both
come from the payload that rendered the PDF.
"""

import re
from typing import Any

from app.modules.ruolo.services.tributi_reminder_service import _batch_address_values, _value

NAME_LIMIT = 44
ADDRESS_LIMIT = 88
CITY_LIMIT = 33
SHIPMENT_NAME_LIMIT = 40
RECIPIENT_FIELDS = ("name", "name_extra", "address", "cap", "city", "province")
_CAP_RE = re.compile(r"^\d{5}$")
_PROVINCE_RE = re.compile(r"^[A-Z]{2}$")


def shipment_name(notice_number: str) -> str:
    name = f"GAIA {notice_number.strip()}"
    if not notice_number.strip() or len(name) > SHIPMENT_NAME_LIMIT:
        raise ValueError("Numero avviso non utilizzabile come nome spedizione Poste")
    return name


def clean(value: Any) -> str:
    text = " ".join(str(value or "").split()).upper()
    return "" if text == "-" else text


def split_name(name: str) -> tuple[str, str]:
    """Poste has two 44-character lines: name and additional name information."""
    if len(name) <= NAME_LIMIT:
        return name, ""
    cut = name.rfind(" ", 0, NAME_LIMIT + 1)
    cut = cut if cut > 0 else NAME_LIMIT
    return name[:cut].strip(), name[cut:].strip()


def recipient_from_payload(payload: dict[str, Any]) -> dict[str, str]:
    address = _batch_address_values(payload)
    name, extra = split_name(clean(_value(payload.get("display_name"))))
    return {
        "name": name,
        "name_extra": extra,
        "address": clean(address["indirizzo"]),
        "cap": clean(address["cap"]),
        "city": clean(address["citta"]),
        "province": clean(address["provincia"]),
    }


def normalize_recipient(fields: dict[str, Any]) -> dict[str, str]:
    return {field: clean(fields.get(field)) for field in RECIPIENT_FIELDS}


def recipient_problems(recipient: dict[str, str], *, manual: bool = False) -> list[str]:
    """A manual address skips the Poste street directory, so CAP and province are required."""
    limits = {
        "name": NAME_LIMIT,
        "name_extra": NAME_LIMIT,
        "address": ADDRESS_LIMIT,
        "city": CITY_LIMIT,
    }
    problems = [
        f"{field}: oltre {limit} caratteri"
        for field, limit in limits.items()
        if len(recipient[field]) > limit
    ]
    problems += [
        f"{field}: mancante" for field in ("name", "address", "city") if not recipient[field]
    ]
    if (manual or recipient["cap"]) and not _CAP_RE.match(recipient["cap"]):
        problems.append("cap: servono 5 cifre")
    if (manual or recipient["province"]) and not _PROVINCE_RE.match(recipient["province"]):
        problems.append("province: servono 2 lettere")
    return problems
