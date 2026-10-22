from __future__ import annotations

import re

import pytest

from app.modules.ruolo.services import tributi_reminder_service as reminder_service
from app.modules.ruolo.services.tributi_legal_text import (
    INSTALLMENT_TIERS,
    ROLE_YEAR_RESOLUTIONS,
    MissingRoleYearResolutionsError,
    apply_role_year_resolutions,
    legal_page_html,
    resolutions_for_years,
)

FIELD_VALUES = {"CodFiscale": "RSSMRA80A01H501Z", "Avviso_n": "020210000637550"}


def _legal_text(years: list[int]) -> str:
    rendered = legal_page_html(_template_blocks(), FIELD_VALUES, years)
    return (
        re.sub(r"<[^>]+>", "", rendered)
        .replace("&#x27;", "'")
        .replace("\N{RIGHT SINGLE QUOTATION MARK}", "'")
    )


def _template_blocks() -> list[dict]:
    return reminder_service._extract_gaia_legal_blocks(
        reminder_service._default_batch_reminder_template_path()
    )


@pytest.mark.parametrize(
    ("year", "emission", "emission_date", "approval", "approval_date"),
    [
        (2021, "89/2022", "03.08.2022", "106/2022", "19.09.2022"),
        (2022, "116/2023", "30.08.2023", "131/2023", "16.10.2023"),
        (2023, "52/2024", "05.04.2024", "58/2024", "19.04.2024"),
        (2024, "6/2025", "28.01.2025", "19/2025", "21.02.2025"),
        (2025, "5/2026", "15.01.2026", "23/2026", "20.02.2026"),
    ],
)
def test_single_year_legal_page_prints_the_year_resolutions(
    year: int, emission: str, emission_date: str, approval: str, approval_date: str
) -> None:
    text = _legal_text([year])

    assert text.count("Informazioni sul tributo.") == 1
    assert (
        f"L'emissione dei ruoli per l'anno {year} è stata disposta con delibera Consiglio di Amministrazione "
        f"(di seguito CdA) n. {emission}, pubblicata all'albo in data {emission_date} e approvata con Delibera "
        f"CdA n. {approval} pubblicata all'albo in data {approval_date}."
    ) in text
    assert f"(Delib. CdA n. {approval})" in text
    assert f"in base al bilancio {year}, e successive variazioni" in text
    assert f"confermati con delibera del CdD n.14/2020 e delibera CdA n. {emission}." in text
    assert f"giusta Delibera del CdA n. {approval}" in text
    other_approvals = {item.approval for item in ROLE_YEAR_RESOLUTIONS.values()} - {approval}
    assert not any(f"n. {other}" in text for other in other_approvals)
    assert text.count("esercizio 2017") == (1 if year in (2021, 2022) else 0)
    assert "RSSMRA80A01H501Z" in text and "020210000637550" in text


def test_tribute_info_label_stays_bold() -> None:
    rendered = legal_page_html(_template_blocks(), FIELD_VALUES, [2024])

    assert (
        "<p><strong>Informazioni sul tributo.</strong> L\N{RIGHT SINGLE QUOTATION MARK}\N{LEFT DOUBLE QUOTATION MARK}Avviso di Pagamento\N{RIGHT DOUBLE QUOTATION MARK}"
        in rendered
    )


def test_multi_year_legal_page_lists_every_year_and_uses_latest_resolutions() -> None:
    text = _legal_text([2023, 2021, 2022])

    assert "L'emissione dei ruoli per gli anni 2021, 2022 e 2023 è stata disposta" in text
    assert "(di seguito CdA) n. 89/2022" in text
    assert (
        "pubblicata all'albo in data 19.09.2022 per l'anno 2021, con delibera CdA n. 116/2023"
        in text
    )
    assert "per l'anno 2022 e con delibera CdA n. 52/2024" in text
    assert text.count("(di seguito CdA)") == 1
    assert text.count("esercizio 2017") == 1
    assert "(Delib. CdA n. 58/2024)" in text
    assert "in base al bilancio 2021, 2022 e 2023, e successive variazioni" in text
    assert "delibera CdA n. 52/2024." in text
    assert "giusta Delibera del CdA n. 58/2024" in text


def test_legal_page_without_configured_resolutions_fails_closed() -> None:
    with pytest.raises(MissingRoleYearResolutionsError, match="2026"):
        _legal_text([2025, 2026])
    with pytest.raises(MissingRoleYearResolutionsError, match="nessun anno"):
        resolutions_for_years([])


def test_template_without_expected_paragraphs_fails_closed() -> None:
    blocks = _template_blocks()
    without_tribute_info = [
        block for block in blocks if not block["text"].startswith("Informazioni sul tributo")
    ]
    without_installment = [block for block in blocks if "Delib. CdA" not in block["text"]]

    for broken in (without_tribute_info, without_installment):
        with pytest.raises(MissingRoleYearResolutionsError, match="paragrafi attesi"):
            apply_role_year_resolutions(broken, [2024])


def test_template_paragraphs_keep_list_flags_and_untouched_text() -> None:
    blocks = _template_blocks()
    adapted = apply_role_year_resolutions(blocks, [2025])

    assert [block["list"] for block in adapted] == [block["list"] for block in blocks]
    assert adapted[0] == blocks[0]
    assert adapted[-1] == blocks[-1]


def test_missing_template_uses_generic_fallback_without_resolutions() -> None:
    rendered = legal_page_html([], FIELD_VALUES, [2026])

    assert "atti deliberativi dell'Ente" in rendered
    assert "RSSMRA80A01H501Z" in rendered


def test_proposal_html_uses_payload_years_for_the_legal_page() -> None:
    payload = {
        "years": [2024],
        "notice_number": "020240001804580",
        "codice_fiscale": "RSSMRA80A01H501Z",
        "display_name": "ROSSI MARIO",
        "avvisi": [],
    }

    rendered = reminder_service._gaia_proposal_html(
        payload, include_partitario=False, include_bollettino=False
    )

    assert "per l\N{RIGHT SINGLE QUOTATION MARK}anno 2024 è stata disposta" in rendered
    assert "(Delib. CdA n. 19/2025)" in rendered
    assert (
        "padding: 0; text-align: center; }"
        in rendered.split(".signature .note {")[1].split("\n")[0]
    )


def test_installment_list_becomes_an_ordered_table() -> None:
    rendered = legal_page_html(_template_blocks(), FIELD_VALUES, [2024])

    assert "rate per gli importi" not in rendered
    table = re.search(r'<table class="legal-installments".*?</table>', rendered, re.S)
    assert table is not None
    cells = re.findall(r"<td[^>]*>(.*?)</td>", table.group(0))
    assert cells[:6] == [amount for amount, _ in INSTALLMENT_TIERS]
    assert cells[6:] == [f"<strong>{rate}</strong>" for _, rate in INSTALLMENT_TIERS]
    assert [rate for _, rate in INSTALLMENT_TIERS] == [
        "nessuna dilazione",
        "2",
        "4",
        "6",
        "12",
        "18",
    ]
    assert "Importo dell&#x27;avviso" in table.group(0)
    assert "Numero massimo di rate" in table.group(0)


def test_template_without_installment_list_fails_closed() -> None:
    blocks = [block for block in _template_blocks() if "rate per gli importi" not in block["text"]]

    with pytest.raises(MissingRoleYearResolutionsError, match="fasce di dilazione"):
        legal_page_html(blocks, FIELD_VALUES, [2024])


def test_legal_page_is_wrapped_with_the_print_fit_script() -> None:
    rendered = legal_page_html(_template_blocks(), FIELD_VALUES, [2021, 2022, 2023, 2024, 2025])

    assert rendered.startswith('<div class="legal-fit">')
    assert rendered.endswith("})();</script>")
    assert "</div><script>" in rendered
    assert "largest(1.05, 1.8" in rendered and "largest(70, 100" in rendered
