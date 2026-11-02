"""An invalid tax code cannot identify a taxpayer, archive or portal account.

Keep these notices tied to their individual avviso and its original recipient.
Explicit payer assignments are applied afterwards by the ordinary batch pipeline.
"""

from functools import lru_cache

from app.modules.catasto.services.validation import validate_codice_fiscale


@lru_cache(maxsize=4096)
def valid_tax_code(value: str | None) -> bool:
    return bool(validate_codice_fiscale(value)["is_valid"])


def display_name(avviso, linked_name: str | None) -> str | None:
    if not valid_tax_code(avviso.codice_fiscale_raw):
        return avviso.nominativo_raw
    return linked_name or avviso.nominativo_raw


def group_key(avviso) -> str:
    code = (avviso.codice_fiscale_raw or "").strip().upper()
    return code if valid_tax_code(code) else f"avviso:{avviso.id}"


def subject_id(avviso):
    return avviso.subject_id if valid_tax_code(avviso.codice_fiscale_raw) else None


def resolve_archive(db, code: str, linked_subject_id, resolver):
    if not valid_tax_code(code):
        return None, None
    return resolver(db, code, linked_subject_id)


def portal_tax_codes(candidates) -> set[str]:
    return {
        candidate["codice_fiscale"].strip().upper()
        for candidate in candidates
        if valid_tax_code(candidate["codice_fiscale"])
    }


def requires_local_storage(code: str, *local_reasons) -> bool:
    return any(local_reasons) or not valid_tax_code(code)
