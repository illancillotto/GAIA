from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import math
import os
import re
import signal
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_EXPLANATION_MARKERS = {
    "captcha",
    "caratteri",
    "character",
    "characters",
    "rispondi",
    "risposta",
    "rispondo",
    "testo",
    "immagine",
    "image",
    "leggo",
    "vedo",
    "restituisco",
    "solo",
    "exact",
    "esatti",
    "esatto",
}
_TOKEN_RE = re.compile(r"[A-Za-z0-9]{4,12}")
_PROVIDER_ERROR_RE = re.compile(
    r"quota|rate.?limit|usage.?limit|token.?limit|insufficient|exhausted|"
    r"unauthorized|not authenticated|authentication|failed|error|timed out|"
    r"upgrade your|limit reached|limit exceeded",
    re.IGNORECASE,
)

_PROMPT_TEMPLATE = (
    "Leggi con attenzione il testo CAPTCHA in questa immagine. "
    "Rispondi SOLO con i caratteri esatti che vedi, rispettando maiuscole/minuscole, "
    "senza spazi né spiegazioni: {image_path}"
)


class LLMCaptchaSolver:
    def __init__(self, agent_cmd: str = "agent") -> None:
        self._agent_cmd = agent_cmd

    async def solve(self, image_bytes: bytes) -> str | None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = Path(tmp.name)

        try:
            return await self._run_agent(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    async def solve_from_path(self, image_path: Path) -> str | None:
        return await self._run_agent(image_path)

    @staticmethod
    def _timeout(name: str) -> float:
        try:
            value = float(os.getenv(name, "45"))
        except ValueError:
            return 45.0
        return value if math.isfinite(value) and value > 0 else 45.0

    @staticmethod
    async def _communicate_agent(proc: asyncio.subprocess.Process) -> tuple[bytes, bytes]:
        try:
            return await asyncio.wait_for(
                proc.communicate(), LLMCaptchaSolver._timeout("CAPTCHA_LLM_AGENT_TIMEOUT_SECONDS")
            )
        except BaseException:
            # Children may hold stdout open even after the CLI parent has exited.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            await proc.communicate()
            raise

    async def _run_codex_lb(self, image_path: Path) -> str | None:
        enabled = os.getenv("CAPTCHA_CODEX_LB_FALLBACK_ENABLED", "true").strip().lower()
        api_key = os.getenv("CAPTCHA_CODEX_LB_API_KEY") or os.getenv("CODEX_LB_API_KEY")
        if enabled not in {"true", "1", "yes", "on"} or not api_key:
            return None
        url = os.getenv("CAPTCHA_CODEX_LB_URL") or os.getenv("CODEX_LB_URL", "http://127.0.0.1:2455/v1")
        model = os.getenv("CAPTCHA_CODEX_LB_MODEL", "gpt-5.4-mini")
        timeout = self._timeout("CAPTCHA_CODEX_LB_TIMEOUT_SECONDS")
        logger.info("LLM CAPTCHA solver: fallback codex-lb model=%s", model)
        try:
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            payload = {
                "model": model,
                "reasoning": {"effort": "low"},
                "store": False,
                "stream": False,
                "input": [{"role": "user", "content": [
                    {"type": "input_text", "text": _PROMPT_TEMPLATE.format(image_path="immagine allegata")},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{encoded}", "detail": "high"},
                ]}],
            }
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await asyncio.wait_for(
                    client.post(
                        url.rstrip("/") + "/responses",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json=payload,
                    ),
                    timeout=timeout,
                )
                response.raise_for_status()
                return self._codex_candidate(response.json())
        except Exception as exc:
            logger.warning("LLM CAPTCHA solver: fallback codex-lb fallito (%s)", type(exc).__name__)
            return None

    @staticmethod
    def _codex_candidate(payload: dict) -> str | None:
        if payload.get("error") or payload.get("status") != "completed":
            return None
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if part.get("type") != "output_text":
                    continue
                text = part.get("text", "").strip()
                if _TOKEN_RE.fullmatch(text):
                    return text
        return None

    async def _run_agent(self, image_path: Path) -> str | None:
        prompt = _PROMPT_TEMPLATE.format(image_path=image_path)
        env = self._agent_environment()
        try:
            proc = await asyncio.create_subprocess_exec(
                self._agent_cmd,
                "--print",
                "--trust",
                "--mode", "ask",
                "--model", os.getenv("CAPTCHA_LLM_AGENT_MODEL", "auto"),
                "--output-format", os.getenv("CAPTCHA_LLM_AGENT_OUTPUT_FORMAT", "text"),
                prompt,
                env=env,
                start_new_session=True,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await self._communicate_agent(proc)
        except Exception:
            logger.exception("LLM CAPTCHA solver: impossibile avviare il processo agent")
            return await self._run_codex_lb(image_path)

        if proc.returncode != 0:
            logger.warning(
                "LLM CAPTCHA solver: agent ha restituito codice %s — stderr: %s",
                proc.returncode,
                stderr.decode(errors="replace")[:200],
            )
            return await self._run_codex_lb(image_path)

        raw = self._decode_agent_stdout(stdout)
        if _PROVIDER_ERROR_RE.search(raw):
            return await self._run_codex_lb(image_path)
        return self._extract_candidate(str(raw)) or await self._run_codex_lb(image_path)

    @staticmethod
    def _agent_environment() -> dict[str, str]:
        env = os.environ.copy()
        token_file = env.get("CURSOR_AUTH_TOKEN_FILE", "").strip()
        if token_file and not env.get("CURSOR_AUTH_TOKEN"):
            try:
                data = json.loads(Path(token_file).read_text())
                token = str(data.get("accessToken") or data.get("refreshToken") or "").strip()
            except Exception:
                logger.exception("LLM CAPTCHA solver: impossibile leggere CURSOR_AUTH_TOKEN_FILE")
                token = ""
            if token:
                env["CURSOR_AUTH_TOKEN"] = token
        return env

    @staticmethod
    def _decode_agent_stdout(stdout: bytes) -> str:
        text = stdout.decode(errors="replace").strip()
        if not text:
            return ""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text
        if not isinstance(data, dict):
            return str(data)
        if data.get("is_error") or data.get("type") == "error":
            return ""
        for key in ("result", "text", "message"):
            if data.get(key):
                return str(data[key])
        return ""

    @staticmethod
    def _extract_candidate(raw: str) -> str | None:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        for line in reversed(lines):
            tokens = _TOKEN_RE.findall(line)
            if not tokens:
                continue
            line_words = {word.lower() for word in re.findall(r"[A-Za-z]+", line)}
            if line_words & _EXPLANATION_MARKERS:
                continue
            compact_line = "".join(ch for ch in line if ch.isalnum())
            if 4 <= len(compact_line) <= 12:
                return compact_line
            return tokens[-1]

        raw_words = {word.lower() for word in re.findall(r"[A-Za-z]+", raw)}
        compact = "".join(ch for ch in raw if ch.isalnum())
        if 4 <= len(compact) <= 12 and not (raw_words & _EXPLANATION_MARKERS):
            return compact
        return None
