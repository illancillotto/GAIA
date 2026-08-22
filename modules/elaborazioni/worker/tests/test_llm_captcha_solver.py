import asyncio
import json
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from llm_captcha_solver import LLMCaptchaSolver


def _make_proc(stdout: bytes, returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, b""))
    return proc


def _json_result(text: str) -> bytes:
    return json.dumps({"type": "result", "result": text}).encode()


def run(coro):
    return asyncio.run(coro)


def test_llm_solver_returns_normalized_text() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(_json_result("  neorave\n"))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result == "neorave"


def test_llm_solver_preserves_lowercase() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(_json_result("solangei"))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result == "solangei"


def test_llm_solver_strips_spaces_and_punctuation() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(_json_result("neo rave!"))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result == "neorave"


def test_llm_solver_prefers_last_plausible_line_over_explanation() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(_json_result("Leggo il CAPTCHA e restituisco solo i caratteri esatti.\nsvefotta"))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result == "svefotta"


def test_llm_solver_rejects_overlong_explanatory_blob() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(_json_result("Leggo l'immagine CAPTCHA e ti restituisco solo i caratteri esatti"))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result is None


def test_llm_solver_returns_none_on_empty_result() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(_json_result(""))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result is None


def test_llm_solver_returns_none_on_nonzero_exit() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(b"", returncode=1)

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result is None


def test_llm_solver_returns_none_on_explanatory_plain_text() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(b"I cannot read the captcha image with confidence")

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result is None


def test_llm_solver_returns_none_on_subprocess_exception() -> None:
    solver = LLMCaptchaSolver()

    with patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=OSError("agent not found"))):
        result = run(solver.solve(b"fake-image"))

    assert result is None


def test_llm_solver_passes_image_path_in_prompt() -> None:
    solver = LLMCaptchaSolver(agent_cmd="myagent")
    proc = _make_proc(_json_result("zinurvt"))
    calls: list = []

    async def fake_exec(*args, **kwargs):
        calls.append(args)
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        run(solver.solve(b"fake-image"))

    assert calls[0][0] == "myagent"
    assert "--print" in calls[0]
    assert "--model" in calls[0]
    assert "auto" in calls[0]
    assert "--output-format" in calls[0]
    prompt_arg = calls[0][-1]
    assert ".png" in prompt_arg


def test_llm_solver_accepts_plain_text_agent_output() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(b"pitepade\n")

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve(b"fake-image"))

    assert result == "pitepade"


def test_llm_solver_loads_cursor_auth_token_from_file(tmp_path, monkeypatch) -> None:
    token_file = tmp_path / "auth.json"
    token_file.write_text(json.dumps({"accessToken": "secret-token"}))
    monkeypatch.setenv("CURSOR_AUTH_TOKEN_FILE", str(token_file))
    monkeypatch.delenv("CURSOR_AUTH_TOKEN", raising=False)
    solver = LLMCaptchaSolver(agent_cmd="agent")
    proc = _make_proc(b"roneota\n")
    captured_env: dict[str, str] = {}

    async def fake_exec(*args, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        result = run(solver.solve(b"fake-image"))

    assert result == "roneota"
    assert captured_env["CURSOR_AUTH_TOKEN"] == "secret-token"
    assert captured_env["HOME"] == os.environ.get("HOME", "")


def test_llm_solver_does_not_override_existing_cursor_auth_token(tmp_path, monkeypatch) -> None:
    token_file = tmp_path / "auth.json"
    token_file.write_text(json.dumps({"accessToken": "file-token"}))
    monkeypatch.setenv("CURSOR_AUTH_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("CURSOR_AUTH_TOKEN", "env-token")
    solver = LLMCaptchaSolver(agent_cmd="agent")
    proc = _make_proc(b"solangei\n")
    captured_env: dict[str, str] = {}

    async def fake_exec(*args, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        result = run(solver.solve(b"fake-image"))

    assert result == "solangei"
    assert captured_env["CURSOR_AUTH_TOKEN"] == "env-token"


def test_llm_solver_uses_refresh_token_fallback(tmp_path, monkeypatch) -> None:
    token_file = tmp_path / "auth.json"
    token_file.write_text(json.dumps({"refreshToken": "refresh-token"}))
    monkeypatch.setenv("CURSOR_AUTH_TOKEN_FILE", str(token_file))
    monkeypatch.delenv("CURSOR_AUTH_TOKEN", raising=False)
    solver = LLMCaptchaSolver(agent_cmd="agent")
    proc = _make_proc(b"neorave\n")
    captured_env: dict[str, str] = {}

    async def fake_exec(*args, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        result = run(solver.solve(b"fake-image"))

    assert result == "neorave"
    assert captured_env["CURSOR_AUTH_TOKEN"] == "refresh-token"


def test_llm_solver_ignores_unreadable_cursor_auth_token_file(tmp_path, monkeypatch) -> None:
    token_file = tmp_path / "missing-auth.json"
    monkeypatch.setenv("CURSOR_AUTH_TOKEN_FILE", str(token_file))
    monkeypatch.delenv("CURSOR_AUTH_TOKEN", raising=False)
    solver = LLMCaptchaSolver(agent_cmd="agent")
    proc = _make_proc(b"dumata\n")
    captured_env: dict[str, str] = {}

    async def fake_exec(*args, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return proc

    with patch("asyncio.create_subprocess_exec", fake_exec):
        result = run(solver.solve(b"fake-image"))

    assert result == "dumata"
    assert "CURSOR_AUTH_TOKEN" not in captured_env


def test_llm_solver_decodes_json_text_message_and_list() -> None:
    assert LLMCaptchaSolver._decode_agent_stdout(json.dumps({"text": "abc123"}).encode()) == "abc123"
    assert LLMCaptchaSolver._decode_agent_stdout(json.dumps({"message": "xyz789"}).encode()) == "xyz789"
    assert LLMCaptchaSolver._decode_agent_stdout(json.dumps(["list-value"]).encode()) == "['list-value']"


def test_llm_solver_extract_candidate_from_last_token_when_line_has_punctuation() -> None:
    assert LLMCaptchaSolver._extract_candidate("candidate: neo-rave") == "rave"


def test_llm_solver_decodes_empty_stdout() -> None:
    assert LLMCaptchaSolver._decode_agent_stdout(b"   \n") == ""


def test_llm_solver_extract_candidate_branches() -> None:
    assert LLMCaptchaSolver._extract_candidate("!!!\nabc123") == "abc123"
    assert LLMCaptchaSolver._extract_candidate("abc123 is-readable") == "readable"
    assert LLMCaptchaSolver._extract_candidate("a b c 1 2 3") == "abc123"


def test_llm_solver_from_path_skips_tempfile(tmp_path) -> None:
    solver = LLMCaptchaSolver()
    img = tmp_path / "captcha.png"
    img.write_bytes(b"fake")
    proc = _make_proc(_json_result("dumata"))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve_from_path(img))

    assert result == "dumata"
