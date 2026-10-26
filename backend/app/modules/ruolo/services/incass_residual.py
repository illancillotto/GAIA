"""Status of an inCASS notice whose residual is settled.

inCASS reports a negative ``importo_residuo`` when the contribuente paid more
than due (stato "Con esubero", or an annulled notice already collected): that
is a credit of the contribuente, never an amount to solicit.
"""

from decimal import Decimal

from app.modules.ruolo.enums import RuoloTributiPaymentStatus


def settled_status(residual_amount: Decimal) -> str:
    if residual_amount < Decimal("0"):
        return RuoloTributiPaymentStatus.OVERPAID.value
    return RuoloTributiPaymentStatus.PAID.value
