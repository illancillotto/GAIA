from __future__ import annotations

import importlib
import subprocess
from types import SimpleNamespace

import pytest


@pytest.fixture
def fallback_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("WIKI_AGENT_FALLBACK_ENABLED", raising=False)
    monkeypatch.delenv("WIKI_AGENT_CLI_PATH", raising=False)
    monkeypatch.delenv("WIKI_AGENT_HOME", raising=False)
    monkeypatch.delenv("WIKI_AGENT_WORKSPACE", raising=False)
    monkeypatch.delenv("WIKI_AGENT_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("WIKI_AGENT_MODEL", raising=False)

    module = importlib.import_module("app.modules.wiki.services.agent_fallback")
    return importlib.reload(module)


def test_is_agent_fallback_enabled_reads_env(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")

    assert fallback_module.is_agent_fallback_enabled() is True


def test_build_agent_fallback_prompt_includes_question_and_context(fallback_module) -> None:
    prompt = fallback_module.build_agent_fallback_prompt(
        question="Come funziona?",
        context="Contesto di prova",
        system_prompt="Prompt sistema",
    )

    assert "Prompt sistema" in prompt
    assert "Contesto di prova" in prompt
    assert "Come funziona?" in prompt
    assert "Non citare workspace" in prompt
    assert "Non dire che stai verificando" in prompt


def test_answer_with_agent_fallback_returns_json_result(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "1")
    monkeypatch.setenv("WIKI_AGENT_CLI_PATH", "/tmp/agent")
    monkeypatch.setenv("WIKI_AGENT_HOME", "/tmp/home")
    monkeypatch.setenv("WIKI_AGENT_WORKSPACE", "/tmp/workspace")
    monkeypatch.setenv("WIKI_AGENT_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("WIKI_AGENT_MODEL", "gpt-test")

    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout='{"type":"result","is_error":false,"result":"Risposta agent"}\n', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    answer = fallback_module.answer_with_agent_fallback(
        question="Domanda",
        context="Contesto",
        system_prompt="Sistema",
    )

    assert answer == "Risposta agent"
    command = captured["command"]
    assert command[:11] == [
        "/tmp/agent",
        "--model",
        "gpt-test",
        "-p",
        "--output-format",
        "json",
        "--mode",
        "ask",
        "--trust",
        "--workspace",
        "/tmp/workspace",
    ]
    assert isinstance(command[11], str)
    assert "Domanda" in command[11]
    assert "Contesto" in command[11]
    assert captured["kwargs"]["timeout"] == 12.0
    assert captured["kwargs"]["env"]["HOME"] == "/tmp/home"


def test_answer_with_agent_fallback_returns_raw_stdout_when_not_json(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="Risposta testuale", stderr=""),
    )

    answer = fallback_module.answer_with_agent_fallback(
        question="Domanda",
        context="Contesto",
        system_prompt="Sistema",
    )

    assert answer == "Risposta testuale"


def test_answer_with_agent_fallback_ignores_non_result_json_lines(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout='{"type":"log","message":"step"}\n{"type":"result","is_error":false,"result":"Risposta finale"}\n',
            stderr="",
        ),
    )

    answer = fallback_module.answer_with_agent_fallback(
        question="Domanda",
        context="Contesto",
        system_prompt="Sistema",
    )

    assert answer == "Risposta finale"


def test_answer_with_agent_fallback_skips_non_dict_json_payload(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='["step"]', stderr=""),
    )

    answer = fallback_module.answer_with_agent_fallback(
        question="Domanda",
        context="Contesto",
        system_prompt="Sistema",
    )

    assert answer == '["step"]'


def test_answer_with_agent_fallback_skips_non_result_json_payload_type(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{"type":"log","message":"step"}', stderr=""),
    )

    answer = fallback_module.answer_with_agent_fallback(
        question="Domanda",
        context="Contesto",
        system_prompt="Sistema",
    )

    assert answer == '{"type":"log","message":"step"}'


def test_answer_with_agent_fallback_raises_when_disabled(fallback_module) -> None:
    with pytest.raises(fallback_module.AgentFallbackError, match="disabilitato"):
        fallback_module.answer_with_agent_fallback(
            question="Domanda",
            context="Contesto",
            system_prompt="Sistema",
        )


def test_answer_with_agent_fallback_raises_on_non_zero_exit(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout="", stderr="boom"),
    )

    with pytest.raises(fallback_module.AgentFallbackError, match="boom"):
        fallback_module.answer_with_agent_fallback(
            question="Domanda",
            context="Contesto",
            system_prompt="Sistema",
        )


def test_answer_with_agent_fallback_raises_on_json_error_result(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout='{"type":"result","is_error":true,"result":"errore agent"}\n',
            stderr="",
        ),
    )

    with pytest.raises(fallback_module.AgentFallbackError, match="errore agent"):
        fallback_module.answer_with_agent_fallback(
            question="Domanda",
            context="Contesto",
            system_prompt="Sistema",
        )


def test_answer_with_agent_fallback_raises_on_timeout(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(fallback_module.AgentFallbackError, match="timeout"):
        fallback_module.answer_with_agent_fallback(
            question="Domanda",
            context="Contesto",
            system_prompt="Sistema",
        )


def test_answer_with_agent_fallback_raises_on_missing_cli(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(fallback_module.AgentFallbackError, match="CLI agent non trovata"):
        fallback_module.answer_with_agent_fallback(
            question="Domanda",
            context="Contesto",
            system_prompt="Sistema",
        )


def test_answer_with_agent_fallback_raises_on_empty_output(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=" \n ", stderr=""),
    )

    with pytest.raises(fallback_module.AgentFallbackError, match="alcun contenuto"):
        fallback_module.answer_with_agent_fallback(
            question="Domanda",
            context="Contesto",
            system_prompt="Sistema",
        )


def test_answer_with_agent_fallback_raises_on_oserror(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")

    def fake_run(*args, **kwargs):
        raise OSError("permessi")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(fallback_module.AgentFallbackError, match="impossibile avviare agent"):
        fallback_module.answer_with_agent_fallback(
            question="Domanda",
            context="Contesto",
            system_prompt="Sistema",
        )


def test_answer_with_agent_fallback_uses_default_timeout_on_invalid_value(monkeypatch: pytest.MonkeyPatch, fallback_module) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("WIKI_AGENT_TIMEOUT_SECONDS", "abc")

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return SimpleNamespace(returncode=0, stdout="Risposta testuale", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    fallback_module.answer_with_agent_fallback(
        question="Domanda",
        context="Contesto",
        system_prompt="Sistema",
    )

    assert captured["timeout"] == 45.0


def test_answer_with_agent_fallback_uses_default_timeout_on_non_positive_value(
    monkeypatch: pytest.MonkeyPatch,
    fallback_module,
) -> None:
    monkeypatch.setenv("WIKI_AGENT_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("WIKI_AGENT_TIMEOUT_SECONDS", "0")

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return SimpleNamespace(returncode=0, stdout="Risposta testuale", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    fallback_module.answer_with_agent_fallback(
        question="Domanda",
        context="Contesto",
        system_prompt="Sistema",
    )

    assert captured["timeout"] == 45.0
