from __future__ import annotations

import runpy
import sys
from types import SimpleNamespace

import pytest

import app.scripts.bootstrap_admin as bootstrap_admin_script
from app.models import catasto_phase1 as catasto_models
from app.models import elaborazioni as elaborazioni_models
from app.modules.catasto.models import registry as catasto_registry
from app.modules.network import scanner_script, sophos_snmp_script, sophos_syslog_script
from app.modules.ruolo import bootstrap as ruolo_bootstrap
from app.schemas import catasto as catasto_schemas
from app.schemas import elaborazioni as elaborazioni_schemas
from app.services import bootstrap_admin as bootstrap_admin_service


def test_star_reexport_modules_expose_expected_symbols() -> None:
    from app.modules.catasto import schemas as catasto_compat_schemas
    from app.modules.elaborazioni import models as elaborazioni_compat_models
    from app.modules.elaborazioni import schemas as elaborazioni_compat_schemas

    assert catasto_compat_schemas is not None
    assert elaborazioni_compat_models.ElaborazioneBatch is elaborazioni_models.ElaborazioneBatch
    assert elaborazioni_compat_schemas.ElaborazioneBatchResponse is elaborazioni_schemas.ElaborazioneBatchResponse
    assert catasto_registry.CatImportBatch is catasto_models.CatImportBatch
    assert catasto_registry.CatDistretto is catasto_models.CatDistretto
    assert "CatParticellaHistory" in catasto_registry.__all__
    assert ruolo_bootstrap.RUOLO_SECTIONS[0]["key"] == "ruolo.dashboard"
    assert ruolo_bootstrap.RUOLO_SECTIONS[2]["min_role"] == "admin"


def test_bootstrap_admin_main_prints_created_or_existing_user(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    closed: list[str] = []
    fake_db = SimpleNamespace(close=lambda: closed.append("closed"))

    monkeypatch.setattr(bootstrap_admin_script, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(
        bootstrap_admin_script,
        "ensure_bootstrap_admin",
        lambda db: (SimpleNamespace(username="admin", role="super_admin"), True),
    )

    bootstrap_admin_script.main()
    out = capsys.readouterr().out

    assert "bootstrap_admin=created username=admin role=super_admin" in out
    assert closed == ["closed"]


def test_bootstrap_admin_main_closes_db_when_user_already_exists(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    closed: list[str] = []
    fake_db = SimpleNamespace(close=lambda: closed.append("closed"))

    monkeypatch.setattr(bootstrap_admin_script, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(
        bootstrap_admin_script,
        "ensure_bootstrap_admin",
        lambda db: (SimpleNamespace(username="admin", role="admin"), False),
    )

    bootstrap_admin_script.main()
    out = capsys.readouterr().out

    assert "bootstrap_admin=existing username=admin role=admin" in out
    assert closed == ["closed"]


def test_wrapper_scripts_reexport_and_main_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.scripts.network_scanner as network_scanner_script
    import app.scripts.network_sophos_snmp as network_sophos_snmp_script
    import app.scripts.network_sophos_syslog as network_sophos_syslog_script

    assert network_scanner_script.main is scanner_script.main
    assert network_sophos_snmp_script.main is sophos_snmp_script.main
    assert network_sophos_syslog_script.main is sophos_syslog_script.main

    calls: list[str] = []
    monkeypatch.setattr(scanner_script, "main", lambda: calls.append("scanner"))
    monkeypatch.setattr(sophos_snmp_script, "main", lambda: calls.append("snmp"))
    monkeypatch.setattr(sophos_syslog_script, "main", lambda: calls.append("syslog"))

    monkeypatch.setattr(sys, "argv", ["network_scanner.py"])
    runpy.run_module("app.scripts.network_scanner", run_name="__main__")

    monkeypatch.setattr(sys, "argv", ["network_sophos_snmp.py"])
    runpy.run_module("app.scripts.network_sophos_snmp", run_name="__main__")

    monkeypatch.setattr(sys, "argv", ["network_sophos_syslog.py"])
    runpy.run_module("app.scripts.network_sophos_syslog", run_name="__main__")

    assert calls == ["scanner", "snmp", "syslog"]


def test_bootstrap_admin_main_guard_executes_under_main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    closed: list[str] = []
    fake_db = SimpleNamespace(close=lambda: closed.append("closed"))

    monkeypatch.setattr(bootstrap_admin_service, "ensure_bootstrap_admin", lambda db: (SimpleNamespace(username="root", role="super_admin"), True))
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: fake_db)
    monkeypatch.setattr(sys, "argv", ["bootstrap_admin.py"])

    runpy.run_module("app.scripts.bootstrap_admin", run_name="__main__")

    out = capsys.readouterr().out
    assert "bootstrap_admin=created username=root role=super_admin" in out
    assert closed == ["closed"]
