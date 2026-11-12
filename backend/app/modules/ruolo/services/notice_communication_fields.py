"""Communication fields from the saved notice, using the same rules as its PDF."""

from decimal import Decimal, InvalidOperation

from cryptography.fernet import InvalidToken

from app.modules.ruolo.services.notice_branding import TAXPAYER_PORTAL_URL
from app.modules.ruolo.services.notice_payment_deadline import front_payment_due_phrase
from app.modules.ruolo.services.taxpayer_portal_access import (
    PORTAL_ACCESS_KEY,
    printable_portal_access,
)
from app.modules.ruolo.services.tributi_reminder_service import (
    REGISTERED_MAIL_NOTIFICATION_AMOUNT,
    _gaia_bollettino_due_date,
    notice_total_amount,
)
from app.services.elaborazioni_credentials import ElaborazioneCredentialConfigurationError


def template_variables(item) -> dict[str, str]:
    payload = item.payload_json or {}
    variables = {
        "contribuente_nome": item.display_name or item.codice_fiscale,
        "numero_avviso": payload.get("notice_number", ""),
        "anno_tributario": ", ".join(str(year) for year in item.years_json),
        # Preserve the original variable for existing approved template versions.
        "importo": str(payload.get("notice_total_amount") or item.saldo_amount),
        "ente_nome": "Consorzio di Bonifica dell'Oristanese",
        "codice_fiscale": item.codice_fiscale,
        "url_portale": TAXPAYER_PORTAL_URL,
        "termine_pagamento": front_payment_due_phrase(
            payload, item.years_json, _gaia_bollettino_due_date
        ),
        **_portal_fields(payload),
        **_document_amount(payload),
    }
    return variables


def _document_amount(payload) -> dict[str, str]:
    # A missing source amount must block templates that require the document total.
    # Do not use a live accounting recalculation or omit the printed notification fee.
    amount = payload.get("saldo_amount") or payload.get("due_amount")
    fee = payload.get("notification_amount") or REGISTERED_MAIL_NOTIFICATION_AMOUNT
    if _valid_saved_amount(amount) and _valid_saved_amount(fee):
        return {
            "importo_documento": f"{notice_total_amount(payload):,.2f}".replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        }
    return {}


def _valid_saved_amount(value) -> bool:
    # Saved PDF amounts use decimal points. Reject localised/invalid values;
    # the legacy renderer's zero fallback cannot establish an amount to send.
    try:
        return Decimal(str(value).replace("EUR", "").strip()).is_finite()
    except InvalidOperation:
        return False


def _portal_fields(payload) -> dict[str, str]:
    # Use the encrypted snapshot already bound to this PDF, never a fresh CF lookup.
    entries = payload.get(PORTAL_ACCESS_KEY) or []
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        return {}
    entry = entries[0]
    if not _access_digits(entry.get("account_code")) or not isinstance(
        entry.get("pin_encrypted"), str
    ):
        return {}
    try:
        account, pin = printable_portal_access(payload)[0]
    except (InvalidToken, ElaborazioneCredentialConfigurationError, UnicodeError):
        return {}
    if not _access_digits(pin):
        return {}
    return {"codice_utenza": account, "pin_utenza": pin}


def _access_digits(value) -> bool:
    return isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 32
