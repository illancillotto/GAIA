import asyncio
import json
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


def test_llm_solver_returns_none_on_invalid_json() -> None:
    solver = LLMCaptchaSolver()
    proc = _make_proc(b"not json at all")

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
    assert "--output-format" in calls[0]
    prompt_arg = calls[0][-1]
    assert ".png" in prompt_arg


def test_llm_solver_from_path_skips_tempfile(tmp_path) -> None:
    solver = LLMCaptchaSolver()
    img = tmp_path / "captcha.png"
    img.write_bytes(b"fake")
    proc = _make_proc(_json_result("dumata"))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = run(solver.solve_from_path(img))

    assert result == "dumata"
