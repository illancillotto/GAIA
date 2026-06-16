from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.network.models import NetworkDevice, NetworkFirewall, NetworkFirewallEvent, NetworkTrackedSubject
from app.modules.network.telemetry_rollups import (
    build_network_statistics_summary_from_rollups,
    refresh_network_firewall_hourly_rollups,
    refresh_network_firewall_hourly_rollups_for_range,
)


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_network_rollups_refresh_and_summary_build() -> None:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="operatore.ced",
        email="operatore.ced@example.local",
        full_name="Operatore CED",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.VIEWER.value,
        is_active=True,
        module_rete=True,
    )
    db.add(user)
    db.flush()

    device = NetworkDevice(
        assigned_user_id=user.id,
        ip_address="192.168.1.10",
        hostname="pc-ced",
        display_name="PC CED",
        lifecycle_state="active",
        is_known_device=True,
        status="online",
        is_monitored=True,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db.add(device)
    db.flush()

    firewall = NetworkFirewall(
        vendor="Sophos",
        name="Sophos XGS87",
        management_ip="192.168.1.126",
        status="online",
    )
    db.add(firewall)
    db.flush()

    db.add(
        NetworkTrackedSubject(
            entity_type="device",
            normalized_value=str(device.id),
            value=str(device.id),
            label="PC CED monitorato",
            device_id=device.id,
            is_active=True,
        )
    )
    db.add(
        NetworkFirewallEvent(
            firewall_id=firewall.id,
            device_id=device.id,
            source="sophos_syslog",
            event_type="content_filtering.http.allowed",
            severity="info",
            src_ip=device.ip_address,
            dst_ip="8.8.8.8",
            protocol="TCP",
            raw_payload='{"parsed":{"domain":"dns.google","bytes_sent":"1024","bytes_received":"2048","fw_rule_name":"Internet senza blocco web"}}',
            observed_at=datetime.now(UTC) - timedelta(minutes=10),
        )
    )
    db.commit()

    created_rows = refresh_network_firewall_hourly_rollups(db, lookback_hours=2)
    assert created_rows > 0

    summary = build_network_statistics_summary_from_rollups(db, window_hours=1)
    assert summary is not None
    assert summary.total_events == 1
    assert summary.allowed_events == 1
    assert summary.blocked_events == 0
    assert summary.top_source_devices[0].ip_address == "192.168.1.10"
    assert summary.top_source_devices[0].label == "Operatore CED"
    assert summary.top_domains[0].label == "dns.google"
    assert summary.top_firewall_rules[0].key == "Internet senza blocco web"
    db.close()


def test_network_rollups_can_refresh_explicit_time_range() -> None:
    db = TestingSessionLocal()
    firewall = NetworkFirewall(
        vendor="Sophos",
        name="Sophos XGS87",
        management_ip="192.168.1.126",
        status="online",
    )
    db.add(firewall)
    observed_at = datetime.now(UTC).replace(minute=15, second=0, microsecond=0)
    db.add(
        NetworkFirewallEvent(
            firewall_id=1,
            source="sophos_syslog",
            event_type="firewall.invalid_traffic.denied",
            severity="info",
            src_ip="192.168.1.20",
            dst_ip="8.8.4.4",
            protocol="UDP",
            raw_payload='{"parsed":{"bytes_sent":"512","bytes_received":"256"}}',
            observed_at=observed_at,
        )
    )
    db.commit()

    rows = refresh_network_firewall_hourly_rollups_for_range(
        db,
        start=observed_at - timedelta(hours=1),
        end=observed_at,
    )
    assert rows > 0

    summary = build_network_statistics_summary_from_rollups(db, window_hours=1)
    assert summary is not None
    assert summary.total_events == 1
    assert summary.blocked_events == 1
    db.close()


def test_network_rollups_can_refresh_same_range_twice_without_unique_conflicts() -> None:
    db = TestingSessionLocal()
    firewall = NetworkFirewall(
        vendor="Sophos",
        name="Sophos XGS87",
        management_ip="192.168.1.126",
        status="online",
    )
    db.add(firewall)
    db.flush()

    observed_at = datetime.now(UTC).replace(minute=15, second=0, microsecond=0)
    db.add(
        NetworkFirewallEvent(
            firewall_id=firewall.id,
            source="sophos_syslog",
            event_type="content_filtering.http.allowed",
            severity="info",
            src_ip="192.168.1.20",
            dst_ip="8.8.8.8",
            protocol="TCP",
            raw_payload='{"parsed":{"domain":"dns.google","bytes_sent":"512","bytes_received":"256"}}',
            observed_at=observed_at,
        )
    )
    db.commit()

    start = observed_at - timedelta(hours=1)
    end = observed_at
    first_rows = refresh_network_firewall_hourly_rollups_for_range(db, start=start, end=end)
    second_rows = refresh_network_firewall_hourly_rollups_for_range(db, start=start, end=end)

    assert first_rows > 0
    assert second_rows == first_rows

    summary = build_network_statistics_summary_from_rollups(db, window_hours=1)
    assert summary is not None
    assert summary.total_events == 1
    db.close()
