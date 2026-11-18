"""Discovery probes preserve fallback order, identity and truth tests."""

from types import SimpleNamespace

import pytest

from app.modules.network import services


class ProbeResult:
    def __init__(self, name, trace, value):
        self.name = name
        self.trace = trace
        self.value = value

    def __bool__(self):
        self.trace.append(("bool", self.name))
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


@pytest.fixture
def discovery_case(monkeypatch):
    def setup(*, winner="fallback", error_at=None, bool_error_at=None):
        trace = []
        results = {
            name: ProbeResult(
                name,
                trace,
                RuntimeError("truth " + name) if name == bool_error_at else name == winner,
            )
            for name in ["arp", "nmap", "scapy", "fallback"]
        }

        def validate(network_range, *, strict):
            trace.append(("validate", network_range, strict))
            if error_at == "validate":
                raise ValueError("network")

        monkeypatch.setattr(services.ipaddress, "ip_network", validate)
        monkeypatch.setattr(
            services,
            "settings",
            SimpleNamespace(network_range="default-range", network_scan_ports="default-ports"),
        )

        def probe(name):
            def run(*args):
                trace.append((name, *args))
                if error_at == name:
                    raise RuntimeError("probe " + name)
                return results[name]

            return run

        for name, function in [
            ("arp", "_run_nmap_arp_scan"),
            ("nmap", "_run_nmap_scan"),
            ("scapy", "_run_scapy_scan"),
            ("fallback", "_fallback_hosts"),
        ]:
            monkeypatch.setattr(services, function, probe(name))
        return trace, results

    return setup


@pytest.mark.parametrize("scan_type", ["arp", "incremental", "other", "ARP", None])
@pytest.mark.parametrize("winner", ["primary", "scapy", "fallback"])
@pytest.mark.parametrize("defaults", [False, True])
def test_order_single_truth_test_and_exact_result_identity(
    discovery_case, scan_type, winner, defaults
):
    first = "arp" if scan_type == "arp" else "nmap"
    selected = first if winner == "primary" else winner
    trace, results = discovery_case(winner=selected)
    network_range, ports = ("default-range", "default-ports") if defaults else ("range", "ports")
    actual = services.discover_hosts(
        None if defaults else network_range, None if defaults else ports, scan_type=scan_type
    )
    expected = [("validate", network_range, False)]
    expected.append((first, network_range) if first == "arp" else (first, network_range, ports))
    expected.append(("bool", first))
    if winner != "primary":
        expected.extend([("scapy", network_range), ("bool", "scapy")])
    if winner == "fallback":
        expected.append(("fallback",))
    assert trace == expected
    assert actual is results[selected]


@pytest.mark.parametrize("scan_type", ["arp", "incremental"])
@pytest.mark.parametrize(
    "failure", ["primary", "scapy", "fallback", "truth-primary", "truth-scapy"]
)
def test_failure_stops_without_trying_later_probes(discovery_case, scan_type, failure):
    first = "arp" if scan_type == "arp" else "nmap"
    name = failure.replace("primary", first)
    trace, _ = discovery_case(
        error_at=None if name.startswith("truth-") else name,
        bool_error_at=name.removeprefix("truth-") if name.startswith("truth-") else None,
    )
    with pytest.raises(RuntimeError):
        services.discover_hosts("range", "ports", scan_type=scan_type)
    assert trace[-1][0] == ("bool" if name.startswith("truth-") else name)
    if name in {first, "truth-" + first}:
        assert not any(item[0] in {"scapy", "fallback"} for item in trace)
    elif name in {"scapy", "truth-scapy"}:
        assert not any(item[0] == "fallback" for item in trace)


def test_invalid_range_reports_resolved_value_and_suppresses_cause(discovery_case):
    trace, _ = discovery_case(error_at="validate")
    with pytest.raises(ValueError, match="Invalid network range: default-range") as exc:
        services.discover_hosts()
    assert exc.value.__cause__ is None and exc.value.__suppress_context__
    assert trace == [("validate", "default-range", False)]


def test_empty_arguments_use_defaults_before_arp_scan(discovery_case):
    trace, result = discovery_case(winner="arp")
    assert services.discover_hosts("", "", scan_type="arp") is result["arp"]
    assert trace[:2] == [("validate", "default-range", False), ("arp", "default-range")]
