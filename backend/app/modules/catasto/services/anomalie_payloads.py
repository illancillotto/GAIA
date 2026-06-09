from __future__ import annotations

from decimal import Decimal

from app.models.catasto_phase1 import CatAnomalia, CatUtenzaIrrigua


def _to_float(value: Decimal | float | int | None, digits: int | None = None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return round(number, digits) if digits is not None else number


def build_anomalia_payload(anomalia: CatAnomalia, utenza: CatUtenzaIrrigua | None = None) -> dict | None:
    payload = dict(anomalia.dati_json) if isinstance(anomalia.dati_json, dict) else {}
    if anomalia.tipo != "VAL-06-imponibile" or utenza is None:
        return payload or None

    sup_irrigabile = _to_float(utenza.sup_irrigabile_mq, 2)
    sup_catastale = _to_float(utenza.sup_catastale_mq, 2)
    indice_spese_fisse = _to_float(utenza.ind_spese_fisse, 4)
    imponibile_registrato = _to_float(utenza.imponibile_sf, 2)

    if sup_irrigabile is not None:
        payload["sup_irrigabile_mq"] = sup_irrigabile
    if sup_catastale is not None:
        payload["sup_catastale_mq"] = sup_catastale
    if indice_spese_fisse is not None:
        payload["ind_spese_fisse"] = indice_spese_fisse
    if imponibile_registrato is not None:
        payload["imponibile_registrato"] = imponibile_registrato

    if sup_irrigabile is not None and indice_spese_fisse is not None:
        atteso_irrigabile = round(sup_irrigabile * indice_spese_fisse, 2)
        payload["atteso"] = atteso_irrigabile
        if imponibile_registrato is not None:
            payload["delta"] = round(abs(imponibile_registrato - atteso_irrigabile), 4)

    if sup_catastale is not None and indice_spese_fisse is not None:
        atteso_catastale = round(sup_catastale * indice_spese_fisse, 2)
        payload["atteso_catastale"] = atteso_catastale
        if imponibile_registrato is not None:
            delta_vs_catastale = round(abs(imponibile_registrato - atteso_catastale), 4)
            payload["delta_vs_catastale"] = delta_vs_catastale
            payload["coincide_con_catastale"] = delta_vs_catastale <= 0.01

    return payload or None
