from __future__ import annotations

import pandas as pd
from app.modules.catasto.services.comuni_reference import get_comune_by_capacitas_code, load_comuni_reference

_comuni_df: pd.DataFrame | None = None

try:
    import codicefiscale as _codicefiscale  # type: ignore
except Exception:  # pragma: no cover
    _codicefiscale = None


def _get_comuni() -> pd.DataFrame:
    global _comuni_df
    if _comuni_df is None:
        _comuni_df = load_comuni_reference()
    return _comuni_df


def validate_codice_fiscale(cf_raw: str | None) -> dict[str, object | None]:
    if not cf_raw or str(cf_raw).strip() == "" or str(cf_raw).upper() == "NAN":
        return {
            "cf_normalizzato": None,
            "is_valid": False,
            "tipo": "MANCANTE",
            "error_code": "CF_MANCANTE",
        }

    cf = str(cf_raw).upper().strip()
    if len(cf) == 16:
        try:
            if _codicefiscale is not None:
                is_valid = bool(_codicefiscale.isvalid(cf))
            else:
                is_valid = _is_valid_cf_checksum(cf)
            return {
                "cf_normalizzato": cf,
                "is_valid": is_valid,
                "tipo": "PF",
                "error_code": None if is_valid else "CHECKSUM_ERRATO",
            }
        except Exception:
            return {
                "cf_normalizzato": cf,
                "is_valid": False,
                "tipo": "PF",
                "error_code": "CHECKSUM_ERRATO",
            }

    if len(cf) == 11 and cf.isdigit():
        is_valid = _check_digit_piva(cf)
        return {
            "cf_normalizzato": cf,
            "is_valid": is_valid,
            "tipo": "PG",
            "error_code": None if is_valid else "CHECKSUM_ERRATO",
        }

    return {
        "cf_normalizzato": cf,
        "is_valid": False,
        "tipo": "FORMATO_SCONOSCIUTO",
        "error_code": "FORMATO_NON_RICONOSCIUTO",
    }


_ODD_MAP = {
    **{str(i): v for i, v in enumerate([1, 0, 5, 7, 9, 13, 15, 17, 19, 21])},
    "A": 1,
    "B": 0,
    "C": 5,
    "D": 7,
    "E": 9,
    "F": 13,
    "G": 15,
    "H": 17,
    "I": 19,
    "J": 21,
    "K": 2,
    "L": 4,
    "M": 18,
    "N": 20,
    "O": 11,
    "P": 3,
    "Q": 6,
    "R": 8,
    "S": 12,
    "T": 14,
    "U": 16,
    "V": 10,
    "W": 22,
    "X": 25,
    "Y": 24,
    "Z": 23,
}

_EVEN_MAP = {
    **{str(i): i for i in range(10)},
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
    "E": 4,
    "F": 5,
    "G": 6,
    "H": 7,
    "I": 8,
    "J": 9,
    "K": 10,
    "L": 11,
    "M": 12,
    "N": 13,
    "O": 14,
    "P": 15,
    "Q": 16,
    "R": 17,
    "S": 18,
    "T": 19,
    "U": 20,
    "V": 21,
    "W": 22,
    "X": 23,
    "Y": 24,
    "Z": 25,
}

_CHECK_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _is_valid_cf_checksum(cf: str) -> bool:
    """
    Validazione checksum CF 16 caratteri (persone fisiche).
    Non verifica semantica (data/comune), solo check digit.
    """
    if len(cf) != 16:
        return False
    cf = cf.upper().strip()
    if not cf.isalnum():
        return False

    total = 0
    for i, ch in enumerate(cf[:15]):
        if i % 2 == 0:  # posizioni 1,3,... in 1-based => odd map
            total += _ODD_MAP.get(ch, 0)
        else:
            total += _EVEN_MAP.get(ch, 0)
    expected = _CHECK_CHARS[total % 26]
    return cf[15] == expected


def _check_digit_piva(piva: str) -> bool:
    checksum = 0
    for index, char in enumerate(piva[:-1]):
        number = int(char)
        if index % 2 == 0:
            checksum += number
        else:
            doubled = number * 2
            checksum += doubled if doubled < 10 else doubled - 9
    return (10 - checksum % 10) % 10 == int(piva[-1])


def validate_comune(cod_istat: int | None) -> dict[str, object | None]:
    """
    Valida il codice comune legacy usato oggi da Catasto/Capacitas.

    Il parametro si chiama ancora `cod_istat` per compatibilita con il modello
    attuale, ma semanticamente non rappresenta il codice comune numerico
    ufficiale ISTAT moderno. Il controllo delega al dataset di riferimento del
    dominio, che conserva sia il codice legacy sia gli identificativi ufficiali.
    """
    if cod_istat is None:
        return {"is_valid": False, "nome_ufficiale": None}

    match = get_comune_by_capacitas_code(int(cod_istat))
    if match is None:
        return {"is_valid": False, "nome_ufficiale": None}
    return {"is_valid": True, "nome_ufficiale": str(match["nome_comune"])}


def validate_superficie(
    sup_irr: float | int | None,
    sup_cata: float | int | None,
    tolerance_pct: float = 0.01,
) -> dict[str, float | bool]:
    if sup_irr is None or sup_cata is None:
        return {"ok": True, "delta_pct": 0.0, "delta_mq": 0.0}
    delta = float(sup_irr) - float(sup_cata)
    delta_pct = delta / float(sup_cata) if float(sup_cata) > 0 else 0.0
    return {"ok": delta_pct <= tolerance_pct, "delta_pct": round(delta_pct, 6), "delta_mq": round(delta, 2)}


def validate_imponibile(
    imponibile: float | int | None,
    sup_irr: float | int | None,
    ind_sf: float | int | None,
    tolerance: float = 0.01,
) -> dict[str, float | bool | None]:
    if any(value is None for value in (imponibile, sup_irr, ind_sf)):
        return {"ok": True, "delta": 0.0, "atteso": None}
    atteso = float(sup_irr) * float(ind_sf)
    delta = abs(float(imponibile) - atteso)
    return {"ok": delta <= tolerance, "delta": round(delta, 4), "atteso": round(atteso, 2)}


def validate_importo_0648(
    importo: float | int | None,
    imponibile: float | int | None,
    aliquota: float | int | None,
    tolerance: float = 0.01,
) -> dict[str, float | bool | None]:
    if any(value is None for value in (importo, imponibile, aliquota)):
        return {"ok": True, "delta": 0.0, "atteso": None}
    atteso = float(imponibile) * float(aliquota)
    delta = abs(float(importo) - atteso)
    return {"ok": delta <= tolerance, "delta": round(delta, 4), "atteso": round(atteso, 4)}


def validate_importo_0985(
    importo: float | int | None,
    imponibile: float | int | None,
    aliquota: float | int | None,
    tolerance: float = 0.01,
) -> dict[str, float | bool | None]:
    if any(value is None for value in (importo, imponibile, aliquota)):
        return {"ok": True, "delta": 0.0, "atteso": None}
    atteso = float(imponibile) * float(aliquota)
    delta = abs(float(importo) - atteso)
    return {"ok": delta <= tolerance, "delta": round(delta, 4), "atteso": round(atteso, 4)}
