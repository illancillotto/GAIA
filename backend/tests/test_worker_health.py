from __future__ import annotations

import asyncio
import json
import runpy
from pathlib import Path

import pytest
from app import worker_health


@pytest.fixture(autouse=True)
def health_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("GAIA_WORKER_HEALTH_DIR", str(tmp_path))
    return tmp_path


def test_heartbeat_writes_atomic_payload_and_merges_details(
    health_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(worker_health.time, "time", lambda: 1_700_000_000.0)
    monkeypatch.setattr(worker_health.os, "getpid", lambda: 1234)
    heartbeat = worker_health.WorkerHeartbeat(
        "Example-Worker",
        details={"family": "runtime", "shared": "base"},
    )

    heartbeat.touch(status="waiting", details={"shared": "cycle", "jobs": 2})

    payload = json.loads((health_directory / "example-worker.json").read_text())
    assert payload == {
        "details": {"family": "runtime", "jobs": 2, "shared": "cycle"},
        "pid": 1234,
        "schema_version": 1,
        "service": "example-worker",
        "status": "waiting",
        "updated_at": "2023-11-14T22:13:20+00:00",
        "updated_at_epoch": 1_700_000_000.0,
    }
    assert list(health_directory.glob("*.tmp")) == []
    assert worker_health.check_heartbeat(
        "example-worker",
        max_age_seconds=10,
        now=1_700_000_005.0,
    ) == payload


@pytest.mark.parametrize("service", ("", "bad_name", "UPPER SPACE", "a" * 129))
def test_heartbeat_rejects_invalid_service_names(service: str) -> None:
    with pytest.raises(ValueError, match="Invalid worker heartbeat service name"):
        worker_health.WorkerHeartbeat(service)


def test_check_rejects_non_positive_max_age() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        worker_health.check_heartbeat("worker", max_age_seconds=0)


@pytest.mark.parametrize(
    ("raw_payload", "message"),
    (
        ("not-json", "Heartbeat unavailable"),
        ("[]", "is not an object"),
        ('{"schema_version": 2}', "schema mismatch"),
        ('{"schema_version": 1, "service": "other"}', "service mismatch"),
        ('{"schema_version": 1, "service": "worker", "status": ""}', "status missing"),
        (
            (
                '{"schema_version": 1, "service": "worker", "status": "ok", '
                '"updated_at_epoch": true}'
            ),
            "timestamp invalid",
        ),
    ),
)
def test_check_rejects_missing_or_malformed_payloads(
    health_directory: Path,
    raw_payload: str,
    message: str,
) -> None:
    (health_directory / "worker.json").write_text(raw_payload)

    with pytest.raises(worker_health.HeartbeatError, match=message):
        worker_health.check_heartbeat("worker", max_age_seconds=10, now=100)


def test_check_rejects_missing_future_and_stale_heartbeats(health_directory: Path) -> None:
    with pytest.raises(worker_health.HeartbeatError, match="unavailable"):
        worker_health.check_heartbeat("missing", max_age_seconds=10, now=100)

    payload = {
        "schema_version": 1,
        "service": "worker",
        "status": "running",
        "updated_at": "unused",
        "updated_at_epoch": 200.0,
    }
    path = health_directory / "worker.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(worker_health.HeartbeatError, match="in the future"):
        worker_health.check_heartbeat("worker", max_age_seconds=10, now=100)

    payload["updated_at_epoch"] = 50.0
    path.write_text(json.dumps(payload))
    with pytest.raises(worker_health.HeartbeatError, match="stale"):
        worker_health.check_heartbeat("worker", max_age_seconds=10, now=100)


def test_check_uses_system_clock_when_now_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    heartbeat = worker_health.WorkerHeartbeat("worker")
    monkeypatch.setattr(worker_health.time, "time", lambda: 100.0)
    heartbeat.touch()

    assert worker_health.check_heartbeat("worker", max_age_seconds=1)["status"] == "running"


def test_cli_reports_healthy_and_unhealthy_heartbeat(
    capsys: pytest.CaptureFixture[str],
) -> None:
    worker_health.WorkerHeartbeat("worker").touch()

    assert worker_health.main(["check", "--service", "worker", "--max-age-seconds", "90"]) == 0
    assert "heartbeat ok service=worker" in capsys.readouterr().out

    assert worker_health.main(["check", "--service", "missing", "--max-age-seconds", "90"]) == 1
    assert "Heartbeat unavailable" in capsys.readouterr().err


@pytest.mark.anyio
async def test_run_with_heartbeat_pulses_and_returns_result() -> None:
    calls: list[str] = []
    pulsed = asyncio.Event()

    class FakeHeartbeat:
        def touch(self) -> None:
            calls.append("touch")
            if len(calls) == 2:
                pulsed.set()

    async def operation() -> str:
        await pulsed.wait()
        return "result"

    assert (
        await worker_health.run_with_heartbeat(
            operation(),
            FakeHeartbeat(),  # type: ignore[arg-type]
            interval_seconds=0.001,
        )
        == "result"
    )
    assert calls == ["touch", "touch"]


@pytest.mark.anyio
async def test_run_with_heartbeat_rejects_invalid_interval() -> None:
    operation = asyncio.sleep(0)
    with pytest.raises(ValueError, match="interval_seconds must be positive"):
        await worker_health.run_with_heartbeat(
            operation,
            worker_health.WorkerHeartbeat("worker"),
            interval_seconds=0,
        )
    operation.close()


def test_module_main_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    worker_health.WorkerHeartbeat("guard-worker").touch()
    monkeypatch.setattr(
        worker_health.sys,
        "argv",
        [
            "worker_health.py",
            "check",
            "--service",
            "guard-worker",
            "--max-age-seconds",
            "90",
        ],
    )
    with pytest.raises(SystemExit, match="0"):
        runpy.run_module("app.worker_health", run_name="__main__")
