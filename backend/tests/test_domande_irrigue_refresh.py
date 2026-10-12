from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.elaborazioni import domande_irrigue_autosync_scheduler as scheduler
from app.modules.elaborazioni import domande_irrigue_refresh as refresh


@pytest.mark.parametrize("completed", [None, "2026-10-07"])
def test_legacy_state_starts_a_verified_full_pass(completed):
    state = SimpleNamespace(
        completed_cycle_key=completed, cycle_key="legacy", cursor="ZZZ", pending_job_id=None
    )
    assert refresh.sync_cycle_key(state, "2026-10-08") == "full-v1"
    assert state.cursor is None
    assert refresh.refresh_years(state, 2026) is None


def test_full_pass_preserves_cursor_across_days_and_restart():
    state = SimpleNamespace(completed_cycle_key=None, cycle_key="full-v1", cursor="ABC")
    assert refresh.sync_cycle_key(state, "2026-10-08") == "full-v1"
    assert refresh.sync_cycle_key(state, "2026-10-09") == "full-v1"
    assert state.cursor == "ABC"


def test_upgrade_does_not_reset_cursor_while_legacy_job_runs():
    state = SimpleNamespace(
        completed_cycle_key=None, cycle_key="legacy", cursor="ABC", pending_job_id=8
    )
    assert refresh.sync_cycle_key(state, "2026-10-08") == "full-v1"
    assert state.cursor == "ABC"
    state.pending_job_id = None
    assert refresh.sync_cycle_key(state, "2026-10-09") == "full-v1"
    assert state.cursor is None


@pytest.mark.parametrize("completed", ["full-v1", "recent-v1:2026-12-31"])
def test_verified_completion_enables_recent_years_and_rollover(completed):
    state = SimpleNamespace(completed_cycle_key=completed, cursor="ABC")
    assert refresh.sync_cycle_key(state, "2027-01-01") == "recent-v1:2027-01-01"
    assert refresh.refresh_years(state, 2026) == [2025, 2026]
    assert refresh.refresh_years(state, 2027) == [2026, 2027]
    assert state.cursor == "ABC"


@pytest.mark.parametrize("status", ["failed", "completed_with_errors"])
def test_partial_chunk_does_not_advance_full_pass(status):
    state = SimpleNamespace(
        pending_job_id=1,
        pending_cursor="ZZZ",
        cursor="ABC",
        cycle_key="full-v1",
        completed_cycle_key=None,
    )
    db = MagicMock()
    db.get.return_value = SimpleNamespace(status=status, error_detail="retry")
    assert scheduler._reconcile_pending_job(db, state) is False
    assert state.cursor == "ABC"
    assert state.completed_cycle_key is None
    assert state.pending_job_id is None
    assert state.last_error == "retry"


def test_recent_payload_is_serializable_and_uses_local_year(monkeypatch):
    monkeypatch.setattr(
        scheduler.settings, "capacitas_domande_irrigue_autosync_timezone", "Europe/Rome"
    )
    state = SimpleNamespace(
        completed_cycle_key="full-v1",
        cycle_key=None,
        pending_job_id=None,
        pending_cursor=None,
    )
    create = MagicMock(return_value=SimpleNamespace(id=8))
    monkeypatch.setattr(scheduler, "create_domande_irrigue_sync_job", create)
    scheduler._enqueue_chunk(
        MagicMock(),
        state,
        ["ABC"],
        cycle_key="recent-v1:2027-01-01",
        credential_id=7,
        now=datetime(2026, 12, 31, 23, 30, tzinfo=UTC),
    )
    payload = create.call_args.kwargs["payload"].model_dump(exclude_none=True, mode="json")
    assert payload["refresh_years"] == [2026, 2027]
    assert payload["trigger"] == "autosync"


@pytest.mark.parametrize("payload", [None, {}, {"refresh_years": None}])
def test_unbounded_jobs_keep_original_scraper(payload):
    scraper = object()
    assert refresh.limit_scraper(scraper, payload) is scraper


@pytest.mark.parametrize(
    "years",
    [[], [2026], [2024, 2026], [2025, "2026"], [True, 2026], "2025", [999, 1000], [9999, 10000]],
)
def test_invalid_year_bounds_fail_closed(years):
    with pytest.raises(ValueError, match="due anni consecutivi"):
        refresh.limit_scraper(object(), {"refresh_years": years})


@pytest.mark.anyio
@pytest.mark.parametrize("include_details", [False, True])
async def test_filter_precedes_detail_http_requests(monkeypatch, include_details):
    rows = [
        SimpleNamespace(anno=str(year), external_row_id=str(year))
        for year in [2024, 2025, 2026, 2027]
    ]
    result = SimpleNamespace(
        domande=rows, total_domande=4, detail_op=None, details_by_domanda_id={}
    )

    async def fetch(self, **kwargs):
        if kwargs["include_details"]:
            await self._append_details(result, "list-url")
        return result

    monkeypatch.setattr(refresh.DomandeIrrigueScraper, "fetch_domande_irrigue", fetch)
    manager = object()
    scraper = refresh.limit_scraper(
        SimpleNamespace(_manager=manager), {"refresh_years": [2025, 2026]}
    )
    details = AsyncMock(return_value=[])
    monkeypatch.setattr(scraper, "fetch_domanda_details", details)
    filtered = await scraper.fetch_domande_irrigue(include_details=include_details)
    assert filtered is result
    assert [row.anno for row in filtered.domande] == ["2025", "2026"]
    assert filtered.total_domande == 2
    assert len(rows) == 4
    assert scraper._manager is manager
    assert details.await_count == (2 if include_details else 0)
    assert [call.kwargs["domanda_id"] for call in details.await_args_list] == (
        ["2025", "2026"] if include_details else []
    )


@pytest.mark.parametrize("year", [None, "", "abc", "20x6", "\uff12\uff10\uff12\uff16", "20266"])
def test_unknown_year_does_not_silently_skip_application(year):
    scraper = refresh.RecentDomandeIrrigueScraper(object(), [2025, 2026])
    result = SimpleNamespace(domande=[SimpleNamespace(anno=year)])
    with pytest.raises(ValueError, match="Anno domanda irrigua non valido"):
        scraper._filter(result)


def test_empty_recent_list_is_valid():
    scraper = refresh.RecentDomandeIrrigueScraper(object(), [2025, 2026])
    result = SimpleNamespace(domande=[], total_domande=0)
    scraper._filter(result)
    assert result.domande == []
    assert result.total_domande == 0
