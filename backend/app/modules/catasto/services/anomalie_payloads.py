from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.catasto_phase1 import CatAnomalia, CatUtenzaIrrigua

DIR_SURFACE_ANOMALY_TYPES = {
    "DIR-01-superficie_coltura_superata",
    "DIR-02-superficie_totale_da_verificare",
}


def _to_float(value: Decimal | float | int | None, digits: int | None = None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return round(number, digits) if digits is not None else number


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _format_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _unique_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _unique_domande(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            continue
        identity = str(value.get("id") or index)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(dict(value))
    return unique


def _enrich_domande_irrigue_surface_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sup_irrigata = _to_decimal(payload.get("sup_irrigata_mq"))
    superficie_riferimento = _to_decimal(payload.get("superficie_riferimento_mq"))
    if sup_irrigata is not None and superficie_riferimento is not None:
        payload["eccedenza_mq"] = _format_decimal(sup_irrigata - superficie_riferimento)

    row_ids = _unique_strings(payload.get("domanda_particella_ids"))
    if row_ids:
        payload["domanda_particella_ids"] = row_ids
        payload["righe_domanda_count"] = len(row_ids)

    domande = _unique_domande(payload.get("domande"))
    domanda_ids = _unique_strings(payload.get("domanda_ids")) or [
        str(domanda["id"]) for domanda in domande if domanda.get("id")
    ]
    if domanda_ids:
        payload["domanda_ids"] = domanda_ids
        payload["domande_distinte_count"] = len(domanda_ids)
    if domande:
        payload["domande"] = domande

    if row_ids:
        if len(row_ids) == 1:
            payload["causa_superficie"] = "riga_singola"
        elif len(domanda_ids) <= 1:
            payload["causa_superficie"] = "piu_righe_stessa_domanda"
        else:
            payload["causa_superficie"] = "piu_domande"

    return payload


def build_anomalia_payload(anomalia: CatAnomalia, utenza: CatUtenzaIrrigua | None = None) -> dict | None:
    payload = dict(anomalia.dati_json) if isinstance(anomalia.dati_json, dict) else {}
    if anomalia.tipo in DIR_SURFACE_ANOMALY_TYPES:
        return _enrich_domande_irrigue_surface_payload(payload) or None
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
