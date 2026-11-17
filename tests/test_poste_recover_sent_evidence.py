import asyncio
import fcntl
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts import poste_recover_sent_evidence as recovery


def row(**changes):
    return {
        "item_id": "item-1",
        "mail_id": "mail-1",
        "account_id": 1,
        "account_username": "sender",
        "lot_username": " SENDER ",
        "shipment_id": "12345678",
        "imported_shipment_id": "12345678",
        "tracking": "123456789012",
        "imported_tracking": "123456789012",
        **changes,
    }


@pytest.fixture
def db(monkeypatch):
    session = MagicMock()
    session.__enter__.return_value = session
    session.execute.return_value.mappings.return_value = [row()]
    monkeypatch.setattr(recovery, "SessionLocal", lambda: session)
    return session


def test_plan_is_read_only_private_and_bound_to_unchanged_identities(tmp_path, db):
    assert recovery.load_plan(tmp_path) == [row()]
    assert "SET TRANSACTION READ ONLY" in str(db.execute.call_args_list[0].args[0])
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
    assert (tmp_path / "plan.json").stat().st_mode & 0o777 == 0o600
    assert recovery.load_plan(tmp_path) == [row()]
    (tmp_path / "plan.json").write_text("[]")
    with pytest.raises(ValueError, match="perimetro"):
        recovery.load_plan(tmp_path)


@pytest.mark.parametrize(
    "change",
    [
        {"mail_id": None},
        {"imported_shipment_id": "other"},
        {"shipment_id": "../1", "imported_shipment_id": "../1"},
        {
            "shipment_id": "\uff11\uff12\uff13\uff14",
            "imported_shipment_id": "\uff11\uff12\uff13\uff14",
        },
        {"imported_tracking": "999999999999"},
        {"lot_username": None},
        {"account_username": None},
        {"lot_username": "another-sender"},
    ],
)
def test_inconsistent_shipment_or_account_is_never_recovered(change):
    with pytest.raises(ValueError):
        recovery.validate_identity(row(**change))


def test_atomic_observations_preserve_identity_and_resume_without_repeating_success(tmp_path):
    first, second, third = row(), row(item_id="item-2"), row(item_id="item-3")
    recovery.observation(tmp_path, first, "tracking", payload={"stato": "2"})
    recovery.observation(tmp_path, second, "tracking", error="HTTP 403")
    saved = json.loads((tmp_path / "item-1/tracking.json").read_text())
    assert saved["mail_id"] == first["mail_id"] and saved["tracking"] == first["tracking"]
    assert saved["account_id"] == 1 and saved["observed_at"].endswith("+00:00")
    assert recovery.pending([first, second, third], tmp_path, "tracking", False) == [third]
    assert recovery.pending([first, second, third], tmp_path, "tracking", True) == [second, third]
    assert list(tmp_path.rglob("*.tmp")) == []


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(recovery.asyncio, "sleep", AsyncMock())


@pytest.mark.parametrize(
    "errors,expected",
    [
        ([None, None, None], 3),
        (["HTTP 403", None, None], 1),
        (["HTTP 429", None, None], 1),
        (["timeout", "timeout", None], 2),
        (["timeout", None, "timeout"], 3),
    ],
)
def test_tracking_has_checkpoints_bounded_failures_and_no_retries(
    tmp_path, monkeypatch, fast, errors, expected
):
    http = MagicMock()
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock()
    monkeypatch.setattr(recovery.httpx, "AsyncClient", lambda **_: http)
    results = [RuntimeError(error) if error else {"listaMovimenti": []} for error in errors]
    read = AsyncMock(side_effect=results)
    monkeypatch.setattr(recovery, "read_tracking", read)
    rows = [row(item_id=f"item-{i}") for i in range(3)]
    asyncio.run(recovery.recover_tracking(rows, tmp_path))
    assert read.await_count == expected
    assert recovery.asyncio.sleep.await_count == expected
    assert all(5 <= call.args[0] <= 9 for call in recovery.asyncio.sleep.call_args_list)
    assert len(list(tmp_path.rglob("tracking.json"))) == expected
    assert not list(tmp_path.rglob("receipt.json"))


def test_receipt_recovery_keeps_valid_pdf_separates_absence_and_stops_on_refusal(
    tmp_path, monkeypatch
):
    rows = [row(item_id=f"item-{i}") for i in range(4)]
    client = SimpleNamespace(fetch_detail_html=AsyncMock(return_value="detail"))
    read = AsyncMock(
        side_effect=[
            None,
            (b"%PDF-verified", {"kind": "acceptance_receipt"}),
            RuntimeError("HTTP 403"),
        ]
    )
    monkeypatch.setattr(recovery, "read_acceptance_receipt", read)
    asyncio.run(recovery.recover_receipts(client, rows, tmp_path))
    assert client.fetch_detail_html.await_count == 3
    assert json.loads((tmp_path / "item-0/receipt.json").read_text())["available"] is False
    assert (tmp_path / "item-1/acceptance.pdf").read_bytes() == b"%PDF-verified"
    assert json.loads((tmp_path / "item-2/receipt.json").read_text())["error"] == "HTTP 403"
    assert not (tmp_path / "item-3").exists()


def test_receipt_recovery_completes_all_valid_items(tmp_path, monkeypatch):
    rows = [row(item_id=f"item-{i}") for i in range(2)]
    client = SimpleNamespace(fetch_detail_html=AsyncMock(return_value="detail"))
    monkeypatch.setattr(
        recovery,
        "read_acceptance_receipt",
        AsyncMock(return_value=(b"%PDF-verified", {"kind": "acceptance_receipt"})),
    )
    asyncio.run(recovery.recover_receipts(client, rows, tmp_path))
    assert len(list(tmp_path.rglob("acceptance.pdf"))) == 2
    assert len(list(tmp_path.rglob("receipt.json"))) == 2


def test_captcha_stops_tracking_immediately_and_preserves_checkpoint(tmp_path, monkeypatch, fast):
    http = MagicMock()
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(recovery.httpx, "AsyncClient", lambda **_: http)
    read = AsyncMock(side_effect=recovery.InteractiveCheckRequired("CAPTCHA richiesto"))
    monkeypatch.setattr(recovery, "read_tracking", read)
    asyncio.run(recovery.recover_tracking([row(), row(item_id="item-2")], tmp_path))
    assert read.await_count == 1
    assert (
        json.loads((tmp_path / "item-1/tracking.json").read_text())["error"] == "CAPTCHA richiesto"
    )
    assert not (tmp_path / "item-2").exists()


@pytest.fixture
def portal(monkeypatch, db):
    lease = MagicMock()
    credential = SimpleNamespace(username="sender")
    monkeypatch.setattr(recovery, "pick_credential", lambda *_: (credential, "private-password"))
    monkeypatch.setattr(recovery, "acquire_portal_lease", lambda *_: lease)
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.login = AsyncMock()
    configs = []

    def browser(config):
        configs.append(config)
        return client

    monkeypatch.setattr(recovery, "PostaOnlineBrowserClient", browser)
    guard = SimpleNamespace(install_guard=AsyncMock(), phase="login")
    monkeypatch.setattr(recovery, "PostaOnlineDispatchPortal", lambda _: guard)
    read = AsyncMock()
    monkeypatch.setattr(recovery, "recover_receipts", read)
    return lease, credential, client, configs, guard, read


def test_receipt_session_is_pinned_exclusive_fresh_and_read_only(tmp_path, portal):
    lease, _, client, configs, guard, read = portal
    asyncio.run(recovery.recover_account([row()], tmp_path))
    client.login.assert_awaited_once_with("sender", "private-password")
    assert configs[0].max_retries == 0
    assert configs[0].min_delay_ms == 5000 and configs[0].max_delay_ms == 10000
    assert configs[0].include_contacts is False
    assert configs[0].storage_state_path is None and configs[0].cdp_url is None
    guard.install_guard.assert_awaited_once()
    assert guard.phase == "reconcile"
    read.assert_awaited_once_with(client, [row()], tmp_path)
    lease.close.assert_called_once()


def test_account_changes_or_busy_portal_prevent_login(tmp_path, portal, monkeypatch):
    _, credential, client, _, _, _ = portal
    credential.username = "different"
    with pytest.raises(ValueError, match="Account modificato"):
        asyncio.run(recovery.recover_account([row()], tmp_path))
    credential.username = "sender"
    monkeypatch.setattr(recovery, "acquire_portal_lease", lambda *_: None)
    with pytest.raises(RuntimeError, match="occupato"):
        asyncio.run(recovery.recover_account([row()], tmp_path))
    client.login.assert_not_called()


def test_login_failure_releases_lease_without_receipt_requests(tmp_path, portal):
    lease, _, client, _, _, read = portal
    client.login.side_effect = RuntimeError("login failure")
    with pytest.raises(RuntimeError, match="login failure"):
        asyncio.run(recovery.recover_account([row()], tmp_path))
    lease.close.assert_called_once()
    read.assert_not_called()


@pytest.mark.parametrize(
    "phase,account,limit,tracking_calls,receipt_calls",
    [
        ("plan", None, 10, 0, 0),
        ("tracking", None, 1, 1, 0),
        ("receipts", None, 10, 0, 2),
        ("receipts", 2, 10, 0, 1),
        ("receipts", 999, 10, 0, 0),
    ],
)
def test_runner_limits_and_groups_by_original_account(
    tmp_path, monkeypatch, phase, account, limit, tracking_calls, receipt_calls
):
    rows = [row(), row(item_id="item-2", account_id=2)]
    monkeypatch.setattr(recovery, "load_plan", lambda _: rows)
    tracking, receipts = AsyncMock(), AsyncMock()
    monkeypatch.setattr(recovery, "recover_tracking", tracking)
    monkeypatch.setattr(recovery, "recover_account", receipts)
    args = SimpleNamespace(
        output=tmp_path, phase=phase, account=account, limit=limit, retry_errors=False
    )
    asyncio.run(recovery.run(args))
    assert tracking.await_count == tracking_calls
    assert receipts.await_count == receipt_calls
    for call in receipts.call_args_list:
        assert len({r["account_id"] for r in call.args[0]}) == 1


def test_cli_validation_and_entrypoint(tmp_path, monkeypatch, db, capsys):
    monkeypatch.setattr(sys, "argv", ["recovery", "--output", str(tmp_path), "--limit", "0"])
    with pytest.raises(SystemExit):
        recovery.main()
    monkeypatch.setattr(sys, "argv", ["recovery", "--output", str(tmp_path)])
    # The script entrypoint imports SessionLocal afresh; replace only the DB boundary.
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: db)
    recovery.main()
    runpy.run_path(str(Path(recovery.__file__)), run_name="__main__")
    assert capsys.readouterr().out.splitlines() == ['{"planned": 1}', '{"planned": 1}']
    assert json.loads((tmp_path / "plan.json").read_text()) == [row()]
    assert db.rollback.call_count == 2
    db.commit.assert_not_called()


def test_failed_account_does_not_prevent_reading_other_accounts(tmp_path, monkeypatch):
    rows = [row(), row(item_id="item-2", account_id=2)]
    monkeypatch.setattr(recovery, "load_plan", lambda _: rows)
    receipts = AsyncMock(side_effect=[RuntimeError("Login requires attention"), None])
    monkeypatch.setattr(recovery, "recover_account", receipts)
    args = SimpleNamespace(
        output=tmp_path, phase="receipts", account=None, limit=10, retry_errors=False
    )
    asyncio.run(recovery.run(args))
    assert receipts.await_count == 2
    assert (
        json.loads((tmp_path / "account-1-error.json").read_text())["error"]
        == "Login requires attention"
    )
    assert not (tmp_path / "account-2-error.json").exists()


@pytest.mark.parametrize("phase", ["plan", "tracking", "receipts"])
def test_cli_refuses_concurrent_runs_even_across_phases(tmp_path, monkeypatch, db, phase):
    monkeypatch.setattr(sys, "argv", ["recovery", "--output", str(tmp_path), "--phase", phase])
    with (tmp_path / ".recovery.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            recovery.main()
    db.execute.assert_not_called()


@pytest.mark.parametrize("content", [None, b"altered receipt"])
def test_resume_rejects_missing_or_altered_receipt(tmp_path, content):
    recovery.observation(tmp_path, row(), "receipt", available=True, sha256="original-hash")
    if content is not None:
        recovery.private_write(tmp_path / "item-1/acceptance.pdf", content)
    with pytest.raises(ValueError, match="assente o alterata"):
        recovery.pending([row()], tmp_path, "receipt", False)


def test_receipt_end_to_end_persists_verified_pdf_and_resumes_without_network(tmp_path):
    from modules.elaborazioni.worker.tests.test_posta_online_delivery import HTML, pdf_bytes

    content = pdf_bytes()
    response = SimpleNamespace(status=200, body=AsyncMock(return_value=content))
    client = SimpleNamespace(
        fetch_detail_html=AsyncMock(return_value=HTML),
        context=SimpleNamespace(request=SimpleNamespace(post=AsyncMock(return_value=response))),
        throttle=SimpleNamespace(wait=AsyncMock()),
    )
    asyncio.run(recovery.recover_receipts(client, [row()], tmp_path))
    saved = json.loads((tmp_path / "item-1/receipt.json").read_text())
    assert saved["kind"] == "acceptance_receipt" and saved["available"] is True
    assert saved["tracking"] == row()["tracking"] and saved["account_id"] == 1
    assert saved["bytes"] == len(content) and saved["pages"] == 1
    assert (tmp_path / "item-1/acceptance.pdf").read_bytes() == content
    assert (tmp_path / "item-1/acceptance.pdf").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "item-1").stat().st_mode & 0o777 == 0o700
    assert recovery.pending([row()], tmp_path, "receipt", True) == []
    client.context.request.post.assert_awaited_once()
