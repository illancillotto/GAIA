from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from pathlib import Path

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
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
        except Exception:
            logger.exception("LLM CAPTCHA solver: impossibile avviare il processo agent")
            return None

        if proc.returncode != 0:
            logger.warning(
                "LLM CAPTCHA solver: agent ha restituito codice %s — stderr: %s",
                proc.returncode,
                stderr.decode(errors="replace")[:200],
            )
            return None

        raw = self._decode_agent_stdout(stdout)

        normalized = self._extract_candidate(str(raw))
        logger.info("LLM CAPTCHA solver raw=%r normalized=%r", raw, normalized)
        return normalized or None

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
        if isinstance(data, dict):
            return str(data.get("result") or data.get("text") or data.get("message") or "")
        return str(data)

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
