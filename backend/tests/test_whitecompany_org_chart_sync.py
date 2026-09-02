from unittest.mock import Mock, call

import pytest

from app.modules.accessi.sync_org_charts import WhiteOrgChartsSyncResult
from app.services import whitecompany_org_chart_sync


def test_sync_white_org_charts_to_canonical_runs_both_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = Mock()
    rows = []
    staging_result = WhiteOrgChartsSyncResult(
        synced=1,
        skipped=0,
        entries_synced=2,
        errors=[],
    )
    staging_sync = Mock(return_value=staging_result)
    canonical_sync = Mock()
    sync_order = Mock()
    sync_order.attach_mock(staging_sync, "staging")
    sync_order.attach_mock(canonical_sync, "canonical")
    monkeypatch.setattr(whitecompany_org_chart_sync, "sync_white_org_charts", staging_sync)
    monkeypatch.setattr(whitecompany_org_chart_sync, "sync_from_whitecompany", canonical_sync)

    result = whitecompany_org_chart_sync.sync_white_org_charts_to_canonical(
        db=db,
        rows=rows,
        user_id=7,
    )

    assert result is staging_result
    assert sync_order.mock_calls == [
        call.staging(db=db, rows=rows),
        call.canonical(db, user_id=7),
    ]
    staging_sync.assert_called_once_with(db=db, rows=rows)
    canonical_sync.assert_called_once_with(db, user_id=7)
