from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any
from urllib import request as urllib_request


ANTI_CAPTCHA_API_BASE_URL = "https://api.anti-captcha.com"


class AntiCaptchaClientError(RuntimeError):
    pass


class AntiCaptchaClient:
    def __init__(
        self,
        api_key: str,
        poll_interval_sec: int = 3,
        timeout_sec: int = 120,
    ) -> None:
        self.api_key = api_key.strip()
        self.poll_interval_sec = poll_interval_sec
        self.timeout_sec = timeout_sec

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def solve_image_to_text(self, image_bytes: bytes) -> str | None:
        if not self.enabled:
            return None

        task_id = await asyncio.to_thread(self._create_image_to_text_task, image_bytes)
        deadline = time.monotonic() + self.timeout_sec

        while time.monotonic() < deadline:
            result = await asyncio.to_thread(self._get_task_result, task_id)
            status = result.get("status")
            if status == "processing":
                await asyncio.sleep(self.poll_interval_sec)
                continue
            if status != "ready":
                raise AntiCaptchaClientError(f"Unexpected Anti-Captcha task status: {status}")

            solution = result.get("solution") or {}
            text = solution.get("text")
            if not isinstance(text, str):
                return None
            normalized = "".join(char for char in text.upper() if char.isalnum())
            return normalized or None

        raise AntiCaptchaClientError("Anti-Captcha task result timeout")

    def _create_image_to_text_task(self, image_bytes: bytes) -> int:
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "ImageToTextTask",
                "body": base64.b64encode(image_bytes).decode("ascii"),
                "phrase": False,
                "case": False,
                "numeric": 0,
                "math": False,
                "minLength": 0,
                "maxLength": 0,
            },
        }
        response = self._post_json("createTask", payload)
        task_id = response.get("taskId")
        if not isinstance(task_id, int):
            raise AntiCaptchaClientError("Anti-Captcha createTask response missing taskId")
        return task_id

    def _get_task_result(self, task_id: int) -> dict[str, Any]:
        return self._post_json(
            "getTaskResult",
            {
                "clientKey": self.api_key,
                "taskId": task_id,
            },
        )

    def _post_json(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib_request.Request(
            f"{ANTI_CAPTCHA_API_BASE_URL}/{method}",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(http_request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))

        if parsed.get("errorId") != 0:
            raise AntiCaptchaClientError(
                f"{parsed.get('errorCode', 'ANTI_CAPTCHA_ERROR')}: {parsed.get('errorDescription', 'Unknown error')}"
            )
        return parsed
