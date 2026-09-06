import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

# Standalone worker imports require WORKER_ROOT on sys.path.
from llm_captcha_solver import LLMCaptchaSolver, _PROMPT_TEMPLATE  # noqa: E402


def test_prompt_does_not_mention_captcha():
    prompt = _PROMPT_TEMPLATE.format(image_path="x.png")
    assert "captcha" not in prompt.lower()
    assert "trascrivi" in prompt.lower()


@pytest.fixture(autouse=True)
def isolate_provider_settings(monkeypatch):
    for key in list(os.environ):
        if key.startswith(("CAPTCHA_CODEX_LB_", "CODEX_LB_", "CAPTCHA_LLM_AGENT_")):
            monkeypatch.delenv(key)


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


def _completed_response(text="AbC123"):
    return {"status": "completed", "output": [
        {"type": "message", "content": [{"type": "output_text", "text": text}]}
    ]}


@pytest.mark.parametrize("stdout,exit_code", [
    (b"", 1),
    (b"", 0),
    (b"Usage limit exceeded", 0),
    (b"Error: unavailable", 0),
    (b'{"is_error":true,"result":"unavailable"}', 0),
    (b'{"type":"error","message":"unavailable"}', 0),
    (b"I cannot read the captcha image with confidence", 0),
])
def test_agent_failure_calls_gpt54_mini_with_image(monkeypatch, stdout, exit_code):
    import base64

    monkeypatch.setenv("CODEX_LB_API_KEY", "test-key")
    monkeypatch.setenv("CODEX_LB_URL", "http://host.docker.internal:2455/v1/")
    captured = []

    async def respond(request):
        captured.append(request)
        return httpx.Response(200, json=_completed_response())

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=_make_proc(stdout, exit_code))),
        patch("llm_captcha_solver.httpx.AsyncClient", return_value=client),
    ):
        assert run(LLMCaptchaSolver().solve(b"image-content")) == "AbC123"
    request = captured[0]
    assert str(request.url) == "http://host.docker.internal:2455/v1/responses"
    assert request.headers["Authorization"] == "Bearer test-key"
    payload = json.loads(request.content)
    assert payload["model"] == "gpt-5.4-mini"
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["store"] is False
    assert payload["stream"] is False
    image = payload["input"][0]["content"][1]
    assert base64.b64decode(image["image_url"].split(",")[1]) == b"image-content"
    assert image["detail"] == "high"


def test_agent_success_does_not_call_codex(monkeypatch):
    monkeypatch.setenv("CODEX_LB_API_KEY", "test-key")
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=_make_proc(b"AbC123"))),
        patch("llm_captcha_solver.httpx.AsyncClient") as client,
    ):
        assert run(LLMCaptchaSolver().solve(b"image")) == "AbC123"
        client.assert_not_called()


def test_disabled_codex_does_not_call_provider(monkeypatch):
    monkeypatch.setenv("CODEX_LB_API_KEY", "test-key")
    monkeypatch.setenv("CAPTCHA_CODEX_LB_FALLBACK_ENABLED", "false")
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=FileNotFoundError)),
        patch("llm_captcha_solver.httpx.AsyncClient") as client,
    ):
        assert run(LLMCaptchaSolver().solve(b"image")) is None
        client.assert_not_called()


@pytest.mark.parametrize("failure", [
    httpx.ConnectError("unreachable"), httpx.ReadTimeout("timeout"), TimeoutError(),
    httpx.Response(401), httpx.Response(429), httpx.Response(503),
    httpx.Response(200, content=b"invalid json"),
    httpx.Response(200, json={"status": "failed", "error": {"message": "quota"}}),
    httpx.Response(200, json={"status": "incomplete"}),
    httpx.Response(200, json=["unexpected"]),
    httpx.Response(200, json=_completed_response("cannot read this")),
])
def test_codex_failure_returns_none(monkeypatch, failure):
    monkeypatch.setenv("CODEX_LB_API_KEY", "test-key")

    async def respond(request):
        if isinstance(failure, Exception):
            raise failure
        return failure

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=OSError)),
        patch("llm_captcha_solver.httpx.AsyncClient", return_value=client),
    ):
        assert run(LLMCaptchaSolver().solve(b"image")) is None


def test_codex_overrides_and_path_preserved(monkeypatch, tmp_path):
    monkeypatch.setenv("CAPTCHA_CODEX_LB_API_KEY", "dedicated")
    monkeypatch.setenv("CODEX_LB_API_KEY", "shared")
    monkeypatch.setenv("CAPTCHA_CODEX_LB_URL", "http://localhost:2455/v1")
    monkeypatch.setenv("CAPTCHA_CODEX_LB_MODEL", "test-terra")
    monkeypatch.setenv("CAPTCHA_CODEX_LB_TIMEOUT_SECONDS", "12")
    image = tmp_path / "captcha.png"
    image.write_bytes(b"image")

    async def respond(request):
        assert str(request.url) == "http://localhost:2455/v1/responses"
        assert request.headers["Authorization"] == "Bearer dedicated"
        assert json.loads(request.content)["model"] == "test-terra"
        return httpx.Response(200, json=_completed_response())

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=OSError)),
        patch("llm_captcha_solver.httpx.AsyncClient", return_value=client) as factory,
    ):
        assert run(LLMCaptchaSolver().solve_from_path(image)) == "AbC123"
        factory.assert_called_once_with(timeout=12)
    assert image.read_bytes() == b"image"


def test_codex_missing_image_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_LB_API_KEY", "test-key")
    assert run(LLMCaptchaSolver()._run_codex_lb(tmp_path / "missing.png")) is None


def test_codex_total_timeout_cancels_request(monkeypatch):
    monkeypatch.setenv("CODEX_LB_API_KEY", "test-key")
    monkeypatch.setenv("CAPTCHA_CODEX_LB_TIMEOUT_SECONDS", "0.001")
    cancelled = []

    async def respond(request):
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.append(True)

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=OSError)),
        patch("llm_captcha_solver.httpx.AsyncClient", return_value=client),
    ):
        assert run(LLMCaptchaSolver().solve(b"image")) is None
    assert cancelled == [True]


def test_codex_cancellation_propagates(monkeypatch):
    monkeypatch.setenv("CODEX_LB_API_KEY", "test-key")

    async def respond(request):
        raise asyncio.CancelledError()

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=OSError)),
        patch("llm_captcha_solver.httpx.AsyncClient", return_value=client),
        pytest.raises(asyncio.CancelledError),
    ):
        run(LLMCaptchaSolver().solve(b"image"))


@pytest.mark.parametrize("value,expected", [
    ("invalid", 45), ("0", 45), ("-1", 45), ("nan", 45), ("inf", 45), ("0.1", 0.1),
])
def test_provider_timeout_validation(monkeypatch, value, expected):
    monkeypatch.setenv("CAPTCHA_LLM_AGENT_TIMEOUT_SECONDS", value)
    assert LLMCaptchaSolver._timeout("CAPTCHA_LLM_AGENT_TIMEOUT_SECONDS") == expected


@pytest.mark.parametrize("gone,returncode", [(False, None), (True, None), (False, 0)])
def test_agent_timeout_kills_group_and_falls_back(monkeypatch, gone, returncode):
    monkeypatch.setenv("CAPTCHA_LLM_AGENT_TIMEOUT_SECONDS", "0.001")
    proc = _make_proc(b"")
    proc.returncode = returncode
    proc.pid = 12345

    async def communicate():
        if proc.communicate.await_count == 1:
            await asyncio.sleep(60)
        return b"", b""

    proc.communicate = AsyncMock(side_effect=communicate)
    solver = LLMCaptchaSolver()
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)) as spawn,
        patch("llm_captcha_solver.os.killpg", side_effect=ProcessLookupError if gone else None) as kill,
        patch.object(solver, "_run_codex_lb", AsyncMock(return_value="AbC123")) as fallback,
    ):
        assert run(solver.solve(b"image")) == "AbC123"
        assert spawn.call_args.kwargs["start_new_session"] is True
        kill.assert_called_once_with(12345, 9)
        assert proc.communicate.await_count == 2
        assert not fallback.call_args.args[0].exists()


def test_agent_cancellation_cleans_up_without_fallback():
    proc = _make_proc(b"")
    proc.returncode = None
    proc.communicate = AsyncMock(side_effect=[asyncio.CancelledError(), (b"", b"")])
    solver = LLMCaptchaSolver()
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)),
        patch("llm_captcha_solver.os.killpg") as kill,
        patch.object(solver, "_run_codex_lb", AsyncMock()) as fallback,
        pytest.raises(asyncio.CancelledError),
    ):
        run(solver.solve(b"image"))
    kill.assert_called_once()
    fallback.assert_not_called()


def test_codex_parser_skips_reasoning_refusal_and_invalid_text():
    payload = {"status": "completed", "output": [
        {"type": "reasoning"},
        {"type": "message", "content": [
            {"type": "refusal", "refusal": "cannot read"},
            {"type": "output_text", "text": ""},
            {"type": "output_text", "text": "AbC123"},
        ]},
    ]}
    assert LLMCaptchaSolver._codex_candidate(payload) == "AbC123"
    assert LLMCaptchaSolver._codex_candidate({"status": "completed"}) is None


def test_candidate_skips_punctuation_only_last_line():
    assert LLMCaptchaSolver._extract_candidate("AbC123\n!!!") == "AbC123"
