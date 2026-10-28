"""Real notice summaries retain interest when any annual amount is payable."""

import pytest
from bs4 import BeautifulSoup

from app.modules.ruolo.services import tributi_reminder_service as renderer

from .test_notice_presentation import _payload


@pytest.mark.parametrize(
    "amounts,visible",
    [
        ([None], False),
        (["0.00", "-0.00"], False),
        (["0.004"], False),
        (["0.00", "0.01"], True),
        (["1234.56"], True),
        (["-2.00"], True),
        (["1.00", "-1.00"], True),
    ],
)
def test_summary_interest_column_matches_displayed_annual_amounts(amounts, visible):
    payload = _payload(list(range(2021, 2021 + len(amounts))))
    for avviso, amount in zip(payload["avvisi"], amounts, strict=True):
        avviso["interest_amount"] = amount
    document = BeautifulSoup(renderer._gaia_proposal_html(payload), "html.parser")
    table = document.select_one("table.summary")
    headings = [cell.get_text() for cell in table.select("thead th")]
    assert ("Interessi" in headings) is visible
    assert bool(table.select("col.interessi")) is visible
    width = 9 if visible else 8
    assert len(headings) == len(table.select("col")) == width
    annual_rows = table.select("tbody tr")[:-1]
    assert len(annual_rows) == len(amounts)
    assert all(len(row.select("td")) == width for row in annual_rows)
    if visible:
        expected = renderer._batch_yearly_row_values(payload)
        assert [row.select("td")[6].get_text() for row in annual_rows] == [
            row["Interessi"] for row in expected
        ]
    notification = table.select("tbody tr")[-1]
    assert notification.select("td")[1]["colspan"] == str(width - 2)
    assert notification.select("td")[-1].get_text() == "11,55"
    assert document.select_one(".amount .euro").get_text() == "€. 221,55"


def test_notice_without_annual_details_uses_eight_aligned_columns():
    payload = {**_payload([2021]), "avvisi": []}
    document = BeautifulSoup(renderer._gaia_proposal_html(payload), "html.parser")
    table = document.select_one("table.summary")
    assert "Interessi" not in [cell.get_text() for cell in table.select("thead th")]
    assert len(table.select_one("tbody tr").select("td")) == 8
    assert table.select_one("tbody tr td").get_text() == "Ruolo -"
