from __future__ import annotations

import asyncio
import json
import logging
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
        try:
            proc = await asyncio.create_subprocess_exec(
                self._agent_cmd,
                "--print",
                "--trust",
                "--output-format", "json",
                prompt,
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

        try:
            data = json.loads(stdout.decode())
            raw = data.get("result", "")
        except Exception:
            logger.warning("LLM CAPTCHA solver: risposta non JSON — stdout: %s", stdout[:200])
            return None

        normalized = self._extract_candidate(str(raw))
        logger.info("LLM CAPTCHA solver raw=%r normalized=%r", raw, normalized)
        return normalized or None

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
            candidate = tokens[-1]
            if 4 <= len(candidate) <= 12:
                return candidate

        raw_words = {word.lower() for word in re.findall(r"[A-Za-z]+", raw)}
        quoted_tokens = _TOKEN_RE.findall(raw)
        if quoted_tokens and not (raw_words & _EXPLANATION_MARKERS):
            candidate = quoted_tokens[-1]
            if 4 <= len(candidate) <= 12:
                return candidate

        compact = "".join(ch for ch in raw if ch.isalnum())
        if 4 <= len(compact) <= 12 and not (raw_words & _EXPLANATION_MARKERS):
            return compact
        return None
