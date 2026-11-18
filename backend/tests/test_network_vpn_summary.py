"""VPN bypass summary preserves subject counts, queries and failure order."""

from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.network.router.routes import tracking as routes


def activity(**changes):
    return SimpleNamespace(
        **{
            "suspicious_events": 0,
            "vpn_suspected_events": 0,
            "proxy_suspected_events": 0,
            "tor_suspected_events": 0,
            "encrypted_dns_events": 0,
            **changes,
        }
    )


@pytest.fixture
def summary_case(monkeypatch):
    def prepare(subjects=(), scalars=(0, 0, 0, 0, 0, 0), *, fail=None):
        trace = []
        queries = []
        user = object()

        def record(name, *args):
            trace.append((name, *args))
            if name == fail:
                raise RuntimeError(f"failed {name}")

        def scalar(query):
            compiled = query.compile(dialect=postgresql.dialect())
            queries.append((str(compiled), compiled.params))
            record(f"query{len(queries)}")
            return scalars[len(queries) - 1]

        db = SimpleNamespace(scalar=scalar)

        def authorize(current):
            assert current is user
            record("auth")

        def seed(session):
            assert session is db
            record("seed")

        def get_subjects(**kwargs):
            record("subjects", kwargs)
            return subjects

        monkeypatch.setattr(routes, "_require_network_module", authorize)
        monkeypatch.setattr(routes, "_ensure_detection_watchlist_seeded", seed)
        monkeypatch.setattr(routes, "get_tracked_subjects", get_subjects)
        return SimpleNamespace(
            call=lambda: routes.get_vpn_bypass_summary(user, db, window_hours=24),
            trace=trace,
            queries=queries,
            user=user,
            db=db,
        )

    return prepare


def test_categories_count_subjects_independently_and_sum_only_positive_suspicious_events(
    summary_case,
):
    case = summary_case(
        [
            SimpleNamespace(activity_summary=activity(suspicious_events=4, vpn_suspected_events=9)),
            SimpleNamespace(
                activity_summary=activity(
                    suspicious_events=2, proxy_suspected_events=3, tor_suspected_events=1
                )
            ),
            SimpleNamespace(
                activity_summary=activity(
                    suspicious_events=-1, encrypted_dns_events=8, vpn_suspected_events=1
                )
            ),
            SimpleNamespace(activity_summary=activity(proxy_suspected_events=-2)),
            SimpleNamespace(activity_summary=None),
        ]
    )
    assert case.call().model_dump() == {
        "total_subjects": 2,
        "vpn_subjects": 2,
        "proxy_subjects": 1,
        "tor_subjects": 1,
        "encrypted_dns_subjects": 1,
        "total_suspicious_events": 6,
        "open_alerts": 0,
        "transient_device_alerts": 0,
        "arp_ephemeral_alerts": 0,
        "arp_identity_alerts": 0,
        "arp_spoofing_alerts": 0,
        "watchlist_rules": 0,
    }
    assert case.trace[2] == (
        "subjects",
        {
            "current_user": case.user,
            "db": case.db,
            "include_inactive": False,
            "include_inferred": True,
            "window_hours": 24,
            "search": None,
            "entity_type": None,
        },
    )


def test_six_ordered_queries_preserve_open_status_type_predicates_and_watchlist_count(summary_case):
    case = summary_case(scalars=(11, 12, 13, 14, 15, 16))
    result = case.call()
    assert (
        result.open_alerts,
        result.transient_device_alerts,
        result.arp_ephemeral_alerts,
        result.arp_identity_alerts,
        result.arp_spoofing_alerts,
        result.watchlist_rules,
    ) == (11, 12, 13, 14, 15, 16)
    types = [
        "VPN_BYPASS_SUSPECTED",
        "VPN_BYPASS_TRANSIENT_DEVICE",
        "ARP_EPHEMERAL_DEVICE",
        "ARP_MAC_CHANGE_SUSPECTED",
        "ARP_IP_ROTATION_SUSPECTED",
    ]
    assert case.queries[0][1] == {"status_1": "open", "alert_type_1": types}
    assert "network_alerts.alert_type IN" in case.queries[0][0]
    for query, kind in zip(case.queries[1:5], types[1:], strict=True):
        assert query[1] == {"status_1": "open", "alert_type_1": kind}
        assert "network_alerts.alert_type =" in query[0]
        assert "network_alerts.status =" in query[0]
    assert "FROM network_detection_watchlist" in case.queries[5][0]
    assert "WHERE" not in case.queries[5][0]
    assert case.queries[5][1] == {}
    assert [entry[0] for entry in case.trace] == [
        "auth",
        "seed",
        "subjects",
        "query1",
        "query2",
        "query3",
        "query4",
        "query5",
        "query6",
    ]


@pytest.mark.parametrize("value,expected", [(None, 0), (False, 0), (0, 0), (7, 7), (-1, -1)])
def test_scalar_falsey_fallback_and_truthy_values_are_preserved(summary_case, value, expected):
    case = summary_case(scalars=(value,) * 6)
    result = case.call()
    assert (
        result.open_alerts,
        result.transient_device_alerts,
        result.arp_ephemeral_alerts,
        result.arp_identity_alerts,
        result.arp_spoofing_alerts,
        result.watchlist_rules,
    ) == (expected,) * 6


def test_suspicious_guard_and_total_read_the_activity_separately(summary_case):
    reads = []

    class ChangingActivity:
        vpn_suspected_events = proxy_suspected_events = tor_suspected_events = (
            encrypted_dns_events
        ) = 0

        @property
        def suspicious_events(self):
            reads.append("suspicious")
            return 1 if len(reads) == 1 else 9

    result = summary_case([SimpleNamespace(activity_summary=ChangingActivity())]).call()
    assert reads == ["suspicious", "suspicious"]
    assert (result.total_subjects, result.total_suspicious_events) == (1, 9)


def test_absent_and_falsey_activity_use_window_default_before_queries(summary_case, monkeypatch):
    reads = []

    class FalseyActivity:
        def __bool__(self):
            reads.append("bool")
            return False

        def __getattr__(self, key):
            raise AssertionError(f"falsey activity read {key}")

    def default(**kwargs):
        reads.append(kwargs)
        return activity()

    monkeypatch.setattr(routes, "NetworkTrackedSubjectActivitySummary", default)
    result = summary_case(
        [SimpleNamespace(activity_summary=None), SimpleNamespace(activity_summary=FalseyActivity())]
    ).call()
    assert reads == [{"window_hours": 24}, "bool", {"window_hours": 24}]
    assert result.total_subjects == result.total_suspicious_events == 0


@pytest.mark.parametrize(
    "fail", ["auth", "seed", "subjects", "query1", "query2", "query3", "query4", "query5", "query6"]
)
def test_failures_stop_without_later_queries_or_implicit_retry(summary_case, fail):
    case = summary_case(fail=fail)
    with pytest.raises(RuntimeError, match=f"failed {fail}"):
        case.call()
    stages = [
        "auth",
        "seed",
        "subjects",
        "query1",
        "query2",
        "query3",
        "query4",
        "query5",
        "query6",
    ]
    assert [entry[0] for entry in case.trace] == stages[: stages.index(fail) + 1]


def test_activity_failure_precedes_all_queries(summary_case):
    class Subject:
        @property
        def activity_summary(self):
            raise ValueError("activity unavailable")

    case = summary_case([Subject()])
    with pytest.raises(ValueError, match="activity unavailable"):
        case.call()
    assert case.queries == []


def test_response_is_constructed_only_after_all_queries(summary_case, monkeypatch):
    case = summary_case()

    def response(**_kwargs):
        assert len(case.queries) == 6
        raise RuntimeError("response failed")

    monkeypatch.setattr(routes, "NetworkVpnBypassSummary", response)
    with pytest.raises(RuntimeError, match="response failed"):
        case.call()
