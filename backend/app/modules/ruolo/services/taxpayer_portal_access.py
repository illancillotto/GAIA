"""One verified portal account per recipient; ambiguous accounts require office review."""

from collections import defaultdict

from sqlalchemy import select

from app.modules.ruolo.portal_access_models import RuoloTaxpayerPortalAccess
from app.services.elaborazioni_credentials import get_credential_fernet

PORTAL_ACCESS_KEY = "taxpayer_portal_access"


def with_portal_access(db, candidates):
    tax_codes = {candidate["codice_fiscale"].strip().upper() for candidate in candidates}
    accesses = defaultdict(list)
    if tax_codes:
        rows = db.scalars(
            select(RuoloTaxpayerPortalAccess)
            .where(RuoloTaxpayerPortalAccess.tax_code.in_(tax_codes))
            .order_by(RuoloTaxpayerPortalAccess.account_code)
        )
        for row in rows:
            accesses[row.tax_code].append(
                {
                    "account_code": row.account_code,
                    "pin_encrypted": row.pin_encrypted.decode("ascii"),
                }
            )
    return [
        {
            **candidate,
            PORTAL_ACCESS_KEY: _single_account(
                accesses[candidate["codice_fiscale"].strip().upper()]
            ),
        }
        for candidate in candidates
    ]


def _single_account(entries):
    # A CF with multiple source accounts does not identify the notice's utenza.
    # Never choose the first account or print other utenze's credentials.
    return entries if len(entries) == 1 else []


def printable_portal_access(payload):
    """Decrypt only at rendering time; persistent payloads never contain cleartext PINs."""
    entries = _single_account(payload.get(PORTAL_ACCESS_KEY) or [])
    if not entries:
        return []
    fernet = get_credential_fernet()
    return [
        (entry["account_code"], fernet.decrypt(entry["pin_encrypted"].encode("ascii")).decode())
        for entry in entries
    ]
