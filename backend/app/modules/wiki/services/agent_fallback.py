"""Fallback locale del Wiki tramite CLI `agent` installata sul server."""

from __future__ import annotations

import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "on"}


class AgentFallbackError(RuntimeError):
    """Errore durante l'uso del fallback locale `agent`."""


def _get_env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


def is_agent_fallback_enabled() -> bool:
    return _get_env_flag("WIKI_AGENT_FALLBACK_ENABLED", default=False)


def _agent_cli_path() -> str:
    return os.getenv("WIKI_AGENT_CLI_PATH", "agent")


def _agent_home() -> str | None:
    value = os.getenv("WIKI_AGENT_HOME")
    return value or None


def _agent_workspace() -> str:
    return os.getenv("WIKI_AGENT_WORKSPACE", "/app/docs")


def _agent_timeout_seconds() -> float:
    raw = os.getenv("WIKI_AGENT_TIMEOUT_SECONDS", "45")
    try:
        timeout = float(raw)
    except ValueError:
        return 45.0
    return timeout if timeout > 0 else 45.0


def _agent_model() -> str | None:
    value = os.getenv("WIKI_AGENT_MODEL")
    return value or None


def build_agent_fallback_prompt(*, question: str, context: str, system_prompt: str) -> str:
    return (
        f"{system_prompt}\n\n"
        "Lavora solo sul contesto documentale fornito. Se il contesto non basta, dillo chiaramente "
        "senza inventare dettagli. Rispondi direttamente all'utente in tono operativo e sintetico. "
        "Non dire che stai verificando, controllando o cercando altro. "
        "Non citare workspace, file, documenti caricati, strumenti usati, prompt, contesto fornito o limiti implementativi interni. "
        "Non descrivere il tuo processo di ragionamento.\n\n"
        f"Contesto documentale:\n{context}\n\n"
        f"Domanda: {question}"
    )


def _build_agent_command(prompt: str) -> list[str]:
    command = [
        _agent_cli_path(),
        "-p",
        "--output-format",
        "json",
        "--mode",
        "ask",
        "--trust",
        "--workspace",
        _agent_workspace(),
        prompt,
    ]
    model = _agent_model()
    if model:
        command[1:1] = ["--model", model]
    return command


def _build_agent_env() -> dict[str, str]:
    env = os.environ.copy()
    home = _agent_home()
    if home:
        env["HOME"] = home
    return env


def _extract_agent_result(stdout: str) -> str:
    stripped = stdout.strip()
    if not stripped:
        raise AgentFallbackError("agent non ha restituito alcun contenuto")

    for line in reversed(stripped.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("type") != "result":
            continue
        if payload.get("is_error") is True:
            raise AgentFallbackError(str(payload.get("result") or "agent ha restituito un errore"))
        result = payload.get("result")
        if isinstance(result, str) and result.strip():
            return result.strip()

    return stripped


def answer_with_agent_fallback(*, question: str, context: str, system_prompt: str) -> str:
    if not is_agent_fallback_enabled():
        raise AgentFallbackError("fallback agent disabilitato")

    prompt = build_agent_fallback_prompt(question=question, context=context, system_prompt=system_prompt)
    command = _build_agent_command(prompt)
    logger.info("Wiki agent fallback start cli=%s workspace=%s", command[0], _agent_workspace())
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=_agent_timeout_seconds(),
            env=_build_agent_env(),
        )
    except FileNotFoundError as exc:
        raise AgentFallbackError(f"CLI agent non trovata: {_agent_cli_path()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise AgentFallbackError("timeout del fallback agent") from exc
    except OSError as exc:
        raise AgentFallbackError(f"impossibile avviare agent: {exc}") from exc

    if completed.returncode != 0:
        error_text = (completed.stderr or completed.stdout).strip() or f"exit code {completed.returncode}"
        raise AgentFallbackError(f"agent ha fallito: {error_text}")

    return _extract_agent_result(completed.stdout)
