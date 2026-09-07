import sys
from pathlib import Path

WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from captcha_result import CaptchaSolveResult, as_result  # noqa: E402


def test_solved_property_tracks_text():
    assert CaptchaSolveResult("AbC123", "solved", "agent").solved is True
    assert CaptchaSolveResult(None, "codex_lb_refusal", "codex-lb").solved is False


def test_label_uses_it_table_and_appends_detail():
    assert CaptchaSolveResult(None, "codex_lb_refusal", "codex-lb").label() == "codex-lb rifiuto del modello"
    assert (
        CaptchaSolveResult(None, "codex_lb_http_error", "codex-lb", "HTTP 400 no_plan_support_for_model").label()
        == "codex-lb errore HTTP (HTTP 400 no_plan_support_for_model)"
    )


def test_label_falls_back_to_raw_reason_for_unknown_code():
    assert CaptchaSolveResult(None, "brand_new_code", "x").label() == "brand_new_code"


def test_as_result_normalizes_str_none_and_passthrough():
    assert as_result(None) == CaptchaSolveResult(None, "no_answer")
    assert as_result("  AbC123 ") == CaptchaSolveResult("AbC123", "solved")
    assert as_result("") == CaptchaSolveResult(None, "no_answer")
    already = CaptchaSolveResult("x", "solved", "agent")
    assert as_result(already) is already
