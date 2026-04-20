from __future__ import annotations

from io import BytesIO

import pandas as pd


def build_capacitas_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ANNO": "2025",
                "PVC": "95",
                "COM": "165",
                "CCO": "UT-001",
                "FRA": "1",
                "DISTRETTO": "10",
                "Unnamed: 7": "Distretto 10",
                "COMUNE": "Arborea",
                "SEZIONE": "",
                "FOGLIO": "5",
                "PARTIC": "120",
                "SUB": "1",
                "SUP.CATA.": "1000",
                "SUP.IRRIGABILE": "1000",
                "Ind. Spese Fisse": "1.5",
                "Imponibile s.f.": "1500",
                "ESENTE 0648": "false",
                "ALIQUOTA 0648": "0.1",
                "IMPORTO 0648": "150",
                "ALIQUOTA 0985": "0.2",
                "IMPORTO 0985": "300",
                "DENOMINAZIONE": "Mario Rossi",
                "CODICE FISCALE": "Dnifse64c01l122y",
            },
            {
                "ANNO": "2025",
                "PVC": "95",
                "COM": "999",
                "CCO": "UT-002",
                "FRA": "1",
                "DISTRETTO": "10",
                "Unnamed: 7": "Distretto 10",
                "COMUNE": "Comune Inventato",
                "SEZIONE": "",
                "FOGLIO": "9",
                "PARTIC": "999",
                "SUB": "",
                "SUP.CATA.": "1000",
                "SUP.IRRIGABILE": "1200",
                "Ind. Spese Fisse": "1.5",
                "Imponibile s.f.": "999",
                "ESENTE 0648": "false",
                "ALIQUOTA 0648": "0.1",
                "IMPORTO 0648": "1",
                "ALIQUOTA 0985": "0.2",
                "IMPORTO 0985": "2",
                "DENOMINAZIONE": "Soggetto Test",
                "CODICE FISCALE": "BADCF",
            },
        ]
    )


def build_oristanese_territorial_capacitas_dataframe(*, year: str = "2025") -> pd.DataFrame:
    """
    Fixture "realistic but small" focused on Oristanese area.

    Keeps data synthetic and compact (no real personal data).
    """
    suffix = "TERR"
    rows: list[dict[str, str]] = [
        # Arborea (165)
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "165",
            "CCO": f"UT-{suffix}-ARB-001",
            "FRA": "1",
            "DISTRETTO": "10",
            "Unnamed: 7": "Distretto 10",
            "COMUNE": "Arborea",
            "SEZIONE": "",
            "FOGLIO": "5",
            "PARTIC": "120",
            "SUB": "1",
            "SUP.CATA.": "1000",
            "SUP.IRRIGABILE": "900",
            "Ind. Spese Fisse": "1.5",
            "Imponibile s.f.": "1350",
            "ESENTE 0648": "false",
            "ALIQUOTA 0648": "0.1",
            "IMPORTO 0648": "135",
            "ALIQUOTA 0985": "0.2",
            "IMPORTO 0985": "270",
            "DENOMINAZIONE": "Soggetto Fixture",
            "CODICE FISCALE": "Dnifse64c01l122y",
        },
        # Cabras (212)
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "212",
            "CCO": f"UT-{suffix}-CAB-001",
            "FRA": "1",
            "DISTRETTO": "12",
            "Unnamed: 7": "Distretto 12",
            "COMUNE": "Cabras",
            "SEZIONE": "",
            "FOGLIO": "3",
            "PARTIC": "45",
            "SUB": "",
            "SUP.CATA.": "800",
            "SUP.IRRIGABILE": "800",
            "Ind. Spese Fisse": "1.4",
            "Imponibile s.f.": "1120",
            "ESENTE 0648": "false",
            "ALIQUOTA 0648": "0.1",
            "IMPORTO 0648": "112",
            "ALIQUOTA 0985": "0.2",
            "IMPORTO 0985": "224",
            "DENOMINAZIONE": "Soggetto Fixture 2",
            "CODICE FISCALE": "Dnifse64c01l122y",
        },
        # Oristano (200)
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "200",
            "CCO": f"UT-{suffix}-ORI-001",
            "FRA": "1",
            "DISTRETTO": "15",
            "Unnamed: 7": "Distretto 15",
            "COMUNE": "Oristano",
            "SEZIONE": "",
            "FOGLIO": "1",
            "PARTIC": "10",
            "SUB": "",
            "SUP.CATA.": "500",
            "SUP.IRRIGABILE": "450",
            "Ind. Spese Fisse": "1.6",
            "Imponibile s.f.": "720",
            "ESENTE 0648": "false",
            "ALIQUOTA 0648": "0.1",
            "IMPORTO 0648": "72",
            "ALIQUOTA 0985": "0.2",
            "IMPORTO 0985": "144",
            "DENOMINAZIONE": "Soggetto Fixture 3",
            "CODICE FISCALE": "Dnifse64c01l122y",
        },
    ]
    return pd.DataFrame(rows)


def build_oristanese_territorial_capacitas_workbook_bytes(
    dataframe: pd.DataFrame | None = None,
    *,
    sheet_name: str = "Ruoli 2025",
) -> bytes:
    output = BytesIO()
    dataframe = dataframe if dataframe is not None else build_oristanese_territorial_capacitas_dataframe()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


def build_capacitas_workbook_bytes(dataframe: pd.DataFrame | None = None) -> bytes:
    output = BytesIO()
    dataframe = dataframe if dataframe is not None else build_capacitas_dataframe()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Ruoli 2025", index=False)
    return output.getvalue()
