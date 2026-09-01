from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.core.database import Base
from app.modules.presenze.models import PresenzeSyncJob
from app.modules.presenze.services.inaz_sync_status import (
    _parse_datetime,
    _payload,
    build_auto_retry_history_entry,
    build_inaz_sync_status,
    build_presenze_snapshot_metadata,
    resolve_inaz_sync_status,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

UTC = timezone.utc


def _job(
    *,
    status: str,
    started_at: object = datetime(2026, 8, 31, 7, 25, tzinfo=UTC),
    finished_at: object = datetime(2026, 8, 31, 7, 25, 12, tzinfo=UTC),
    records_errors: object = 0,
    failed_collaborators: object = 0,
    params: dict | None = None,
    credential_id: int | None = 1,
    period_start: date = date(2026, 8, 1),
    period_end: date = date(2026, 8, 31),
) -> SimpleNamespace:
    params_json = dict(params or {})
    params_json.setdefault("progress", {"failed_collaborators": failed_collaborators})
    return SimpleNamespace(
        id=uuid4(),
        credential_id=credential_id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        records_errors=records_errors,
        params_json=params_json,
        period_start=period_start,
        period_end=period_end,
    )


def test_resolve_inaz_sync_status_reports_success_in_utc() -> None:
    payload = resolve_inaz_sync_status(
        [
            _job(
                status="completed",
                started_at=datetime(2026, 8, 31, 9, 25),  # noqa: DTZ001 - verifies legacy naive DB values
                finished_at=datetime(2026, 8, 31, 9, 25, 12),  # noqa: DTZ001 - verifies legacy naive DB values
            )
        ],
        month="2026-08",
    )

    assert payload == {
        "status": "success",
        "last_attempt_at": "2026-08-31T09:25:00Z",
        "last_success_at": "2026-08-31T09:25:12Z",
        "data_updated_at": "2026-08-31T09:25:12Z",
        "error_code": None,
        "error_message": None,
    }


def test_resolve_inaz_sync_status_uses_latest_success_across_cohorts() -> None:
    earlier = _job(
        status="completed",
        finished_at=datetime(2026, 8, 30, 7, 25, tzinfo=UTC),
    )
    later = _job(
        status="completed",
        finished_at=datetime(2026, 8, 31, 7, 25, tzinfo=UTC),
    )

    payload = resolve_inaz_sync_status([earlier, later])

    assert payload["status"] == "success"
    assert payload["last_success_at"] == "2026-08-31T07:25:00Z"


def test_resolve_inaz_sync_status_reports_never_without_visible_attempts() -> None:
    queued = _job(status="pending", started_at=None, finished_at=None)
    file_import = _job(status="completed", params={"mode": "xlsm_export"})
    no_credential = _job(status="completed", credential_id=None)
    other_month = _job(
        status="completed",
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
    )

    assert resolve_inaz_sync_status(
        [queued, file_import, no_credential, other_month], month="2026-08"
    ) == {
        "status": "never",
        "last_attempt_at": None,
        "last_success_at": None,
        "data_updated_at": None,
        "error_code": None,
        "error_message": None,
    }


def test_resolve_inaz_sync_status_keeps_previous_success_after_failure() -> None:
    previous = _job(
        status="completed",
        started_at=datetime(2026, 8, 30, 7, 0, tzinfo=UTC),
        finished_at=datetime(2026, 8, 30, 7, 5, tzinfo=UTC),
    )
    failed = _job(
        status="failed",
        started_at=datetime(2026, 8, 31, 7, 25, tzinfo=UTC),
        finished_at=datetime(2026, 8, 31, 7, 26, tzinfo=UTC),
    )

    payload = resolve_inaz_sync_status([previous, failed])

    assert payload["status"] == "degraded"
    assert payload["last_attempt_at"] == "2026-08-31T07:25:00Z"
    assert payload["last_success_at"] == "2026-08-30T07:05:00Z"
    assert payload["data_updated_at"] == "2026-08-30T07:05:00Z"
    assert payload["error_code"] == "inaz_sync_failed"
    assert "credential" not in payload["error_message"].lower()


def test_resolve_inaz_sync_status_reports_error_without_previous_success() -> None:
    payload = resolve_inaz_sync_status([_job(status="cancelled")])

    assert payload["status"] == "error"
    assert payload["last_success_at"] is None
    assert payload["error_code"] == "inaz_sync_failed"


def test_resolve_inaz_sync_status_reports_running() -> None:
    running = _job(status="running", finished_at=None)

    payload = resolve_inaz_sync_status([running])

    assert payload["status"] == "running"
    assert payload["last_attempt_at"] == "2026-08-31T07:25:00Z"
    assert payload["last_success_at"] is None
    assert payload["error_code"] is None


@pytest.mark.parametrize(
    ("finished_at", "records_errors", "failed_collaborators"),
    [
        (None, 0, 0),
        ("not-a-timestamp", 0, 0),
        (datetime(2026, 8, 31, 7, 26, tzinfo=UTC), "invalid", 0),
        (datetime(2026, 8, 31, 7, 26, tzinfo=UTC), 0, "invalid"),
        (datetime(2026, 8, 31, 7, 26, tzinfo=UTC), -1, 0),
    ],
)
def test_resolve_inaz_sync_status_degrades_invalid_or_incomplete_metadata(
    finished_at: object,
    records_errors: object,
    failed_collaborators: object,
) -> None:
    payload = resolve_inaz_sync_status(
        [
            _job(
                status="completed",
                finished_at=finished_at,
                records_errors=records_errors,
                failed_collaborators=failed_collaborators,
            )
        ]
    )

    assert payload["status"] == "degraded"
    assert payload["last_success_at"] is None
    assert payload["error_code"] == "inaz_sync_partial"


def test_resolve_inaz_sync_status_uses_preserved_retry_attempt_timestamp() -> None:
    retried = _job(
        status="pending",
        started_at=None,
        finished_at=None,
        params={
            "auto_retry_history": [
                {"previous_started_at": "invalid"},
                {"previous_started_at": datetime(2026, 8, 31, 7, 25, tzinfo=UTC)},
            ]
        },
    )

    payload = resolve_inaz_sync_status([retried])

    assert payload["status"] == "error"
    assert payload["last_attempt_at"] == "2026-08-31T07:25:00Z"
    assert payload["error_code"] == "inaz_sync_metadata_invalid"


def test_resolve_inaz_sync_status_ignores_unusable_retry_history() -> None:
    retried = _job(
        status="pending",
        started_at=None,
        finished_at=None,
        params={"auto_retry_history": ["invalid", {"previous_started_at": "invalid"}]},
    )

    assert resolve_inaz_sync_status([retried])["status"] == "never"


def test_failed_employee_retry_uses_parent_attempt_cohort() -> None:
    parent = _job(status="completed")
    retry = _job(
        status="failed",
        started_at=datetime(2026, 8, 31, 7, 26, tzinfo=UTC),
        params={"parent_sync_job_id": str(parent.id)},
    )

    payload = resolve_inaz_sync_status([parent, retry])

    assert payload["status"] == "error"
    assert payload["last_success_at"] is None


def test_resolve_inaz_sync_status_requires_all_parallel_shards_to_succeed() -> None:
    group = "sync-group"
    first = _job(status="completed", params={"sync_group_id": group})
    second = _job(
        status="failed",
        started_at=datetime(2026, 8, 31, 7, 25, 1, tzinfo=UTC),
        params={"sync_group_id": group},
    )

    payload = resolve_inaz_sync_status([first, second])

    assert payload["status"] == "error"
    assert payload["last_success_at"] is None


def test_build_inaz_sync_status_queries_persisted_jobs() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine, tables=[PresenzeSyncJob.__table__])
    db = sessionmaker(bind=engine)()
    try:
        db.add(
            PresenzeSyncJob(
                status="completed",
                requested_by_user_id=1,
                credential_id=1,
                period_start=date(2026, 8, 1),
                period_end=date(2026, 8, 31),
                records_errors=0,
                params_json={"progress": {"failed_collaborators": 0}},
                started_at=datetime(2026, 8, 31, 7, 25, tzinfo=UTC),
                finished_at=datetime(2026, 8, 31, 7, 25, 12, tzinfo=UTC),
            )
        )
        db.commit()

        payload = build_inaz_sync_status(db, month="2026-08")

        assert payload["status"] == "success"
        assert payload["data_updated_at"] == "2026-08-31T07:25:12Z"

        metadata = build_presenze_snapshot_metadata(
            db,
            rules_version="2026.08",
            export_rules_version="export-1",
            month="2026-08",
            now=datetime(2026, 8, 31, 7, 30, tzinfo=UTC),
        )
        assert metadata["synced_from_gaia_at"] == "2026-08-31T07:30:00Z"
        assert metadata["inaz_sync"]["status"] == "success"
        assert metadata["month"] == "2026-08"
        assert metadata["export_rules_version"] == "export-1"
    finally:
        db.close()


def test_snapshot_metadata_omits_optional_contract_fields() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine, tables=[PresenzeSyncJob.__table__])
    db = sessionmaker(bind=engine)()
    try:
        metadata = build_presenze_snapshot_metadata(
            db, rules_version="2026.08", now=None
        )

        assert metadata["source"] == "gaia"
        assert metadata["inaz_sync"]["status"] == "never"
        assert "month" not in metadata
        assert "export_rules_version" not in metadata
    finally:
        db.close()


def test_build_auto_retry_history_entry_preserves_attempt_metadata() -> None:
    job = _job(status="failed")
    job.attempt_count = 2
    job.error_detail = "internal detail"

    entry = build_auto_retry_history_entry(
        job, queued_at=datetime(2026, 8, 31, 8, 0, tzinfo=UTC)
    )

    assert entry == {
        "queued_at": "2026-08-31T08:00:00Z",
        "attempt_count": 2,
        "previous_status": "failed",
        "previous_started_at": "2026-08-31T07:25:00Z",
        "previous_finished_at": "2026-08-31T07:25:12Z",
        "previous_error": "internal detail",
    }


def test_payload_rejects_unsupported_status() -> None:
    with pytest.raises(ValueError, match="Unsupported INAZ sync status"):
        _payload(status="pending")


def test_parse_datetime_rejects_absent_and_invalid_values() -> None:
    assert _parse_datetime(None) is None
    assert _parse_datetime("not-a-timestamp") is None


def test_month_filter_accepts_year_boundary_period() -> None:
    spanning = _job(
        status="completed",
        period_start=date(2026, 12, 1),
        period_end=date(2027, 1, 31),
    )

    assert resolve_inaz_sync_status([spanning], month="2026-12")["status"] == "success"
    assert resolve_inaz_sync_status([spanning], month="2027-01")["status"] == "success"


def test_latest_attempt_is_selected_by_timestamp_not_input_order() -> None:
    later = _job(
        status="running",
        started_at=datetime(2026, 8, 31, 8, 0, tzinfo=UTC),
        finished_at=None,
    )
    earlier = _job(status="failed", started_at=datetime(2026, 8, 31, 7, 0, tzinfo=UTC))

    payload = resolve_inaz_sync_status([later, earlier])

    assert payload["status"] == "running"
    assert payload["last_attempt_at"] == "2026-08-31T08:00:00Z"
