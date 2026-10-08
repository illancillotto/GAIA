from collections.abc import Iterator
from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.datetime_compat import UTC
from app.modules.wiki.models import (
    WikiConversation,
    WikiConversationDailyMetric,
    WikiConversationEvent,
    WikiConversationGovernanceConfig,
    WikiToolAuditLog,
)
from app.modules.wiki.services import conversation_metrics as metrics


@pytest.fixture
def metrics_db() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            WikiConversation.__table__,
            WikiConversationDailyMetric.__table__,
            WikiConversationEvent.__table__,
            WikiConversationGovernanceConfig.__table__,
            WikiToolAuditLog.__table__,
        ],
    )
    with Session(engine) as session:
        session.add(
            WikiConversationGovernanceConfig(
                id=1,
                fallback_heavy_threshold=2,
                no_match_repeated_threshold=2,
                high_latency_ms_threshold=1000,
            )
        )
        session.commit()
        yield session
    engine.dispose()


def _conversation(created_at: datetime, **values: object) -> WikiConversation:
    return WikiConversation(
        id=uuid4(),
        title="Campaign characterization",
        created_by="campaign",
        created_at=created_at,
        status=values.pop("status", "open"),
        priority=values.pop("priority", "medium"),
        **values,
    )


def _event(
    conversation: WikiConversation,
    created_at: datetime,
    **values: object,
) -> WikiConversationEvent:
    return WikiConversationEvent(
        id=uuid4(),
        conversation_id=conversation.id,
        created_at=created_at,
        event_type=values.pop("event_type", "status_changed"),
        **values,
    )


def _global_rows(db: Session) -> list[WikiConversationDailyMetric]:
    return list(
        db.scalars(
            select(WikiConversationDailyMetric)
            .where(WikiConversationDailyMetric.dimension_type == "global")
            .order_by(WikiConversationDailyMetric.metric_date)
        )
    )


def test_refresh_characterizes_event_timing_counts_and_all_dimensions(metrics_db: Session) -> None:
    day = date.today() - timedelta(days=1)
    day_start = datetime.combine(day, time.min)
    created = day_start - timedelta(hours=4)
    conversation = _conversation(
        created,
        status="resolved",
        priority="high",
        assigned_to="reviewer",
        review_reason="manual_flag",
        resolved_at=day_start + timedelta(hours=8),
        last_reviewed_at=day_start + timedelta(hours=6),
    )
    metrics_db.add(conversation)
    metrics_db.add_all(
        [
            _event(conversation, day_start - timedelta(hours=2), to_status="in_review"),
            _event(
                conversation,
                day_start - timedelta(hours=1),
                event_type="assignment_changed",
            ),
            _event(conversation, day_start + timedelta(hours=1), to_status="in_review"),
            _event(conversation, day_start + timedelta(hours=2), to_status="waiting_user"),
            _event(
                conversation,
                day_start + timedelta(hours=5),
                from_status="waiting_user",
                to_status="in_review",
            ),
            _event(conversation, day_start + timedelta(hours=8), to_status="resolved"),
            _event(
                conversation,
                day_start + timedelta(hours=9),
                from_status="resolved",
                to_status="open",
            ),
            _event(
                conversation,
                day_start + timedelta(hours=10),
                event_type="assignment_changed",
            ),
            _event(
                conversation,
                day_start + timedelta(hours=11),
                event_type="message_sent",
                from_status="waiting_user",
                to_status="in_review",
            ),
            _event(conversation, day_start + timedelta(days=1), to_status="in_review"),
        ]
    )
    metrics_db.commit()

    metrics.refresh_wiki_conversation_daily_metrics(metrics_db, start_date=day, end_date=day)

    rows = list(metrics_db.scalars(select(WikiConversationDailyMetric)))
    assert {(row.dimension_type, row.dimension_key) for row in rows} == {
        ("global", None),
        ("status", "resolved"),
        ("priority", "high"),
        ("assigned_to", "reviewer"),
        ("review_reason", "n/d"),
    }
    for row in rows:
        assert row.created_count == 0
        assert row.closed_count == 1
        assert row.resolved_count == 1
        assert row.high_priority_count == 1
        assert row.review_entered_count == 2
        assert row.reopened_count == 1
        assert row.reassigned_count == 1
        assert row.avg_time_to_review_hours == 10
        assert row.avg_time_to_resolve_hours == 12
        assert row.avg_open_to_review_hours == 2
        assert row.avg_review_to_resolve_hours == 3
        assert row.avg_waiting_user_hours == 3


def test_refresh_boundary_snapshot_and_idempotent_replacement(metrics_db: Session) -> None:
    day = date.today() - timedelta(days=1)
    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time.max)
    metrics_db.add_all(
        [
            _conversation(start),
            _conversation(end, status="waiting_user"),
            _conversation(start + timedelta(days=1)),
            _conversation(start - timedelta(days=1), resolved_at=start, status="open"),
            _conversation(start - timedelta(days=1), resolved_at=start, status="resolved"),
        ]
    )
    metrics_db.add(
        WikiConversationDailyMetric(
            metric_date=day - timedelta(days=1), dimension_type="global", created_count=99
        )
    )
    metrics_db.commit()

    for _iteration in range(2):
        metrics.refresh_wiki_conversation_daily_metrics(metrics_db, start_date=day, end_date=day)
        rows = _global_rows(metrics_db)
        assert len(rows) == 2
        assert rows[0].created_count == 99
        assert rows[1].created_count == 2
        assert rows[1].closed_count == 2
        assert rows[1].open_count == 1
        assert rows[1].waiting_user_count == 1
        assert rows[1].resolved_count == 1


@pytest.mark.parametrize("granularity", ["week", "month"])
def test_period_series_preserves_latest_snapshot_and_nonzero_sample_averages(
    metrics_db: Session, monkeypatch: pytest.MonkeyPatch, granularity: str
) -> None:
    monkeypatch.setattr(
        metrics, "refresh_recent_wiki_conversation_daily_metrics", lambda *_a, **_k: None
    )
    today = date.today()
    period_start = (
        metrics._start_of_week(today) if granularity == "week" else metrics._start_of_month(today)
    )
    earlier = period_start - timedelta(days=1)
    metrics_db.add_all(
        [
            WikiConversationDailyMetric(
                metric_date=earlier,
                dimension_type="global",
                created_count=2,
                closed_count=1,
                open_count=5,
                review_entered_count=3,
                reassigned_count=2,
                reopened_count=1,
                avg_time_to_review_hours=2,
                avg_time_to_resolve_hours=4,
                avg_open_to_review_hours=6,
                avg_review_to_resolve_hours=8,
                avg_waiting_user_hours=10,
            ),
            WikiConversationDailyMetric(
                metric_date=period_start,
                dimension_type="global",
                created_count=7,
                open_count=3,
            ),
        ]
    )
    metrics_db.commit()
    points = metrics.get_wiki_conversation_metrics_series(
        metrics_db, days=40, granularity=granularity
    )
    assert len(points) == 2
    assert points[0].created_count == 2
    assert points[0].open_count == 5
    assert points[0].avg_time_to_review_hours == 2
    assert points[0].avg_time_to_resolve_hours == 4
    assert points[0].avg_open_to_review_hours == 6
    assert points[0].avg_review_to_resolve_hours == 8
    assert points[0].avg_waiting_user_hours == 10
    assert points[1].created_count == 7
    assert points[1].open_count == 3
    assert points[1].avg_time_to_review_hours == 0
    assert points[1].avg_time_to_resolve_hours == 0
    assert points[1].avg_open_to_review_hours == 0
    assert points[1].avg_review_to_resolve_hours == 0
    assert points[1].avg_waiting_user_hours == 0
    assert points[1].period_label == metrics._period_label(granularity, period_start)


def test_empty_summary_and_series_do_not_invent_threads(metrics_db: Session) -> None:
    summary = metrics.get_wiki_conversation_metrics_summary(metrics_db, days=0)
    assert summary.total_threads == summary.created_count == summary.closed_count == 0
    assert summary.open_count == summary.resolved_count == 0
    assert summary.top_statuses == summary.top_event_types == []
    assert metrics.get_wiki_conversation_metrics_series(metrics_db, days=0) == []
    assert metrics.get_wiki_conversation_metrics_series(metrics_db, granularity="week") == []


def test_summary_counts_audited_threads_not_audit_rows(metrics_db: Session) -> None:
    today = date.today()
    now = datetime.combine(today, time(1))
    conversation = _conversation(now, priority="high")
    metrics_db.add(conversation)
    metrics_db.add_all(
        [
            WikiToolAuditLog(
                id=uuid4(),
                conversation_id=conversation.id,
                username="campaign",
                role="admin",
                intent="live_data",
                mode="hybrid",
                tool_name="test_lookup",
                question_hash=f"audit-{index}",
                question_preview="metrics test",
                success=0,
                found=0,
                fallback_reason="tool_denied",
                created_at=now,
            )
            for index in range(2)
        ]
    )
    metrics_db.add(_event(conversation, now, event_type="assignment_changed"))
    governance = metrics_db.get(WikiConversationGovernanceConfig, 1)
    governance.data_complete_from = today
    metrics_db.commit()

    summary = metrics.get_wiki_conversation_metrics_summary(metrics_db, days=1)
    assert summary.total_threads == 1
    assert summary.needs_review_count == 1
    assert summary.high_priority_count == 1
    assert summary.data_complete_from == today.isoformat()
    assert [(item.key, item.count) for item in summary.top_statuses] == [("open", 1)]
    assert [(item.key, item.count) for item in summary.top_priorities] == [("high", 1)]
    assert [(item.key, item.count) for item in summary.top_owners] == [("unassigned", 1)]
    assert [(item.key, item.count) for item in summary.top_review_reasons] == [
        ("denied_present", 1)
    ]
    assert [(item.key, item.count) for item in summary.top_event_types] == [
        ("assignment_changed", 1)
    ]
    point = metrics.get_wiki_conversation_metrics_series(metrics_db, days=1)[0]
    assert point.denied_threads_count == 1
    assert point.fallback_threads_count == 1
    assert point.no_match_threads_count == 1
    assert point.reassigned_count == 1


def test_helpers_normalize_timezone_and_preserve_rounding() -> None:
    assert metrics._to_utc(None) is None
    naive = datetime.combine(date.today(), time(12))
    aware = naive.replace(tzinfo=timezone(timedelta(hours=2)))
    assert metrics._to_utc(aware) == naive.replace(hour=10, tzinfo=UTC)
    assert metrics._to_utc(naive) == naive.replace(tzinfo=UTC)
    assert metrics._hours_between(None, naive) == 0
    assert metrics._hours_between(naive, None) == 0
    assert metrics._hours_between(naive, naive - timedelta(hours=1)) == 0
    assert metrics._hours_between(naive, naive + timedelta(hours=2, minutes=30)) == 2
    assert metrics._average_hours([]) == 0
    assert metrics._average_hours([2, 3]) == 2
    assert metrics._period_label("day", date.today()) == date.today().isoformat()
    with pytest.raises(ValueError, match="Unsupported dimension type"):
        metrics._dimension_key(_conversation(naive), None, "unsupported")


@pytest.mark.parametrize("dimension", ["status", "priority", "assigned_to", "review_reason"])
def test_dimension_rankings_preserve_snapshot_sum_review_counts_and_tie_order(
    metrics_db: Session, dimension: str
) -> None:
    today = date.today()
    for key in ["z", "a"]:
        metrics_db.add(
            WikiConversationDailyMetric(
                metric_date=today,
                dimension_type=dimension,
                dimension_key=key,
                open_count=1,
                in_review_count=2,
                waiting_user_count=3,
                resolved_count=4,
                closed_count=99,
                needs_review_count=7,
            )
        )
    metrics_db.commit()
    ranked = metrics._latest_dimension_counts(
        metrics_db, dimension_type=dimension, metric_date=today
    )
    expected_count = 7 if dimension == "review_reason" else 10
    assert [(item.key, item.count) for item in ranked] == [
        ("a", expected_count),
        ("z", expected_count),
    ]


def test_hours_fail_closed_if_normalizer_cannot_produce_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(metrics, "_to_utc", lambda _value: None)
    now = datetime.now(UTC)
    assert metrics._hours_between(now, now) == 0


def test_postgresql_advisory_lock_uses_transaction_scoped_key() -> None:
    db = Mock(spec=Session)
    db.get_bind.return_value.dialect.name = "postgresql"
    metrics._acquire_metrics_refresh_lock(db)
    statement = db.execute.call_args.args[0]
    assert "pg_advisory_xact_lock" in str(statement)
    assert (
        metrics._WIKI_CONVERSATION_METRICS_ADVISORY_LOCK_KEY in statement.compile().params.values()
    )


def test_refresh_commit_failure_requires_caller_rollback(
    metrics_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    today = date.today()
    metrics_db.add(_conversation(datetime.combine(today, time(1))))
    metrics_db.add(
        WikiConversationDailyMetric(metric_date=today, dimension_type="global", created_count=99)
    )
    metrics_db.commit()
    commit = Mock(side_effect=RuntimeError("commit failed"))
    monkeypatch.setattr(metrics_db, "commit", commit)
    with pytest.raises(RuntimeError, match="commit failed"):
        metrics.refresh_wiki_conversation_daily_metrics(
            metrics_db, start_date=today, end_date=today
        )
    commit.assert_called_once_with()
    metrics_db.rollback()
    assert _global_rows(metrics_db)[0].created_count == 99


def test_nullable_source_timestamps_are_skipped_and_future_events_stop_the_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today = date.today()
    start = datetime.combine(today, time.min, UTC)
    conversation = _conversation(start, status="open")
    absent_created = _conversation(start)
    absent_created.created_at = None
    db = Mock(spec=Session)
    db.get_bind.return_value.dialect.name = "sqlite"
    db.scalars.return_value.all.return_value = [absent_created, conversation]
    db.execute.return_value.all.return_value = [
        SimpleNamespace(
            conversation_id=conversation.id, event_type="status_changed", created_at=None
        ),
        SimpleNamespace(
            conversation_id=conversation.id,
            event_type="status_changed",
            created_at=start + timedelta(days=1),
        ),
    ]
    monkeypatch.setattr(
        metrics,
        "_build_conversation_audit_stats",
        lambda _db: SimpleNamespace(denied_count={}, fallback_count={}, no_match_count={}),
    )
    monkeypatch.setattr(
        metrics,
        "get_or_create_wiki_conversation_governance_config",
        lambda _db: SimpleNamespace(
            fallback_heavy_threshold=2,
            no_match_repeated_threshold=2,
            high_latency_ms_threshold=1000,
        ),
    )
    monkeypatch.setattr(metrics, "_derive_review_reason_with_config", lambda *_a, **_k: None)
    monkeypatch.setattr(metrics, "_needs_review_with_config", lambda *_a, **_k: False)
    metrics.refresh_wiki_conversation_daily_metrics(db, start_date=today, end_date=today)
    rows = [call.args[0] for call in db.add.call_args_list]
    assert len(rows) == 5
    assert all(row.created_count == 1 and row.review_entered_count == 0 for row in rows)
    db.commit.assert_called_once_with()
