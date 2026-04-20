from __future__ import annotations

from pathlib import Path

import codicefiscale
import pandas as pd

_comuni_df: pd.DataFrame | None = None


def _get_comuni() -> pd.DataFrame:
    global _comuni_df
    if _comuni_df is None:
        csv_path = Path(__file__).resolve().parent.parent / "data" / "comuni_istat.csv"
        _comuni_df = pd.read_csv(csv_path, dtype={"cod_istat": int})
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
            is_valid = bool(codicefiscale.isvalid(cf))
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
    if cod_istat is None:
        return {"is_valid": False, "nome_ufficiale": None}

    comuni = _get_comuni()
    match = comuni[comuni["cod_istat"] == int(cod_istat)]
    if match.empty:
        return {"is_valid": False, "nome_ufficiale": None}
    return {"is_valid": True, "nome_ufficiale": match.iloc[0]["nome_comune"]}


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
