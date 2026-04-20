import asyncio
from pathlib import Path
import sys


WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from anti_captcha_client import AntiCaptchaClient, AntiCaptchaClientError


def test_anti_captcha_client_polls_until_ready(monkeypatch) -> None:
    responses = iter(
        [
            {"errorId": 0, "taskId": 321},
            {"errorId": 0, "status": "processing"},
            {"errorId": 0, "status": "ready", "solution": {"text": " ab-12 \n"}},
        ]
    )

    def fake_post_json(_method: str, _payload: dict) -> dict:
        return next(responses)

    client = AntiCaptchaClient("test-key", poll_interval_sec=0, timeout_sec=1)
    monkeypatch.setattr(client, "_post_json", fake_post_json)

    result = asyncio.run(client.solve_image_to_text(b"fake-image"))

    assert result == "AB12"


def test_anti_captcha_client_raises_api_errors(monkeypatch) -> None:
    def fake_post_json(_method: str, _payload: dict) -> dict:
        raise AntiCaptchaClientError("ERROR_ZERO_BALANCE: Account balance is zero")

    client = AntiCaptchaClient("test-key")
    monkeypatch.setattr(client, "_post_json", fake_post_json)

    try:
        asyncio.run(client.solve_image_to_text(b"fake-image"))
    except AntiCaptchaClientError as exc:
        assert "ERROR_ZERO_BALANCE" in str(exc)
    else:
        raise AssertionError("Expected AntiCaptchaClientError")
