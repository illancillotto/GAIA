from __future__ import annotations

import re

_SEPARATORS_RE = re.compile(r"[\s().-]")
_ITALIAN_MOBILE_RE = re.compile(r"^3\d{8,9}$")
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_whatsapp_phone(value: str | None) -> str | None:
    """Numero E.164 raggiungibile su WhatsApp; per l'Italia solo cellulari."""
    digits = _SEPARATORS_RE.sub("", (value or "").strip())
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+") and _ITALIAN_MOBILE_RE.match(digits):
        digits = "+39" + digits
    if not _E164_RE.match(digits):
        return None
    if digits.startswith("+39") and not digits.startswith("+393"):
        return None
    return digits
