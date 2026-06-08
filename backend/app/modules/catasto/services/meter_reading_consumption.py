from __future__ import annotations

from decimal import Decimal


def effective_consumption_mc(
    *,
    consumo_mc: Decimal | None,
    lettura_iniziale: Decimal | None,
    lettura_finale: Decimal | None,
) -> Decimal | None:
    if consumo_mc is not None:
        return consumo_mc
    if lettura_iniziale is None or lettura_finale is None:
        return None
    if lettura_finale < lettura_iniziale:
        return None
    return lettura_finale - lettura_iniziale
