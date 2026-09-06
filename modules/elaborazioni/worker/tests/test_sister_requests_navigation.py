import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sister_requests_navigation as navigation
from sister_requests_navigation import select_requests_category


@pytest.mark.parametrize("period_present", [False, True])
@pytest.mark.parametrize(
    "label,value", [("Non evadibili", "nonEspletabili"), ("Espletate", "espletate")]
)
def test_radio_filter_is_submitted_before_reading_rows(period_present, label, value):
    page = MagicMock()
    radio, period, submit = AsyncMock(), AsyncMock(), AsyncMock()
    radio.count.return_value = 1
    radio.is_checked.return_value = True
    period.count.return_value = int(period_present)
    period.input_value.return_value = "-"
    selectors = {
        f"input[name='radioCount'][value='{value}']": radio,
        "select[name='comboGiorni']": period,
        "input[name='metodo'][value='Aggiorna']": submit,
    }
    page.locator.side_effect = selectors.__getitem__
    page.wait_for_load_state = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    assert asyncio.run(select_requests_category(page, label))
    radio.check.assert_awaited_once()
    submit.click.assert_awaited_once()
    assert period.select_option.await_count == int(period_present)
    if period_present:
        period.select_option.assert_awaited_once_with("-", timeout=5000)


@pytest.mark.parametrize(
    "count,visible,expected", [(0, True, False), (1, False, False), (1, True, True)]
)
def test_legacy_category_navigation(count, visible, expected):
    page = MagicMock()
    radio, tab = AsyncMock(), AsyncMock()
    radio.count.return_value = 0
    tab.count.return_value = count
    tab.is_visible.return_value = visible
    page.locator.side_effect = [radio, MagicMock(first=tab)]
    page.wait_for_load_state = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    assert asyncio.run(select_requests_category(page, "Tab")) is expected
    assert tab.click.await_count == int(expected)


def test_submit_failure_does_not_report_success():
    page = MagicMock()
    radio, period, submit = AsyncMock(), AsyncMock(), AsyncMock()
    radio.count.return_value = 1
    period.count.return_value = 0
    submit.click.side_effect = TimeoutError("filter not submitted")
    page.locator.side_effect = [radio, radio, period, submit]
    with pytest.raises(TimeoutError, match="filter not submitted"):
        asyncio.run(select_requests_category(page, "Espletate"))


@pytest.mark.parametrize("outcome", ["found", "missing", "unavailable"])
def test_search_dates_is_finite_and_deduplicated(monkeypatch, outcome, caplog):
    page = MagicMock()
    options = AsyncMock()
    options.evaluate_all.return_value = ["05/09/2026", "04/09/2026", "05/09/2026"]
    page.locator.return_value = options
    select = AsyncMock(side_effect=[True, outcome != "unavailable", True])
    monkeypatch.setattr(navigation, "select_requests_category", select)
    row = object()
    find = AsyncMock(side_effect=[None, None, row if outcome == "found" else None])
    result = asyncio.run(navigation.find_in_requests_category(page, "Prelevate", find))
    assert result is (row if outcome == "found" else None)
    if outcome == "found":
        assert select.await_count == 3
        assert select.await_args.args[-1] == "04/09/2026"
    else:
        assert "elenco potenzialmente limitato" in caplog.text


@pytest.mark.parametrize("checked,period", [(False, "-"), (True, "05/09/2026")])
def test_unapplied_filter_fails_closed(checked, period):
    page = MagicMock()
    radio, selector, submit = AsyncMock(), AsyncMock(), AsyncMock()
    radio.is_checked.return_value = checked
    selector.count.return_value = 1
    selector.input_value.return_value = period
    page.locator.side_effect = [radio, selector, submit]
    page.wait_for_load_state = AsyncMock()
    with pytest.raises(navigation.SisterRequestCorrelationError, match="non ha applicato"):
        asyncio.run(navigation.submit_requests_filter(page, "prelevate", "-"))
