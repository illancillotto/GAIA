from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd


_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "comuni_istat.csv"


@lru_cache(maxsize=1)
def load_comuni_reference() -> pd.DataFrame:
    """
    Dataset di riferimento comuni usato dal dominio Catasto.

    Nota importante:
    - `cod_istat` mantiene il codice numerico legacy scambiato da Capacitas e
      usato oggi nei join applicativi Catasto
    - NON coincide con il codice comune numerico ufficiale ISTAT moderno
    - il dataset include quindi anche `codice_catastale` e i codici ufficiali
      per rendere esplicita la distinzione ed evitare mapping hardcoded divergenti
    """
    return pd.read_csv(
        _CSV_PATH,
        dtype={
            "cod_istat": int,
            "codice_catastale": str,
            "codice_comune_formato_numerico": int,
            "codice_comune_numerico_2017_2025": int,
            "cod_provincia": int,
            "sigla_provincia": str,
            "regione": str,
        },
    )


def get_comune_by_legacy_code(codice: int | None) -> dict[str, object] | None:
    """Restituisce il comune a partire dal codice legacy Capacitas/Catasto."""
    if codice is None:
        return None
    comuni = load_comuni_reference()
    match = comuni[comuni["cod_istat"] == int(codice)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def get_legacy_code_by_catastale() -> dict[str, int]:
    """Mapping `codice catastale comune` -> `codice legacy Catasto/Capacitas`."""
    comuni = load_comuni_reference()
    return {str(row["codice_catastale"]).strip().upper(): int(row["cod_istat"]) for _, row in comuni.iterrows()}


def get_official_name_by_catastale() -> dict[str, str]:
    """Nome comune ufficiale usato per popolare le particelle importate da shapefile."""
    comuni = load_comuni_reference()
    return {
        str(row["codice_catastale"]).strip().upper(): str(row["nome_comune"]).strip()
        for _, row in comuni.iterrows()
    }
