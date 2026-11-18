from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from app.modules.network.models import NetworkFirewallEvent
from app.modules.network.schemas import (
    NetworkTrackedSubjectActivityEvent,
    NetworkTrackedSubjectActivitySummary,
)


@dataclass
class TrackedActivityStats:
    total_events: int = 0
    allowed_events: int = 0
    blocked_events: int = 0
    suspicious_events: int = 0
    vpn_suspected_events: int = 0
    proxy_suspected_events: int = 0
    tor_suspected_events: int = 0
    encrypted_dns_events: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    last_observed_at: datetime | None = None
    detection_counter: Counter[str] = field(default_factory=Counter)

    def record_traffic(self, event: NetworkFirewallEvent, bytes_in: int, bytes_out: int) -> None:
        self.bytes_in += bytes_in
        self.bytes_out += bytes_out
        if self.last_observed_at is None:
            self.last_observed_at = event.observed_at

    def record_event_type(self, event_type: str) -> None:
        lowered_type = event_type.lower()
        if "allow" in lowered_type:
            self.allowed_events += 1
        if (
            "deny" in lowered_type
            or "denied" in lowered_type
            or "block" in lowered_type
            or "drop" in lowered_type
        ):
            self.blocked_events += 1

    def record_detection_tags(self, detection_tags: list[str]) -> None:
        if detection_tags:
            self.suspicious_events += 1
            self.detection_counter.update(detection_tags)
            if "vpn_suspected" in detection_tags:
                self.vpn_suspected_events += 1
            if "proxy_suspected" in detection_tags:
                self.proxy_suspected_events += 1
            if "tor_suspected" in detection_tags:
                self.tor_suspected_events += 1
            if "encrypted_dns" in detection_tags:
                self.encrypted_dns_events += 1

    def build_summary(
        self, window_hours: int, recent_events: list[NetworkTrackedSubjectActivityEvent]
    ) -> NetworkTrackedSubjectActivitySummary:
        return NetworkTrackedSubjectActivitySummary(
            window_hours=window_hours,
            total_events=self.total_events,
            allowed_events=self.allowed_events,
            blocked_events=self.blocked_events,
            suspicious_events=self.suspicious_events,
            vpn_suspected_events=self.vpn_suspected_events,
            proxy_suspected_events=self.proxy_suspected_events,
            tor_suspected_events=self.tor_suspected_events,
            encrypted_dns_events=self.encrypted_dns_events,
            bytes_in=self.bytes_in,
            bytes_out=self.bytes_out,
            last_observed_at=self.last_observed_at,
            top_detection_tags=[tag for tag, _ in self.detection_counter.most_common(4)],
            recent_events=recent_events,
        )
