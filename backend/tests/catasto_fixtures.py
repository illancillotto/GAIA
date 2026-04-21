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


def build_oristanese_dirty_capacitas_dataframe(*, year: str = "2025") -> pd.DataFrame:
    """
    Wider fixture for Oristanese-area imports with intentionally mixed quality.

    Goals:
    - multiple comuni and distretti
    - mixed CF formatting / missing CF
    - subalterno optional / blank
    - one invalid comune to keep anomaly path exercised
    """
    rows: list[dict[str, str]] = [
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "165",
            "CCO": "UT-DIRTY-ARB-001",
            "FRA": "1",
            "DISTRETTO": "10",
            "Unnamed: 7": "Distretto Arborea",
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
            "DENOMINAZIONE": "Azienda Arborea Nord",
            "CODICE FISCALE": " dnifse64c01l122y ",
        },
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "212",
            "CCO": "UT-DIRTY-CAB-001",
            "FRA": "2",
            "DISTRETTO": "12",
            "Unnamed: 7": "Distretto Cabras",
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
            "DENOMINAZIONE": "Cooperativa Cabras Centro",
            "CODICE FISCALE": "00588230953",
        },
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "283",
            "CCO": "UT-DIRTY-MAR-001",
            "FRA": "1",
            "DISTRETTO": "18",
            "Unnamed: 7": "Distretto Marrubiu",
            "COMUNE": "Marrubiu",
            "SEZIONE": "",
            "FOGLIO": "11",
            "PARTIC": "205",
            "SUB": "",
            "SUP.CATA.": "1600",
            "SUP.IRRIGABILE": "1550",
            "Ind. Spese Fisse": "1.45",
            "Imponibile s.f.": "2247.5",
            "ESENTE 0648": "false",
            "ALIQUOTA 0648": "0.1",
            "IMPORTO 0648": "224.75",
            "ALIQUOTA 0985": "0.2",
            "IMPORTO 0985": "449.5",
            "DENOMINAZIONE": "Impresa Marrubiu Sud",
            "CODICE FISCALE": "",
        },
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "222",
            "CCO": "UT-DIRTY-NUR-001",
            "FRA": "1",
            "DISTRETTO": "22",
            "Unnamed: 7": "Distretto Nurachi",
            "COMUNE": "Nurachi",
            "SEZIONE": "",
            "FOGLIO": "6",
            "PARTIC": "88",
            "SUB": "2",
            "SUP.CATA.": "600",
            "SUP.IRRIGABILE": "610",
            "Ind. Spese Fisse": "1.3",
            "Imponibile s.f.": "793",
            "ESENTE 0648": "false",
            "ALIQUOTA 0648": "0.1",
            "IMPORTO 0648": "79.3",
            "ALIQUOTA 0985": "0.2",
            "IMPORTO 0985": "158.6",
            "DENOMINAZIONE": "Azienda Nurachi Est",
            "CODICE FISCALE": "RSSMRA80A01H501U",
        },
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "280",
            "CCO": "UT-DIRTY-TER-001",
            "FRA": "1",
            "DISTRETTO": "25",
            "Unnamed: 7": "Distretto Terralba",
            "COMUNE": "Terralba",
            "SEZIONE": "",
            "FOGLIO": "14",
            "PARTIC": "330",
            "SUB": "",
            "SUP.CATA.": "2100",
            "SUP.IRRIGABILE": "2100",
            "Ind. Spese Fisse": "1.55",
            "Imponibile s.f.": "3255",
            "ESENTE 0648": "false",
            "ALIQUOTA 0648": "0.1",
            "IMPORTO 0648": "325.5",
            "ALIQUOTA 0985": "0.2",
            "IMPORTO 0985": "651",
            "DENOMINAZIONE": "Societa Terralba Ovest",
            "CODICE FISCALE": "00588230953",
        },
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "239",
            "CCO": "UT-DIRTY-SGI-001",
            "FRA": "3",
            "DISTRETTO": "27",
            "Unnamed: 7": "Distretto Santa Giusta",
            "COMUNE": "Santa Giusta",
            "SEZIONE": "",
            "FOGLIO": "2",
            "PARTIC": "19",
            "SUB": "",
            "SUP.CATA.": "980",
            "SUP.IRRIGABILE": "970",
            "Ind. Spese Fisse": "1.25",
            "Imponibile s.f.": "1212.5",
            "ESENTE 0648": "true",
            "ALIQUOTA 0648": "0.1",
            "IMPORTO 0648": "0",
            "ALIQUOTA 0985": "0.2",
            "IMPORTO 0985": "242.5",
            "DENOMINAZIONE": "Consorziato Santa Giusta",
            "CODICE FISCALE": "dnifse64c01l122y",
        },
        {
            "ANNO": year,
            "PVC": "95",
            "COM": "999",
            "CCO": "UT-DIRTY-INV-001",
            "FRA": "1",
            "DISTRETTO": "99",
            "Unnamed: 7": "Distretto Invalido",
            "COMUNE": "Comune Inventato",
            "SEZIONE": "",
            "FOGLIO": "99",
            "PARTIC": "999",
            "SUB": "",
            "SUP.CATA.": "100",
            "SUP.IRRIGABILE": "120",
            "Ind. Spese Fisse": "1.1",
            "Imponibile s.f.": "100",
            "ESENTE 0648": "false",
            "ALIQUOTA 0648": "0.1",
            "IMPORTO 0648": "1",
            "ALIQUOTA 0985": "0.2",
            "IMPORTO 0985": "2",
            "DENOMINAZIONE": "Comune Invalido Fixture",
            "CODICE FISCALE": "BADCF",
        },
    ]
    return pd.DataFrame(rows)


def build_oristanese_dirty_capacitas_workbook_bytes(
    dataframe: pd.DataFrame | None = None,
    *,
    sheet_name: str = "Ruoli 2025",
) -> bytes:
    output = BytesIO()
    dataframe = dataframe if dataframe is not None else build_oristanese_dirty_capacitas_dataframe()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


def build_capacitas_workbook_bytes(dataframe: pd.DataFrame | None = None) -> bytes:
    output = BytesIO()
    dataframe = dataframe if dataframe is not None else build_capacitas_dataframe()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Ruoli 2025", index=False)
    return output.getvalue()
