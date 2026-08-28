from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import anti_captcha_client
import pytest
import reporting
import runtime_policy
from credential_vault import WorkerCredentialVault
from cryptography.fernet import Fernet
from sister_browser_reliability import _is_non_blocking_init_portale_error


def run(coro):
    return asyncio.run(coro)


def test_credential_vault_round_trip() -> None:
    key = Fernet.generate_key()
    encrypted = Fernet(key).encrypt(b"secret")

    assert WorkerCredentialVault(key.decode()).decrypt(encrypted) == "secret"


def test_runtime_policy_covers_retryable_and_terminal_statuses() -> None:
    assert runtime_policy.can_retry_request_status("failed") is True
    assert runtime_policy.can_retry_request_status("completed") is False
    for status in ("completed", "failed", "skipped", "not_found", "non_evadibile"):
        assert runtime_policy.classify_terminal_status(f" {status.upper()} ") == status
    assert runtime_policy.classify_terminal_status("") == "failed"
    assert runtime_policy.classify_terminal_status("unexpected") == "failed"


def _request(**overrides):
    values = {
        "id": uuid.uuid4(),
        "row_index": 1,
        "search_mode": "immobile",
        "comune": "ROMA",
        "foglio": "1",
        "particella": "2",
        "subalterno": "3",
        "status": "completed",
        "current_operation": "done",
        "error_message": None,
        "attempts": 2,
        "artifact_dir": "/tmp/artifact",
        "document_id": uuid.uuid4(),
        "processed_at": datetime(2026, 8, 27, tzinfo=timezone.utc),
        "subject_kind": None,
        "subject_id": None,
        "request_type": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_reporting_writes_json_markdown_and_both_label_types(tmp_path) -> None:
    batch = SimpleNamespace(id=uuid.uuid4(), name="Batch", status="completed")
    requests = [
        _request(),
        _request(
            search_mode="soggetto",
            status="failed",
            subject_kind="PF",
            subject_id="RSSMRA",
            request_type="storica",
            artifact_dir=None,
            error_message="boom",
            document_id=None,
            processed_at=None,
        ),
        _request(
            status="skipped",
            comune=None,
            foglio=None,
            particella=None,
            subalterno=None,
        ),
        _request(
            search_mode="soggetto",
            status="not_found",
            subject_kind=None,
            subject_id=None,
            request_type=None,
        ),
    ]

    json_path, markdown_path = reporting.write_batch_report(batch, requests, tmp_path / "reports")

    payload = json.loads(json_path.read_text())
    assert payload["completed"] == 1
    assert payload["failed"] == 1
    assert payload["skipped"] == 1
    assert payload["not_found"] == 1
    assert payload["requests"][0]["label"] == "ROMA Fg.1 Part.2/3"
    assert payload["requests"][1]["label"] == "PF RSSMRA (storica)"
    assert payload["requests"][2]["label"] == "- Fg.- Part.-"
    assert payload["requests"][3]["label"] == "SOGGETTO - (-)"
    assert "error=boom" in markdown_path.read_text()


def test_anti_captcha_disabled_unexpected_missing_solution_and_timeout(monkeypatch) -> None:
    assert run(anti_captcha_client.AntiCaptchaClient(" ").solve_image_to_text(b"image")) is None

    client = anti_captcha_client.AntiCaptchaClient("key", timeout_sec=1)
    monkeypatch.setattr(client, "_create_image_to_text_task", lambda _image: 1)
    monkeypatch.setattr(client, "_get_task_result", lambda _task: {"status": "unexpected"})
    with pytest.raises(anti_captcha_client.AntiCaptchaClientError, match="Unexpected"):
        run(client.solve_image_to_text(b"image"))

    monkeypatch.setattr(client, "_get_task_result", lambda _task: {"status": "ready", "solution": {}})
    assert run(client.solve_image_to_text(b"image")) is None
    monkeypatch.setattr(
        client,
        "_get_task_result",
        lambda _task: {"status": "ready", "solution": {"text": "---"}},
    )
    assert run(client.solve_image_to_text(b"image")) is None

    results = iter(
        (
            {"status": "processing"},
            {"status": "ready", "solution": {"text": " ab-12 "}},
        )
    )
    monkeypatch.setattr(client, "_get_task_result", lambda _task: next(results))
    original_sleep = asyncio.sleep
    monkeypatch.setattr(
        anti_captcha_client.asyncio,
        "sleep",
        lambda _seconds: original_sleep(0),
    )
    assert run(client.solve_image_to_text(b"image")) == "AB12"

    client.timeout_sec = -1
    with pytest.raises(anti_captcha_client.AntiCaptchaClientError, match="timeout"):
        run(client.solve_image_to_text(b"image"))


def test_anti_captcha_create_and_http_response_branches(monkeypatch) -> None:
    client = anti_captcha_client.AntiCaptchaClient("key")
    monkeypatch.setattr(client, "_post_json", lambda *_args: {})
    with pytest.raises(anti_captcha_client.AntiCaptchaClientError, match="missing taskId"):
        client._create_image_to_text_task(b"image")

    monkeypatch.setattr(client, "_post_json", lambda method, payload: {"taskId": 7})
    assert client._create_image_to_text_task(b"image") == 7
    assert client._get_task_result(7) == {"taskId": 7}

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(self.payload).encode()

    http_client = anti_captcha_client.AntiCaptchaClient("key")
    monkeypatch.setattr(
        anti_captcha_client.urllib_request,
        "urlopen",
        lambda request, timeout: Response({"errorId": 0, "taskId": 9}),
    )
    assert http_client._post_json("createTask", {"x": 1})["taskId"] == 9

    monkeypatch.setattr(
        anti_captcha_client.urllib_request,
        "urlopen",
        lambda request, timeout: Response(
            {"errorId": 1, "errorCode": "BAD", "errorDescription": "broken"}
        ),
    )
    with pytest.raises(anti_captcha_client.AntiCaptchaClientError, match="BAD: broken"):
        http_client._post_json("createTask", {})


def test_init_portale_validation_handles_page_read_failure() -> None:
    class WrongPage:
        url = "https://example.test/not-sister"

    assert (
        run(
            _is_non_blocking_init_portale_error(
                WrongPage(),
                501,
                "https://sister/portale-rest/rs/initPortale",
            )
        )
        is False
    )

    class Page:
        url = "https://sister3.agenziaentrate.gov.it/Servizi/home"

        async def title(self):
            raise RuntimeError("broken page")

        def locator(self, _selector):
            raise AssertionError("locator must not be reached")

    assert (
        run(
            _is_non_blocking_init_portale_error(
                Page(),
                501,
                "https://sister/portale-rest/rs/initPortale",
            )
        )
        is False
    )
