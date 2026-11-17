"""Characterize grouped firewall log counts, timestamps, examples and query boundaries."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.network.router.helpers import firewalls


@pytest.fixture
def summary_runner(monkeypatch):
    anchor = datetime.now(UTC)
    trace = []
    queries = []

    class Clock:
        @staticmethod
        def now(zone):
            assert zone is UTC
            trace.append("clock")
            return anchor + timedelta(seconds=trace.count("clock") - 1)

    monkeypatch.setattr(firewalls, "datetime", Clock)

    def run(rows, *, window_hours=24):
        def mappings():
            trace.append("mappings")
            for row in rows:
                trace.append(("row", row["event_type"]))
                yield row
            trace.append("exhausted")

        def execute(query):
            queries.append(query)
            trace.append("execute")
            return SimpleNamespace(mappings=mappings)

        result = firewalls._build_firewall_log_coverage_summary(
            SimpleNamespace(execute=execute),
            firewall=SimpleNamespace(id=19),
            window_hours=window_hours,
        )
        return result

    return SimpleNamespace(run=run, anchor=anchor, trace=trace, queries=queries)


def row(event_type, count, observed_at):
    return {"event_type": event_type, "events_count": count, "last_observed_at": observed_at}


def test_empty_summary_keeps_expected_order_and_streaming_query(summary_runner):
    result = summary_runner.run([], window_hours=7)
    assert result.firewall_id == 19
    assert result.window_hours == 7
    assert result.generated_at == summary_runner.anchor + timedelta(seconds=1)
    assert result.total_events == 0
    assert result.additional_families == []
    assert result.top_event_types == []
    assert result.missing_expected_families == [
        "firewall",
        "vpn",
        "ips",
        "authentication",
        "system",
    ]
    assert [item.label for item in result.expected_families] == [
        "Firewall",
        "VPN",
        "IPS",
        "Authentication",
        "System",
    ]
    assert all(
        item.expected
        and item.status == "missing"
        and item.observed_count == 0
        and item.last_observed_at is None
        and item.examples == []
        for item in result.expected_families
    )
    assert summary_runner.trace == ["clock", "execute", "mappings", "exhausted", "clock"]
    query = summary_runner.queries[0]
    assert dict(query.get_execution_options()) == {"stream_results": True, "yield_per": 1000}
    compiled = query.compile(dialect=postgresql.dialect())
    assert compiled.params == {
        "firewall_id_1": 19,
        "observed_at_1": summary_runner.anchor - timedelta(hours=7),
    }
    sql = str(compiled)
    assert "GROUP BY network_firewall_events.event_type" in sql
    assert "count(network_firewall_events.id)" in sql
    assert "max(network_firewall_events.observed_at)" in sql
    assert "raw_payload" not in sql


@pytest.mark.parametrize("count", [None, "", 0, "0", -2, "-2", "3", 3.9])
def test_count_conversion_preserves_zero_negative_and_numeric_values(summary_runner, count):
    result = summary_runner.run([row("firewall.rule", count, summary_runner.anchor)])
    expected = int(count or 0)
    assert result.total_events == expected
    assert result.expected_families[0].observed_count == expected
    assert result.expected_families[0].status == ("ok" if expected > 0 else "missing")
    assert result.expected_families[0].last_observed_at == summary_runner.anchor
    assert result.expected_families[0].examples == ["firewall.rule"]
    assert result.top_event_types[0].count == expected


def test_latest_timestamp_and_first_three_distinct_examples_follow_input_order(summary_runner):
    now = summary_runner.anchor
    rows = [
        row("custom.first", 2, now),
        row("custom.first", 3, now - timedelta(hours=1)),
        row("custom.second", 4, now + timedelta(hours=2)),
        row("custom.third", 5, now + timedelta(hours=2)),
        row("custom.fourth", 6, now + timedelta(hours=1)),
        row("custom.fourth", 7, now + timedelta(hours=3)),
        row("firewall.rule", 1, now),
        row("firewall.rule", 8, now - timedelta(hours=1)),
    ]
    result = summary_runner.run(rows)
    assert result.total_events == 36
    custom = result.additional_families[0]
    assert custom.model_dump() == {
        "family_key": "custom",
        "label": "Custom",
        "expected": False,
        "observed_count": 27,
        "last_observed_at": now + timedelta(hours=3),
        "status": "observed",
        "examples": ["custom.first", "custom.second", "custom.third"],
    }
    assert result.expected_families[0].observed_count == 9
    assert result.expected_families[0].last_observed_at == now
    assert result.missing_expected_families == ["vpn", "ips", "authentication", "system"]
    assert [(item.key, item.count) for item in result.top_event_types] == [
        ("custom.fourth", 13),
        ("firewall.rule", 9),
        ("custom.first", 5),
        ("custom.third", 5),
        ("custom.second", 4),
    ]
    assert summary_runner.trace == [
        "clock",
        "execute",
        "mappings",
        *[("row", item["event_type"]) for item in rows],
        "exhausted",
        "clock",
    ]


def test_additional_ties_are_stable_and_top_event_types_are_limited_to_six(summary_runner):
    kinds = ["zeta.a", "alpha.a", "beta.a", "gamma.a", "delta.a", "epsilon.a", "theta.a"]
    result = summary_runner.run([row(kind, 2, summary_runner.anchor) for kind in kinds])
    assert [item.family_key for item in result.additional_families] == [
        kind.split(".")[0] for kind in kinds
    ]
    assert [item.key for item in result.top_event_types] == kinds[:6]
    assert [item.label for item in result.top_event_types] == kinds[:6]
    assert result.total_events == 14


def test_expected_and_additional_families_use_their_distinct_orders(summary_runner):
    kinds = [
        ("content_filtering.web", 0),
        ("anti-virus.scan", 8),
        ("custom.a", 10),
        ("system_health.cpu", 2),
        ("user.auth", 3),
        ("network.ips", 4),
        ("remote.vpn", 5),
        ("firewall.rule", 1),
    ]
    result = summary_runner.run([row(kind, count, summary_runner.anchor) for kind, count in kinds])
    assert [item.family_key for item in result.expected_families] == [
        "firewall",
        "vpn",
        "ips",
        "authentication",
        "system",
    ]
    assert result.missing_expected_families == []
    assert [item.family_key for item in result.additional_families] == [
        "custom",
        "anti-virus",
        "content_filtering",
    ]
    assert result.additional_families[-1].label == "Content Filtering"
    assert result.additional_families[-1].status == "observed"
    assert result.additional_families[-1].observed_count == 0


@pytest.mark.parametrize(
    "count, error", [("bad", ValueError), ([1], TypeError), ({"x": 1}, TypeError)]
)
def test_invalid_counts_fail_before_the_second_clock_read(summary_runner, count, error):
    with pytest.raises(error):
        summary_runner.run([row("custom.a", count, summary_runner.anchor)])
    assert summary_runner.trace == ["clock", "execute", "mappings", ("row", "custom.a")]


def test_naive_aware_timestamp_comparison_error_is_not_hidden(summary_runner):
    with pytest.raises(TypeError, match="offset-naive and offset-aware"):
        summary_runner.run(
            [
                row("custom.a", 1, summary_runner.anchor),
                row("custom.b", 1, summary_runner.anchor.replace(tzinfo=None)),
            ]
        )
    assert summary_runner.trace.count("clock") == 1
