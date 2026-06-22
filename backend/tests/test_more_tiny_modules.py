from __future__ import annotations

from http import HTTPStatus
import http.server
from io import BytesIO
import runpy
import sys
from types import SimpleNamespace

import pytest

from app.models import application_user, effective_permission, nas_group, nas_user, permission_entry, review, section_permission, share, snapshot, sync_run
from app.modules.accessi import models as accessi_models
from app.modules.accessi import org_structure, wc_org_charts
from app.modules.network import scanner_script, sophos_snmp_script, sophos_syslog_script
from app.scripts import arp_helper, seed_riordino_demo


def test_accessi_models_reexport_expected_symbols() -> None:
    assert accessi_models.ApplicationUser is application_user.ApplicationUser
    assert accessi_models.ApplicationUserRole is application_user.ApplicationUserRole
    assert accessi_models.EffectivePermission is effective_permission.EffectivePermission
    assert accessi_models.NasGroup is nas_group.NasGroup
    assert accessi_models.NasUser is nas_user.NasUser
    assert accessi_models.PermissionEntry is permission_entry.PermissionEntry
    assert accessi_models.Review is review.Review
    assert accessi_models.RoleSectionPermission is section_permission.RoleSectionPermission
    assert accessi_models.Section is section_permission.Section
    assert accessi_models.UserSectionPermission is section_permission.UserSectionPermission
    assert accessi_models.Share is share.Share
    assert accessi_models.Snapshot is snapshot.Snapshot
    assert accessi_models.SyncRun is sync_run.SyncRun
    assert accessi_models.OrgStructureAssignment is org_structure.OrgStructureAssignment
    assert accessi_models.WCOrgChart is wc_org_charts.WCOrgChart
    assert accessi_models.WCOrgChartEntry is wc_org_charts.WCOrgChartEntry
    assert "UserSectionPermission" in accessi_models.__all__


def test_network_scanner_script_main_chooses_scheduler_or_one_shot(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(scanner_script.settings, "network_scan_enabled", True)
    monkeypatch.setattr(scanner_script, "run_scheduler", lambda: calls.append("scheduler"))
    monkeypatch.setattr(scanner_script, "execute_scheduled_scan", lambda: calls.append("one-shot"))
    scanner_script.main()
    assert calls == ["scheduler"]

    calls.clear()
    monkeypatch.setattr(scanner_script.settings, "network_scan_enabled", False)
    scanner_script.main()
    assert calls == ["one-shot"]

    import app.modules.network.scheduler as network_scheduler_module

    monkeypatch.setattr(network_scheduler_module, "run_scheduler", lambda: calls.append("scheduler-main"))
    monkeypatch.setattr(network_scheduler_module, "execute_scheduled_scan", lambda: calls.append("one-shot-main"))
    monkeypatch.setattr(scanner_script.settings, "network_scan_enabled", True)
    monkeypatch.setattr(sys, "argv", ["scanner_script.py"])
    runpy.run_module("app.modules.network.scanner_script", run_name="__main__")
    assert calls[-1] == "scheduler-main"


def test_sophos_scripts_main_and_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    snmp_calls: list[str] = []
    syslog_calls: list[str] = []

    monkeypatch.setattr(sophos_snmp_script.settings, "network_sophos_snmp_enabled", False)
    with pytest.raises(SystemExit, match="NETWORK_SOPHOS_SNMP_ENABLED is false"):
        sophos_snmp_script.main()

    monkeypatch.setattr(sophos_snmp_script.settings, "network_sophos_snmp_enabled", True)
    monkeypatch.setattr(sophos_snmp_script, "run_sophos_snmp_poller", lambda: snmp_calls.append("snmp"))
    sophos_snmp_script.main()
    assert snmp_calls == ["snmp"]

    monkeypatch.setattr(sophos_syslog_script.settings, "network_sophos_syslog_enabled", False)
    with pytest.raises(SystemExit, match="NETWORK_SOPHOS_SYSLOG_ENABLED is false"):
        sophos_syslog_script.main()

    monkeypatch.setattr(sophos_syslog_script.settings, "network_sophos_syslog_enabled", True)
    monkeypatch.setattr(sophos_syslog_script, "run_sophos_syslog_listener", lambda: syslog_calls.append("syslog"))
    sophos_syslog_script.main()
    assert syslog_calls == ["syslog"]

    import app.modules.network.sophos_snmp as sophos_snmp_module
    import app.modules.network.sophos_syslog_listener as sophos_syslog_listener_module

    monkeypatch.setattr(sophos_snmp_module, "run_sophos_snmp_poller", lambda: snmp_calls.append("snmp-main"))
    monkeypatch.setattr(sophos_snmp_script.settings, "network_sophos_snmp_enabled", True)
    monkeypatch.setattr(sys, "argv", ["sophos_snmp_script.py"])
    runpy.run_module("app.modules.network.sophos_snmp_script", run_name="__main__")

    monkeypatch.setattr(sophos_syslog_listener_module, "run_sophos_syslog_listener", lambda: syslog_calls.append("syslog-main"))
    monkeypatch.setattr(sophos_syslog_script.settings, "network_sophos_syslog_enabled", True)
    monkeypatch.setattr(sys, "argv", ["sophos_syslog_script.py"])
    runpy.run_module("app.modules.network.sophos_syslog_script", run_name="__main__")

    assert snmp_calls[-1] == "snmp-main"
    assert syslog_calls[-1] == "syslog-main"


def test_seed_riordino_demo_main_and_main_guard(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    closed: list[str] = []
    fake_db = SimpleNamespace(close=lambda: closed.append("closed"))
    monkeypatch.setattr(seed_riordino_demo, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(seed_riordino_demo, "ensure_demo_practices", lambda db: {"created": 2, "skipped": 3, "total": 5})

    seed_riordino_demo.main()
    assert "created=2 skipped=3 total=5" in capsys.readouterr().out
    assert closed == ["closed"]

    import app.modules.riordino.services as riordino_services
    import app.core.database as core_database

    closed.clear()
    monkeypatch.setattr(core_database, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(riordino_services, "ensure_demo_practices", lambda db: {"created": 1, "skipped": 0, "total": 1})
    monkeypatch.setattr(sys, "argv", ["seed_riordino_demo.py"])
    runpy.run_module("app.scripts.seed_riordino_demo", run_name="__main__")
    assert "created=1 skipped=0 total=1" in capsys.readouterr().out
    assert closed == ["closed"]


def test_arp_helper_normalize_and_lookup_mac(monkeypatch: pytest.MonkeyPatch) -> None:
    assert arp_helper._normalize_mac(None) is None
    assert arp_helper._normalize_mac(" AA-BB-CC-DD-EE-FF ") == "aa:bb:cc:dd:ee:ff"

    monkeypatch.setattr(arp_helper.shutil, "which", lambda cmd: "/usr/bin/" + cmd if cmd == "ip" else None)
    monkeypatch.setattr(
        arp_helper.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="192.168.1.10 dev eth0 lladdr AA-BB-CC-DD-EE-FF REACHABLE"),
    )
    assert arp_helper._lookup_mac("192.168.1.10") == "aa:bb:cc:dd:ee:ff"

    calls = iter(
        [
            OSError("boom"),
            SimpleNamespace(returncode=1, stdout=""),
        ]
    )

    monkeypatch.setattr(arp_helper.shutil, "which", lambda cmd: "/usr/bin/" + cmd)

    def fake_run(*args, **kwargs):
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(arp_helper.subprocess, "run", fake_run)
    assert arp_helper._lookup_mac("192.168.1.11") is None

    monkeypatch.setattr(arp_helper.shutil, "which", lambda cmd: None)
    assert arp_helper._lookup_mac("192.168.1.12") is None

    monkeypatch.setattr(arp_helper.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
    monkeypatch.setattr(arp_helper.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(arp_helper.subprocess.TimeoutExpired(cmd="ip", timeout=1.5)))
    assert arp_helper._lookup_mac("192.168.1.13") is None


def test_arp_lookup_handler_routes_and_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def build_handler(path: str):
        handler = object.__new__(arp_helper.ArpLookupHandler)
        handler.path = path
        handler.wfile = BytesIO()
        handler.responses = []
        handler.headers_sent = []
        handler.end_headers_called = False
        handler.send_response = lambda code: handler.responses.append(code)
        handler.send_header = lambda key, value: handler.headers_sent.append((key, value))
        handler.end_headers = lambda: setattr(handler, "end_headers_called", True)
        return handler

    health = build_handler("/health")
    arp_helper.ArpLookupHandler.do_GET(health)
    assert health.responses == [HTTPStatus.OK.value]
    assert b'"status": "ok"' in health.wfile.getvalue()

    not_found = build_handler("/missing")
    arp_helper.ArpLookupHandler.do_GET(not_found)
    assert not_found.responses == [HTTPStatus.NOT_FOUND.value]

    missing_ip = build_handler("/lookup")
    arp_helper.ArpLookupHandler.do_GET(missing_ip)
    assert missing_ip.responses == [HTTPStatus.BAD_REQUEST.value]

    monkeypatch.setattr(arp_helper, "_lookup_mac", lambda ip: "aa:bb:cc:dd:ee:ff")
    lookup = build_handler("/lookup?ip=192.168.1.20")
    arp_helper.ArpLookupHandler.do_GET(lookup)
    payload = lookup.wfile.getvalue().decode("utf-8")
    assert lookup.responses == [HTTPStatus.OK.value]
    assert '"ip_address": "192.168.1.20"' in payload
    assert '"found": true' in payload
    assert lookup.end_headers_called is True

    assert arp_helper.ArpLookupHandler.log_message(lookup, "%s", "ignored") is None


def test_arp_helper_main_closes_server(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class _FakeServer:
        def serve_forever(self):
            events.append("serve")
            raise KeyboardInterrupt

        def server_close(self):
            events.append("close")

    monkeypatch.setattr(arp_helper, "ThreadingHTTPServer", lambda addr, handler: _FakeServer())

    arp_helper.main()

    assert events == ["serve", "close"]


def test_arp_helper_main_guard_runs_under_main(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class _FakeServer:
        def __init__(self, *args, **kwargs):
            pass

        def serve_forever(self):
            events.append("serve")
            raise KeyboardInterrupt

        def server_close(self):
            events.append("close")

    monkeypatch.setattr(http.server, "ThreadingHTTPServer", _FakeServer)
    monkeypatch.setattr(sys, "argv", ["arp_helper.py"])

    runpy.run_module("app.scripts.arp_helper", run_name="__main__")

    assert events == ["serve", "close"]
