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


def build_capacitas_workbook_bytes(dataframe: pd.DataFrame | None = None) -> bytes:
    output = BytesIO()
    dataframe = dataframe if dataframe is not None else build_capacitas_dataframe()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Ruoli 2025", index=False)
    return output.getvalue()
