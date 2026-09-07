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

from captcha_result import CaptchaSolveResult

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
_REFUSAL_RE = re.compile(
    r"mi dispiace|non posso|non sono in grado|cannot|can't|can not|unable|i'?m sorry|"
    r"i can'?t|non aiut|no puedo",
    re.IGNORECASE,
)
_PROVIDER_ERROR_RE = re.compile(
    r"quota|rate.?limit|usage.?limit|token.?limit|insufficient|exhausted|"
    r"unauthorized|not authenticated|authentication|failed|error|timed out|"
    r"upgrade your|limit reached|limit exceeded",
    re.IGNORECASE,
)

_PROMPT_TEMPLATE = (
    "Trascrivi esattamente il testo che vedi in questa immagine. "
    "Rispondi SOLO con i caratteri esatti, rispettando maiuscole/minuscole, "
    "senza spazi né spiegazioni: {image_path}"
)


class LLMCaptchaSolver:
    def __init__(self, agent_cmd: str = "agent") -> None:
        self._agent_cmd = agent_cmd
        # Esito dell'ultima chiamata a solve()/solve_from_path(). Il worker lo
        # legge per costruire un messaggio d'errore visura specifico. Le chiamate
        # sono sequenziali (un tentativo per volta), quindi un attributo va bene.
        self.last_result: CaptchaSolveResult = CaptchaSolveResult(None, "no_answer", "none")

    def _record(self, text: str | None, reason: str, provider: str, detail: str = "") -> str | None:
        self.last_result = CaptchaSolveResult(text or None, reason, provider, detail)
        return text or None

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
            return self._record(None, "codex_lb_disabled", "codex-lb")
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
                if response.status_code >= 400:
                    return self._record(
                        None, "codex_lb_http_error", "codex-lb",
                        f"HTTP {response.status_code} {self._upstream_error_code(response)}".strip(),
                    )
                text, reason, detail = self._codex_outcome(response.json())
                return self._record(text, reason if not text else "solved", "codex-lb", detail or model)
        except asyncio.CancelledError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            logger.warning("LLM CAPTCHA solver: fallback codex-lb timeout (%ss)", timeout)
            return self._record(None, "codex_lb_timeout", "codex-lb", f"{timeout}s")
        except httpx.ConnectError as exc:
            logger.warning("LLM CAPTCHA solver: fallback codex-lb non raggiungibile (%s)", exc)
            return self._record(None, "codex_lb_connect_error", "codex-lb", url)
        except Exception as exc:
            logger.warning("LLM CAPTCHA solver: fallback codex-lb fallito (%s)", type(exc).__name__)
            return self._record(None, "codex_lb_error", "codex-lb", type(exc).__name__)

    @staticmethod
    def _upstream_error_code(response: httpx.Response) -> str:
        try:
            body = response.json()
        except Exception:
            return ""
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            return str(error.get("code") or error.get("type") or "")
        return ""

    @classmethod
    def _codex_outcome(cls, payload: dict) -> tuple[str | None, str, str]:
        """Ritorna (testo, reason, detail) per una risposta codex-lb 200."""
        if payload.get("error"):
            error = payload["error"]
            code = error.get("code") if isinstance(error, dict) else None
            return None, "codex_lb_api_error", str(code or error)[:80]
        if payload.get("status") != "completed":
            return None, "codex_lb_api_error", f"status={payload.get('status')}"
        texts = [
            part.get("text", "").strip()
            for item in payload.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        ]
        texts = [text for text in texts if text]
        if not texts:
            return None, "codex_lb_no_answer", ""
        for text in texts:
            if _TOKEN_RE.fullmatch(text):
                return text, "solved", ""
        joined = " ".join(texts)
        if _REFUSAL_RE.search(joined):
            return None, "codex_lb_refusal", ""
        return None, "codex_lb_unparseable", joined[:60]

    @classmethod
    def _codex_candidate(cls, payload: dict) -> str | None:
        return cls._codex_outcome(payload)[0]

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
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("LLM CAPTCHA solver: impossibile avviare il processo agent")
            return await self._codex_fallback(image_path, "agent_unavailable")

        if proc.returncode != 0:
            logger.warning(
                "LLM CAPTCHA solver: agent ha restituito codice %s — stderr: %s",
                proc.returncode,
                stderr.decode(errors="replace")[:200],
            )
            return await self._codex_fallback(image_path, "agent_exit_error", f"code {proc.returncode}")

        raw = self._decode_agent_stdout(stdout)
        if _PROVIDER_ERROR_RE.search(raw):
            return await self._codex_fallback(image_path, "agent_provider_error")

        candidate = self._extract_candidate(str(raw))
        if candidate:
            return self._record(candidate, "solved", "agent")
        return await self._codex_fallback(image_path, "agent_no_candidate")

    async def _codex_fallback(self, image_path: Path, agent_reason: str, agent_detail: str = "") -> str | None:
        """Prova codex-lb; se è disattivato riporta il motivo del fallimento Agent."""
        text = await self._run_codex_lb(image_path)
        if text is None and self.last_result.reason == "codex_lb_disabled":
            return self._record(None, agent_reason, "agent", agent_detail)
        return text

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
