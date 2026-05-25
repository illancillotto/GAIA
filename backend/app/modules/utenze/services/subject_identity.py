from __future__ import annotations

import re


_RE_TAX_ID_11 = re.compile(r"^\d{11}$")
_RE_PERSON_CF = re.compile(r"^[A-Z0-9]{16}$")
_RE_COMPANY_MARKERS = re.compile(
    r"\b("
    r"S\.?R\.?L\.?|"
    r"S\.?P\.?A\.?|"
    r"SNC|"
    r"SAS|"
    r"S\.?S\.?|"
    r"SOC(?:IETA|IETA')|"
    r"COOP(?:ERATIVA)?|"
    r"CONSORZIO|"
    r"COMUNE|"
    r"AZIENDA|"
    r"ENTE|"
    r"IMPRESA|"
    r"FONDAZIONE|"
    r"ASSOCIAZIONE|"
    r"MINISTERO|"
    r"DEMANIO|"
    r"REGIONE|"
    r"PROVINCIA|"
    r"LAORE|"
    r"ANAS"
    r")\b",
    re.IGNORECASE,
)


def normalize_tax_identifier(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"\s+", "", value).upper()
    return normalized or None


def is_probable_vat_number(value: str | None) -> bool:
    normalized = normalize_tax_identifier(value)
    return bool(normalized and _RE_TAX_ID_11.fullmatch(normalized))


def is_probable_person_cf(value: str | None) -> bool:
    normalized = normalize_tax_identifier(value)
    return bool(normalized and _RE_PERSON_CF.fullmatch(normalized))


def has_company_name_markers(value: str | None) -> bool:
    return bool(value and _RE_COMPANY_MARKERS.search(value))


def infer_subject_kind(
    *,
    codice_fiscale: str | None = None,
    partita_iva: str | None = None,
    denominazione: str | None = None,
    is_persona_fisica: bool | None = None,
) -> str:
    normalized_cf = normalize_tax_identifier(codice_fiscale)
    normalized_piva = normalize_tax_identifier(partita_iva)

    if is_probable_vat_number(normalized_piva):
        return "company"
    if is_persona_fisica is False:
        return "company"
    if is_probable_vat_number(normalized_cf):
        return "company"
    if is_probable_person_cf(normalized_cf):
        return "person"
    if has_company_name_markers(denominazione):
        return "company"
    if is_persona_fisica is True:
        return "person"
    return "unknown"
