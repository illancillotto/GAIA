import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sister_requests_navigation as navigation
from sister_request_rows import parse_remote_rows
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


@pytest.mark.parametrize("present", [False, True])
def test_restore_menu_uses_same_page_authenticated_home_only_when_missing(present):
    page = MagicMock()
    link = AsyncMock()
    link.count.return_value = int(present)
    page.get_by_role.return_value = link
    page.goto = AsyncMock()
    asyncio.run(navigation.restore_portal_menu(page, "Consultazioni e Certificazioni"))
    assert page.goto.await_count == int(not present)
    assert link.wait_for.await_count == int(not present)


@pytest.mark.parametrize(
    "day,matched,snapshot",
    [("-", False, True), ("06/09/2026", True, True), ("06/09/2026", False, False)],
)
def test_search_diagnostics_are_bounded_and_do_not_log_row_contents(
    tmp_path, day, matched, snapshot
):
    page = MagicMock()
    page.locator.return_value = AsyncMock(count=AsyncMock(return_value=12))
    page.content = AsyncMock(return_value="<html>Requests</html>")
    page.screenshot = AsyncMock()
    for _ in range(2):
        asyncio.run(
            navigation.record_search_snapshot(page, "Espletate", day, matched, str(tmp_path))
        )
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text()) == {
        "category": "Espletate",
        "day": day,
        "rows": 12,
        "matched": matched,
    }
    assert page.screenshot.await_count == 2 * int(snapshot)
    assert len(list(tmp_path.glob("*.html"))) == int(snapshot)


def test_search_diagnostics_io_error_does_not_interrupt_recovery(tmp_path, caplog):
    blocked = tmp_path / "file"
    blocked.touch()
    page = MagicMock()
    page.locator.return_value = AsyncMock(count=AsyncMock(return_value=0))
    asyncio.run(navigation.record_search_snapshot(page, "Espletate", "-", False, str(blocked)))
    assert "Snapshot ricerca SISTER non salvato" in caplog.text


@pytest.mark.parametrize("ready_at", [0, 1, 2, 3, None])
def test_ready_fast_path_searches_both_categories_before_history(monkeypatch, ready_at):
    page = MagicMock()
    today = navigation.datetime.now(navigation.ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y")
    page.locator.return_value = AsyncMock()
    page.locator.return_value.evaluate_all.return_value = [today, "01/01/2020"]
    select = AsyncMock(return_value=True)
    monkeypatch.setattr(navigation, "select_requests_category", select)
    monkeypatch.setattr(navigation, "record_search_snapshot", AsyncMock())
    ready = SimpleNamespace(state="ready")
    rows = [None] * 4
    if ready_at is not None:
        rows[ready_at] = ready
    find = AsyncMock(side_effect=rows)
    result = asyncio.run(navigation.find_ready_request(page, find, None))
    assert result is (ready if ready_at is not None else None)
    expected = [(page, "Espletate"), (page, "Espletate", today),
                (page, "Prelevate"), (page, "Prelevate", today)]
    assert [call.args for call in select.await_args_list] == expected[:find.await_count]


@pytest.mark.parametrize("mode", ["unavailable", "missing_date", "date_unavailable", "not_ready"])
def test_fast_path_uses_only_exposed_dates_and_ready_correlated_rows(monkeypatch, mode):
    page = MagicMock()
    today = navigation.datetime.now(navigation.ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y")
    page.locator.return_value = AsyncMock()
    page.locator.return_value.evaluate_all.return_value = [] if mode == "missing_date" else [today]
    outcomes = {"unavailable": [False, False], "date_unavailable": [True, False, True, False]}
    select = AsyncMock(side_effect=outcomes.get(mode), return_value=True)
    monkeypatch.setattr(navigation, "select_requests_category", select)
    monkeypatch.setattr(navigation, "record_search_snapshot", AsyncMock())
    find = AsyncMock(return_value=SimpleNamespace(state="pending"))
    assert asyncio.run(navigation.find_ready_request(page, find, None)) is None
    if mode == "unavailable":
        find.assert_not_awaited()
    if mode == "missing_date":
        assert all(len(call.args) == 2 for call in select.await_args_list)


@pytest.mark.parametrize("found", [True, False])
def test_non_evadibili_retains_full_search_when_fast_path_misses(monkeypatch, found):
    page = MagicMock()
    ready = SimpleNamespace(state="ready")
    historical = SimpleNamespace(state="non_evadibile")
    fast = AsyncMock(return_value=ready if found else None)
    monkeypatch.setattr(navigation, "find_ready_request", fast)
    select = AsyncMock(return_value=True)
    monkeypatch.setattr(navigation, "select_requests_category", select)
    monkeypatch.setattr(navigation, "record_search_snapshot", AsyncMock())
    find = AsyncMock(return_value=historical)
    result = asyncio.run(navigation.find_in_requests_category(page, "Non evadibili", find))
    assert result is (ready if found else historical)
    assert select.await_count == int(not found)


def test_fast_path_does_not_swallow_filter_timeouts(monkeypatch):
    select = AsyncMock(side_effect=TimeoutError("filter timeout"))
    monkeypatch.setattr(navigation, "select_requests_category", select)
    with pytest.raises(TimeoutError, match="filter timeout"):
        asyncio.run(navigation.find_ready_request(MagicMock(), AsyncMock(), None))


@pytest.mark.parametrize("present", [False, True])
def test_visure_menu_navigation_preserves_existing_menu_recovery(monkeypatch, present):
    page = MagicMock()
    consultazioni, visure = AsyncMock(), AsyncMock()
    visure.count.return_value = int(present)
    page.get_by_role.side_effect = lambda role, name: {
        "Consultazioni": consultazioni, "Visure": visure
    }[name]
    restore = AsyncMock()
    monkeypatch.setattr(navigation, "restore_portal_menu", restore)
    selectors = SimpleNamespace(consultazioni_link_name="Consultazioni", visure_link_name="Visure")
    trace = AsyncMock()
    asyncio.run(navigation.open_portal_visure_menu(page, selectors, trace))
    restore.assert_awaited_once_with(page, "Consultazioni")
    assert consultazioni.click.await_count == int(not present)
    visure.click.assert_awaited_once()
    assert trace.await_count == 1 + int(not present)


@pytest.mark.parametrize("label", ["Espletate", "Prelevate"])
def test_verified_ready_category_supplies_state_when_row_has_no_status(label):
    page = MagicMock()
    page.locator.return_value = AsyncMock(count=AsyncMock(return_value=1))
    row = parse_remote_rows([{"text": "VISURA PDF", "values": ["idElemento=123"]}])[0]
    find = AsyncMock(return_value=row)
    result = asyncio.run(navigation.read_correlated_category_row(page, label, find))
    assert result.state == "ready"
    assert result.remote_id == "123"
    assert row.state == "unknown"


@pytest.mark.parametrize("label,count", [("Tab", 1), ("Non evadibili", 0), ("Espletate", 2)])
def test_unverified_category_does_not_manufacture_state(label, count):
    page = MagicMock()
    page.locator.return_value = AsyncMock(count=AsyncMock(return_value=count))
    row = parse_remote_rows([{"text": "VISURA", "values": ["idElemento=123"]}])[0]
    assert asyncio.run(navigation.read_correlated_category_row(page, label, AsyncMock(return_value=row))) is row


def test_non_evadibile_checkbox_row_requires_review_without_delete_or_retry():
    page = MagicMock()
    page.locator.return_value = AsyncMock(count=AsyncMock(return_value=1))
    row = parse_remote_rows([{"text": "VISURA", "values": ["idElemento=123"]}])[0]
    with pytest.raises(navigation.SisterNonEvadibileReviewRequiredError, match=r"123 conservata.*verifica manuale"):
        asyncio.run(navigation.read_correlated_category_row(page, "Non evadibili", AsyncMock(return_value=row)))
    page.locator.return_value.click.assert_not_awaited()
