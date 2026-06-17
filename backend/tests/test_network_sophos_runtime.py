from datetime import datetime

from app.modules.network.models import NetworkSophosConfig
from app.modules.network.sophos_runtime import build_sophos_runtime_policy


def test_sophos_runtime_policy_handles_overnight_window() -> None:
    config = NetworkSophosConfig(
        id=1,
        syslog_enabled=True,
        snmp_enabled=True,
        operation_window_enabled=True,
        operation_start_hour=19,
        operation_end_hour=4,
        operation_timezone="Europe/Rome",
    )

    policy_inside_evening = build_sophos_runtime_policy(config, now=datetime.fromisoformat("2026-06-17T18:30:00+00:00"))
    policy_inside_night = build_sophos_runtime_policy(config, now=datetime.fromisoformat("2026-06-17T01:30:00+00:00"))
    policy_outside = build_sophos_runtime_policy(config, now=datetime.fromisoformat("2026-06-17T10:00:00+00:00"))

    assert policy_inside_evening.is_within_window is True
    assert policy_inside_evening.syslog_should_ingest is True
    assert policy_inside_night.is_within_window is True
    assert policy_inside_night.snmp_should_poll is True
    assert policy_outside.is_within_window is False
    assert policy_outside.syslog_should_ingest is False
    assert policy_outside.snmp_should_poll is False
