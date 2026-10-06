import hashlib
import json
import re

from app.modules.catasto.services.validation import _is_valid_cf_checksum, validate_codice_fiscale
from app.modules.ruolo.services.parsing_common import resolve_section_hint_for_ruolo_comune

YEARS = tuple(range(2020, 2026))
PF_FORMAT = re.compile(
    r"^[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$"
)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def token(value: object) -> str:
    result = str(value or "").strip().upper()
    return str(int(result)) if result.isascii() and result.isdigit() else result


def tax_code_check(value: str | None) -> dict:
    normalized = str(value or "").strip().upper()
    result = validate_codice_fiscale(value)
    valid = pf_valid(normalized) if len(normalized) == 16 else result["is_valid"]
    if result["tipo"] == "MANCANTE":
        anomaly = "missing"
    elif len(normalized) in {*range(1, 11), *range(12, 16)}:
        anomaly = "incomplete"
    elif not valid:
        anomaly = "invalid"
    else:
        anomaly = None
    return {
        "original": value,
        "normalized": normalized,
        "anomaly": anomaly,
        "identity_verified": False,
    }


def pf_valid(value: str) -> bool:
    if not PF_FORMAT.fullmatch(value) or not _is_valid_cf_checksum(value):
        return False
    day = int(value[9:11].translate(str.maketrans("LMNPQRSTUV", "0123456789")))
    return day in {*range(1, 32), *range(41, 72)}


def source_identity(parcel, partita) -> dict:
    section = resolve_section_hint_for_ruolo_comune(partita.comune_nome)
    reference = {
        "namespace": "ruolo_source",
        "comune_codice": token(partita.comune_codice),
        "comune_nome": str(partita.comune_nome or "").strip().upper(),
        "sezione": section,
        "foglio": token(parcel.foglio),
        "particella": token(parcel.particella),
        "subalterno": token(parcel.subalterno),
        "catasto": None,
    }
    incomplete = not all(reference[field] for field in ("comune_codice", "foglio", "particella"))
    key = {**reference, "unresolved_id": str(parcel.id) if incomplete else None}
    return {"key": digest(key), "reference": reference, "incomplete": incomplete}


def annual_presence(present: bool, complete: bool) -> str:
    return "present" if present else "absent" if complete else "not_verifiable"
