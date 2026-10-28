"""The avviso row of a reminder candidate, built from its effective tributi item."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_ITEM_KEYS = (
    "principal_saldo_amount",
    "surcharge_amount",
    "interest_amount",
    "adjusted_due_amount",
    "interest_start_source",
    "calculation_policy_name",
    "paid_amount",
    "saldo_amount",
    "payment_status",
    "capacitas_url",
    "annuality_manager_key",
    "annuality_manager_label",
    "calculation_policy",
)
_AMOUNT_COLUMNS = (
    "importo_totale_0648",
    "importo_totale_0985",
    "importo_totale_0668",
    "importo_totale_euro",
)


def _amount(value: object) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _day(value: object) -> str | None:
    return str(value) if value else None


def candidate_avviso_entry(avviso: Any, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": avviso.id,
        "codice_cnc": item["capacitas_avviso_code"] or avviso.codice_cnc,
        "anno_tributario": avviso.anno_tributario,
        "nominativo_raw": avviso.nominativo_raw,
        "domicilio_raw": avviso.domicilio_raw,
        "residenza_raw": avviso.residenza_raw,
        "codice_utenza": avviso.codice_utenza,
        **{column: _amount(getattr(avviso, column)) for column in _AMOUNT_COLUMNS},
        **{key: item[key] for key in _ITEM_KEYS},
        "calculation_date": _day(item["calculation_date"]),
        "interest_start_date": _day(item["interest_start_date"]),
        "rateization_fee_amount": item["incass_notice"].get("rateization_fee_amount"),
        "incass_stato_label": item["incass_notice"].get("stato_label"),
    }
