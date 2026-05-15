from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path


logger = logging.getLogger(__name__)

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

        normalized = "".join(ch for ch in str(raw) if ch.isalnum())
        logger.info("LLM CAPTCHA solver raw=%r normalized=%r", raw, normalized)
        return normalized or None
