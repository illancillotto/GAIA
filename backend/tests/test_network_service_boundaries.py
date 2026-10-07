import asyncio
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.network import services


@pytest.mark.parametrize("raw", ["invalid-json", "null", "1", '"text"', "{}", "[]"])
def test_snmp_invalid_profiles_preserve_unique_defaults(monkeypatch, raw):
    monkeypatch.setattr(services.settings, "network_snmp_community_profiles", raw)
    monkeypatch.setattr(services.settings, "network_snmp_communities", " public, ,public, backup ")
    assert services._snmp_profile_communities("10.0.0.1") == ["public", "backup"]


@pytest.mark.parametrize("address", ["10.0.0.1", "invalid", "2001:db8::1"])
def test_snmp_profile_order_duplicates_and_invalid_entries(monkeypatch, address):
    profiles = [
        None,
        {"cidr": None, "communities": []},
        {"cidr": "10.0.0.0/8", "communities": "bad"},
        {"cidr": "bad", "communities": []},
        {"cidr": "192.168.0.0/16", "communities": ["outside"]},
        {"cidr": "10.0.0.2/8", "communities": [" private ", "", None, "private"]},
        {"cidr": "10.0.0.0/8", "communities": ["public"]},
    ]
    monkeypatch.setattr(services.settings, "network_snmp_community_profiles", json.dumps(profiles))
    monkeypatch.setattr(services.settings, "network_snmp_communities", "public,backup,backup")
    expected = ["private", "private", "public", "backup"]
    assert services._snmp_profile_communities(address) == (
        expected if address == "10.0.0.1" else ["public", "backup"]
    )


@pytest.mark.parametrize(
    ("ports", "device_type", "system"),
    [
        ([3389, 22], "workstation", "Windows"),
        ([22, 445], "server", "Linux/Unix server"),
        ([445], None, "Windows or SMB appliance"),
        ([22], None, "Linux/Unix"),
        ([443], "network-service", "Embedded/Web appliance"),
        ([], None, None),
    ],
)
def test_port_classification_priority(ports, device_type, system):
    assert services._guess_device_type(ports) == device_type
    assert services._guess_operating_system(ports) == system


def test_metadata_parsing_and_empty_identity():
    assert services._normalize_mac(None) is None
    assert services._extract_mac_from_text("no address") is None
    assert services._safe_text(None) is None
    assert services._safe_text(" . ") is None
    assert services._json_dumps({}) is None
    assert services.metadata_sources_to_dict("bad") is None
    assert services.metadata_sources_to_dict("[]") is None
    assert services._merge_metadata_sources('{"dns":"old"}', None) == '{"dns": "old"}'
    assert services._classify_snmp_descr(None) == (None, None, None)
    assert services._classify_http_identity(None, None) == (None, None, None)
    assert services._extract_html_title("<TITLE>  Printer\n Name. </TITLE>") == "Printer Name"
    assert services._extract_html_title("no title") is None
    assert services._extract_meta_refresh_target("no refresh") is None
    assert services._extract_device_name('<span id="deviceName"> </span>') is None
    assert (
        services._extract_device_name('<meta name="device-name" content="HP Laser">') == "HP Laser"
    )
    assert services._normalize_http_model_name("Accesso", None, None) is None
    assert services._parse_netbios_name("ignored\nNAME <00> inactive\n<00> <ACTIVE>") is None


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        ([OSError(), subprocess.TimeoutExpired("arp", 1)], None),
        ([SimpleNamespace(returncode=1), SimpleNamespace(returncode=1)], None),
        ([SimpleNamespace(returncode=0, stdout="unknown")] * 2, None),
        ([SimpleNamespace(returncode=0, stdout="lladdr AA-BB-CC-DD-EE-FF")], "aa:bb:cc:dd:ee:ff"),
        ([SimpleNamespace(returncode=0, stdout="at AA:BB:CC:DD:EE:FF")], "aa:bb:cc:dd:ee:ff"),
    ],
)
def test_arp_cache_tool_fallback(monkeypatch, results, expected):
    monkeypatch.setattr(services.shutil, "which", lambda name: name)
    runner = MagicMock(side_effect=results)
    monkeypatch.setattr(services.subprocess, "run", runner)
    assert services._resolve_mac_from_arp_cache("10.0.0.1") == expected
    assert runner.call_args.kwargs["check"] is False


def test_arp_cache_no_tools(monkeypatch):
    monkeypatch.setattr(services.shutil, "which", lambda name: None)
    assert services._resolve_mac_from_arp_cache("10.0.0.1") is None


@pytest.mark.parametrize("mode", ["missing", "disabled", "status", "error", "list", "non-string"])
def test_arp_helper_unavailable_or_invalid_response(monkeypatch, mode):
    client = MagicMock()
    response = client.return_value.__enter__.return_value.get.return_value
    response.status_code = 503 if mode == "status" else 200
    response.json.return_value = [] if mode == "list" else {"mac_address": 17}
    if mode == "error":
        response.json.side_effect = ValueError("bad JSON")
    monkeypatch.setattr(
        services, "httpx", None if mode == "missing" else SimpleNamespace(Client=client)
    )
    monkeypatch.setattr(
        services.settings,
        "network_arp_helper_base_url",
        "" if mode == "disabled" else "http://helper",
    )
    assert services._resolve_mac_via_arp_helper("10.0.0.1") is None


@pytest.mark.parametrize("mode", ["missing", "disabled", "credentials", "key", "password", "error"])
def test_gateway_arp_credentials_and_cleanup(monkeypatch, mode):
    ssh = MagicMock()
    ssh.exec_command.return_value = (
        None,
        SimpleNamespace(read=lambda: b"at AA:BB:CC:DD:EE:FF"),
        None,
    )
    if mode == "error":
        ssh.connect.side_effect = OSError("unreachable")
    module = SimpleNamespace(SSHClient=lambda: ssh, AutoAddPolicy=MagicMock())
    monkeypatch.setattr(services, "paramiko", None if mode == "missing" else module)
    monkeypatch.setattr(
        services.settings, "network_gateway_arp_host", "" if mode == "disabled" else "gateway"
    )
    monkeypatch.setattr(services.settings, "network_gateway_arp_username", "scanner")
    monkeypatch.setattr(
        services.settings, "network_gateway_arp_private_key_path", "/key" if mode == "key" else None
    )
    monkeypatch.setattr(
        services.settings,
        "network_gateway_arp_password",
        "secret" if mode in {"password", "error"} else None,
    )
    expected = "aa:bb:cc:dd:ee:ff" if mode in {"key", "password"} else None
    assert services._resolve_mac_via_gateway_arp("10.0.0.1") == expected
    if mode in {"key", "password", "error"}:
        ssh.close.assert_called_once()
        assert ssh.connect.call_args.kwargs["hostname"] == "gateway"
    else:
        ssh.connect.assert_not_called()


@pytest.mark.parametrize("failure", [False, True])
def test_dns_lookup_handles_os_error(monkeypatch, failure):
    lookup = MagicMock(
        return_value=("host.local.", [], []), side_effect=OSError() if failure else None
    )
    monkeypatch.setattr(services.socket, "gethostbyaddr", lookup)
    assert services._resolve_dns_name("10.0.0.1") == (None if failure else "host.local")


@pytest.mark.parametrize("resolver", ["_resolve_mdns_name", "_resolve_netbios_name"])
@pytest.mark.parametrize("mode", ["missing", "error", "status", "empty", "success"])
def test_external_name_resolvers(monkeypatch, resolver, mode):
    monkeypatch.setattr(services.shutil, "which", lambda name: None if mode == "missing" else name)
    output = "10.0.0.1 host.local.\n" if resolver == "_resolve_mdns_name" else "HOST <00> <ACTIVE>"
    runner = MagicMock(
        return_value=SimpleNamespace(
            returncode=1 if mode == "status" else 0, stdout="" if mode == "empty" else output
        )
    )
    if mode == "error":
        runner.side_effect = subprocess.TimeoutExpired("lookup", 1)
    monkeypatch.setattr(services.subprocess, "run", runner)
    expected = "host.local" if resolver == "_resolve_mdns_name" else "HOST"
    assert getattr(services, resolver)("10.0.0.1") == (expected if mode == "success" else None)


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "no-ports",
        "empty",
        "failure",
        "refresh",
        "refresh-failure",
        "refresh-500",
        "absolute",
    ],
)
def test_http_enrichment_fallback_refresh_and_sources(monkeypatch, mode):
    response = SimpleNamespace(text="", headers={})
    refresh = '<meta http-equiv="refresh" content="0;url=/printer">'
    if mode in {"refresh", "refresh-failure", "refresh-500", "absolute"}:
        response.text = refresh.replace(
            "/printer", "http://printer/" if mode == "absolute" else "/printer"
        )
    enriched = SimpleNamespace(
        status_code=200,
        text='<title>Canon printer</title><span id="deviceName">Office</span>',
        headers={"server": "Printer Server"},
    )
    client = MagicMock()
    get = client.return_value.__enter__.return_value.get
    get.side_effect = [OSError(), enriched] if mode == "failure" else [response, enriched]
    if mode == "refresh-failure":
        get.side_effect = [response, OSError()]
    if mode == "refresh-500":
        enriched.status_code = 500
    monkeypatch.setattr(
        services, "httpx", None if mode == "missing" else SimpleNamespace(Client=client)
    )
    result = services._resolve_http_metadata("10.0.0.1", [] if mode == "no-ports" else [80, 443])
    if mode in {"missing", "no-ports", "empty"}:
        assert result == services.EnrichmentMetadata()
    elif mode in {"refresh-failure", "refresh-500"}:
        assert result.metadata_sources == {"http_refresh_target": "/printer", "http": "http:80"}
    else:
        assert result.vendor == "Canon"
        assert result.http_title == "Canon printer"
        assert result.http_server == "Printer Server"
        assert result.metadata_sources["http_device_name"] == "Office"
    if mode == "failure":
        assert get.call_args.args[0] == "https://10.0.0.1:443/"
    if mode == "absolute":
        assert get.call_args.args[0] == "http://printer/"


def test_http_enrichment_all_connections_fail(monkeypatch):
    client = MagicMock()
    client.return_value.__enter__.return_value.get.side_effect = OSError()
    monkeypatch.setattr(services, "httpx", SimpleNamespace(Client=client))
    assert services._resolve_http_metadata("10.0.0.1", [80]) == services.EnrichmentMetadata()


@pytest.mark.parametrize(
    "mode", ["missing-command", "missing-target", "empty", "errors", "success"]
)
def test_snmp_async_retries_communities_and_classifies(monkeypatch, mode):
    communities = [] if mode == "empty" else ["first", "second", "third", "last"]
    monkeypatch.setattr(services, "_snmp_profile_communities", lambda address: communities)
    target = SimpleNamespace(create=AsyncMock(return_value="transport"))
    bindings = [
        ("unknown", "ignored"),
        ("1.3.6.1.2.1.1.5.0", " switch. "),
        ("1.3.6.1.2.1.1.1.0", "Cisco IOS"),
    ]
    get = AsyncMock(
        side_effect=[
            OSError(),
            ("timeout", 0, None, []),
            (None, 1, None, []),
            (None, 0, None, bindings),
        ]
        if mode == "success"
        else OSError()
    )
    monkeypatch.setattr(
        services, "UdpTransportTarget", None if mode == "missing-target" else target
    )
    monkeypatch.setattr(services, "get_cmd", None if mode == "missing-command" else get)
    for name in ["SnmpEngine", "CommunityData", "ContextData", "ObjectType", "ObjectIdentity"]:
        monkeypatch.setattr(services, name, MagicMock())
    result = asyncio.run(services._resolve_snmp_metadata_async("10.0.0.1"))
    if mode == "success":
        assert result.snmp_name == "switch"
        assert result.vendor == "Cisco"
        assert result.metadata_sources == {"snmp": "last"}
        assert get.await_count == 4
    else:
        assert result == services.EnrichmentMetadata()


def test_snmp_sync_loop_and_exception_fallback(monkeypatch):
    monkeypatch.setattr(services, "get_cmd", None)
    assert services._resolve_snmp_metadata("host") == services.EnrichmentMetadata()
    monkeypatch.setattr(services, "get_cmd", object())
    metadata = services.EnrichmentMetadata(snmp_name="switch")
    resolver = AsyncMock(return_value=metadata)
    monkeypatch.setattr(services, "_resolve_snmp_metadata_async", resolver)
    assert services._resolve_snmp_metadata("host") == metadata

    async def active_loop():
        return services._resolve_snmp_metadata("host")

    assert asyncio.run(active_loop()) == services.EnrichmentMetadata()
    resolver.side_effect = OSError()
    assert services._resolve_snmp_metadata("host") == services.EnrichmentMetadata()
    monkeypatch.setattr(
        asyncio, "get_running_loop", lambda: SimpleNamespace(is_running=lambda: False)
    )
    resolver.side_effect = None
    assert services._resolve_snmp_metadata("host") == metadata


@pytest.mark.parametrize("source", ["snmp", "netbios", "mdns", "dns", None])
def test_enrichment_hostname_precedence_and_vendor_priority(monkeypatch, source):
    priorities = ["snmp", "netbios", "mdns", "dns", None]
    for name in ["dns", "mdns", "netbios"]:
        value = name if priorities.index(name) >= priorities.index(source) and source else None
        monkeypatch.setattr(services, f"_resolve_{name}_name", lambda address, value=value: value)
    snmp = services.EnrichmentMetadata(
        snmp_name="snmp" if source == "snmp" else None,
        vendor="Cisco" if source == "snmp" else None,
        metadata_sources={"snmp": "public"} if source == "snmp" else None,
    )
    http = services.EnrichmentMetadata(
        vendor="Canon",
        http_title="Printer",
        http_server="Server",
        metadata_sources={"http": "http:80"},
    )
    monkeypatch.setattr(services, "_resolve_snmp_metadata", lambda address: snmp)
    monkeypatch.setattr(services, "_resolve_http_metadata", lambda address, ports: http)
    result = services._collect_enrichment("10.0.0.1", [161, 80])
    assert result.hostname_source == source
    assert result.vendor == ("Cisco" if source == "snmp" else "Canon")
    assert services._preferred_hostname(None, result) == source
    assert services._preferred_hostname("observed.", result) == "observed"
    assert services._preferred_hostname_source(None, result) == source
    assert services._preferred_hostname_source("observed", result) == "nmap"
    http.metadata_sources = None
    assert services._collect_enrichment("10.0.0.1", [443]).http_title == "Printer"
    assert services._collect_enrichment("10.0.0.1", []).vendor is None


def test_fallback_hosts_handles_dns_failure(monkeypatch):
    monkeypatch.setattr(services.socket, "gethostname", lambda: "scanner")
    lookup = MagicMock(return_value="127.0.0.1")
    monkeypatch.setattr(services.socket, "gethostbyname", lookup)
    assert services._fallback_hosts()[0].device_type == "scanner"
    lookup.side_effect = OSError()
    assert services._fallback_hosts() == []


def test_nmap_unavailable_or_no_online_hosts(monkeypatch):
    fallback = [services.DiscoveredHost("127.0.0.1")]
    monkeypatch.setattr(services, "_fallback_hosts", lambda: fallback)
    monkeypatch.setattr(services, "nmap", None)
    assert services._run_nmap_scan("10.0.0.0/24", "80") == fallback
    assert services._run_nmap_arp_scan("10.0.0.0/24") == []
    scanner = MagicMock()
    scanner.all_hosts.return_value = ["10.0.0.1"]
    scanner.__getitem__.return_value.state.return_value = "down"
    monkeypatch.setattr(services, "nmap", SimpleNamespace(PortScanner=lambda: scanner))
    monkeypatch.setattr(services.shutil, "which", lambda name: name)
    assert services._run_nmap_scan("10.0.0.0/24", "80") == []
    assert services._run_nmap_arp_scan("10.0.0.0/24") == []
    monkeypatch.setattr(services.shutil, "which", lambda name: None)
    assert services._run_nmap_scan("10.0.0.0/24", "80") == fallback
    assert services._run_nmap_arp_scan("10.0.0.0/24") == []


def test_scapy_scan_normalizes_arp_response(monkeypatch):
    packet = MagicMock()
    srp = MagicMock(
        return_value=([(None, SimpleNamespace(psrc="10.0.0.1", hwsrc="AA-BB-CC-DD-EE-FF"))], [])
    )
    module = SimpleNamespace(
        ARP=MagicMock(return_value=packet), Ether=MagicMock(return_value=packet), srp=srp
    )
    monkeypatch.setitem(sys.modules, "scapy.all", module)
    hosts = services._run_scapy_scan("10.0.0.0/24")
    assert hosts == [
        services.DiscoveredHost("10.0.0.1", mac_address="aa:bb:cc:dd:ee:ff", open_ports=[])
    ]
    module.ARP.assert_called_once_with(pdst="10.0.0.0/24")
    assert srp.call_args.kwargs["verbose"] is False


@pytest.mark.parametrize("scan_type", ["arp", "incremental"])
@pytest.mark.parametrize("winner", ["nmap", "scapy", "fallback"])
def test_discovery_fallback_chain(monkeypatch, scan_type, winner):
    hosts = [services.DiscoveredHost("10.0.0.1")]
    nmap = MagicMock(return_value=hosts if winner == "nmap" else [])
    scapy = MagicMock(return_value=hosts if winner == "scapy" else [])
    fallback = MagicMock(return_value=hosts)
    monkeypatch.setattr(services, "_run_nmap_scan", nmap)
    monkeypatch.setattr(services, "_run_nmap_arp_scan", nmap)
    monkeypatch.setattr(services, "_run_scapy_scan", scapy)
    monkeypatch.setattr(services, "_fallback_hosts", fallback)
    assert services.discover_hosts("10.0.0.0/24", "80", scan_type=scan_type) == hosts
    assert scapy.called is (winner != "nmap")
    assert fallback.called is (winner == "fallback")
    with pytest.raises(ValueError, match="Invalid network range: bad"):
        services.discover_hosts("bad")


def test_scanner_subprocess_entrypoint(monkeypatch):
    call = MagicMock(return_value=7)
    monkeypatch.setattr(services.subprocess, "call", call)
    assert services.run_network_scan_subprocess() == 7
    call.assert_called_once_with(["python", "-m", "app.scripts.network_scanner"])
